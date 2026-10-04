from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction


DOWN = "↓"
UP = "↑"
PICKING_COVERED = "COVERED"


class PickingEventSource(str, Enum):
    """Origin of a normalized picking slot."""

    REAL_PATTERN = "real_pattern"
    RAMP_PLACEHOLDER = "ramp_placeholder"


@dataclass(frozen=True)
class PickingEvent:
    """Normalized Picking Logic v2 slot.

    P1 intentionally models identity and continuity without changing the
    current runtime optimizer. Real attacks receive a persistent id derived
    from their stored-pattern coordinates; generated Ramp placeholders never
    receive that id and remain stage-local.
    """

    slot_id: str
    beat_index: int
    subdivision_index: int | None
    source: PickingEventSource
    state: str
    attack: bool
    string: int | None
    phrase_boundary_before: bool
    reset_before: bool
    motif_id: str | None
    persistent_attack_id: str | None
    rhythmic_phase: Fraction


def _picking_string_for_state(
    state: str,
    ti_state: str,
    ta_state: str,
) -> int | None:
    if state == ti_state:
        return 5
    if state == ta_state:
        return 6
    return None


def normalize_picking_events(
    full_beats: list[list[str]],
    effective_beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    placeholder_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
    reset_before_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
    stage_id: str = "stage",
) -> list[PickingEvent]:
    """Normalize one effective exercise stage into Picking Logic v2 events.

    This is the P1 identity layer only. It deliberately does not decide pick
    directions yet.

    Rules:
    - real attacks keep stable coordinate-based persistent ids;
    - Ramp placeholder attacks are stage-local and have no persistent id;
    - OFF is a slot, not an automatic phrase reset;
    - covered metric beats become explicit COVERED events;
    - reset boundaries are explicit inputs rather than side effects of rests.
    """
    if len(full_beats) != len(effective_beats):
        raise ValueError("full and effective beat counts must match")

    placeholder_set = {int(index) for index in placeholder_beats}
    reset_set = {int(index) for index in reset_before_beats}
    beat_count = len(full_beats)

    if any(index < 0 or index >= beat_count for index in placeholder_set):
        raise ValueError("placeholder beat index out of range")
    if any(index < 0 or index >= beat_count for index in reset_set):
        raise ValueError("reset beat index out of range")

    allowed_states = {ti_state, ta_state, off_state}
    events: list[PickingEvent] = []

    for beat_index, (full_states, states) in enumerate(
        zip(full_beats, effective_beats)
    ):
        is_placeholder = beat_index in placeholder_set

        if not states:
            if is_placeholder:
                raise ValueError("covered beat cannot be a Ramp placeholder")
            events.append(
                PickingEvent(
                    slot_id=f"{stage_id}:b{beat_index}:covered",
                    beat_index=beat_index,
                    subdivision_index=None,
                    source=PickingEventSource.REAL_PATTERN,
                    state=PICKING_COVERED,
                    attack=False,
                    string=None,
                    phrase_boundary_before=(
                        not events or beat_index in reset_set
                    ),
                    reset_before=beat_index in reset_set,
                    motif_id=None,
                    persistent_attack_id=None,
                    rhythmic_phase=Fraction(0, 1),
                )
            )
            continue

        if not full_states:
            raise ValueError("effective slots cannot replace a covered beat")
        if len(full_states) != len(states):
            raise ValueError(
                "full and effective subdivision counts must match per beat"
            )
        if not is_placeholder and states != full_states:
            raise ValueError(
                "non-placeholder effective beat must match the full beat"
            )

        source = (
            PickingEventSource.RAMP_PLACEHOLDER
            if is_placeholder
            else PickingEventSource.REAL_PATTERN
        )

        for subdivision_index, state in enumerate(states):
            if state not in allowed_states:
                raise ValueError(f"unsupported picking state: {state!r}")

            string = _picking_string_for_state(state, ti_state, ta_state)
            attack = string is not None
            persistent_attack_id = None
            if source is PickingEventSource.REAL_PATTERN and attack:
                persistent_attack_id = (
                    f"beat:{beat_index}:sub:{subdivision_index}"
                )

            events.append(
                PickingEvent(
                    slot_id=(
                        f"{stage_id}:b{beat_index}:s{subdivision_index}"
                    ),
                    beat_index=beat_index,
                    subdivision_index=subdivision_index,
                    source=source,
                    state=state,
                    attack=attack,
                    string=string,
                    phrase_boundary_before=(
                        not events
                        or (
                            subdivision_index == 0
                            and beat_index in reset_set
                        )
                    ),
                    reset_before=(
                        subdivision_index == 0
                        and beat_index in reset_set
                    ),
                    motif_id=None,
                    persistent_attack_id=persistent_attack_id,
                    rhythmic_phase=Fraction(
                        subdivision_index,
                        len(states),
                    ),
                )
            )

    return events


