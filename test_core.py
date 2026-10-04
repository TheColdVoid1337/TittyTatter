from fractions import Fraction

from audio_engine import (
    EngineConfig,
    GAME_HIT_SOUNDS,
    GAME_MISS_SOUNDS,
    GAME_TA_HIT_FOR_TI,
    GAME_TA_HIT_SOUNDS,
    GAME_TI_HIT_SOUNDS,
)
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
    PICKING_COVERED,
    UP,
    EscapeProfile,
    PickDecision,
    PickingEventSource,
    PickingTransition,
    alternate_pick_beats_v2,
    annotate_whole_beat_motifs,
    alternate_pick_events,
    classify_pick_transition,
    economy_pick_beats_v2,
    economy_pick_events,
    economy_pick_ramp_stages_v2,
    escape_profile_adjustment,
    escape_profile_crossing_status,
    normalize_picking_events,
    normalize_ramp_stage_events,
    picking_directions_by_beat,
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
assert len(GAME_TI_HIT_SOUNDS) == 4
assert len(GAME_TA_HIT_SOUNDS) == 4
assert len(GAME_HIT_SOUNDS) == 4
assert len(GAME_MISS_SOUNDS) == 4
assert GAME_TI_HIT_SOUNDS[0][1] == "game_hit"
assert GAME_TA_HIT_FOR_TI["game_hit"] == "game_ta_hit"
assert GAME_TA_HIT_FOR_TI["game_hit_guitar_ti"] == "game_hit_guitar_ta"
assert GAME_MISS_SOUNDS[-1][1] == "game_miss_string"


# Picking Logic v2 P1: normalize slots without changing runtime stroke output.
p1_full = [
    [TA, OFF, TI, TA],
    [TI, TA],
    [],
]
p1_events = normalize_picking_events(
    p1_full,
    [list(states) for states in p1_full],
    TI,
    TA,
    OFF,
    stage_id="loop:test",
)
assert p1_events[0].slot_id == "loop:test:b0:s0"
assert p1_events[0].source is PickingEventSource.REAL_PATTERN
assert p1_events[0].attack is True
assert p1_events[0].string == 6
assert p1_events[0].persistent_attack_id == "beat:0:sub:0"
assert p1_events[0].phrase_boundary_before is True
assert p1_events[0].rhythmic_phase == Fraction(0, 1)

# OFF remains a real rhythmic slot but does not consume an attack identity or
# implicitly reset phrase continuity.
assert p1_events[1].state == OFF
assert p1_events[1].attack is False
assert p1_events[1].string is None
assert p1_events[1].persistent_attack_id is None
assert p1_events[1].phrase_boundary_before is False
assert p1_events[1].rhythmic_phase == Fraction(1, 4)

# Real attacks receive stable coordinate-based identity independent of stage.
assert p1_events[2].state == TI
assert p1_events[2].persistent_attack_id == "beat:0:sub:2"
assert p1_events[2].string == 5

# Covered metric beats are explicit normalized events rather than disappearing.
assert p1_events[-1].state == PICKING_COVERED
assert p1_events[-1].subdivision_index is None
assert p1_events[-1].attack is False
assert p1_events[-1].persistent_attack_id is None

# Reset boundaries are explicit inputs; silence alone does not create them.
p1_reset = normalize_picking_events(
    p1_full,
    [list(states) for states in p1_full],
    TI,
    TA,
    OFF,
    reset_before_beats={1},
    stage_id="loop:reset",
)
beat1_first = next(
    event
    for event in p1_reset
    if event.beat_index == 1 and event.subdivision_index == 0
)
assert beat1_first.phrase_boundary_before is True
assert beat1_first.reset_before is True

# Ramp real attacks preserve identity across stages while temporary TA pulses
# are stage-local placeholders with no persistent attack id.
p1_ramp_full = [
    [TA, TI, OFF, TA],
    [TI, TA, TI, TA],
    [TA, TI, TA, TI],
    [],
]
p1_ramp_stage1 = normalize_ramp_stage_events(
    p1_ramp_full,
    1,
    TI,
    TA,
    OFF,
)
p1_ramp_stage2 = normalize_ramp_stage_events(
    p1_ramp_full,
    2,
    TI,
    TA,
    OFF,
)

