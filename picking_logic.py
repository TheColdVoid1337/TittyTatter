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


def _transition_cost(previous_string: int, previous_direction: str, string: int, direction: str) -> float:
    if previous_string == string:
        # Repeated notes on one string are fastest with alternate picking.
        return 0.0 if previous_direction != direction else 4.0

    if previous_string == 6 and string == 5:
        # A downstroke naturally sweeps from string 6 toward string 5.
        if previous_direction == DOWN and direction == DOWN:
            return 0.0
        if previous_direction != direction:
            return 1.6
        return 4.5

    if previous_string == 5 and string == 6:
        # An upstroke naturally sweeps from string 5 toward string 6.
        if previous_direction == UP and direction == UP:
            return 0.0
        if previous_direction != direction:
            return 1.6
        return 4.5

    return 0.0 if previous_direction != direction else 2.0


def _optimise_run(
    strings: list[int],
    fixed: list[str | None] | None = None,
) -> list[str]:
    if not strings:
        return []

    directions = (DOWN, UP)
    if fixed is None:
        fixed = [None] * len(strings)
    if len(fixed) != len(strings):
        raise ValueError("fixed picking length must match attack count")

    first_choices = (fixed[0],) if fixed[0] in directions else directions
    # Tiny downstroke preference only breaks exact ties. The dynamic program is
    # still free to choose an upstroke start when it enables a cheaper sweep.
    costs: list[dict[str, tuple[float, str | None]]] = [
        {
            direction: (0.0 if direction == DOWN else 0.02, None)
            for direction in first_choices
        }
    ]

    for index in range(1, len(strings)):
        layer: dict[str, tuple[float, str | None]] = {}
        choices = (fixed[index],) if fixed[index] in directions else directions
        for direction in choices:
            best_cost = float("inf")
            best_previous: str | None = None
            for previous_direction, (previous_cost, _previous) in costs[index - 1].items():
                candidate = previous_cost + _transition_cost(
                    strings[index - 1],
                    previous_direction,
                    strings[index],
                    direction,
                )
                if candidate < best_cost:
                    best_cost = candidate
                    best_previous = previous_direction
            layer[direction] = (best_cost, best_previous)
        costs.append(layer)

    final_direction = min(costs[-1], key=lambda direction: costs[-1][direction][0])
    result = [final_direction]
    for index in range(len(strings) - 1, 0, -1):
        previous = costs[index][result[-1]][1]
        assert previous is not None
        result.append(previous)
    result.reverse()
    return result


def _optimise_cycle(
    strings: list[int],
    fixed: list[str | None] | None = None,
) -> list[str]:
    """Optimize a phrase whose last attack leads back into its first attack."""
    if not strings:
        return []

    directions = (DOWN, UP)
    if fixed is None:
        fixed = [None] * len(strings)
    if len(fixed) != len(strings):
        raise ValueError("fixed picking length must match attack count")

    best_total = float("inf")
    best_result: list[str] | None = None
    first_choices = (fixed[0],) if fixed[0] in directions else directions

    for first_direction in first_choices:
        layers: list[dict[str, tuple[float, str | None]]] = [
            {first_direction: (0.0, None)}
        ]

        for index in range(1, len(strings)):
            layer: dict[str, tuple[float, str | None]] = {}
            choices = (fixed[index],) if fixed[index] in directions else directions
            for direction in choices:
                best_cost = float("inf")
                best_previous: str | None = None
                for previous_direction, (previous_cost, _previous) in layers[-1].items():
                    candidate = previous_cost + _transition_cost(
                        strings[index - 1],
                        previous_direction,
                        strings[index],
                        direction,
                    )
                    if candidate < best_cost:
                        best_cost = candidate
                        best_previous = previous_direction
                layer[direction] = (best_cost, best_previous)
            layers.append(layer)

        for final_direction, (path_cost, _previous) in layers[-1].items():
            total = path_cost + _transition_cost(
                strings[-1],
                final_direction,
                strings[0],
                first_direction,
            )
            # Stable tie-break: prefer a downstroke start when two cycles are
            # musically equivalent.
            if first_direction == UP:
                total += 0.02
            if total >= best_total:
                continue

            result = [final_direction]
            for index in range(len(strings) - 1, 0, -1):
                previous = layers[index][result[-1]][1]
                assert previous is not None
                result.append(previous)
            result.reverse()

            best_total = total
            best_result = result

    assert best_result is not None
    return best_result


