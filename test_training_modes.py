"""Deterministic post-0.0.5 Training Mode regression gate.

No sound device, GUI, stream or PortAudio callback is opened. The _event()
seam exercises real callback scheduling without starting a Windows device.
Native GUI/audio smoke is still required before accepting the feature.
"""
from __future__ import annotations

import math

import numpy as np

from audio_engine import AudioEngine, EngineConfig
from model import BarPattern, BeatPattern
from presets import OFF, TA, TI
from training_modes import (
    LADDER_GRIDS,
    TEMPO_MODES,
    TRAINING_MODES,
    ladder_effective_pattern,
    tempo_for_bar,
    training_phase,
)

NEW_MODES = {
    "subdivision_ladder", "burst", "accent_shift",
    "blind_pattern", "endurance", "tempo_wave", "random_tempo",
}
assert NEW_MODES <= {key for key, _ in TRAINING_MODES}
assert len(TRAINING_MODES) == 14
assert TEMPO_MODES == {"burst", "tempo_wave", "random_tempo"}


def fixture_engine(mode: str, pattern: BarPattern, **overrides: object) -> AudioEngine:
    """Construct the scheduling state without probing/allocating audio hardware."""
    engine = AudioEngine.__new__(AudioEngine)
    engine.sample_rate = 48000.0
    engine._config = EngineConfig(
        practice_mode=mode, bpm=60.0, metronome_enabled=False,
        count_in_bars=0, **overrides,
    )
    engine._pattern = pattern
    engine._effective_pattern = pattern
    engine._coverage = pattern.coverage()
    engine._effective_bpm = engine._config.bpm
    engine._running = False
    engine._beat_index = 0
    engine._sub_index = 0
    engine._bar_number = 0
    engine._stage_index = 0
    engine._stage_bar = 0
    engine._count_in_beats_left = 0
    engine._count_in_total_beats = 0
    engine._practice_started_sample = None
    engine._visual_beat = 0
    engine._visual_sub = 0
    engine._visual_beat_start = 0.0
    engine._visual_beat_samples = engine.sample_rate
    engine._sample_cursor = 0
    engine._sounds = {
        k: np.ones(4, dtype=np.float32)
        for k in ("Wood", "Low tick", "metro", "metro_accent")
    }
    engine._update_effective_pattern()
    engine._update_effective_bpm()
    return engine


def run_bar(engine: AudioEngine, sample: float = 0.0):
    """Collect target coordinates, gains and callback intervals for one bar."""
    bar = engine._bar_number
    targets, gains, intervals = [], [], []
    for _ in range(1000):
        sounds, interval, target = engine._event(sample)
        if target is not None:
            targets.append(target)
        gains.extend(gain for _, gain in sounds)
        intervals.append(interval)
        assert interval > 0.0
        sample += interval
        if engine._bar_number > bar:
            return sample, targets, gains, intervals
    raise AssertionError("Event scheduler failed to complete bar")


# Pure phase-cycle edge cases.
assert [training_phase("subdivision_ladder", b, 7, ladder_bars=2).stage_index for b in range(10)] == [
    0, 0, 1, 1, 2, 2, 3, 3, 0, 0
]
assert [training_phase("burst", b, 3, burst_base_bars=4, burst_fast_bars=1).stage_index for b in range(6)] == [0, 0, 0, 0, 1, 0]
assert [training_phase("accent_shift", b, 3, accent_bars=1).accent_beat for b in range(5)] == [0, 1, 2, 0, 1]
assert [training_phase("accent_shift", b, 1).accent_beat for b in range(3)] == [0, 0, 0]
assert [training_phase("endurance", b, 4, endurance_work_bars=2, endurance_rest_bars=1).rest for b in range(6)] == [False, False, True, False, False, True]
assert [training_phase("blind_pattern", b, 4, blind_learn_bars=1, blind_memory_bars=2).blind_hidden for b in range(6)] == [False, True, True, False, True, True]

# Ladder stages cycle played string identities; they never mutate the stored bar.
pattern = BarPattern([
    BeatPattern("quad", [TI, TA, OFF, TI]),
    BeatPattern("beat", [TA]),
], 2, 4)
source = pattern.to_dict()
assert LADDER_GRIDS == ("beat", "duplet", "triplet", "quad")
for stage, count in enumerate((1, 2, 3, 4)):
    effective = ladder_effective_pattern(pattern, stage)
    assert [b.grid for b in effective.beats] == [LADDER_GRIDS[stage]] * 2
    assert effective.beats[0].steps == [TI, TA, TI, TI][:count] if count < 4 else [TI, TA, TI, TI] == effective.beats[0].steps
    assert effective.beats[1].steps == [TA] * count
