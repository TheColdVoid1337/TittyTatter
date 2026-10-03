from audio_engine import EngineConfig, GAME_HIT_SOUNDS, GAME_MISS_SOUNDS
from game_logic import (
    EARLY_HIT_WINDOW_MS,
    HIT_WINDOW_MS,
    INPUT_BUFFER_MAX_MS,
    LATE_HIT_WINDOW_MS,
    choose_target_index,
    grade_timing,
    progress_bar,
)
from input_binding import binding_display, binding_identity, normalize_binding, scan_binding
from model import BarPattern, BeatPattern
from picking_logic import (
    DOWN,
    UP,
    economy_pick_beats,
    economy_pick_pattern,
    strict_alternate_pick_beats,
)
from training_modes import (
    GAP_MODES,
    RAMP_MODES,
    TRAINING_MODES,
    displaced_click_spec,
    gap_phase,
    ramp_stages,
    sparse_click_matches,
)
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
assert len(GAME_HIT_SOUNDS) == 3
assert len(GAME_MISS_SOUNDS) == 3
assert GAME_HIT_SOUNDS[0][1] == "game_hit"
assert GAME_MISS_SOUNDS[0][1] == "game_miss"


# Training modes remain additive: the original repeat and beat-ramp modes are
# preserved while the new guitar-practice modes share the same engine timeline.
assert [key for key, _label in TRAINING_MODES][:3] == ["loop", "ramp_1_4", "ramp_2_4"]
assert {"ramp_1_4", "ramp_2_4"} == set(RAMP_MODES)
assert {"gap", "progressive_gap"} == set(GAP_MODES)
assert ramp_stages("ramp_1_4", 4) == (1, 2, 3, 4)
assert ramp_stages("ramp_2_4", 4) == (2, 4)
assert ramp_stages("ramp_2_4", 1) == (1,)
assert ramp_stages("loop", 7) == (7,)

# Fixed gaps: four audible bars followed by two silent bars, then repeat.
fixed_gap = [
    gap_phase(
        "gap",
        bar,
        play_bars=4,
        silent_bars=2,
        progressive_max_silent_bars=4,
    ).silent
    for bar in range(8)
]
assert fixed_gap == [False, False, False, False, True, True, False, False]

# Progressive gaps keep the audible block fixed while silence grows 1 -> 2 -> 3.
progressive = [
    gap_phase(
        "progressive_gap",
        bar,
        play_bars=2,
        silent_bars=99,
        progressive_max_silent_bars=3,
    )
    for bar in range(12)
]
assert [(p.silent_bars, p.silent) for p in progressive[:3]] == [
    (1, False),
    (1, False),
    (1, True),
]
assert progressive[3].silent_bars == 2 and progressive[3].silent is False
assert progressive[5].silent_bars == 2 and progressive[5].silent is True
assert progressive[7].silent_bars == 3 and progressive[7].silent is False
assert progressive[9].silent_bars == 3 and progressive[9].silent is True

assert sparse_click_matches("2_4", 0, 1) is True
assert sparse_click_matches("2_4", 0, 0) is False
assert sparse_click_matches("beat_1", 3, 0) is True
assert sparse_click_matches("bar_2", 0, 0) is True
assert sparse_click_matches("bar_2", 1, 0) is False
assert displaced_click_spec("eighth_and") == (2, 1)
assert displaced_click_spec("sixteenth_e") == (4, 1)
assert displaced_click_spec("sixteenth_and") == (4, 2)
assert displaced_click_spec("sixteenth_a") == (4, 3)


# Keyboard game bindings are stored by physical Windows scan code so active
# keyboard layout does not change F/J input matching.
assert normalize_binding("F") == "scan:33:F"
assert normalize_binding("key:J") == "scan:36:J"
assert binding_identity("scan:33:F") == "scan:33"
assert binding_identity("scan:33:А") == "scan:33"
assert binding_display("scan:33:F") == "F"
assert scan_binding(36, "О") == "scan:36:J"
assert normalize_binding("mouse:4") == "mouse:4"
assert binding_identity("mouse:4") == "mouse:4"

assert EARLY_HIT_WINDOW_MS == 180.0
assert LATE_HIT_WINDOW_MS == 300.0
assert HIT_WINDOW_MS == 300.0
assert INPUT_BUFFER_MAX_MS == 180.0
assert grade_timing(0).label == "PERFECT"
assert grade_timing(30).label == "PERFECT"
assert grade_timing(50).label == "GREAT"
assert grade_timing(100).label == "GOOD"
assert grade_timing(200).label == "HIT"
assert grade_timing(-181).accepted is False
assert grade_timing(301).accepted is False

# Lane-only matching: an opposite-lane note can never consume the input.
# At t=0.08 the nearest valid TA is the future TA at t=0.25 (-170 ms),
# not the older TA at t=-0.20 (+280 ms).
lane_targets = [(-0.20, TA), (0.00, TI), (0.25, TA), (0.50, TA)]
assert choose_target_index(lane_targets, TI, 0.08) == 1
assert choose_target_index(lane_targets, TA, 0.08) == 2

# Same-lane nearest target wins, within the asymmetric playable window.
subdivision_targets = [(0.00, TI), (0.25, TA), (0.50, TA), (0.75, TA)]
assert choose_target_index(subdivision_targets, TA, 0.45) == 2
assert choose_target_index(subdivision_targets, TI, 0.45) is None

# A wrong lane must not fall back to an opposite-lane target.
assert choose_target_index([(0.0, TI)], TA, 0.05) is None

assert progress_bar(4, 8) == "■■■■□□□□"

assert economy_pick_pattern([TI, TI, TA, TA], TI, TA, OFF) == [DOWN, UP, UP, DOWN]
assert economy_pick_pattern([TA, TA, TI, TI], TI, TA, OFF) == [UP, DOWN, DOWN, UP]


strict_alt = strict_alternate_pick_beats(
    [[TI, TA, OFF, TI], [TA, TA]],
    TI,
    TA,
    OFF,
)
assert strict_alt == [
    [DOWN, UP, None, DOWN],
    [UP, DOWN],
]


# Loop picking preserves the shortest whole-beat period. Four identical
# TI-TA-TA-TA beats must therefore display the same picking each time.
identical_loop = economy_pick_beats(
    [[TI, TA, TA, TA]] * 4,
    TI,
    TA,
    OFF,
    loop=True,
)
assert identical_loop[0] == identical_loop[1] == identical_loop[2] == identical_loop[3]

# A/B/A/B also preserves its two-beat visual/picking period.
abab_loop = economy_pick_beats(
    [
        [TI, TA, TA, TA],
        [TA, TI, TA, TI],
        [TI, TA, TA, TA],
        [TA, TI, TA, TI],
    ],
    TI,
    TA,
    OFF,
    loop=True,
)
assert abab_loop[0] == abab_loop[2]
assert abab_loop[1] == abab_loop[3]

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
