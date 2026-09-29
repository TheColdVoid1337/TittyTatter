from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import sounddevice as sd

from model import BarPattern
from presets import OFF, TA, TI


@dataclass(frozen=True)
class EngineConfig:
    bpm: float = 60.0
    master_volume: float = 1.0
    ti_enabled: bool = True
    ti_sound: str = "Clap"
    ti_volume: float = 1.0
    ta_enabled: bool = False
    ta_sound: str = "Muted click"
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


class AudioEngine:
    """Low-latency audio-callback metronome/rhythm engine."""

    def __init__(self, sample_rate: float | None = None, blocksize: int = 0) -> None:
        device = self._query_default_output()
        if sample_rate is None:
            sample_rate = float(device.get("default_samplerate", 48_000.0)) if device else 48_000.0
        self.sample_rate = float(sample_rate)
        self.blocksize = int(blocksize)
        max_channels = int(device.get("max_output_channels", 2)) if device else 2
        self.channels = 2 if max_channels >= 2 else 1

        self._stream: sd.OutputStream | None = None
        self._config = EngineConfig()
        self._pattern = BarPattern()
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

        self._visual_beat = 0
        self._visual_sub = 0
        self._visual_quarter_start = 0.0
        self._visual_beat_samples = self.sample_rate

        self._active_voices: list[tuple[np.ndarray, int]] = []
        self._last_error = ""
        self._sounds = self._build_sounds()

    @staticmethod
    def _query_default_output() -> dict[str, Any] | None:
        try:
            return dict(sd.query_devices(kind="output"))
        except Exception:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    def set_pattern(self, pattern: BarPattern) -> None:
        new_pattern = copy.deepcopy(pattern)
        new_pattern.normalize()
        self._pattern = new_pattern

    def set_config(self, **kwargs: Any) -> None:
        valid = {k: v for k, v in kwargs.items() if hasattr(self._config, k)}
        if "bpm" in valid:
            valid["bpm"] = float(max(20.0, min(320.0, valid["bpm"])))
        self._config = replace(self._config, **valid)

    def get_config(self) -> EngineConfig:
        return self._config

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
        self._count_in_total_beats = max(0, int(self._config.count_in_bars)) * 4
        self._count_in_beats_left = self._count_in_total_beats
        self._visual_beat = 0
        self._visual_sub = 0
        self._visual_quarter_start = 0.0
        self._active_voices.clear()
        self._last_error = ""

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            latency="low",
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
        stages = self._stages(cfg.practice_mode)
        active_beats = stages[self._stage_index % len(stages)]
        beat_samples = max(1.0, self._visual_beat_samples)
        phase = (self._sample_cursor - self._visual_quarter_start) / beat_samples
        phase = float(max(0.0, min(0.999, phase)))
        return {
            "running": self._running,
            "bpm": cfg.bpm,
            "beat": self._visual_beat,
            "sub": self._visual_sub,
            "beat_phase": phase,
            "bar": self._bar_number + 1,
            "stage_index": self._stage_index,
            "stage_bar": self._stage_bar + 1,
            "active_beats": active_beats,
            "count_in": self._count_in_beats_left > 0,
            "count_in_beat": self._count_in_total_beats - self._count_in_beats_left,
            "last_error": self._last_error,
        }

    def stream_info(self) -> dict[str, Any]:
        result = {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "blocksize": self.blocksize,
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

        kept: list[tuple[np.ndarray, int]] = []
        for wave, pos in self._active_voices:
            n = min(frames, len(wave) - pos)
            if n > 0:
                mono[:n] += wave[pos : pos + n]
                pos += n
            if pos < len(wave):
                kept.append((wave, pos))
        self._active_voices = kept

        safety = 0
        while self._next_event_sample < block_end and safety < 128:
            safety += 1
            event_sample = self._next_event_sample
            offset = max(0, int(round(event_sample - block_start)))
            sounds, interval = self._event(event_sample)
            for wave in sounds:
                self._mix_sound(mono, offset, wave)
            self._next_event_sample += max(1.0, interval)

        self._sample_cursor = block_end
        mono *= float(self._config.master_volume)
        np.clip(mono, -0.995, 0.995, out=mono)
        if self.channels == 1:
            outdata[:, 0] = mono
        else:
            outdata[:] = mono[:, None]

    def _event(self, event_sample: float) -> tuple[list[np.ndarray], float]:
        cfg = self._config
        pattern = self._pattern
        beat_samples = self.sample_rate * 60.0 / max(20.0, cfg.bpm)
        sounds: list[np.ndarray] = []

        if self._count_in_beats_left > 0:
            idx = self._count_in_total_beats - self._count_in_beats_left
            beat = idx % 4
            self._set_visual_event(beat, 0, event_sample, beat_samples)
            if cfg.metronome_enabled:
                key = "metro_accent" if beat == 0 and cfg.accent_first_beat else "metro"
                sounds.append(self._sounds[key] * float(cfg.metronome_volume))
            self._count_in_beats_left -= 1
            if self._count_in_beats_left == 0:
                self._beat_index = 0
                self._sub_index = 0
            return sounds, beat_samples

        stages = self._stages(cfg.practice_mode)
        active_beats = stages[self._stage_index % len(stages)]
        coverage = pattern.coverage()
        owner = coverage[self._beat_index]
        covered_by_active_note = owner is not None and owner != self._beat_index and owner < active_beats
        beat_active = self._beat_index < active_beats
        beat_def = pattern.beats[self._beat_index]

        if covered_by_active_note:
            n_sub = 1
            state = OFF
        elif beat_active:
            n_sub = beat_def.subdivision
            state = beat_def.steps[self._sub_index]
        else:
            n_sub = 1
            state = TA if cfg.inactive_pulse else OFF

        if self._sub_index == 0:
            self._visual_quarter_start = event_sample
            self._visual_beat_samples = beat_samples

        self._set_visual_event(self._beat_index, self._sub_index, self._visual_quarter_start, beat_samples)

        if self._sub_index == 0 and cfg.metronome_enabled:
            key = "metro_accent" if self._beat_index == 0 and cfg.accent_first_beat else "metro"
            sounds.append(self._sounds[key] * float(cfg.metronome_volume))

        if state == TI and cfg.ti_enabled:
            sounds.append(self._sounds[self._ti_key(cfg.ti_sound)] * float(cfg.ti_volume))
        elif state == TA and cfg.ta_enabled:
            sounds.append(self._sounds[self._ta_key(cfg.ta_sound)] * float(cfg.ta_volume))

        interval = beat_samples / n_sub
        self._sub_index += 1
        if self._sub_index >= n_sub:
            self._sub_index = 0
            self._beat_index += 1
            if self._beat_index >= 4:
                self._beat_index = 0
                self._on_bar_boundary(cfg)
        return sounds, interval

    def _set_visual_event(self, beat: int, sub: int, quarter_start: float, beat_samples: float) -> None:
        self._visual_beat = int(beat)
        self._visual_sub = int(sub)
        self._visual_quarter_start = float(quarter_start)
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

        stages = self._stages(cfg.practice_mode)
        if cfg.practice_mode != "loop" and self._stage_bar >= max(1, cfg.bars_per_stage):
            self._stage_bar = 0
            self._stage_index = (self._stage_index + 1) % len(stages)

    @staticmethod
    def _stages(mode: str) -> tuple[int, ...]:
        if mode == "ramp_1_4":
            return (1, 2, 3, 4)
        if mode == "ramp_2_4":
            return (2, 4)
        return (4,)

    def _mix_sound(self, block: np.ndarray, offset: int, wave: np.ndarray) -> None:
        if offset >= len(block):
            self._active_voices.append((wave, 0))
            return
        n = min(len(wave), len(block) - offset)
        if n > 0:
            block[offset : offset + n] += wave[:n]
        if n < len(wave):
            self._active_voices.append((wave, n))

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

        def normalize(wave: np.ndarray, peak: float = 0.92) -> np.ndarray:
            m = float(np.max(np.abs(wave))) if len(wave) else 0.0
            if m > 1e-9:
                wave = wave * (peak / m)
            return wave.astype(np.float32)

        clap_n = int(sr * 0.10)
        clap = np.zeros(clap_n, dtype=np.float32)
        noise = np.diff(rng.normal(0.0, 1.0, clap_n + 1).astype(np.float32))
        for delay_ms, gain, decay in ((0, 1.0, 0.014), (11, 0.66, 0.017), (23, 0.42, 0.021)):
            start = int(sr * delay_ms / 1000.0)
            n = clap_n - start
            if n > 0:
                clap[start:] += noise[:n] * env(n, decay) * gain
        bright = tone(1850, 0.025, 0.006, 0.75)
        clap[: len(bright)] += bright
        clap = normalize(clap, 0.95)

        wood = normalize(tone(900, 0.060, 0.018, 1.0) + tone(1450, 0.060, 0.012, 0.55), 0.92)
        click = normalize(tone(2600, 0.020, 0.0045, 1.0) + tone(3900, 0.015, 0.0035, 0.35), 0.95)
        beep = normalize(tone(1150, 0.055, 0.028, 1.0), 0.88)

        muted_n = int(sr * 0.035)
        muted = rng.normal(0.0, 1.0, muted_n).astype(np.float32) * env(muted_n, 0.007)
        muted += tone(210, 0.035, 0.010, 0.65)
        muted = normalize(muted, 0.80)
        rim = normalize(tone(1750, 0.022, 0.005, 1.0) + tone(790, 0.026, 0.008, 0.25), 0.90)
        low_tick = normalize(tone(290, 0.035, 0.009, 1.0), 0.82)

        metro = normalize(tone(1800, 0.030, 0.006, 1.0) + tone(2850, 0.020, 0.004, 0.42), 0.95)
        metro_accent = normalize(tone(2550, 0.040, 0.008, 1.0) + tone(3800, 0.025, 0.005, 0.50), 0.98)

        return {
            "ti_clap": clap,
            "ti_wood": wood,
            "ti_click": click,
            "ti_beep": beep,
            "ta_muted": muted,
            "ta_rim": rim,
            "ta_low": low_tick,
            "metro": metro,
            "metro_accent": metro_accent,
        }

    @staticmethod
    def _ti_key(name: str) -> str:
        return {
            "Clap": "ti_clap",
            "Wood": "ti_wood",
            "Click": "ti_click",
            "Beep": "ti_beep",
        }.get(name, "ti_clap")

    @staticmethod
    def _ta_key(name: str) -> str:
        return {
            "Muted click": "ta_muted",
            "Rim": "ta_rim",
            "Low tick": "ta_low",
        }.get(name, "ta_muted")