def normalize_ramp_stage_events(
    full_beats: list[list[str]],
    active_beats: int,
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    stage_id: str | None = None,
    reset_before_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
) -> list[PickingEvent]:
    """Build a normalized Ramp stage with explicit placeholder identity.

    Inactive non-covered beats use the current Ramp training representation:
    TA on the beat followed by OFF for the remaining subdivisions.
    """
    beat_count = len(full_beats)
    active = max(0, min(beat_count, int(active_beats)))

    effective_beats: list[list[str]] = []
    placeholder_beats: set[int] = set()

    for beat_index, states in enumerate(full_beats):
        if beat_index >= active and states:
            effective_beats.append(
                [ta_state] + [off_state] * max(0, len(states) - 1)
            )
            placeholder_beats.add(beat_index)
        else:
            effective_beats.append(list(states))

    return normalize_picking_events(
        full_beats,
        effective_beats,
        ti_state,
        ta_state,
        off_state,
        placeholder_beats=placeholder_beats,
        reset_before_beats=reset_before_beats,
        stage_id=stage_id or f"ramp:{active}",
    )


def alternate_pick_events(
    events: list[PickingEvent],
    *,
    start_direction: str = DOWN,
) -> list[str | None]:
    """Assign deterministic attack-alternate strokes to normalized events.

    Alternate v2 advances only on attacks. OFF, COVERED, and any other
    non-attack slots receive no stroke and do not consume alternation parity.
    Explicit phrase/reset boundaries are intentionally ignored: the public
    Alternate strategy means consecutive attacks alternate across the complete
    effective exercise stream.

    The result is aligned one-to-one with `events`.
    """
    direction = start_direction if start_direction in (DOWN, UP) else DOWN
    result: list[str | None] = []

    for event in events:
        if not event.attack:
            result.append(None)
            continue
        if event.string not in (5, 6):
            raise ValueError("attack event must map to string 5 or 6")
        result.append(direction)
        direction = UP if direction == DOWN else DOWN

    return result


def picking_directions_by_beat(
    events: list[PickingEvent],
    directions: list[str | None],
    beat_count: int,
) -> list[list[str | None]]:
    """Project event-aligned stroke decisions back to beat/subdivision rows.

    This is a compatibility adapter for the current UI shape. Picking Logic v2
    itself operates on normalized events.
    """
    if len(events) != len(directions):
        raise ValueError("event and direction counts must match")

    count = max(0, int(beat_count))
    rows: list[list[str | None]] = [[] for _ in range(count)]

    for event, direction in zip(events, directions):
        if event.beat_index < 0 or event.beat_index >= count:
            raise ValueError("event beat index out of range")
        if event.subdivision_index is None:
            continue

        row = rows[event.beat_index]
        subdivision = event.subdivision_index
        while len(row) <= subdivision:
            row.append(None)
        row[subdivision] = direction

    return rows


def alternate_pick_beats_v2(
    full_beats: list[list[str]],
    effective_beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    placeholder_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
    start_direction: str = DOWN,
    stage_id: str = "alternate",
) -> list[list[str | None]]:
    """Compatibility adapter for Alternate v2.

    Normalize the exercise first, solve attack alternation on PickingEvent
    objects, then project the result back to the existing per-beat UI shape.
    """
    events = normalize_picking_events(
        full_beats,
        effective_beats,
        ti_state,
        ta_state,
        off_state,
        placeholder_beats=placeholder_beats,
        stage_id=stage_id,
    )
    directions = alternate_pick_events(
        events,
        start_direction=start_direction,
    )
    return picking_directions_by_beat(
        events,
        directions,
        len(full_beats),
    )


def annotate_whole_beat_motifs(
    events: list[PickingEvent],
) -> list[PickingEvent]:
    """Assign deterministic motif ids to repeated whole-beat event shapes.

    P4 starts with whole-beat motifs. A beat signature includes source, state,
    attack/string identity, rhythmic phase, and covered-slot shape. Only
    signatures that occur at least twice become constrained motifs.

    The function returns new immutable PickingEvent objects and preserves any
    explicit motif_id that a future caller may already have supplied.
    """
    if not events:
        return []

    beat_events: dict[int, list[PickingEvent]] = {}
    beat_order: list[int] = []
    for event in events:
        if event.beat_index not in beat_events:
            beat_events[event.beat_index] = []
            beat_order.append(event.beat_index)
        beat_events[event.beat_index].append(event)

    def signature(beat: list[PickingEvent]) -> tuple[tuple[object, ...], ...]:
        return tuple(
            (
                event.source.value,
                event.state,
                event.attack,
                event.string,
                event.subdivision_index,
                event.rhythmic_phase,
            )
            for event in beat
        )

    signatures = {
        beat_index: signature(beat_events[beat_index])
        for beat_index in beat_order
    }
    counts: dict[tuple[tuple[object, ...], ...], int] = {}
    for beat_index in beat_order:
        value = signatures[beat_index]
        counts[value] = counts.get(value, 0) + 1

    motif_for_signature: dict[tuple[tuple[object, ...], ...], str] = {}
    next_motif = 0
    result: list[PickingEvent] = []

    for beat_index in beat_order:
        beat = beat_events[beat_index]
        value = signatures[beat_index]
        motif_id: str | None = None
        if counts[value] >= 2:
            motif_id = motif_for_signature.get(value)
            if motif_id is None:
                motif_id = f"beat-motif:{next_motif}"
                motif_for_signature[value] = motif_id
                next_motif += 1

        for event in beat:
            if event.motif_id is not None or motif_id is None:
                result.append(event)
            else:
                result.append(replace(event, motif_id=motif_id))

    return result