def economy_pick_pattern(
    states: list[str],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    cyclic: bool = False,
    fixed_directions: list[str | None] | None = None,
) -> list[str | None]:
    """Choose an efficient pick direction for each rhythmic slot.

    TI is string 5 and TA is string 6. Consecutive attacks are optimized as a
    phrase: same-string notes favour alternate picking, while 6→5 favours a
    downstroke sweep and 5→6 favours an upstroke sweep. A rest splits the
    phrase. In cyclic mode the end of the phrase is also optimized against its
    beginning, which is required for a continuously repeating loop.
    """
    if fixed_directions is not None and len(fixed_directions) != len(states):
        raise ValueError("fixed picking length must match rhythmic slot count")

    if cyclic and states:
        separators = [
            index
            for index, state in enumerate(states)
            if state not in (ti_state, ta_state)
        ]
        if not separators:
            strings = [5 if state == ti_state else 6 for state in states]
            return list(_optimise_cycle(strings, fixed_directions))

        # Rotate the loop so a rest/invalid slot is the boundary. That boundary
        # already breaks picking continuity, so ordinary linear optimization is
        # correct for the rotated phrase.
        cut = separators[0]
        rotated = states[cut:] + states[:cut]
        rotated_fixed = None
        if fixed_directions is not None:
            rotated_fixed = fixed_directions[cut:] + fixed_directions[:cut]
        rotated_result = economy_pick_pattern(
            rotated,
            ti_state,
            ta_state,
            off_state,
            cyclic=False,
            fixed_directions=rotated_fixed,
        )
        result: list[str | None] = [None] * len(states)
        for rotated_index, direction in enumerate(rotated_result):
            original_index = (cut + rotated_index) % len(states)
            result[original_index] = direction
        return result

    result: list[str | None] = [None] * len(states)
    run_slots: list[int] = []
    run_strings: list[int] = []
    run_fixed: list[str | None] = []

    def flush() -> None:
        if not run_slots:
            return
        directions = _optimise_run(run_strings, run_fixed)
        for slot, direction in zip(run_slots, directions):
            result[slot] = direction
        run_slots.clear()
        run_strings.clear()
        run_fixed.clear()

    for slot, state in enumerate(states):
        if state == off_state:
            flush()
            continue
        if state == ti_state:
            string = 5
        elif state == ta_state:
            string = 6
        else:
            flush()
            continue
        run_slots.append(slot)
        run_strings.append(string)
        run_fixed.append(
            fixed_directions[slot] if fixed_directions is not None else None
        )

    flush()
    return result


def strict_alternate_pick_beats(
    beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    start_direction: str = DOWN,
) -> list[list[str | None]]:
    """Assign strict down/up alternation across every attack in the bar.

    Rests and covered beats do not consume a pick direction. The displayed bar
    starts with the requested direction (down by default), making this strategy
    predictable for deliberate alternate-picking drills.
    """
    direction = start_direction if start_direction in (DOWN, UP) else DOWN
    result: list[list[str | None]] = []

    for states in beats:
        if not states:
            result.append([])
            continue

        beat_result: list[str | None] = []
        for state in states:
            if state in (ti_state, ta_state):
                beat_result.append(direction)
                direction = UP if direction == DOWN else DOWN
            else:
                beat_result.append(None)
        result.append(beat_result)

    return result


def _minimal_beat_period(beats: list[list[str]]) -> int:
    """Return the shortest whole-beat period that tiles the complete bar."""
    count = len(beats)
    if count <= 1:
        return count

    for period in range(1, count + 1):
        if count % period:
            continue
        if all(beats[index] == beats[index % period] for index in range(count)):
            return period
    return count


def _economy_pick_beat_block(
    beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    period: int,
    cyclic: bool,
    fixed_by_beat: list[list[str | None]] | None = None,
) -> list[list[str | None]]:
    """Optimize one beat block and repeat its requested whole-beat period."""
    base_beats = beats[:period]
    if fixed_by_beat is not None and len(fixed_by_beat) != len(beats):
        raise ValueError("fixed beat picking length must match beat count")

    flat: list[str] = []
    flat_fixed: list[str | None] = []
    spans: list[tuple[int, int, bool]] = []
    for beat_index, states in enumerate(base_beats):
        start = len(flat)
        if states:
            flat.extend(states)
            if fixed_by_beat is None:
                flat_fixed.extend([None] * len(states))
            else:
                fixed_states = fixed_by_beat[beat_index]
                if len(fixed_states) != len(states):
                    raise ValueError("fixed beat picking must match subdivision count")
                flat_fixed.extend(fixed_states)
            spans.append((start, len(states), True))
        else:
            # Covered metric beats need a separator so picking does not bridge
            # through an event that belongs to a spanning previous beat.
            flat.append(off_state)
            flat_fixed.append(None)
            spans.append((start, 1, False))

    flat_directions = economy_pick_pattern(
        flat,
        ti_state,
        ta_state,
        off_state,
        cyclic=cyclic,
        fixed_directions=flat_fixed,
    )

    base_directions: list[list[str | None]] = []
    for start, length, visible in spans:
        if visible:
            base_directions.append(list(flat_directions[start : start + length]))
        else:
            base_directions.append([])

    return [
        list(base_directions[index % period])
        for index in range(len(beats))
    ]


