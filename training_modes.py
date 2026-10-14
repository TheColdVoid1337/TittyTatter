from __future__ import annotations

from dataclasses import dataclass

from model import BarPattern, BeatPattern
from presets import OFF, TA, TI

TRAINING_MODES = (
    ("loop", "Повтор"),
    ("ramp_1_4", "Разгон с 1 доли"),
    ("ramp_2_4", "Разгон с 2 долей"),
    ("gap", "Пропуски"),
    ("progressive_gap", "Нарастающие пропуски"),
    ("sparse_click", "Редкий метроном"),
    ("displaced_click", "Смещённый метроном"),
    ("subdivision_ladder", "Лестница делений"),
    ("burst", "Рывки темпа"),
    ("accent_shift", "Сдвиг акцента"),
    ("blind_pattern", "По памяти"),
    ("endurance", "Интервалы"),
    ("tempo_wave", "Волна темпа"),
    ("random_tempo", "Случайный темп"),
)

RAMP_MODES = frozenset({"ramp_1_4", "ramp_2_4"})
GAP_MODES = frozenset({"gap", "progressive_gap"})
TEMPO_MODES = frozenset({"burst", "tempo_wave", "random_tempo"})
LADDER_GRIDS = ("beat", "duplet", "triplet", "quad")
LADDER_LABELS = ("Четверти", "Восьмые", "Триоли", "Шестнадцатые")

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


@dataclass(frozen=True)
class TrainingPhase:
    """Pure, deterministic bar-aligned state; the callback owns the clock."""

    stage_index: int = 0
    stage_count: int = 1
    stage_bar: int = 1
    stage_bars: int = 1
    label: str = ""
    rest: bool = False
    blind_hidden: bool = False
    accent_beat: int = -1


def _cycle_phase(bar_number: int, lengths: tuple[int, ...]) -> tuple[int, int, int]:
    lengths = tuple(max(1, int(n)) for n in lengths)
    pos = max(0, int(bar_number)) % sum(lengths)
    for index, length in enumerate(lengths):
        if pos < length:
            return index, pos + 1, length
        pos -= length
    raise AssertionError("Invalid cycle position")


def training_phase(
    mode: str,
    bar_number: int,
    numerator: int,
    *,
    ladder_bars: int = 2,
    burst_base_bars: int = 4,
    burst_fast_bars: int = 1,
    accent_bars: int = 1,
    tempo_block_bars: int = 2,
    endurance_work_bars: int = 4,
    endurance_rest_bars: int = 1,
    blind_learn_bars: int = 4,
    blind_memory_bars: int = 2,
) -> TrainingPhase:
    bar = max(0, int(bar_number))
    num = max(1, int(numerator))
    if mode == "subdivision_ladder":
        n = max(1, int(ladder_bars))
        idx, within, length = _cycle_phase(bar, (n,) * len(LADDER_GRIDS))
        return TrainingPhase(idx, len(LADDER_GRIDS), within, length, LADDER_LABELS[idx])
    if mode == "burst":
        idx, within, length = _cycle_phase(bar, (burst_base_bars, burst_fast_bars))
        return TrainingPhase(idx, 2, within, length, "Рывок" if idx else "База")
    if mode == "accent_shift":
        length = max(1, int(accent_bars))
        idx = (bar // length) % num
        return TrainingPhase(idx, num, bar % length + 1, length, f"Акцент: доля {idx + 1}", accent_beat=idx)
    if mode == "endurance":
        idx, within, length = _cycle_phase(bar, (endurance_work_bars, endurance_rest_bars))
        return TrainingPhase(idx, 2, within, length, "Отдых" if idx else "Работа", rest=bool(idx))
    if mode == "blind_pattern":
        idx, within, length = _cycle_phase(bar, (blind_learn_bars, blind_memory_bars))
        return TrainingPhase(idx, 2, within, length, "По памяти" if idx else "Разучивание", blind_hidden=bool(idx))
    if mode == "tempo_wave":
        length = max(1, int(tempo_block_bars))
        idx = (bar // length) % 7
        return TrainingPhase(idx, 7, bar % length + 1, length, f"Волна {idx + 1}/7")
    if mode == "random_tempo":
        length = max(1, int(tempo_block_bars))
        idx = bar // length
        return TrainingPhase(idx, 0, bar % length + 1, length, f"Блок {idx + 1}")
    return TrainingPhase()


def ladder_effective_pattern(pattern: BarPattern, stage_index: int) -> BarPattern:
    """Make a temporary density exercise; never change the stored Pattern.

    Each nonempty beat cycles through its played TI/TA string sequence
    at the stage density. Rests do not become sound when a beat has no
    attacks. Muted beats and long-note coverage stay silent/unchanged.
    This intentional simplification is documented in the user guide.
    """
    grid = LADDER_GRIDS[int(stage_index) % len(LADDER_GRIDS)]
    density = (1, 2, 3, 4)[LADDER_GRIDS.index(grid)]
    owners = pattern.coverage()
    effective = []
    for index, beat in enumerate(pattern.beats):
        if owners[index] != index:
            effective.append(BeatPattern("beat", [OFF], True))
        elif beat.span_beats > 1:
            effective.append(beat.copy())
        else:
            attacks = [state for state in beat.steps if state in (TI, TA)]
            states = [attacks[j % len(attacks)] for j in range(density)] if attacks else [OFF] * density
            effective.append(BeatPattern(grid, states, beat.muted))
    result = BarPattern(effective, pattern.numerator, pattern.denominator)
    result.normalize()
    return result


def _random_bpm(block: int, low: int, high: int, seed: int) -> int:
    """Stable integer-only mixing; never depends on global random state."""
    x = (int(seed) + 0x9E3779B9 * (int(block) + 1)) & 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return low + x % (high - low + 1)


def tempo_for_bar(
    mode: str,
    bar_number: int,
    base_bpm: float,
    *,
    burst_base_bars: int = 4,
    burst_fast_bars: int = 1,
    burst_fast_bpm: int = 120,
    tempo_min_bpm: int = 80,
    tempo_max_bpm: int = 120,
    tempo_block_bars: int = 2,
    random_seed: int = 7,
) -> float:
    """Compute effective bar BPM without feeding it back into base BPM."""
    base = max(20.0, min(320.0, float(base_bpm)))
    bar = max(0, int(bar_number))
    if mode == "burst":
        idx, _, _ = _cycle_phase(bar, (burst_base_bars, burst_fast_bars))
        return float(max(20, min(320, int(burst_fast_bpm)))) if idx else base
    if mode in ("tempo_wave", "random_tempo"):
        low = max(20, min(320, int(tempo_min_bpm)))
        high = max(low, min(320, int(tempo_max_bpm)))
        block = bar // max(1, int(tempo_block_bars))
        if mode == "random_tempo":
            return float(_random_bpm(block, low, high, random_seed))
        position = block % 7
        height = position if position <= 3 else 6 - position
        return float(low + round((high - low) * height / 3))
    return base
