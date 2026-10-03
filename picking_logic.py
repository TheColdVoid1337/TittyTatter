from __future__ import annotations

DOWN = "↓"
UP = "↑"


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
    a small transition cost at the edge of a repeated run. A repeated beat is
    therefore optimized as its own cycle and the same picking is copied to
    every repetition. In cyclic mode the end/start bar boundary also counts as
    adjacent.
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
    while still preserving the useful transition into the final temporary TA
    pulse. Earlier stages inherit the already-open prefix from that anchor;
    later/full stages keep that learned prefix and optimize only newly opened
    beats.
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

    if active == anchor_active and effective_beats == anchor_beats:
        return [list(row) for row in anchor_directions]

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

    return _economy_pick_beat_block(
        effective_beats,
        ti_state,
        ta_state,
        off_state,
        period=len(effective_beats),
        cyclic=True,
        fixed_by_beat=fixed_by_beat,
    )
