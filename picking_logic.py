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


def economy_pick_pattern(
    states: list[str],
    ti_state: str,
    ta_state: str,
    off_state: str,
) -> list[str | None]:
    """Choose an efficient pick direction for each rhythmic slot.

    TI is string 5 and TA is string 6. Consecutive attacks are optimized as a
    phrase: same-string notes favour alternate picking, while 6→5 favours a
    downstroke sweep and 5→6 favours an upstroke sweep. A rest splits the
    phrase and lets the next run choose its own optimal starting direction.
    """
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
