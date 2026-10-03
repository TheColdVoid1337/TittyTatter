from __future__ import annotations

import copy
import math
import threading
from collections import deque
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import sounddevice as sd

from model import BarPattern
from presets import OFF, TA, TI
from training_modes import (
    GAP_MODES,
    RAMP_MODES,
    displaced_click_spec,
    gap_phase,
    ramp_stages,
    sparse_click_matches,
)

SOUND_NAMES = (
    "Wood",
    "Low tick",
    "Clap",
    "Click",
    "Beep",
    "Bell",
    "Clave",
    "Glass",
    "Kick",
    "Tom",
    "Voice TI",
    "Voice TA",
)


@dataclass(frozen=True)
class EngineConfig:
    bpm: float = 60.0
    master_volume: float = 1.0
    ti_enabled: bool = True
    ti_sound: str = "Wood"
    ti_volume: float = 1.0
    ta_enabled: bool = True
    ta_sound: str = "Low tick"
    ta_volume: float = 0.7
    metronome_enabled: bool = True
    metronome_volume: float = 0.7
    accent_first_beat: bool = True
    practice_mode: str = "loop"
    bars_per_stage: int = 8
    count_in_bars: int = 1
    inactive_pulse: bool = True
    tempo_trainer_enabled: bool = False
    tempo_step: int = 2
    tempo_every_bars: int = 4
    tempo_target: int = 140
    gap_play_bars: int = 4
    gap_silent_bars: int = 2
    progressive_gap_max_silent_bars: int = 4
    sparse_click_pattern: str = "beat_1"
    displaced_click: str = "eighth_and"


