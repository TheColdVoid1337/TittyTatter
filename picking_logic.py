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


def _optimise_run(strings: list[int]) -> list[str]:
    if not strings:
        return []

    directions = (DOWN, UP)
    # Tiny downstroke preference only breaks exact ties. The dynamic program is
    # still free to choose an upstroke start when it enables a cheaper sweep.
    costs: list[dict[str, tuple[float, str | None]]] = [
        {
            DOWN: (0.0, None),
            UP: (0.02, None),
        }
    ]

    for index in range(1, len(strings)):
        layer: dict[str, tuple[float, str | None]] = {}
        for direction in directions:
            best_cost = float("inf")
            best_previous: str | None = None
            for previous_direction in directions:
                candidate = (
                    costs[index - 1][previous_direction][0]
                    + _transition_cost(
                        strings[index - 1],
                        previous_direction,
                        strings[index],
                        direction,
                    )
                )
                if candidate < best_cost:
                    best_cost = candidate
                    best_previous = previous_direction
            layer[direction] = (best_cost, best_previous)
        costs.append(layer)

    final_direction = min(directions, key=lambda direction: costs[-1][direction][0])
    result = [final_direction]
    for index in range(len(strings) - 1, 0, -1):
        previous = costs[index][result[-1]][1]
        assert previous is not None
        result.append(previous)
    result.reverse()
    return result


def _optimise_cycle(strings: list[int]) -> list[str]:
    """Optimize a phrase whose last attack leads back into its first attack."""
    if not strings:
        return []

    directions = (DOWN, UP)
    best_total = float("inf")
    best_result: list[str] | None = None

    for first_direction in directions:
        layers: list[dict[str, tuple[float, str | None]]] = [
            {first_direction: (0.0, None)}
        ]

        for index in range(1, len(strings)):
            layer: dict[str, tuple[float, str | None]] = {}
            for direction in directions:
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
) -> list[str | None]:
    """Choose an efficient pick direction for each rhythmic slot.

    TI is string 5 and TA is string 6. Consecutive attacks are optimized as a
    phrase: same-string notes favour alternate picking, while 6→5 favours a
    downstroke sweep and 5→6 favours an upstroke sweep. A rest splits the
    phrase. In cyclic mode the end of the phrase is also optimized against its
    beginning, which is required for a continuously repeating loop.
    """
    if cyclic and states:
        separators = [
            index
            for index, state in enumerate(states)
            if state not in (ti_state, ta_state)
        ]
        if not separators:
            strings = [5 if state == ti_state else 6 for state in states]
            return list(_optimise_cycle(strings))

        # Rotate the loop so a rest/invalid slot is the boundary. That boundary
        # already breaks picking continuity, so ordinary linear optimization is
        # correct for the rotated phrase.
        cut = separators[0]
        rotated = states[cut:] + states[:cut]
        rotated_result = economy_pick_pattern(
            rotated,
            ti_state,
            ta_state,
            off_state,
            cyclic=False,
        )
        result: list[str | None] = [None] * len(states)
        for rotated_index, direction in enumerate(rotated_result):
            original_index = (cut + rotated_index) % len(states)
            result[original_index] = direction
        return result

    result: list[str | None] = [None] * len(states)
    run_slots: list[int] = []
    run_strings: list[int] = []

    def flush() -> None:
        if not run_slots:
            return
        directions = _optimise_run(run_strings)
        for slot, direction in zip(run_slots, directions):
            result[slot] = direction
        run_slots.clear()
        run_strings.clear()

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


def economy_pick_beats(
    beats: list[list[str]],
    ti_state: str,
    ta_state: str,
    off_state: str,
    *,
    loop: bool,
) -> list[list[str | None]]:
    """Choose picking per beat while preserving repeated loop structure.

    In loop mode the shortest whole-beat period is optimized as a cycle and
    then repeated. Therefore four identical rhythmic beats receive four
    identical picking patterns, and A/B/A/B keeps the same A and B picking on
    both repetitions.
    """
    if not beats:
        return []

    period = _minimal_beat_period(beats) if loop else len(beats)
    base_beats = beats[:period]

    flat: list[str] = []
    spans: list[tuple[int, int, bool]] = []
    for states in base_beats:
        start = len(flat)
        if states:
            flat.extend(states)
            spans.append((start, len(states), True))
        else:
            # Covered metric beats need a separator so picking does not bridge
            # through an event that belongs to a spanning previous beat.
            flat.append(off_state)
            spans.append((start, 1, False))

    flat_directions = economy_pick_pattern(
        flat,
        ti_state,
        ta_state,
        off_state,
        cyclic=loop,
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