assert pattern.to_dict() == source
silent = BarPattern([BeatPattern("quad", [OFF] * 4, False)], 1, 16)
assert ladder_effective_pattern(silent, 3).beats[0].steps == [OFF] * 4
span = BarPattern([BeatPattern("long2", [TI]), BeatPattern("quad", [TA] * 4)], 2, 8)
assert ladder_effective_pattern(span, 3).beats[0].grid == "long2"
assert ladder_effective_pattern(span, 3).beats[1].steps == [OFF]

# Exercise engine uses the effective per-stage model for BOTH timing and Game.
ladder = fixture_engine("subdivision_ladder", pattern, ladder_bars=1)
sample = 0.0
for stage, expected_count in enumerate((2, 4, 6, 8, 2)):
    sample, targets, gains, _ = run_bar(ladder, sample)
    assert len(targets) == expected_count, (stage, targets)
    assert all(t[0] in (TI, TA) for t in targets)
    assert len(gains) == expected_count

simple = BarPattern([BeatPattern("beat", [TI]), BeatPattern("beat", [TA])], 2, 4)

# Blind Pattern: note guidance disappears but Game targets continue.
blind = fixture_engine("blind_pattern", simple, blind_learn_bars=1, blind_memory_bars=1)
sample, targets, gains, _ = run_bar(blind)
assert len(targets) == len(gains) == 2
sample, targets, gains, _ = run_bar(blind, sample)
assert len(targets) == 2 and not gains

# Recovery: neither note audio nor Game targets, and clock still progresses.
rest = fixture_engine("endurance", simple, endurance_work_bars=1, endurance_rest_bars=1)
sample, targets, gains, _ = run_bar(rest)
assert len(targets) == len(gains) == 2
sample, targets, gains, _ = run_bar(rest, sample)
assert targets == [] and gains == []
assert rest._bar_number == 2

# Accent changes only the first existing attack on the selected metric beat.
accent = fixture_engine("accent_shift", simple, accent_bars=1)
sample, targets, gains, _ = run_bar(accent)
assert len(targets) == 2
assert math.isclose(gains[0], 1.45) and math.isclose(gains[1], 0.7)
sample, targets, gains, _ = run_bar(accent, sample)
assert len(targets) == 2
assert math.isclose(gains[0], 1.0) and math.isclose(gains[1], 0.7 * 1.45)

# Tempo progression: bar-aligned values, no mutation of base tempo.
assert [tempo_for_bar("burst", b, 80, burst_base_bars=4, burst_fast_bars=1, burst_fast_bpm=120) for b in range(6)] == [80, 80, 80, 80, 120, 80]
assert [tempo_for_bar("tempo_wave", b, 60, tempo_min_bpm=80, tempo_max_bpm=110, tempo_block_bars=1) for b in range(7)] == [80, 90, 100, 110, 100, 90, 80]
random_a = [tempo_for_bar("random_tempo", b, 60, tempo_min_bpm=70, tempo_max_bpm=100, tempo_block_bars=2, random_seed=42) for b in range(16)]
random_b = [tempo_for_bar("random_tempo", b, 60, tempo_min_bpm=70, tempo_max_bpm=100, tempo_block_bars=2, random_seed=42) for b in range(16)]
assert random_a == random_b
assert all(70 <= value <= 100 for value in random_a)
assert all(random_a[i] == random_a[i + 1] for i in range(0, len(random_a), 2))
assert len(set(random_a)) >= 2

burst = fixture_engine("burst", simple, burst_base_bars=1, burst_fast_bars=1, burst_fast_bpm=120)
sample, targets, gains, intervals = run_bar(burst)
assert len(targets) == 2 and all(math.isclose(x, 48000.0) for x in intervals)
assert burst._effective_bpm == 120
sample, targets, gains, intervals = run_bar(burst, sample)
assert len(targets) == 2 and all(math.isclose(x, 24000.0) for x in intervals)
assert burst._effective_bpm == 60
assert burst._config.bpm == 60.0

print("training modes OK")
