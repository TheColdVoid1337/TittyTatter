from audio_engine import EngineConfig
from game_logic import CALIBRATION_WINDOW_MS, HIT_WINDOW_MS, grade_timing, progress_bar, timing_bias
from model import BarPattern, BeatPattern
from picking_logic import DOWN, UP, economy_pick_pattern
from presets import (
    CORE_PRACTICE_PRESETS,
    EIGHTH_PRESETS,
    SIXTEENTH_PRESETS,
    TRIPLET_PRESETS,
    OFF,
    TA,
    TI,
    TI_MARK,
    all_binary_patterns,
    grid_label,
)

assert TI_MARK == "(ТИ)"
assert EngineConfig().ti_enabled is True
assert EngineConfig().ta_enabled is True

assert HIT_WINDOW_MS == 420.0
assert CALIBRATION_WINDOW_MS == 520.0
assert grade_timing(0).label == "PERFECT"
assert grade_timing(100).label == "GREAT"
assert grade_timing(200).label == "GOOD"
assert grade_timing(330).label == "HIT"
assert grade_timing(421).accepted is False
assert timing_bias([180.0]) == 180.0
assert timing_bias([170.0, 180.0, 190.0]) == 180.0
assert progress_bar(4, 8) == "■■■■□□□□"

assert economy_pick_pattern([TI, TI, TA, TA], TI, TA, OFF) == [DOWN, UP, UP, DOWN]
assert economy_pick_pattern([TA, TA, TI, TI], TI, TA, OFF) == [UP, DOWN, DOWN, UP]

assert len(SIXTEENTH_PRESETS) == 16
assert len(TRIPLET_PRESETS) == 8
assert len(CORE_PRACTICE_PRESETS) == 24
assert len(EIGHTH_PRESETS) == 4
assert {p.steps for p in SIXTEENTH_PRESETS} == set(all_binary_patterns(4))
assert {p.steps for p in TRIPLET_PRESETS} == set(all_binary_patterns(3))
assert {p.steps for p in EIGHTH_PRESETS} == set(all_binary_patterns(2))

assert grid_label("quad", 4).startswith("1/16")
assert grid_label("quad", 8).startswith("1/32")
assert grid_label("beat", 8).startswith("1/8")

bar = BarPattern(
    [
        BeatPattern("quad", [TI, TA, TI, TA], True),
        BeatPattern("triplet", [TA, TI, TA]),
        BeatPattern("duplet", [TA, TI]),
        BeatPattern("beat", [TI]),
    ],
    4,
    4,
)
raw = bar.to_dict()
assert raw["beats"][0]["muted"] is True
assert raw["time_signature"] == {"numerator": 4, "denominator": 4}
assert BarPattern.from_dict(raw).to_dict() == raw

legacy = {
    "beats": [
        {"subdivision": 4, "steps": [TI, TA, TA, TA]},
        {"subdivision": 3, "steps": [TI, TI, TA]},
        {"subdivision": 4, "steps": [TA, TA, TI, TI]},
        {"subdivision": 3, "steps": [TA, TI, TA]},
    ]
}
legacy_bar = BarPattern.from_dict(legacy)
assert [b.grid for b in legacy_bar.beats] == ["quad", "triplet", "quad", "triplet"]
assert [b.muted for b in legacy_bar.beats] == [False, False, False, False]
assert (legacy_bar.numerator, legacy_bar.denominator) == (4, 4)

span_bar = BarPattern(
    [
        BeatPattern("long2", [TI]),
        BeatPattern("quad", [TA, TA, TA, TA]),
        BeatPattern("long2", [TA]),
        BeatPattern("triplet", [TI, TA, TI]),
    ],
    4,
    4,
)
assert span_bar.coverage() == [0, 0, 2, 2]

odd_bar = BarPattern(
    [
        BeatPattern("duplet", [TI, TA]),
        BeatPattern("triplet", [TA, TI, TA]),
        BeatPattern("quad", [TI, TA, TI, TA]),
        BeatPattern("beat", [TA]),
        BeatPattern("duplet", [TA, TI]),
        BeatPattern("beat", [TI]),
        BeatPattern("quad", [TA, TI, TA, TI]),
    ],
    7,
    8,
)
odd_raw = odd_bar.to_dict()
assert len(odd_raw["beats"]) == 7
assert odd_raw["time_signature"] == {"numerator": 7, "denominator": 8}
assert BarPattern.from_dict(odd_raw).to_dict() == odd_raw

print("core tests OK")