stage1_real = next(
    event
    for event in p1_ramp_stage1
    if event.beat_index == 0 and event.subdivision_index == 1
)
stage2_same_real = next(
    event
    for event in p1_ramp_stage2
    if event.beat_index == 0 and event.subdivision_index == 1
)
assert stage1_real.source is PickingEventSource.REAL_PATTERN
assert stage2_same_real.source is PickingEventSource.REAL_PATTERN
assert (
    stage1_real.persistent_attack_id
    == stage2_same_real.persistent_attack_id
    == "beat:0:sub:1"
)

stage1_placeholder = next(
    event
    for event in p1_ramp_stage1
    if event.beat_index == 1 and event.subdivision_index == 0
)
stage2_opened = next(
    event
    for event in p1_ramp_stage2
    if event.beat_index == 1 and event.subdivision_index == 0
)
assert stage1_placeholder.source is PickingEventSource.RAMP_PLACEHOLDER
assert stage1_placeholder.attack is True
assert stage1_placeholder.string == 6
assert stage1_placeholder.persistent_attack_id is None
assert stage2_opened.source is PickingEventSource.REAL_PATTERN
assert stage2_opened.persistent_attack_id == "beat:1:sub:0"
assert stage1_placeholder.slot_id != stage2_opened.slot_id

placeholder_tail = next(
    event
    for event in p1_ramp_stage1
    if event.beat_index == 1 and event.subdivision_index == 1
)
assert placeholder_tail.source is PickingEventSource.RAMP_PLACEHOLDER
assert placeholder_tail.state == OFF
assert placeholder_tail.attack is False

covered_stage1 = next(
    event
    for event in p1_ramp_stage1
    if event.beat_index == 3
)
assert covered_stage1.state == PICKING_COVERED
assert covered_stage1.source is PickingEventSource.REAL_PATTERN


# Picking Logic v2 P2: Alternate means attack-alternate on normalized events.
p2_events = normalize_picking_events(
    [
        [TA, OFF, TA, TI],
        [OFF, TI],
        [],
        [TA],
    ],
    [
        [TA, OFF, TA, TI],
        [OFF, TI],
        [],
        [TA],
    ],
    TI,
    TA,
    OFF,
    reset_before_beats={3},
    stage_id="alternate:p2",
)
p2_directions = alternate_pick_events(p2_events)

# Attacks alternate globally regardless of string changes.
p2_attack_directions = [
    direction
    for event, direction in zip(p2_events, p2_directions)
    if event.attack
]
assert p2_attack_directions == [DOWN, UP, DOWN, UP, DOWN]

# OFF and COVERED do not consume parity and receive no stroke.
for event, direction in zip(p2_events, p2_directions):
    if not event.attack:
        assert direction is None

# Explicit reset boundaries do not restart public Alternate: consecutive
# attacks still flip across the complete effective exercise stream.
beat3_attack = next(
    (event, direction)
    for event, direction in zip(p2_events, p2_directions)
    if event.beat_index == 3 and event.attack
)
assert beat3_attack[0].phrase_boundary_before is True
assert beat3_attack[1] == DOWN

# UP is a supported explicit starting polarity; invalid input falls back DOWN.
assert [
    direction
    for event, direction in zip(
        p2_events,
        alternate_pick_events(p2_events, start_direction=UP),
    )
    if event.attack
][:3] == [UP, DOWN, UP]
assert [
    direction
    for event, direction in zip(
        p2_events,
        alternate_pick_events(p2_events, start_direction="invalid"),
    )
    if event.attack
][:2] == [DOWN, UP]

# Ramp placeholder attacks consume Alternate parity exactly like real attacks.
p2_ramp = normalize_ramp_stage_events(
    [
        [TA, OFF, TI, TA],
        [TI, TA, TI, TA],
        [TA, TI, TA, TI],
        [TI, TI, TA, TA],
    ],
    1,
    TI,
    TA,
    OFF,
    stage_id="alternate:ramp1",
)
p2_ramp_directions = alternate_pick_events(p2_ramp)
p2_ramp_attacks = [
    (event, direction)
    for event, direction in zip(p2_ramp, p2_ramp_directions)
    if event.attack
]
assert [direction for _event, direction in p2_ramp_attacks] == [
    DOWN,
    UP,
    DOWN,
    UP,
    DOWN,
    UP,
]
assert sum(
    event.source is PickingEventSource.RAMP_PLACEHOLDER
    for event, _direction in p2_ramp_attacks
) == 3