def _motif_variable_keys(
    events: list[PickingEvent],
    attack_indices: list[int],
) -> dict[int, str]:
    """Map repeated-motif attacks to shared equality-variable keys."""
    attack_ordinal_by_beat: dict[int, int] = {}
    keys: dict[int, str] = {}

    for event_index in attack_indices:
        event = events[event_index]
        ordinal = attack_ordinal_by_beat.get(event.beat_index, 0)
        attack_ordinal_by_beat[event.beat_index] = ordinal + 1
        if event.motif_id is not None:
            keys[event_index] = f"{event.motif_id}:attack:{ordinal}"

    return keys


def _solve_economy_constrained(
    events: list[PickingEvent],
    attack_indices: list[int],
    *,
    cyclic: bool,
) -> list[str]:
    """Exact DP for Economy with shared motif-direction variables.

    Repeated motif attacks share a variable key, so equality is enforced while
    the full phrase/cycle is optimized. This replaces post-hoc rewriting: the
    optimizer never generates an inconsistent motif solution in the first
    place.

    Only motif variables that will reappear are retained in DP state, keeping
    unique one-off attacks cheap.
    """
    if not attack_indices:
        return []

    motif_keys = _motif_variable_keys(events, attack_indices)
    positions_by_key: dict[str, list[int]] = {}
    for position, event_index in enumerate(attack_indices):
        key = motif_keys.get(event_index)
        if key is not None:
            positions_by_key.setdefault(key, []).append(position)

    # A motif variable matters only if it is actually shared by two or more
    # attacks. Single-occurrence ids are equivalent to unconstrained attacks.
    shared_keys = {
        key
        for key, positions in positions_by_key.items()
        if len(positions) >= 2
    }
    last_position = {
        key: positions_by_key[key][-1]
        for key in shared_keys
    }

    directions = (DOWN, UP)
    # state -> (cost, path). State stores previous stroke, first stroke for the
    # cyclic closing edge, and currently-live shared motif assignments.
    states: dict[
        tuple[str | None, str | None, tuple[tuple[str, str], ...]],
        tuple[float, tuple[str, ...]],
    ] = {
        (None, None, ()): (0.0, ())
    }

    for position, event_index in enumerate(attack_indices):
        event = events[event_index]
        if event.string not in (5, 6):
            raise ValueError("attack event must map to string 5 or 6")

        key = motif_keys.get(event_index)
        if key not in shared_keys:
            key = None

        next_states: dict[
            tuple[str | None, str | None, tuple[tuple[str, str], ...]],
            tuple[float, tuple[str, ...]],
        ] = {}

        for (previous_stroke, first_stroke, assignments_tuple), (
            cost,
            path,
        ) in states.items():
            assignments = dict(assignments_tuple)
            if key is not None and key in assignments:
                choices = (assignments[key],)
            else:
                choices = directions

            reset = event.reset_before
            effective_previous = None if reset else previous_stroke

            previous_string: int | None = None
            if effective_previous is not None and position > 0:
                # Find the previous attack that belongs to the same phrase.
                previous_position = position - 1
                previous_event = events[attack_indices[previous_position]]
                if not event.reset_before:
                    previous_string = previous_event.string

            for stroke in choices:
                candidate_cost = cost
                if effective_previous is None:
                    candidate_cost += 0.0 if stroke == DOWN else 0.01
                else:
                    assert previous_string in (5, 6)
                    candidate_cost += _economy_transition_cost_v2(
                        previous_string,
                        effective_previous,
                        event.string,
                        stroke,
                    )

                next_assignments = dict(assignments)
                if key is not None and key not in next_assignments:
                    next_assignments[key] = stroke

                # Once the final occurrence has been processed, equality no
                # longer needs to occupy DP state.
                expired = [
                    live_key
                    for live_key in next_assignments
                    if last_position[live_key] == position
                ]
                for live_key in expired:
                    del next_assignments[live_key]

                candidate_first = first_stroke
                if candidate_first is None:
                    candidate_first = stroke

                state_key = (
                    stroke,
                    candidate_first,
                    tuple(sorted(next_assignments.items())),
                )
                candidate_path = path + (stroke,)
                existing = next_states.get(state_key)
                if existing is None or candidate_cost < existing[0]:
                    next_states[state_key] = (
                        candidate_cost,
                        candidate_path,
                    )
                elif (
                    existing is not None
                    and candidate_cost == existing[0]
                    and candidate_path < existing[1]
                ):
                    next_states[state_key] = (
                        candidate_cost,
                        candidate_path,
                    )

        states = next_states

    best_cost = float("inf")
    best_path: tuple[str, ...] | None = None
    first_event = events[attack_indices[0]]
    last_event = events[attack_indices[-1]]

    has_reset = any(
        events[event_index].reset_before
        for event_index in attack_indices
    )
    close_cycle = cyclic and not has_reset

    for (last_stroke, first_stroke, _assignments), (cost, path) in states.items():
        total = cost
        if close_cycle:
            assert last_stroke in directions
            assert first_stroke in directions
            assert first_event.string in (5, 6)
            assert last_event.string in (5, 6)
            total += _economy_transition_cost_v2(
                last_event.string,
                last_stroke,
                first_event.string,
                first_stroke,
            )

        if best_path is None or total < best_cost:
            best_cost = total
            best_path = path
        elif total == best_cost and path < best_path:
            best_path = path

    assert best_path is not None
    return list(best_path)


