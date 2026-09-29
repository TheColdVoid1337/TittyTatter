from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import sounddevice as sd

from model import BarPattern
from presets import OFF, TA, TI


@dataclass(frozen=True)
class EngineConfig:
    bpm: float = 80.0
    master_volume: float = 0.85
    ti_enabled: bool = True
    ti_sound: str = "Clap"
    ti_volume: float = 0.95
    ta_enabled: bool = False
    ta_sound: str = "Muted click"
    ta_volume: float = 0.58
    metronome_enabled: bool = True
    metronome_volume: float = 0.38
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
    """Audio-callback rhythm engine; GUI timers never schedule musical events."""

    def __init__(self, sample_rate: int = 48_000, blocksize: int = 256) -> None:
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self._lock = threading.RLock()
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
        self._active_voices: list[tuple[np.ndarray, int]] = []
        self._last_error = ""
        self._sounds = self._build_sounds()

    @property
    def is_running(self) -> bool:
        return self._running

    def set_pattern(self, pattern: BarPattern) -> None:
        pattern = copy.deepcopy(pattern)
        pattern.normalize()
        with self._lock:
            self._pattern = pattern

    def set_config(self, **kwargs: Any) -> None:
        with self._lock:
            valid = {k: v for k, v in kwargs.items() if hasattr(self._config, k)}
            if "bpm" in valid:
                valid["bpm"] = float(max(20.0, min(320.0, valid["bpm"])))
            self._config = replace(self._config, **valid)

    def get_config(self) -> EngineConfig:
        with self._lock:
            return self._config

    def start(self) -> None:
        if self._running:
            return
        with self._lock:
            self._sample_cursor = 0
            self._next_event_sample = 0.0
            self._beat_index = self._sub_index = self._bar_number = 0
            self._stage_index = self._stage_bar = 0
            self._count_in_total_beats = max(0, int(self._config.count_in_bars)) * 4
            self._count_in_beats_left = self._count_in_total_beats
            self._active_voices.clear()
            self._last_error = ""
        self._stream = sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype="float32", blocksize=self.blocksize, latency="low", callback=self._audio_callback)
        self._stream.start()
        self._running = True

    def stop(self) -> None:
        self._running = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop(); stream.close()
            except Exception:
                pass
        with self._lock:
            self._active_voices.clear()

    def close(self) -> None:
        self.stop()

    def status(self) -> dict[str, Any]:
        with self._lock:
            cfg = self._config
            stages = self._stages(cfg.practice_mode)
            return {"running": self._running, "bpm": cfg.bpm, "beat": self._beat_index, "sub": self._sub_index, "bar": self._bar_number + 1, "stage_index": self._stage_index, "stage_bar": self._stage_bar + 1, "active_beats": stages[self._stage_index % len(stages)], "count_in": self._count_in_beats_left > 0, "count_in_beat": self._count_in_total_beats - self._count_in_beats_left, "last_error": self._last_error}

    def _audio_callback(self, outdata: np.ndarray, frames: int, _time: Any, status: Any) -> None:
        if status:
            self._last_error = str(status)
        mono = np.zeros(frames, dtype=np.float32)
        block_start, block_end = self._sample_cursor, self._sample_cursor + frames
        kept: list[tuple[np.ndarray, int]] = []
        for wave, pos in self._active_voices:
            n = min(frames, len(wave) - pos)
            if n > 0:
                mono[:n] += wave[pos:pos+n]; pos += n
            if pos < len(wave):
                kept.append((wave, pos))
        self._active_voices = kept
        safety = 0
        while self._next_event_sample < block_end and safety < 64:
            safety += 1
            offset = max(0, int(round(self._next_event_sample - block_start)))
            sounds, interval = self._event()
            for wave in sounds:
                self._mix_sound(mono, offset, wave)
            self._next_event_sample += max(1.0, interval)
        self._sample_cursor = block_end
        mono *= float(self._config.master_volume)
        np.clip(mono, -0.98, 0.98, out=mono)
        outdata[:, 0] = mono

    def _event(self) -> tuple[list[np.ndarray], float]:
        with self._lock:
            cfg, pattern = self._config, self._pattern
        beat_samples = self.sample_rate * 60.0 / max(20.0, cfg.bpm)
        sounds: list[np.ndarray] = []
        if self._count_in_beats_left > 0:
            idx = self._count_in_total_beats - self._count_in_beats_left
            beat = idx % 4
            if cfg.metronome_enabled:
                key = "metro_accent" if beat == 0 and cfg.accent_first_beat else "metro"
                sounds.append(self._sounds[key] * float(cfg.metronome_volume))
            self._beat_index, self._sub_index = beat, 0
            self._count_in_beats_left -= 1
            if not self._count_in_beats_left:
                self._beat_index = self._sub_index = 0
            return sounds, beat_samples
        active_beats = self._stages(cfg.practice_mode)[self._stage_index % len(self._stages(cfg.practice_mode))]
        active = self._beat_index < active_beats
        beat_def = pattern.beats[self._beat_index]
        if active:
            n_sub, state = beat_def.subdivision, beat_def.steps[self._sub_index]
        else:
            n_sub, state = 1, TA if cfg.inactive_pulse else OFF
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
            self._sub_index = 0; self._beat_index += 1
            if self._beat_index >= 4:
                self._beat_index = 0; self._on_bar_boundary(cfg)
        return sounds, interval

    def _on_bar_boundary(self, cfg: EngineConfig) -> None:
        self._bar_number += 1; self._stage_bar += 1
        if cfg.tempo_trainer_enabled and cfg.tempo_every_bars > 0 and self._bar_number % cfg.tempo_every_bars == 0:
            current, target, step = cfg.bpm, float(cfg.tempo_target), abs(float(cfg.tempo_step))
            new_bpm = min(target, current + step) if current < target else max(target, current - step) if current > target else current
            if new_bpm != current:
                with self._lock:
                    self._config = replace(self._config, bpm=new_bpm)
                cfg = self._config
        stages = self._stages(cfg.practice_mode)
        if cfg.practice_mode != "loop" and self._stage_bar >= max(1, cfg.bars_per_stage):
            self._stage_bar = 0; self._stage_index = (self._stage_index + 1) % len(stages)

    @staticmethod
    def _stages(mode: str) -> tuple[int, ...]:
        if mode == "ramp_1_4": return (1, 2, 3, 4)
        if mode == "ramp_2_4": return (2, 4)
        return (4,)

    def _mix_sound(self, block: np.ndarray, offset: int, wave: np.ndarray) -> None:
        if offset >= len(block):
            self._active_voices.append((wave, 0)); return
        n = min(len(wave), len(block) - offset)
        if n > 0: block[offset:offset+n] += wave[:n]
        if n < len(wave): self._active_voices.append((wave, n))

    def _build_sounds(self) -> dict[str, np.ndarray]:
        sr = self.sample_rate
        rng = np.random.default_rng(20260929)
        def env(n: int, decay: float) -> np.ndarray:
            return np.exp(-(np.arange(n, dtype=np.float32) / sr) / decay).astype(np.float32)
        def tone(freq: float, dur: float, decay: float, amp: float = 1.0) -> np.ndarray:
            n = max(1, int(sr * dur)); t = np.arange(n, dtype=np.float32) / sr
            return (amp * np.sin(2*np.pi*freq*t) * env(n, decay)).astype(np.float32)
        clap_n = int(sr * 0.11); clap = np.zeros(clap_n, dtype=np.float32)
        hp = np.diff(rng.normal(0.0, 1.0, clap_n + 1).astype(np.float32))
        for ms, gain, decay in ((0,1.0,0.018),(13,0.72,0.020),(26,0.48,0.024)):
            start = int(sr * ms / 1000); n = clap_n - start
            if n > 0: clap[start:] += hp[:n] * env(n, decay) * gain
        clap /= max(1e-6, np.max(np.abs(clap))); clap *= 0.62
        muted_n = int(sr * 0.045)
        muted = rng.normal(0.0,1.0,muted_n).astype(np.float32)*env(muted_n,0.010)*0.18 + tone(180,0.045,0.015,0.45)
        return {"ti_clap":clap,"ti_wood":tone(850,0.075,0.025,0.8)+tone(1320,0.075,0.018,0.45),"ti_click":tone(2200,0.025,0.006,0.8),"ti_beep":tone(1050,0.065,0.035,0.65),"ta_muted":muted,"ta_rim":tone(1550,0.03,0.008,0.55)+tone(700,0.03,0.010,0.22),"ta_low":tone(260,0.045,0.012,0.55),"metro":tone(1280,0.026,0.008,0.45),"metro_accent":tone(1900,0.035,0.010,0.66)}

    @staticmethod
    def _ti_key(name: str) -> str:
        return {"Clap":"ti_clap","Wood":"ti_wood","Click":"ti_click","Beep":"ti_beep"}.get(name,"ti_clap")

    @staticmethod
    def _ta_key(name: str) -> str:
        return {"Muted click":"ta_muted","Rim":"ta_rim","Low tick":"ta_low"}.get(name,"ta_muted")
