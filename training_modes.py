from __future__ import annotations

from dataclasses import dataclass

TRAINING_MODES = (
    ("loop", "Повтор"),
    ("ramp_1_4", "Разгон с 1 доли"),
    ("ramp_2_4", "Разгон с 2 долей"),
    ("gap", "Пропуски"),
    ("progressive_gap", "Нарастающие пропуски"),
    ("sparse_click", "Редкий метроном"),
    ("displaced_click", "Смещённый метроном"),
)

RAMP_MODES = frozenset({"ramp_1_4", "ramp_2_4"})
GAP_MODES = frozenset({"gap", "progressive_gap"})

SPARSE_CLICK_OPTIONS = (
    ("all", "Все доли"),
    ("2_4", "Только 2 и 4"),
    ("1_3", "Только 1 и 3"),
    ("beat_1", "Только 1"),
    ("bar_2", "Только 1 раз в 2 такта"),
)

DISPLACED_CLICK_OPTIONS = (
    ("eighth_and", "& · между долями"),
    ("sixteenth_e", "e · 2-я шестнадцатая"),
    ("sixteenth_and", "& · 3-я шестнадцатая"),
    ("sixteenth_a", "a · 4-я шестнадцатая"),
)


@dataclass(frozen=True)
class GapPhase:
    silent: bool
    segment_bar: int
    segment_bars: int
    cycle_bar: int
    cycle_bars: int
    silent_bars: int
    stage_index: int
    stage_count: int


def active_beats_for_stage(mode: str, numerator: int, stage_index: int) -> int:
    stages = ramp_stages(mode, numerator)
    return stages[int(stage_index) % len(stages)]


def ramp_stages(mode: str, numerator: int) -> tuple[int, ...]:
    numerator = max(1, int(numerator))
    if mode == "ramp_1_4":
        return tuple(range(1, numerator + 1))
    if mode == "ramp_2_4":
        first = min(2, numerator)
        return (first,) if first == numerator else (first, numerator)
    return (numerator,)


def gap_phase(
    mode: str,
    bar_number: int,
    *,
    play_bars: int,
    silent_bars: int,
    progressive_max_silent_bars: int,
) -> GapPhase:
    bar_number = max(0, int(bar_number))
    play = max(1, int(play_bars))

    if mode == "progressive_gap":
        max_silent = max(1, int(progressive_max_silent_bars))
        stage_lengths = tuple(play + silent for silent in range(1, max_silent + 1))
        super_cycle = sum(stage_lengths)
        pos = bar_number % super_cycle

        stage_index = 0
        while pos >= stage_lengths[stage_index]:
            pos -= stage_lengths[stage_index]
            stage_index += 1

        current_silent = stage_index + 1
        cycle_bars = play + current_silent
        silent = pos >= play
        segment_bar = pos - play + 1 if silent else pos + 1
        segment_bars = current_silent if silent else play
        return GapPhase(
            silent=silent,
            segment_bar=segment_bar,
            segment_bars=segment_bars,
            cycle_bar=pos + 1,
            cycle_bars=cycle_bars,
            silent_bars=current_silent,
            stage_index=stage_index,
            stage_count=max_silent,
        )

    silent_count = max(1, int(silent_bars))
    cycle_bars = play + silent_count
    pos = bar_number % cycle_bars
    silent = pos >= play
    segment_bar = pos - play + 1 if silent else pos + 1
    segment_bars = silent_count if silent else play
    return GapPhase(
        silent=silent,
        segment_bar=segment_bar,
        segment_bars=segment_bars,
        cycle_bar=pos + 1,
        cycle_bars=cycle_bars,
        silent_bars=silent_count,
        stage_index=0,
        stage_count=1,
    )


def sparse_click_matches(option: str, bar_number: int, beat_index: int) -> bool:
    bar = max(0, int(bar_number))
    beat = max(0, int(beat_index))
    option = str(option)

    if option == "2_4":
        return beat in (1, 3)
    if option == "1_3":
        return beat in (0, 2)
    if option == "beat_1":
        return beat == 0
    if option == "bar_2":
        return beat == 0 and bar % 2 == 0
    return True


def displaced_click_spec(option: str) -> tuple[int, int]:
    option = str(option)
    if option == "sixteenth_e":
        return 4, 1
    if option == "sixteenth_and":
        return 4, 2
    if option == "sixteenth_a":
        return 4, 3
    return 2, 1


def displaced_click_label(option: str) -> str:
    labels = dict(DISPLACED_CLICK_OPTIONS)
    return labels.get(str(option), labels["eighth_and"])


def sparse_click_label(option: str) -> str:
    labels = dict(SPARSE_CLICK_OPTIONS)
    return labels.get(str(option), labels["all"])