class PickingTransition(str, Enum):
    """Mechanical relation from the previous attack to the current attack."""

    NONE = "none"
    RESET = "reset"
    SAME_STRING_ALTERNATE = "same_string_alternate"
    SAME_STRING_REPEAT = "same_string_repeat"
    ALTERNATE_CROSSING = "alternate_crossing"
    DIRECTIONAL_SWEEP = "directional_sweep"
    WRONG_DIRECTION_CROSSING = "wrong_direction_crossing"


@dataclass(frozen=True)
class PickDecision:
    """Picking Logic v2 decision aligned to one normalized event."""

    stroke: str | None
    transition_from_previous: PickingTransition
    sweep_group_id: str | None
    reason: str
    attack_parity: int | None
    loop_boundary: bool = False


def classify_pick_transition(
    previous_string: int,
    previous_stroke: str,
    string: int,
    stroke: str,
) -> PickingTransition:
    """Classify one attack-to-attack mechanical transition."""
    if previous_string == string:
        if previous_stroke != stroke:
            return PickingTransition.SAME_STRING_ALTERNATE
        return PickingTransition.SAME_STRING_REPEAT

    if previous_stroke != stroke:
        return PickingTransition.ALTERNATE_CROSSING

    if (
        previous_string == 6
        and string == 5
        and stroke == DOWN
    ) or (
        previous_string == 5
        and string == 6
        and stroke == UP
    ):
        return PickingTransition.DIRECTIONAL_SWEEP

    return PickingTransition.WRONG_DIRECTION_CROSSING


def _economy_transition_cost_v2(
    previous_string: int,
    previous_stroke: str,
    string: int,
    stroke: str,
) -> float:
    transition = classify_pick_transition(
        previous_string,
        previous_stroke,
        string,
        stroke,
    )
    if transition is PickingTransition.SAME_STRING_ALTERNATE:
        return 0.0
    if transition is PickingTransition.DIRECTIONAL_SWEEP:
        return -4.0
    if transition is PickingTransition.ALTERNATE_CROSSING:
        return 0.0
    if transition is PickingTransition.SAME_STRING_REPEAT:
        return 100.0
    if transition is PickingTransition.WRONG_DIRECTION_CROSSING:
        return 100.0
    raise AssertionError(f"unexpected transition: {transition}")


def _transition_reason(
    transition: PickingTransition,
    previous_string: int,
    previous_stroke: str,
    string: int,
    stroke: str,
) -> str:
    if transition is PickingTransition.SAME_STRING_ALTERNATE:
        return f"same-string alternate on string {string}: {previous_stroke}->{stroke}"
    if transition is PickingTransition.SAME_STRING_REPEAT:
        return f"same-string repeated stroke on string {string}: {stroke}"
    if transition is PickingTransition.DIRECTIONAL_SWEEP:
        return (
            f"directional sweep {previous_string}->{string}: "
            f"{previous_stroke}->{stroke}"
        )
    if transition is PickingTransition.ALTERNATE_CROSSING:
        return (
            f"alternate string crossing {previous_string}->{string}: "
            f"{previous_stroke}->{stroke}"
        )
    if transition is PickingTransition.WRONG_DIRECTION_CROSSING:
        return (
            f"same-stroke crossing is not a directional sweep "
            f"{previous_string}->{string}: {stroke}"
        )
    return transition.value