# The beat-shaped adapter is only a projection of the normalized event result.
p2_rows = alternate_pick_beats_v2(
    [
        [TA, OFF, TA, TI],
        [OFF, TI],
        [],
        [TA],
    ],
    [
        [TA, OFF, TA, TI],
        [OFF, TI],
        [],
        [TA],
    ],
    TI,
    TA,
    OFF,
)
assert p2_rows == [
    [DOWN, None, UP, DOWN],
    [None, UP],
    [],
    [DOWN],
]

# P2 is deterministic.
assert alternate_pick_events(p2_events) == p2_directions


# Picking Logic v2 P3: practical directional Economy on normalized events.
p3_down_sweep_events = normalize_picking_events(
    [[TA, TI]],
    [[TA, TI]],
    TI,
    TA,
    OFF,
    stage_id="economy:down-sweep",
)
p3_down_sweep = economy_pick_events(p3_down_sweep_events, cyclic=False)
assert [decision.stroke for decision in p3_down_sweep] == [DOWN, DOWN]
assert (
    p3_down_sweep[1].transition_from_previous
    is PickingTransition.DIRECTIONAL_SWEEP
)
assert p3_down_sweep[0].sweep_group_id == p3_down_sweep[1].sweep_group_id
assert p3_down_sweep[0].sweep_group_id is not None
assert "directional sweep 6->5" in p3_down_sweep[1].reason

# Start polarity is a real optimization choice: 5->6 is most efficient when
# the phrase starts UP so the second attack can continue the upstroke sweep.
p3_up_sweep_events = normalize_picking_events(
    [[TI, TA]],
    [[TI, TA]],
    TI,
    TA,
    OFF,
    stage_id="economy:up-sweep",
)
p3_up_sweep = economy_pick_events(p3_up_sweep_events, cyclic=False)
assert [decision.stroke for decision in p3_up_sweep] == [UP, UP]
assert (
    p3_up_sweep[1].transition_from_previous
    is PickingTransition.DIRECTIONAL_SWEEP
)

# Same-string Economy prefers alternate strokes and exposes attack parity.
p3_same_events = normalize_picking_events(
    [[TI, TI, TI, TI]],
    [[TI, TI, TI, TI]],
    TI,
    TA,
    OFF,
    stage_id="economy:same-string",
)
p3_same = economy_pick_events(p3_same_events, cyclic=False)
assert [decision.stroke for decision in p3_same] == [DOWN, UP, DOWN, UP]
assert [decision.attack_parity for decision in p3_same] == [0, 1, 0, 1]
assert all(
    decision.transition_from_previous is PickingTransition.SAME_STRING_ALTERNATE
    for decision in p3_same[1:]
)

# OFF does not reset Economy continuity: the same 6->5 sweep is available
# across an internal silent slot.
p3_off_events = normalize_picking_events(
    [[TA, OFF, TI]],
    [[TA, OFF, TI]],
    TI,
    TA,
    OFF,
    stage_id="economy:off-continuity",
)
p3_off = economy_pick_events(p3_off_events, cyclic=False)
assert [decision.stroke for decision in p3_off] == [DOWN, None, DOWN]
assert (
    p3_off[2].transition_from_previous
    is PickingTransition.DIRECTIONAL_SWEEP
)
assert p3_off[2].attack_parity == 1

# An explicit reset is different from silence and starts a fresh phrase.
p3_reset_events = normalize_picking_events(
    [[TA], [TI]],
    [[TA], [TI]],
    TI,
    TA,
    OFF,
    reset_before_beats={1},
    stage_id="economy:reset",
)
p3_reset = economy_pick_events(p3_reset_events, cyclic=False)
assert [decision.stroke for decision in p3_reset] == [DOWN, DOWN]
assert p3_reset[1].transition_from_previous is PickingTransition.RESET
assert "explicit phrase reset" in p3_reset[1].reason
assert p3_reset[1].attack_parity == 0