class AudioEngine:
    """Low-latency audio-callback metronome/rhythm engine."""

    def __init__(self, sample_rate: float | None = None, blocksize: int = 0) -> None:
        self.device_index, device, self.host_api_name = self._select_output_device()
        self.device_name = str(device.get("name", "unknown")) if device else "unknown"
        self.device_low_latency = float(device.get("default_low_output_latency", 0.0)) if device else 0.0
        self.latency_mode: str = "low"
        self.exclusive_mode = False

        if sample_rate is None:
            sample_rate = float(device.get("default_samplerate", 48_000.0)) if device else 48_000.0
        self.sample_rate = float(sample_rate)
        self.blocksize = int(blocksize)
        max_channels = int(device.get("max_output_channels", 2)) if device else 2
        self.channels = 2 if max_channels >= 2 else 1

        self._stream: sd.OutputStream | None = None
        self._config = EngineConfig()
        self._pattern = BarPattern()
        self._pattern.normalize()
        self._coverage = self._pattern.coverage()
        self._running = False

        self._sample_cursor = 0
        self._next_event_sample = 0.0
        self._beat_index = 0
        self._sub_index = 0
        self._bar_number = 0
        self._stage_index = 0
        self._stage_bar = 0
        self._count_in_beats_left = 0
        self._count_in_total_beats = 0
        self._practice_started_sample: float | None = None

        self._visual_beat = 0
        self._visual_sub = 0
        self._visual_beat_start = 0.0
        self._visual_beat_samples = self.sample_rate

        self._active_voices: list[tuple[np.ndarray, int, float]] = []
        self._last_error = ""
        self._game_tracking = False
        self._game_targets: deque[tuple[float, str, int, int, int]] = deque(maxlen=512)
        self._notification_queue: deque[tuple[str, float]] = deque(maxlen=64)
        self._sounds = self._build_sounds()

    @staticmethod
    def _select_output_device() -> tuple[int | None, dict[str, Any] | None, str]:
        """Prefer the Windows WASAPI default endpoint, then fall back to PortAudio default."""
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()

            for host in hostapis:
                host_name = str(host.get("name", ""))
                if "WASAPI" not in host_name.upper():
                    continue
                device_index = int(host.get("default_output_device", -1))
                if 0 <= device_index < len(devices):
                    device = dict(devices[device_index])
                    if int(device.get("max_output_channels", 0)) > 0:
                        return device_index, device, host_name

            default_index = int(sd.default.device[1])
            if 0 <= default_index < len(devices):
                device = dict(devices[default_index])
                host_index = int(device.get("hostapi", -1))
                host_name = (
                    str(hostapis[host_index].get("name", "unknown"))
                    if 0 <= host_index < len(hostapis)
                    else "unknown"
                )
                return default_index, device, host_name

            device = dict(sd.query_devices(kind="output"))
            return int(device.get("index", -1)), device, "default"
        except Exception:
            return None, None, "unknown"

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def list_output_devices() -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            for index, device in enumerate(devices):
                if int(device.get("max_output_channels", 0)) <= 0:
                    continue
                host_index = int(device.get("hostapi", -1))
                host_name = (
                    str(hostapis[host_index].get("name", "unknown"))
                    if 0 <= host_index < len(hostapis)
                    else "unknown"
                )
                result.append({
                    "index": index,
                    "name": str(device.get("name", f"Device {index}")),
                    "host_api": host_name,
                    "sample_rate": float(device.get("default_samplerate", 48_000.0)),
                    "low_latency": float(device.get("default_low_output_latency", 0.0)),
                    "high_latency": float(device.get("default_high_output_latency", 0.0)),
                    "max_channels": int(device.get("max_output_channels", 0)),
                })
        except Exception:
            pass
        return result

    def configure_output(
        self,
        *,
        device_index: int | None = None,
        sample_rate: float | None = None,
        blocksize: int | None = None,
        latency_mode: str | None = None,
        exclusive: bool | None = None,
    ) -> None:
        if self._running:
            raise RuntimeError("Stop playback before changing audio device settings.")

        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        if device_index is not None:
            device_index = int(device_index)
            if device_index < 0 or device_index >= len(devices):
                raise ValueError("Selected audio device is not available.")
            device = dict(devices[device_index])
            if int(device.get("max_output_channels", 0)) <= 0:
                raise ValueError("Selected device has no output channels.")
            self.device_index = device_index
            self.device_name = str(device.get("name", "unknown"))
            host_index = int(device.get("hostapi", -1))
            self.host_api_name = (
                str(hostapis[host_index].get("name", "unknown"))
                if 0 <= host_index < len(hostapis)
                else "unknown"
            )
            self.device_low_latency = float(device.get("default_low_output_latency", 0.0))
            self.channels = 2 if int(device.get("max_output_channels", 1)) >= 2 else 1
            if sample_rate is None or float(sample_rate) <= 0:
                sample_rate = float(device.get("default_samplerate", self.sample_rate))

        if sample_rate is not None and float(sample_rate) > 0:
            new_rate = float(sample_rate)
            if abs(new_rate - self.sample_rate) > 0.5:
                self.sample_rate = new_rate
                self._visual_beat_samples = self.sample_rate
                # Same sound definitions, rebuilt only for the selected sample rate.
                self._sounds = self._build_sounds()

        if blocksize is not None:
            self.blocksize = max(0, int(blocksize))
        if latency_mode is not None:
            self.latency_mode = "high" if str(latency_mode).lower() == "high" else "low"
        if exclusive is not None:
            self.exclusive_mode = bool(exclusive)

    def start_game_tracking(self) -> None:
        self._game_targets.clear()
        self._game_tracking = True

    def stop_game_tracking(self) -> None:
        self._game_tracking = False
        self._game_targets.clear()

    def drain_game_targets(self) -> list[tuple[float, str, int, int, int]]:
        items = list(self._game_targets)
        self._game_targets.clear()
        return items

    def stream_time(self) -> float:
        stream = self._stream
        if stream is None:
            return 0.0
        try:
            return float(stream.time)
        except Exception:
            return 0.0

    def queue_notification(self, key: str, gain: float = 0.8) -> None:
        """Queue a short UI/game cue into the realtime output stream."""
        if key not in self._sounds:
            return
        self._notification_queue.append((key, float(gain)))

    def play_notification(self, sound_name: str = "Finish horn", gain: float = 0.9) -> None:
        """Play a one-shot cue reliably after the main realtime stream has stopped."""
        key = {
            "Finish horn": "finish_horn",
            "Bell": "bell",
            "Ramp warning": "ramp_warn",
            "Game hit": "game_hit",
            "Game miss": "game_miss",
        }.get(sound_name, self._sound_key(sound_name))
        wave = self._sounds.get(key)
        if wave is None:
            return
        payload = (wave * float(gain)).astype(np.float32, copy=True)

        def worker() -> None:
            try:
                if self.channels == 1:
                    data = payload[:, None]
                else:
                    data = np.repeat(payload[:, None], self.channels, axis=1)
                with sd.OutputStream(
                    device=self.device_index,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    blocksize=0,
                    latency=self.latency_mode,
                ) as stream:
                    stream.write(data)
            except Exception:
                pass

        threading.Thread(target=worker, name="TittyTatterNotification", daemon=True).start()

    def set_pattern(self, pattern: BarPattern) -> None:
        new_pattern = copy.deepcopy(pattern)
        new_pattern.normalize()
        self._pattern = new_pattern
        self._coverage = new_pattern.coverage()

    def set_config(self, **kwargs: Any) -> None:
        valid = {k: v for k, v in kwargs.items() if hasattr(self._config, k)}
        if "bpm" in valid:
            valid["bpm"] = float(max(20.0, min(320.0, valid["bpm"])))
        self._config = replace(self._config, **valid)

    def get_config(self) -> EngineConfig:
        return self._config

    def sound_wave(self, name: str) -> np.ndarray:
        return self._sounds[self._sound_key(name)]

    def start(self) -> None:
        if self._running:
            return

        self._sample_cursor = 0
        self._next_event_sample = 0.0
        self._beat_index = 0
        self._sub_index = 0
        self._bar_number = 0
        self._stage_index = 0
        self._stage_bar = 0
        self._count_in_total_beats = max(0, int(self._config.count_in_bars)) * self._pattern.numerator
        self._count_in_beats_left = self._count_in_total_beats
        self._practice_started_sample = None
        self._visual_beat = 0
        self._visual_sub = 0
        self._visual_beat_start = 0.0
        self._active_voices.clear()
        self._notification_queue.clear()
        self._last_error = ""

        extra_settings = None
        if self.exclusive_mode and "WASAPI" in self.host_api_name.upper():
            try:
                extra_settings = sd.WasapiSettings(exclusive=True)
            except Exception:
                extra_settings = None

        self._stream = sd.OutputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            latency=self.latency_mode,
            extra_settings=extra_settings,
            callback=self._audio_callback,
            prime_output_buffers_using_stream_callback=True,
        )
        self._stream.start()
        self._running = True

    def stop(self) -> None:
        self._running = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self._active_voices.clear()

    def close(self) -> None:
        self.stop()

    def status(self) -> dict[str, Any]:
        cfg = self._config
        mode = cfg.practice_mode
        stages = ramp_stages(mode, self._pattern.numerator)
        stage_index = self._stage_index % len(stages)
        active_beats = stages[stage_index] if mode in RAMP_MODES else self._pattern.numerator
        next_active_beats = (
            stages[(stage_index + 1) % len(stages)]
            if mode in RAMP_MODES and len(stages) > 1
            else active_beats
        )

        gap = None
        if mode in GAP_MODES:
            gap = gap_phase(
                mode,
                self._bar_number,
                play_bars=cfg.gap_play_bars,
                silent_bars=cfg.gap_silent_bars,
                progressive_max_silent_bars=cfg.progressive_gap_max_silent_bars,
            )

        beat_samples = max(1.0, self._visual_beat_samples)
        phase = (self._sample_cursor - self._visual_beat_start) / beat_samples
        phase = float(max(0.0, min(0.999, phase)))

        if self._practice_started_sample is None:
            practice_elapsed = 0.0
        else:
            practice_elapsed = max(
                0.0,
                (self._sample_cursor - self._practice_started_sample) / self.sample_rate,
            )

        return {
            "running": self._running,
            "bpm": cfg.bpm,
            "beat": self._visual_beat,
            "sub": self._visual_sub,
            "beat_phase": phase,
            "bar": self._bar_number + 1,
            "training_mode": mode,
            "stage_index": stage_index,
            "stage_count": len(stages) if mode in RAMP_MODES else 1,
            "stage_bar": self._stage_bar + 1,
            "bars_per_stage": max(1, int(cfg.bars_per_stage)),
            "active_beats": active_beats,
            "next_active_beats": next_active_beats,
            "training_silent": bool(gap.silent) if gap is not None else False,
            "gap_segment_bar": gap.segment_bar if gap is not None else 0,
            "gap_segment_bars": gap.segment_bars if gap is not None else 0,
            "gap_cycle_bar": gap.cycle_bar if gap is not None else 0,
            "gap_cycle_bars": gap.cycle_bars if gap is not None else 0,
            "gap_silent_bars": gap.silent_bars if gap is not None else 0,
            "gap_stage_index": gap.stage_index if gap is not None else 0,
            "gap_stage_count": gap.stage_count if gap is not None else 1,
            "sparse_click_pattern": cfg.sparse_click_pattern,
            "displaced_click": cfg.displaced_click,
            "count_in": self._count_in_beats_left > 0,
            "count_in_beat": self._count_in_total_beats - self._count_in_beats_left,
            "numerator": self._pattern.numerator,
            "denominator": self._pattern.denominator,
            "practice_elapsed_seconds": practice_elapsed,
            "last_error": self._last_error,
        }

    def stream_info(self) -> dict[str, Any]:
        result = {
            "device_index": self.device_index,
            "device_name": self.device_name,
            "host_api": self.host_api_name,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "blocksize": self.blocksize,
            "latency_mode": self.latency_mode,
            "exclusive": self.exclusive_mode,
            "device_low_latency": self.device_low_latency,
        }
        if self._stream is not None:
            try:
                result["latency"] = self._stream.latency
            except Exception:
                pass
        return result

    def _audio_callback(self, outdata: np.ndarray, frames: int, _time: Any, status: Any) -> None:
        if status:
            self._last_error = str(status)

        mono = np.zeros(frames, dtype=np.float32)
        block_start = self._sample_cursor
        block_end = block_start + frames

        kept: list[tuple[np.ndarray, int, float]] = []
        for wave, pos, gain in self._active_voices:
            n = min(frames, len(wave) - pos)
            if n > 0:
                mono[:n] += wave[pos : pos + n] * gain
                pos += n
            if pos < len(wave):
                kept.append((wave, pos, gain))
        self._active_voices = kept

        while self._notification_queue:
            key, gain = self._notification_queue.popleft()
            wave = self._sounds.get(key)
            if wave is not None:
                self._mix_sound(mono, 0, wave, gain)

        safety = 0
        while self._next_event_sample < block_end and safety < 256:
            safety += 1
            event_sample = self._next_event_sample
            offset = max(0, int(round(event_sample - block_start)))
            sounds, interval, game_target = self._event(event_sample)
            for wave, gain in sounds:
                self._mix_sound(mono, offset, wave, gain)
            if self._game_tracking and game_target is not None:
                state, bar_number, beat_index, sub_index = game_target
                try:
                    dac_time = float(_time.outputBufferDacTime) + offset / self.sample_rate
                    self._game_targets.append((dac_time, state, bar_number, beat_index, sub_index))
                except Exception:
                    pass
            self._next_event_sample += max(1.0, interval)

        self._sample_cursor = block_end
        mono *= float(self._config.master_volume)
        np.clip(mono, -0.995, 0.995, out=mono)

        if self.channels == 1:
            outdata[:, 0] = mono
        else:
            outdata[:] = mono[:, None]

    def _event(
        self,
        event_sample: float,
    ) -> tuple[list[tuple[np.ndarray, float]], float, tuple[str, int, int, int] | None]:
        cfg = self._config
        pattern = self._pattern
        beat_samples = (
            self.sample_rate
            * 60.0
            / max(20.0, cfg.bpm)
            * 4.0
            / max(1, pattern.denominator)
        )
        sounds: list[tuple[np.ndarray, float]] = []

        if self._count_in_beats_left > 0:
            idx = self._count_in_total_beats - self._count_in_beats_left
            beat = idx % pattern.numerator
            self._set_visual_event(beat, 0, event_sample, beat_samples)
            if cfg.metronome_enabled:
                key = "metro_accent" if beat == 0 and cfg.accent_first_beat else "metro"
                sounds.append((self._sounds[key], float(cfg.metronome_volume)))
            self._count_in_beats_left -= 1
            if self._count_in_beats_left == 0:
                self._beat_index = 0
                self._sub_index = 0
            return sounds, beat_samples, None

        if self._practice_started_sample is None:
            self._practice_started_sample = event_sample

        mode = cfg.practice_mode
        stages = ramp_stages(mode, pattern.numerator)
        active_beats = (
            stages[self._stage_index % len(stages)]
            if mode in RAMP_MODES
            else pattern.numerator
        )

        gap = None
        if mode in GAP_MODES:
            gap = gap_phase(
                mode,
                self._bar_number,
                play_bars=cfg.gap_play_bars,
                silent_bars=cfg.gap_silent_bars,
                progressive_max_silent_bars=cfg.progressive_gap_max_silent_bars,
            )
        training_silent = bool(gap.silent) if gap is not None else False

        owner = self._coverage[self._beat_index]
        owner_index = self._beat_index if owner is None else owner
        owner_def = pattern.beats[owner_index]
        beat_muted = bool(owner_def.muted)

        covered_by_active_note = (
            owner is not None
            and owner != self._beat_index
            and owner < active_beats
        )
        beat_active = self._beat_index < active_beats
        beat_def = pattern.beats[self._beat_index]

        if covered_by_active_note:
            pattern_subdivision = 1
            base_state = OFF
            base_logical_state = OFF
        elif beat_active:
            pattern_subdivision = max(1, beat_def.subdivision)
            base_state = None
            base_logical_state = None
        else:
            # Ramp inactive beats remain logical TA targets even if the audible
            # pulse is disabled. This keeps Game semantics identical to guitar
            # training semantics.
            pattern_subdivision = 1
            base_logical_state = TA
            base_state = TA if cfg.inactive_pulse else OFF

        metro_division = 1
        displaced_slot = 0
        if mode == "displaced_click":
            metro_division, displaced_slot = displaced_click_spec(cfg.displaced_click)

        ticks_per_beat = math.lcm(pattern_subdivision, metro_division)
        tick_index = self._sub_index
        pattern_stride = ticks_per_beat // pattern_subdivision
        pattern_event = tick_index % pattern_stride == 0
        pattern_sub_index = tick_index // pattern_stride if pattern_event else None

        state = OFF
        logical_state = OFF
        if pattern_event:
            if base_state is None:
                state = beat_def.steps[int(pattern_sub_index)]
                logical_state = state
            else:
                state = base_state
                logical_state = base_logical_state

        if tick_index == 0:
            self._visual_beat_start = event_sample
            self._visual_beat_samples = beat_samples

        if pattern_event:
            self._set_visual_event(
                self._beat_index,
                int(pattern_sub_index),
                self._visual_beat_start,
                beat_samples,
            )

        metronome_hit = False
        if cfg.metronome_enabled and not beat_muted and not training_silent:
            if mode == "displaced_click":
                metro_stride = ticks_per_beat // metro_division
                metronome_hit = tick_index == displaced_slot * metro_stride
            elif mode == "sparse_click":
                metronome_hit = (
                    tick_index == 0
                    and sparse_click_matches(
                        cfg.sparse_click_pattern,
                        self._bar_number,
                        self._beat_index,
                    )
                )
            else:
                metronome_hit = tick_index == 0

        if metronome_hit:
            key = (
                "metro_accent"
                if self._beat_index == 0 and cfg.accent_first_beat
                else "metro"
            )
            sounds.append((self._sounds[key], float(cfg.metronome_volume)))

        if not beat_muted and not training_silent and pattern_event:
            if state == TI and cfg.ti_enabled:
                sounds.append(
                    (self._sounds[self._sound_key(cfg.ti_sound)], float(cfg.ti_volume))
                )
            elif state == TA and cfg.ta_enabled:
                sounds.append(
                    (self._sounds[self._sound_key(cfg.ta_sound)], float(cfg.ta_volume))
                )

        game_target = None
        if not beat_muted and pattern_event and logical_state in (TI, TA):
            game_target = (
                logical_state,
                self._bar_number,
                self._beat_index,
                int(pattern_sub_index),
            )

        interval = beat_samples / ticks_per_beat
        self._sub_index += 1
        if self._sub_index >= ticks_per_beat:
            self._sub_index = 0
            self._beat_index += 1
            if self._beat_index >= pattern.numerator:
                self._beat_index = 0
                self._on_bar_boundary(cfg)
        return sounds, interval, game_target

    def _set_visual_event(self, beat: int, sub: int, beat_start: float, beat_samples: float) -> None:
        self._visual_beat = int(beat)
        self._visual_sub = int(sub)
        self._visual_beat_start = float(beat_start)
        self._visual_beat_samples = float(beat_samples)

    def _on_bar_boundary(self, cfg: EngineConfig) -> None:
        self._bar_number += 1
        self._stage_bar += 1

        if cfg.tempo_trainer_enabled and cfg.tempo_every_bars > 0:
            if self._bar_number % cfg.tempo_every_bars == 0:
                current = cfg.bpm
                target = float(cfg.tempo_target)
                step = abs(float(cfg.tempo_step))
                if current < target:
                    new_bpm = min(target, current + step)
                elif current > target:
                    new_bpm = max(target, current - step)
                else:
                    new_bpm = current
                if new_bpm != current:
                    self._config = replace(self._config, bpm=new_bpm)
                    cfg = self._config

        if cfg.practice_mode in RAMP_MODES:
            stages = ramp_stages(cfg.practice_mode, self._pattern.numerator)
            if self._stage_bar >= max(1, cfg.bars_per_stage):
                self._stage_bar = 0
                self._stage_index = (self._stage_index + 1) % len(stages)
        else:
            # Stage counters are reserved for the legacy beat-ramp modes.
            self._stage_bar = 0
            self._stage_index = 0

    @staticmethod
    def _stages(mode: str, numerator: int) -> tuple[int, ...]:
        return ramp_stages(mode, numerator)

    def _mix_sound(self, block: np.ndarray, offset: int, wave: np.ndarray, gain: float) -> None:
        if offset >= len(block):
            self._active_voices.append((wave, 0, gain))
            return
        n = min(len(wave), len(block) - offset)
        if n > 0:
            block[offset : offset + n] += wave[:n] * gain
        if n < len(wave):
            self._active_voices.append((wave, n, gain))

    def _build_sounds(self) -> dict[str, np.ndarray]:
        sr = self.sample_rate
        rng = np.random.default_rng(20260929)

        def env(n: int, decay: float) -> np.ndarray:
            t = np.arange(n, dtype=np.float32) / sr
            return np.exp(-t / decay).astype(np.float32)

        def tone(freq: float, dur: float, decay: float, amp: float = 1.0) -> np.ndarray:
            n = max(1, int(sr * dur))
            t = np.arange(n, dtype=np.float32) / sr
            return (amp * np.sin(2 * np.pi * freq * t) * env(n, decay)).astype(np.float32)

        def mix_layers(*waves: np.ndarray) -> np.ndarray:
            if not waves:
                return np.zeros(1, dtype=np.float32)
            length = max(len(wave) for wave in waves)
            mixed = np.zeros(length, dtype=np.float32)
            for wave in waves:
                mixed[: len(wave)] += wave
            return mixed

        def normalize(wave: np.ndarray, peak: float = 0.52) -> np.ndarray:
            wave = wave.astype(np.float32, copy=True)
            m = float(np.max(np.abs(wave))) if len(wave) else 0.0
            if m > 1e-9:
                wave *= peak / m
            fade = min(len(wave), max(8, int(sr * 0.003)))
            if fade > 1:
                wave[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
            return wave

        def voice_sound(kind: str) -> np.ndarray:
            dur = 0.115 if kind == "TI" else 0.145
            n = int(sr * dur)
            t = np.arange(n, dtype=np.float32) / sr
            f0 = 205.0 if kind == "TI" else 155.0
            voiced = np.sin(2 * np.pi * f0 * t)
            voiced += 0.35 * np.sin(2 * np.pi * 2 * f0 * t)
            voiced += 0.15 * np.sin(2 * np.pi * 3 * f0 * t)
            if kind == "TI":
                formant = 0.20 * np.sin(2 * np.pi * 2250 * t) + 0.10 * np.sin(2 * np.pi * 3000 * t)
                consonant = rng.normal(0.0, 1.0, n).astype(np.float32) * np.exp(-t / 0.008)
                wave = (voiced + formant) * np.exp(-t / 0.052) + 0.14 * consonant
            else:
                formant = 0.24 * np.sin(2 * np.pi * 730 * t) + 0.16 * np.sin(2 * np.pi * 1090 * t)
                wave = (voiced + formant) * np.exp(-t / 0.075)
            return normalize(wave, 0.50)

        # A hand-clap-like sound: mid-band noise bursts plus a short body resonance.
        clap_n = int(sr * 0.115)
        white = rng.normal(0.0, 1.0, clap_n).astype(np.float32)
        kernel = np.ones(11, dtype=np.float32) / 11.0
        smooth = np.convolve(white, kernel, mode="same").astype(np.float32)
        clap = np.zeros(clap_n, dtype=np.float32)
        for delay_ms, gain, decay in ((0, 1.0, 0.019), (17, 0.72, 0.020), (34, 0.48, 0.024)):
            start = int(sr * delay_ms / 1000.0)
            n = clap_n - start
            if n > 0:
                clap[start:] += smooth[:n] * env(n, decay) * gain
        clap = mix_layers(clap, tone(760, 0.070, 0.022, 0.45), tone(1180, 0.050, 0.015, 0.28))
        clap = normalize(clap, 0.52)

        wood = normalize(mix_layers(
            tone(900, 0.060, 0.018, 1.0),
            tone(1450, 0.060, 0.012, 0.55),
        ), 0.50)

        click = normalize(mix_layers(
            tone(2600, 0.020, 0.0045, 1.0),
            tone(3900, 0.015, 0.0035, 0.35),
        ), 0.50)

        beep = normalize(tone(1150, 0.055, 0.028, 1.0), 0.50)

        muted_n = int(sr * 0.035)
        muted = rng.normal(0.0, 1.0, muted_n).astype(np.float32) * env(muted_n, 0.007)
        muted += tone(210, 0.035, 0.010, 0.65)
        low_tick = normalize(muted, 0.45)

        bell = normalize(mix_layers(
            tone(1760, 0.170, 0.070, 1.0),
            tone(2640, 0.150, 0.052, 0.52),
            tone(4070, 0.120, 0.040, 0.24),
        ), 0.50)

        clave = normalize(mix_layers(
            tone(1280, 0.045, 0.012, 1.0),
            tone(2440, 0.032, 0.007, 0.40),
        ), 0.50)

        glass = normalize(mix_layers(
            tone(1420, 0.120, 0.045, 1.0),
            tone(2190, 0.100, 0.035, 0.48),
            tone(3310, 0.080, 0.026, 0.26),
        ), 0.48)

        kick_n = int(sr * 0.120)
        kt = np.arange(kick_n, dtype=np.float32) / sr
        phase = 2 * np.pi * (58 * kt + 50 * 0.018 * (1 - np.exp(-kt / 0.018)))
        kick = np.sin(phase).astype(np.float32) * np.exp(-kt / 0.050)
        kick = normalize(kick, 0.50)

        tom = normalize(mix_layers(
            tone(170, 0.120, 0.050, 1.0),
            tone(255, 0.095, 0.035, 0.42),
        ), 0.48)

        voice_ti = voice_sound("TI")
        voice_ta = voice_sound("TA")

        metro = normalize(mix_layers(
            tone(1800, 0.030, 0.006, 1.0),
            tone(2850, 0.020, 0.004, 0.42),
        ), 0.48)
        metro_accent = normalize(mix_layers(
            tone(2550, 0.040, 0.008, 1.0),
            tone(3800, 0.025, 0.005, 0.50),
        ), 0.55)

        game_hit = normalize(mix_layers(
            tone(880, 0.065, 0.022, 0.85),
            tone(1320, 0.075, 0.028, 0.55),
        ), 0.42)

        game_miss = normalize(mix_layers(
            tone(155, 0.090, 0.032, 1.0),
            tone(118, 0.110, 0.042, 0.55),
        ), 0.42)

        ramp_warn = normalize(mix_layers(
            tone(660, 0.105, 0.040, 0.70),
            tone(990, 0.125, 0.052, 0.48),
        ), 0.44)

        horn_dur = 1.05
        horn_n = max(1, int(sr * horn_dur))
        horn_t = np.arange(horn_n, dtype=np.float32) / sr
        horn_gate = np.zeros(horn_n, dtype=np.float32)
        for start_s, end_s in ((0.00, 0.34), (0.44, 0.98)):
            start = int(start_s * sr)
            end = min(horn_n, int(end_s * sr))
            if end > start:
                local = np.linspace(0.0, 1.0, end - start, dtype=np.float32)
                attack = np.minimum(1.0, local * 18.0)
                release = np.minimum(1.0, (1.0 - local) * 10.0)
                horn_gate[start:end] = np.minimum(attack, release)
        vibrato = 1.0 + 0.006 * np.sin(2 * np.pi * 5.2 * horn_t)
        horn = np.zeros(horn_n, dtype=np.float32)
        for base, amp in ((196.0, 0.70), (246.94, 0.52), (293.66, 0.44)):
            phase = 2 * np.pi * base * horn_t * vibrato
            horn += amp * np.sin(phase)
            horn += amp * 0.28 * np.sin(2 * phase)
            horn += amp * 0.12 * np.sin(3 * phase)
        finish_horn = normalize(horn * horn_gate, 0.58)

        return {
            "wood": wood,
            "low_tick": low_tick,
            "clap": clap,
            "click": click,
            "beep": beep,
            "bell": bell,
            "clave": clave,
            "glass": glass,
            "kick": kick,
            "tom": tom,
            "voice_ti": voice_ti,
            "voice_ta": voice_ta,
            "metro": metro,
            "metro_accent": metro_accent,
            "game_hit": game_hit,
            "game_miss": game_miss,
            "ramp_warn": ramp_warn,
            "finish_horn": finish_horn,
        }

    @staticmethod
    def _sound_key(name: str) -> str:
        return {
            "Wood": "wood",
            "Low tick": "low_tick",
            "Clap": "clap",
            "Click": "click",
            "Beep": "beep",
            "Bell": "bell",
            "Clave": "clave",
            "Glass": "glass",
            "Kick": "kick",
            "Tom": "tom",
            "Voice TI": "voice_ti",
            "Voice TA": "voice_ta",
        }.get(name, "wood")