def _solve_economy_attack_segment(
    attacks: list[PickingEvent],
    *,
    cyclic: bool,
) -> list[str]:
    """Choose DOWN/UP for one reset-free attack segment."""
    if not attacks:
        return []

    directions = (DOWN, UP)
    best_total = float("inf")
    best_result: list[str] | None = None

    for first_stroke in directions:
        layers: list[dict[str, tuple[float, str | None]]] = [
            {
                first_stroke: (
                    0.0 if first_stroke == DOWN else 0.01,
                    None,
                )
            }
        ]

        for attack_index in range(1, len(attacks)):
            previous_string = attacks[attack_index - 1].string
            string = attacks[attack_index].string
            if previous_string not in (5, 6) or string not in (5, 6):
                raise ValueError("attack event must map to string 5 or 6")

            layer: dict[str, tuple[float, str | None]] = {}
            for stroke in directions:
                best_cost = float("inf")
                best_previous: str | None = None
                for previous_stroke, (previous_cost, _parent) in layers[-1].items():
                    candidate = previous_cost + _economy_transition_cost_v2(
                        previous_string,
                        previous_stroke,
                        string,
                        stroke,
                    )
                    if candidate < best_cost:
                        best_cost = candidate
                        best_previous = previous_stroke
                layer[stroke] = (best_cost, best_previous)
            layers.append(layer)

        for final_stroke, (path_cost, _parent) in layers[-1].items():
            total = path_cost
            if cyclic:
                last_string = attacks[-1].string
                first_string = attacks[0].string
                if last_string not in (5, 6) or first_string not in (5, 6):
                    raise ValueError("attack event must map to string 5 or 6")
                total += _economy_transition_cost_v2(
                    last_string,
                    final_stroke,
                    first_string,
                    first_stroke,
                )

            if total >= best_total:
                continue

            result = [final_stroke]
            for attack_index in range(len(attacks) - 1, 0, -1):
                previous = layers[attack_index][result[-1]][1]
                assert previous is not None
                result.append(previous)
            result.reverse()

            best_total = total
            best_result = result

    assert best_result is not None
    return best_result


def economy_pick_events(
    events: list[PickingEvent],
    *,
    cyclic: bool,
) -> list[PickDecision]:
    """Solve practical directional Economy on normalized PickingEvent data.

    P3 handles transition mechanics only. Motif equality and joint Ramp-stage
    constraints are deliberately deferred to P4/P5.

    OFF/COVERED slots do not break continuity. Only explicit `reset_before`
    boundaries split phrases. If there is no explicit reset, `cyclic=True`
    scores the real last->first loop transition.

    P4 whole-beat motif equality is applied before optimization, so repeated
    motif attacks share stroke variables instead of being rewritten afterward.
    """
    events = annotate_whole_beat_motifs(events)
    decisions = [
        PickDecision(
            stroke=None,
            transition_from_previous=PickingTransition.NONE,
            sweep_group_id=None,
            reason="non-attack slot",
            attack_parity=None,
        )
        for _event in events
    ]

    attack_indices = [
        index
        for index, event in enumerate(events)
        if event.attack
    ]
    if not attack_indices:
        return decisions

    for index in attack_indices:
        if events[index].string not in (5, 6):
            raise ValueError("attack event must map to string 5 or 6")

    explicit_reset_positions = [
        position
        for position, event_index in enumerate(attack_indices)
        if events[event_index].reset_before
    ]

    segments: list[list[int]] = []
    cycle_segment = cyclic and not explicit_reset_positions

    if cycle_segment:
        segments = [attack_indices]
    else:
        current: list[int] = []
        for event_index in attack_indices:
            if events[event_index].reset_before and current:
                segments.append(current)
                current = []
            current.append(event_index)
        if current:
            segments.append(current)

    strokes_by_event: dict[int, str] = {}
    parity_by_event: dict[int, int] = {}

    constrained_strokes = _solve_economy_constrained(
        events,
        attack_indices,
        cyclic=cyclic,
    )
    for event_index, stroke in zip(attack_indices, constrained_strokes):
        strokes_by_event[event_index] = stroke

    for segment in segments:
        for parity, event_index in enumerate(segment):
            parity_by_event[event_index] = parity % 2

    transition_by_event: dict[int, PickingTransition] = {}
    reason_by_event: dict[int, str] = {}
    loop_by_event: dict[int, bool] = {}
    sweep_group_by_event: dict[int, str] = {}

    for segment_index, segment in enumerate(segments):
        for local_index, event_index in enumerate(segment):
            event = events[event_index]
            stroke = strokes_by_event[event_index]

            if local_index == 0:
                if cycle_segment and len(segments) == 1:
                    previous_index = segment[-1]
                    previous_event = events[previous_index]
                    previous_stroke = strokes_by_event[previous_index]
                    transition = classify_pick_transition(
                        previous_event.string,
                        previous_stroke,
                        event.string,
                        stroke,
                    )
                    transition_by_event[event_index] = transition
                    reason_by_event[event_index] = (
                        "loop boundary: "
                        + _transition_reason(
                            transition,
                            previous_event.string,
                            previous_stroke,
                            event.string,
                            stroke,
                        )
                    )
                    loop_by_event[event_index] = True
                else:
                    transition = (
                        PickingTransition.RESET
                        if event.reset_before
                        else PickingTransition.NONE
                    )
                    transition_by_event[event_index] = transition
                    if transition is PickingTransition.RESET:
                        reason_by_event[event_index] = (
                            f"explicit phrase reset; start {stroke}"
                        )
                    else:
                        reason_by_event[event_index] = (
                            f"phrase start selected by economy search: {stroke}"
                        )
                    loop_by_event[event_index] = False
                continue

            previous_index = segment[local_index - 1]
            previous_event = events[previous_index]
            previous_stroke = strokes_by_event[previous_index]
            transition = classify_pick_transition(
                previous_event.string,
                previous_stroke,
                event.string,
                stroke,
            )
            transition_by_event[event_index] = transition
            reason_by_event[event_index] = _transition_reason(
                transition,
                previous_event.string,
                previous_stroke,
                event.string,
                stroke,
            )
            loop_by_event[event_index] = False

    # A directional sweep is a linked two-attack motion. Give both attacks the
    # same group id so later UI/debug code can distinguish a real sweep from
    # two unrelated identical arrows.
    for segment in segments:
        for local_index, event_index in enumerate(segment):
            transition = transition_by_event[event_index]
            if transition is not PickingTransition.DIRECTIONAL_SWEEP:
                continue
            if local_index == 0 and cycle_segment:
                previous_index = segment[-1]
            elif local_index > 0:
                previous_index = segment[local_index - 1]
            else:
                continue
            group_id = (
                f"sweep:{events[previous_index].slot_id}"
                f"->{events[event_index].slot_id}"
            )
            sweep_group_by_event[previous_index] = group_id
            sweep_group_by_event[event_index] = group_id

    for event_index in attack_indices:
        decisions[event_index] = PickDecision(
            stroke=strokes_by_event[event_index],
            transition_from_previous=transition_by_event[event_index],
            sweep_group_id=sweep_group_by_event.get(event_index),
            reason=reason_by_event[event_index],
            attack_parity=parity_by_event[event_index],
            loop_boundary=loop_by_event[event_index],
        )

    return decisions