# Cyclic scoring includes the real last->first transition. A two-attack 6->5
# phrase therefore avoids a one-way sweep that would create an awkward
# same-stroke crossing every time the bar loops.
p3_cycle = economy_pick_events(p3_down_sweep_events, cyclic=True)
assert [decision.stroke for decision in p3_cycle] == [DOWN, UP]
assert p3_cycle[0].loop_boundary is True
assert (
    p3_cycle[0].transition_from_previous
    is PickingTransition.ALTERNATE_CROSSING
)
assert "loop boundary" in p3_cycle[0].reason

# Wrong-direction same-stroke crossings are classified separately from sweeps.
assert (
    classify_pick_transition(6, UP, 5, UP)
    is PickingTransition.WRONG_DIRECTION_CROSSING
)
assert (
    classify_pick_transition(5, DOWN, 6, DOWN)
    is PickingTransition.WRONG_DIRECTION_CROSSING
)

# The beat adapter projects the same P3 decisions without changing the event
# engine's semantics.
assert economy_pick_beats_v2(
    [[TA, OFF, TI]],
    [[TA, OFF, TI]],
    TI,
    TA,
    OFF,
    cyclic=False,
) == [[DOWN, None, DOWN]]

# P3 is deterministic and every attack decision explains itself.
assert economy_pick_events(p3_off_events, cyclic=False) == p3_off
assert all(
    decision.reason
    for event, decision in zip(p3_off_events, p3_off)
    if event.attack
)


# Picking Logic v2 P4: repeated whole-beat motifs are constraints inside the
# optimizer, not a post-processing rewrite.
p4_a = [TA, TI, TI, TA]
p4_b = [TI, TA, TI, TA]
p4_aaab_events = normalize_picking_events(
    [p4_a, p4_a, p4_a, p4_b],
    [p4_a, p4_a, p4_a, p4_b],
    TI,
    TA,
    OFF,
    stage_id="motif:aaab",
)
p4_aaab_annotated = annotate_whole_beat_motifs(p4_aaab_events)
p4_a_ids = {
    event.motif_id
    for event in p4_aaab_annotated
    if event.beat_index in (0, 1, 2)
}
assert len(p4_a_ids) == 1
assert None not in p4_a_ids
assert all(
    event.motif_id is None
    for event in p4_aaab_annotated
    if event.beat_index == 3
)

p4_aaab = economy_pick_events(p4_aaab_events, cyclic=True)
p4_aaab_rows = picking_directions_by_beat(
    p4_aaab_events,
    [decision.stroke for decision in p4_aaab],
    4,
)
assert p4_aaab_rows[0] == p4_aaab_rows[1] == p4_aaab_rows[2]

# Motif equality must not erase useful Economy. A starts 6->5, so the shared
# motor pattern should retain the directional DOWN/DOWN sweep.
assert p4_aaab_rows[0][0:2] == [DOWN, DOWN]

# A/B/A/B constrains both motif identities independently.
p4_abab_events = normalize_picking_events(
    [p4_a, p4_b, p4_a, p4_b],
    [p4_a, p4_b, p4_a, p4_b],
    TI,
    TA,
    OFF,
    stage_id="motif:abab",
)
p4_abab = economy_pick_events(p4_abab_events, cyclic=True)
p4_abab_rows = picking_directions_by_beat(
    p4_abab_events,
    [decision.stroke for decision in p4_abab],
    4,
)
assert p4_abab_rows[0] == p4_abab_rows[2]
assert p4_abab_rows[1] == p4_abab_rows[3]

# A motif repeated across the visual end/start region keeps one identity.
p4_aba_events = normalize_picking_events(
    [p4_a, p4_b, p4_a],
    [p4_a, p4_b, p4_a],
    TI,
    TA,
    OFF,
    stage_id="motif:aba",
)
p4_aba = economy_pick_events(p4_aba_events, cyclic=True)
p4_aba_rows = picking_directions_by_beat(
    p4_aba_events,
    [decision.stroke for decision in p4_aba],
    3,
)
assert p4_aba_rows[0] == p4_aba_rows[2]

# OFF slots participate in motif shape but not attack parity.
p4_rest_a = [TA, OFF, TI, TA]
p4_rest_events = normalize_picking_events(
    [p4_rest_a, p4_rest_a, p4_b],
    [p4_rest_a, p4_rest_a, p4_b],
    TI,
    TA,
    OFF,
    stage_id="motif:rests",
)
p4_rest = economy_pick_events(p4_rest_events, cyclic=True)
p4_rest_rows = picking_directions_by_beat(
    p4_rest_events,
    [decision.stroke for decision in p4_rest],
    3,
)
assert p4_rest_rows[0] == p4_rest_rows[1]
assert p4_rest_rows[0][1] is None