def _stabilise_repeated_beat_runs(
    beats: list[list[str]],
    directions: list[list[str | None]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    cyclic: bool,
) -> list[list[str | None]]:
    """Keep consecutive identical beats as one repeatable motor pattern.

    Economy picking should not flip an otherwise identical beat merely to save
    a small transition cost at the edge of a repeated run. The phrase-level
    optimizer is allowed to find context-sensitive variants first; among those
    repeated copies, the most sweep-rich variant becomes the stable motor
    pattern for the whole run. In cyclic mode the end/start bar boundary also
    counts as adjacent.
    """
    result = [list(row) for row in directions]
    count = len(beats)
    if count < 2:
        return result

    def has_attack(states: list[str]) -> bool:
        return any(state in (ti_state, ta_state) for state in states)

    def stabilise(indices: list[int]) -> None:
        if len(indices) < 2:
            return
        states = beats[indices[0]]
        if not has_attack(states):
            return
        def economy_score(row: list[str | None]) -> tuple[int, int]:
            same_direction_crossings = 0
            for index in range(1, len(states)):
                left = states[index - 1]
                right = states[index]
                if left not in (ti_state, ta_state) or right not in (ti_state, ta_state):
                    continue
                if left == right:
                    continue
                if row[index - 1] is not None and row[index - 1] == row[index]:
                    same_direction_crossings += 1
            return same_direction_crossings, int(bool(row and row[0] == DOWN))

        stable = max(
            (directions[index] for index in indices),
            key=economy_score,
        )
        for index in indices:
            result[index] = list(stable)

    if not cyclic:
        start = 0
        while start < count:
            end = start + 1
            while end < count and beats[end] == beats[start]:
                end += 1
            stabilise(list(range(start, end)))
            start = end
        return result

    if all(beats[index] == beats[0] for index in range(1, count)):
        stabilise(list(range(count)))
        return result

    # Start immediately after a beat-pattern boundary. This linearises the
    # circular bar while still allowing an identical run to cross end/start.
    start = next(
        index
        for index in range(count)
        if beats[index] != beats[index - 1]
    )
    group = [start]
    for offset in range(1, count):
        index = (start + offset) % count
        previous = (start + offset - 1) % count
        if beats[index] == beats[previous]:
            group.append(index)
        else:
            stabilise(group)
            group = [index]
    stabilise(group)
    return result


def economy_pick_beats(
    beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    loop: bool,
) -> list[list[str | None]]:
    """Choose picking per beat while preserving repeated loop structure.

    In loop mode repeated whole-beat motifs keep the same picking on every
    repetition. Fully silent beats split picking continuity, so a repeated
    motif immediately before/after silence is detected inside that active
    section instead of being flattened into one long phrase.
    """
    if not beats:
        return []

    if not loop:
        result = _economy_pick_beat_block(
            beats,
            ti_state,
            ta_state,
            off_state,
            period=len(beats),
            cyclic=False,
        )
        return _stabilise_repeated_beat_runs(
            beats,
            result,
            ti_state,
            ta_state,
            off_state,
            cyclic=False,
        )

    silent_beats = [
        index
        for index, states in enumerate(beats)
        if not any(state in (ti_state, ta_state) for state in states)
    ]
    if not silent_beats:
        period = _minimal_beat_period(beats)
        result = _economy_pick_beat_block(
            beats,
            ti_state,
            ta_state,
            off_state,
            period=period,
            cyclic=True,
        )
        return _stabilise_repeated_beat_runs(
            beats,
            result,
            ti_state,
            ta_state,
            off_state,
            cyclic=True,
        )

    # A fully silent beat is already a hard picking boundary. Rotate the bar
    # to such a boundary so an active section that wraps across bar end/start
    # stays contiguous while we detect its own repeated whole-beat period.
    cut = silent_beats[0]
    rotated = beats[cut:] + beats[:cut]
    rotated_result: list[list[str | None]] = [
        [None] * len(states)
        for states in rotated
    ]

    index = 0
    while index < len(rotated):
        states = rotated[index]
        if not any(state in (ti_state, ta_state) for state in states):
            index += 1
            continue

        end = index + 1
        while end < len(rotated) and any(
            state in (ti_state, ta_state)
            for state in rotated[end]
        ):
            end += 1

        active_block = rotated[index:end]
        period = _minimal_beat_period(active_block)
        repeated = period < len(active_block)
        block_result = _economy_pick_beat_block(
            active_block,
            ti_state,
            ta_state,
            off_state,
            period=period,
            cyclic=repeated,
        )
        rotated_result[index:end] = block_result
        index = end

    result: list[list[str | None]] = [[] for _ in beats]
    for rotated_index, directions in enumerate(rotated_result):
        original_index = (cut + rotated_index) % len(beats)
        result[original_index] = directions
    return _stabilise_repeated_beat_runs(
        beats,
        result,
        ti_state,
        ta_state,
        off_state,
        cyclic=True,
    )


def economy_pick_ramp_beats(
    full_beats: list[list[str]],
    effective_beats: list[list[str]],
    active_beats: int,
    stage_active_counts: tuple[int, ...] | list[int],
    ti_state: str,
    ta_state: str,
    off_state: str,
) -> list[list[str | None]]:
    """Keep one practical economy-picking scheme across ramp stages.

    Ramp training should not teach one motor pattern and then flip it later.
    At the same time, choosing the fully-open final bar as the only canonical
    source can erase useful sweeps that exist while later beats are still the
    temporary TA pulse used by the ramp.

    Use the latest *incomplete* ramp stage as the anchor instead. It contains
    the most real musical context available before the bar is fully opened,
    while still preserving the useful transition into the first temporary TA
    pulse. Earlier stages inherit the already-open prefix from that anchor;
    later/full stages keep that learned prefix and optimize only newly opened
    beats. Consecutive temporary TA pulses then alternate on string 6 instead
    of resetting to a downstroke after each generated silent tail.
    """
    if len(full_beats) != len(effective_beats):
        raise ValueError("full and effective ramp beat counts must match")
    if not effective_beats:
        return []

    beat_count = len(effective_beats)
    active = max(0, min(beat_count, int(active_beats)))
    stages = sorted(
        {
            max(0, min(beat_count, int(value)))
            for value in stage_active_counts
        }
    )
    if not stages:
        stages = [beat_count]

    incomplete = [value for value in stages if value < beat_count]
    anchor_active = max(incomplete) if incomplete else beat_count

    def effective_for(open_beats: int) -> list[list[str]]:
        result: list[list[str]] = []
        for beat_index, states in enumerate(full_beats):
            if beat_index >= open_beats and states:
                result.append([ta_state] + [off_state] * max(0, len(states) - 1))
            else:
                result.append(list(states))
        return result

    anchor_beats = effective_for(anchor_active)
    anchor_directions = economy_pick_beats(
        anchor_beats,
        ti_state,
        ta_state,
        off_state,
        loop=True,
    )

    def alternate_inactive_ta_pulses(
        directions: list[list[str | None]],
    ) -> list[list[str | None]]:
        """Preserve the first transition, then alternate generated TA pulses."""
        result = [list(row) for row in directions]
        placeholders = [
            beat_index
            for beat_index in range(active, beat_count)
            if effective_beats[beat_index]
            and effective_beats[beat_index][0] == ta_state
            and all(
                state == off_state
                for state in effective_beats[beat_index][1:]
            )
        ]
        if len(placeholders) < 2:
            return result

        first_direction = result[placeholders[0]][0]
        direction = first_direction if first_direction in (DOWN, UP) else DOWN
        for beat_index in placeholders:
            if result[beat_index]:
                result[beat_index][0] = direction
            direction = UP if direction == DOWN else DOWN
        return result

    if active == anchor_active and effective_beats == anchor_beats:
        return alternate_inactive_ta_pulses(anchor_directions)

    fixed_by_beat: list[list[str | None]] = []
    learned_prefix = min(active, anchor_active)
    for beat_index, states in enumerate(effective_beats):
        if beat_index < learned_prefix:
            if len(anchor_directions[beat_index]) != len(states):
                raise ValueError("anchor ramp beat shape must match current stage")
            fixed_by_beat.append(list(anchor_directions[beat_index]))
            continue

        # If a newly opened beat repeats a beat that is already part of the
        # learned prefix, preserve that same motor pattern instead of allowing
        # the optimizer to invent a different copy.
        repeated_from: int | None = None
        if beat_index < active:
            for previous in range(learned_prefix):
                if full_beats[previous] == full_beats[beat_index]:
                    repeated_from = previous
                    break
        if repeated_from is not None:
            if len(anchor_directions[repeated_from]) != len(states):
                raise ValueError("repeated ramp beat shape must match anchor beat")
            fixed_by_beat.append(list(anchor_directions[repeated_from]))
        else:
            fixed_by_beat.append([None] * len(states))

    result = _economy_pick_beat_block(
        effective_beats,
        ti_state,
        ta_state,
        off_state,
        period=len(effective_beats),
        cyclic=True,
        fixed_by_beat=fixed_by_beat,
    )
    return alternate_inactive_ta_pulses(result)