def economy_pick_beats_v2(
    full_beats: list[list[str]],
    effective_beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    placeholder_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
    reset_before_beats: set[int] | frozenset[int] | tuple[int, ...] = (),
    cyclic: bool = True,
    stage_id: str = "economy",
) -> list[list[str | None]]:
    """Compatibility projection for the P3 event-based Economy engine."""
    events = normalize_picking_events(
        full_beats,
        effective_beats,
        ti_state,
        ta_state,
        off_state,
        placeholder_beats=placeholder_beats,
        reset_before_beats=reset_before_beats,
        stage_id=stage_id,
    )
    decisions = economy_pick_events(events, cyclic=cyclic)
    return picking_directions_by_beat(
        events,
        [decision.stroke for decision in decisions],
        len(full_beats),
    )


def _best_placeholder_bridge(
    previous_string: int,
    previous_stroke: str,
    first_string: int,
    first_stroke: str,
    placeholder_count: int,
) -> tuple[float, tuple[str, ...]]:
    """Optimize a stage-local string-6 placeholder chain between real attacks."""
    count = max(0, int(placeholder_count))
    if count == 0:
        return (
            _economy_transition_cost_v2(
                previous_string,
                previous_stroke,
                first_string,
                first_stroke,
            ),
            (),
        )

    directions = (DOWN, UP)
    # Secondary score keeps the temporary TA stream itself alternating when
    # several bridge paths have the same mechanical cost. If one repeat is
    # unavoidable in an odd cyclic phrase, prefer placing it at the boundary
    # back into the real pattern rather than between two placeholder beats.
    states: dict[str, tuple[float, int, int, tuple[str, ...]]] = {}
    for stroke in directions:
        states[stroke] = (
            _economy_transition_cost_v2(
                previous_string,
                previous_stroke,
                6,
                stroke,
            ),
            0,
            int(previous_string == 6 and previous_stroke == stroke),
            (stroke,),
        )

    for _position in range(1, count):
        next_states: dict[str, tuple[float, int, int, tuple[str, ...]]] = {}
        for stroke in directions:
            best: tuple[float, int, int, tuple[str, ...]] | None = None
            for previous_placeholder, (
                cost,
                repeats,
                entry_repeat,
                path,
            ) in states.items():
                candidate = (
                    cost
                    + _economy_transition_cost_v2(
                        6,
                        previous_placeholder,
                        6,
                        stroke,
                    ),
                    repeats + int(previous_placeholder == stroke),
                    entry_repeat,
                    path + (stroke,),
                )
                if best is None or candidate < best:
                    best = candidate
            assert best is not None
            next_states[stroke] = best
        states = next_states

    best_total: tuple[float, int, int, tuple[str, ...]] | None = None
    for last_placeholder, (
        cost,
        repeats,
        entry_repeat,
        path,
    ) in states.items():
        candidate = (
            cost
            + _economy_transition_cost_v2(
                6,
                last_placeholder,
                first_string,
                first_stroke,
            ),
            repeats,
            entry_repeat,
            path,
        )
        if best_total is None or candidate < best_total:
            best_total = candidate

    assert best_total is not None
    cost, _repeats, _entry_repeat, path = best_total
    return cost, path