# Motif-constrained Economy remains deterministic.
assert economy_pick_events(p4_abab_events, cyclic=True) == p4_abab


# Picking Logic v2 P5: all Ramp stages are one constrained exercise.
p5_full = [
    [TA, TI, TI, TA],
    [TA, TI, TI, TA],
    [TA, TI, TI, TA],
    [TI, TA, TI, TA],
]
p5_stages = (1, 2, 3, 4)
p5_joint = economy_pick_ramp_stages_v2(
    p5_full,
    p5_stages,
    TI,
    TA,
    OFF,
)

# Every real attack keeps exactly one direction from the first stage where it
# appears through the final full-pattern stage.
for beat_index in range(4):
    reference = p5_joint[4][beat_index]
    for active in p5_stages:
        if beat_index < active:
            assert p5_joint[active][beat_index] == reference

# The repeated A motif is one motor pattern in the full stage, and that same
# constrained pattern is revealed progressively.
assert (
    p5_joint[4][0]
    == p5_joint[4][1]
    == p5_joint[4][2]
)
assert p5_joint[1][0] == p5_joint[4][0]
assert p5_joint[2][1] == p5_joint[4][1]
assert p5_joint[3][2] == p5_joint[4][2]

# Stage-local inactive TA pulses are not persistent real attacks. Within each
# stage they form a continuing same-string attack stream and therefore
# alternate instead of all restarting DOWN.
p5_stage1_placeholder_strokes = [
    p5_joint[1][beat_index][0]
    for beat_index in (1, 2, 3)
]
assert (
    p5_stage1_placeholder_strokes[0]
    != p5_stage1_placeholder_strokes[1]
)
assert (
    p5_stage1_placeholder_strokes[0]
    == p5_stage1_placeholder_strokes[2]
)

# The first real A keeps its useful 6->5 DOWN/DOWN sweep while remaining stable
# across every Ramp stage.
assert p5_joint[1][0][0:2] == [DOWN, DOWN]
assert p5_joint[4][0][0:2] == [DOWN, DOWN]

# Ramp 2->full is solved by the same persistent-identity rule rather than a
# special anchor stage.
p5_ramp2 = economy_pick_ramp_stages_v2(
    p5_full,
    (2, 4),
    TI,
    TA,
    OFF,
)
assert p5_ramp2[2][0] == p5_ramp2[4][0]
assert p5_ramp2[2][1] == p5_ramp2[4][1]

# Covered beats create no placeholder attack and do not disturb persistent
# identity of surrounding real attacks.
p5_covered_full = [
    [TA, TI],
    [],
    [TI, TA],
    [TA, TI],
]
p5_covered = economy_pick_ramp_stages_v2(
    p5_covered_full,
    (1, 2, 3, 4),
    TI,
    TA,
    OFF,
)
assert p5_covered[1][1] == []
assert p5_covered[2][1] == []
assert p5_covered[4][0] == p5_covered[1][0]

# Joint Ramp solving is deterministic.
assert economy_pick_ramp_stages_v2(
    p5_full,
    p5_stages,
    TI,
    TA,
    OFF,
) == p5_joint

# P6 screenshot regression: when an equal-cost odd placeholder chain makes one
# same-string repeat unavoidable, keep the active->placeholder entry clean and
# move that repeat to the cyclic return boundary instead.
p6_control_a = [TA, TI, TA, TA]
p6_control = economy_pick_ramp_stages_v2(
    [
        p6_control_a,
        p6_control_a,
        p6_control_a,
        [TI, TA, TI, TA],
    ],
    (1, 2, 3, 4),
    TI,
    TA,
    OFF,
)
p6_stage1_placeholders = [
    p6_control[1][beat_index][0]
    for beat_index in (1, 2, 3)
]
assert p6_stage1_placeholders[0] != p6_control[1][0][-1]
assert p6_stage1_placeholders[0] != p6_stage1_placeholders[1]
assert p6_stage1_placeholders[0] == p6_stage1_placeholders[2]


# Picking Logic v2 P7a: public first-stroke control belongs to Alternate.
# Economy's explicit start parameter remains an internal regression/debug hook.
p7_simple_events = normalize_picking_events(
    [[TA, TI]],
    [[TA, TI]],
    TI,
    TA,
    OFF,
    stage_id="p7:start",
)
assert [
    decision.stroke
    for decision in economy_pick_events(
        p7_simple_events,
        cyclic=False,
        start_direction=DOWN,
    )
] == [DOWN, DOWN]
assert [
    decision.stroke
    for decision in economy_pick_events(
        p7_simple_events,
        cyclic=False,
        start_direction=UP,
    )
] == [UP, DOWN]

# Auto remains the established optimizer behavior.
assert economy_pick_events(
    p7_simple_events,
    cyclic=False,
) == economy_pick_events(
    p7_simple_events,
    cyclic=False,
    start_direction=None,
)

# Internal Economy/Ramp hook still supports a fixed start for regression and
# possible future special exercises; the normal UI never passes this override.
p7_ramp_up = economy_pick_ramp_stages_v2(
    p5_full,
    p5_stages,
    TI,
    TA,
    OFF,
    start_direction=UP,
)
for active in p5_stages:
    assert p7_ramp_up[active][0][0] == UP

# Alternate supports the same user override while Auto/invalid still defaults
# to the product's normal DOWN-first attack-alternate behavior.
assert alternate_pick_events(p2_events, start_direction=UP)[0] == UP
assert alternate_pick_events(p2_events, start_direction=None)[0] == DOWN


# Picking Logic v2 P7b: explicit escape-motion profile scoring.
assert escape_profile_adjustment(
    EscapeProfile.USX, 6, UP, 5, DOWN
) < 0
assert escape_profile_adjustment(
    EscapeProfile.USX, 6, DOWN, 5, UP
) > 0
assert escape_profile_adjustment(
    EscapeProfile.DSX, 6, DOWN, 5, UP
) < 0
assert escape_profile_adjustment(
    EscapeProfile.DSX, 6, UP, 5, DOWN
) > 0
assert escape_profile_adjustment(
    EscapeProfile.DBX, 6, UP, 5, DOWN
) <= 0
assert escape_profile_adjustment(
    EscapeProfile.DBX, 6, DOWN, 5, UP
) <= 0
assert escape_profile_crossing_status(
    EscapeProfile.USX,
    UP,
    PickingTransition.ALTERNATE_CROSSING,
) == "compatible"
assert escape_profile_crossing_status(
    EscapeProfile.DSX,
    UP,
    PickingTransition.ALTERNATE_CROSSING,
) == "trapped"
assert escape_profile_crossing_status(
    EscapeProfile.USX,
    DOWN,
    PickingTransition.DIRECTIONAL_SWEEP,
) == "sweep"

# Profiles must be able to influence a complete Economy solution rather than
# existing only as metadata. Search a tiny deterministic two-string corpus.
profile_difference_found = False
for mask in range(1, 31):
    states = [
        TA if (mask >> bit) & 1 else TI
        for bit in range(5)
    ]
    if len(set(states)) < 2:
        continue
    events = normalize_picking_events(
        [states],
        [states],
        TI,
        TA,
        OFF,
        stage_id=f"p7b:{mask}",
    )
    usx = [
        decision.stroke
        for decision in economy_pick_events(
            events,
            cyclic=True,
            escape_profile=EscapeProfile.USX,
        )
    ]
    dsx = [
        decision.stroke
        for decision in economy_pick_events(
            events,
            cyclic=True,
            escape_profile=EscapeProfile.DSX,
        )
    ]
    if usx != dsx:
        profile_difference_found = True
        break
assert profile_difference_found

# Ramp keeps persistent real strokes stable even when an explicit mechanics
# profile participates in scoring.
p7b_ramp = economy_pick_ramp_stages_v2(
    p5_full,
    p5_stages,
    TI,
    TA,
    OFF,
    escape_profile=EscapeProfile.USX,
)
for beat_index in range(4):
    reference = p7b_ramp[4][beat_index]
    for active in p5_stages:
        if beat_index < active:
            assert p7b_ramp[active][beat_index] == reference


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