def _joint_ramp_real_strokes(
    full_events: list[PickingEvent],
    stage_events: dict[int, list[PickingEvent]],
) -> dict[str, str]:
    """Solve all real Ramp attacks once across every practised stage.

    Real pattern attacks are represented by one persistent variable regardless
    of how many Ramp stages contain them. Stage-local placeholder chains are
    analytically minimized at each cyclic stage boundary.

    The real attack sequence is a chain plus stage-boundary factors back to the
    first real attack. Whole-beat motif variables from P4 remain equality
    constraints inside this joint DP.
    """
    annotated_full = annotate_whole_beat_motifs(full_events)
    full_attack_indices = [
        index
        for index, event in enumerate(annotated_full)
        if event.attack
    ]
    if not full_attack_indices:
        return {}

    real_events = [
        annotated_full[index]
        for index in full_attack_indices
    ]
    real_ids: list[str] = []
    for event in real_events:
        if event.persistent_attack_id is None:
            raise ValueError("full Ramp attack must have persistent identity")
        real_ids.append(event.persistent_attack_id)

    real_position = {
        persistent_id: position
        for position, persistent_id in enumerate(real_ids)
    }

    motif_key_by_position: dict[int, str] = {}
    raw_motif_keys = _motif_variable_keys(
        annotated_full,
        full_attack_indices,
    )
    positions_by_motif: dict[str, list[int]] = {}
    for position, event_index in enumerate(full_attack_indices):
        key = raw_motif_keys.get(event_index)
        if key is not None:
            positions_by_motif.setdefault(key, []).append(position)
    shared_motif_keys = {
        key
        for key, positions in positions_by_motif.items()
        if len(positions) >= 2
    }
    for position, event_index in enumerate(full_attack_indices):
        key = raw_motif_keys.get(event_index)
        if key in shared_motif_keys:
            motif_key_by_position[position] = key

    motif_last_position = {
        key: positions[-1]
        for key, positions in positions_by_motif.items()
        if key in shared_motif_keys
    }

    # Each real->real edge is paid once for every stage in which both attacks
    # are already open.
    edge_weights = [0] * len(real_events)

    # Stages with a real prefix contribute a cyclic boundary factor from the
    # last open real attack, through zero or more temporary TA placeholders,
    # back to the first real attack.
    boundary_factors: dict[int, list[int]] = {}

    full_prefix = real_ids
    for active_beats, events in stage_events.items():
        del active_beats  # stage identity is carried by the mapping key only.
        stage_real_ids = [
            event.persistent_attack_id
            for event in events
            if event.attack
            and event.source is PickingEventSource.REAL_PATTERN
        ]
        if any(value is None for value in stage_real_ids):
            raise ValueError("real Ramp attack missing persistent identity")

        stage_real_ids = [str(value) for value in stage_real_ids]
        if stage_real_ids != full_prefix[: len(stage_real_ids)]:
            raise ValueError("Ramp real attacks must form a full-pattern prefix")

        for position in range(1, len(stage_real_ids)):
            edge_weights[position] += 1

        if stage_real_ids:
            placeholder_count = sum(
                1
                for event in events
                if event.attack
                and event.source is PickingEventSource.RAMP_PLACEHOLDER
            )
            last_position = real_position[stage_real_ids[-1]]
            boundary_factors.setdefault(last_position, []).append(
                placeholder_count
            )

    directions = (DOWN, UP)
    # State: previous real stroke, first real stroke, live motif assignments.
    states: dict[
        tuple[str | None, str | None, tuple[tuple[str, str], ...]],
        tuple[float, tuple[str, ...]],
    ] = {
        (None, None, ()): (0.0, ())
    }

    for position, event in enumerate(real_events):
        key = motif_key_by_position.get(position)
        next_states: dict[
            tuple[str | None, str | None, tuple[tuple[str, str], ...]],
            tuple[float, tuple[str, ...]],
        ] = {}

        for (previous_stroke, first_stroke, assignments_tuple), (
            cost,
            path,
        ) in states.items():
            assignments = dict(assignments_tuple)
            if key is not None and key in assignments:
                choices = (assignments[key],)
            else:
                choices = directions

            for stroke in choices:
                candidate_cost = cost

                if position == 0:
                    # One tiny global tie-break only. Individual Ramp stages
                    # are cyclic and therefore do not each impose a fake start.
                    candidate_cost += 0.0 if stroke == DOWN else 0.01
                    candidate_first = stroke
                else:
                    assert previous_stroke in directions
                    weight = edge_weights[position]
                    if weight:
                        previous_event = real_events[position - 1]
                        assert previous_event.string in (5, 6)
                        assert event.string in (5, 6)
                        candidate_cost += weight * _economy_transition_cost_v2(
                            previous_event.string,
                            previous_stroke,
                            event.string,
                            stroke,
                        )
                    candidate_first = first_stroke

                assert candidate_first in directions

                for placeholder_count in boundary_factors.get(position, ()):
                    assert event.string in (5, 6)
                    first_event = real_events[0]
                    assert first_event.string in (5, 6)
                    boundary_cost, _placeholder_path = _best_placeholder_bridge(
                        event.string,
                        stroke,
                        first_event.string,
                        candidate_first,
                        placeholder_count,
                    )
                    candidate_cost += boundary_cost

                next_assignments = dict(assignments)
                if key is not None and key not in next_assignments:
                    next_assignments[key] = stroke

                expired = [
                    live_key
                    for live_key in next_assignments
                    if motif_last_position[live_key] == position
                ]
                for live_key in expired:
                    del next_assignments[live_key]

                state_key = (
                    stroke,
                    candidate_first,
                    tuple(sorted(next_assignments.items())),
                )
                candidate_path = path + (stroke,)
                existing = next_states.get(state_key)
                if existing is None or candidate_cost < existing[0]:
                    next_states[state_key] = (
                        candidate_cost,
                        candidate_path,
                    )
                elif (
                    existing is not None
                    and candidate_cost == existing[0]
                    and candidate_path < existing[1]
                ):
                    next_states[state_key] = (
                        candidate_cost,
                        candidate_path,
                    )

        states = next_states

    best: tuple[float, tuple[str, ...]] | None = None
    for _state, candidate in states.items():
        if best is None or candidate < best:
            best = candidate

    assert best is not None
    _cost, path = best
    return {
        persistent_id: stroke
        for persistent_id, stroke in zip(real_ids, path)
    }


def economy_pick_ramp_stages_v2(
    full_beats: list[list[str]],
    stage_active_counts: tuple[int, ...] | list[int],
    ti_state: str,
    ta_state: str,
    off_state: str,
) -> dict[int, list[list[str | None]]]:
    """Jointly solve all requested Ramp stages.

    Real stored-pattern attacks keep one stroke across every stage in which
    they exist. Temporary Ramp TA pulses are stage-local and are optimized only
    inside their own cyclic stage. P4 whole-beat motif equality is derived from
    the full real pattern and participates in the same joint real-attack solve.
    """
    beat_count = len(full_beats)
    stages: list[int] = []
    for raw_active in stage_active_counts:
        active = max(0, min(beat_count, int(raw_active)))
        if active not in stages:
            stages.append(active)
    if not stages:
        stages.append(beat_count)

    stage_events = {
        active: normalize_ramp_stage_events(
            full_beats,
            active,
            ti_state,
            ta_state,
            off_state,
            stage_id=f"ramp-v2:{active}",
        )
        for active in stages
    }
    full_events = normalize_ramp_stage_events(
        full_beats,
        beat_count,
        ti_state,
        ta_state,
        off_state,
        stage_id="ramp-v2:full",
    )

    real_strokes = _joint_ramp_real_strokes(
        full_events,
        stage_events,
    )

    result: dict[int, list[list[str | None]]] = {}
    for active in stages:
        events = stage_events[active]
        directions: list[str | None] = [None] * len(events)
        real_attack_indices = [
            index
            for index, event in enumerate(events)
            if event.attack
            and event.source is PickingEventSource.REAL_PATTERN
        ]
        placeholder_attack_indices = [
            index
            for index, event in enumerate(events)
            if event.attack
            and event.source is PickingEventSource.RAMP_PLACEHOLDER
        ]

        for event_index in real_attack_indices:
            event = events[event_index]
            if event.persistent_attack_id is None:
                raise ValueError("real Ramp attack missing persistent identity")
            directions[event_index] = real_strokes[event.persistent_attack_id]

        if placeholder_attack_indices:
            if real_attack_indices:
                last_real = events[real_attack_indices[-1]]
                first_real = events[real_attack_indices[0]]
                last_stroke = directions[real_attack_indices[-1]]
                first_stroke = directions[real_attack_indices[0]]
                assert last_real.string in (5, 6)
                assert first_real.string in (5, 6)
                assert last_stroke in (DOWN, UP)
                assert first_stroke in (DOWN, UP)
                _cost, placeholder_path = _best_placeholder_bridge(
                    last_real.string,
                    last_stroke,
                    first_real.string,
                    first_stroke,
                    len(placeholder_attack_indices),
                )
            else:
                placeholder_events = [
                    events[index]
                    for index in placeholder_attack_indices
                ]
                placeholder_path = tuple(
                    _solve_economy_attack_segment(
                        placeholder_events,
                        cyclic=True,
                    )
                )

            for event_index, stroke in zip(
                placeholder_attack_indices,
                placeholder_path,
            ):
                directions[event_index] = stroke

        result[active] = picking_directions_by_beat(
            events,
            directions,
            beat_count,
        )

    return result
