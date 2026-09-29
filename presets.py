from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

TI = "TI"
TA = "TA"
OFF = "OFF"
TI_MARK = "(ТИ)"
VALID_DENOMINATORS = (2, 4, 8, 16)


@dataclass(frozen=True)
class GridSpec:
    key: str
    steps: int
    span_beats: int


GRID_SPECS = (
    GridSpec("long16", 1, 16),
    GridSpec("long8", 1, 8),
    GridSpec("long4", 1, 4),
    GridSpec("long2", 1, 2),
    GridSpec("beat", 1, 1),
    GridSpec("duplet", 2, 1),
    GridSpec("triplet", 3, 1),
    GridSpec("quad", 4, 1),
    GridSpec("octuplet", 8, 1),
)
GRID_BY_KEY = {spec.key: spec for spec in GRID_SPECS}

LEGACY_GRID_MAP = {
    "whole": "long4",
    "half": "long2",
    "quarter": "beat",
    "eighth": "duplet",
    "triplet": "triplet",
    "sixteenth": "quad",
    "thirtysecond": "octuplet",
}
LEGACY_SUBDIVISION_TO_GRID = {
    1: "beat",
    2: "duplet",
    3: "triplet",
    4: "quad",
    8: "octuplet",
}

_NOTE_NAMES = {
    1: "целая",
    2: "половинная",
    4: "четвертная",
    8: "восьмая",
    16: "шестнадцатая",
    32: "тридцать вторая",
    64: "шестьдесят четвертая",
    128: "сто двадцать восьмая",
}


def normalize_grid_key(key: str) -> str:
    key = LEGACY_GRID_MAP.get(str(key), str(key))
    return key if key in GRID_BY_KEY else "quad"


def grid_spec(key: str) -> GridSpec:
    return GRID_BY_KEY[normalize_grid_key(key)]


def _note_label(denominator: int) -> str:
    return _NOTE_NAMES.get(denominator, f"1/{denominator}")


def grid_label(key: str, meter_denominator: int) -> str:
    spec = grid_spec(key)
    d = int(meter_denominator)

    if spec.steps == 1:
        note_denominator = d // spec.span_beats if d % spec.span_beats == 0 else 0
        if note_denominator >= 1:
            return f"1/{note_denominator} · {_note_label(note_denominator)}"
        return f"×{spec.span_beats} долей"

    if spec.key == "duplet":
        note_denominator = d * 2
        return f"1/{note_denominator} · ×2"
    if spec.key == "triplet":
        note_denominator = d * 2
        return f"1/{note_denominator}T · триоль ×3"
    if spec.key == "quad":
        note_denominator = d * 4
        return f"1/{note_denominator} · ×4"
    if spec.key == "octuplet":
        note_denominator = d * 8
        return f"1/{note_denominator} · ×8"
    return spec.key


def grid_specs_for_meter(numerator: int, denominator: int) -> tuple[GridSpec, ...]:
    numerator = max(1, int(numerator))
    denominator = int(denominator)
    if denominator not in VALID_DENOMINATORS:
        denominator = 4

    result: list[GridSpec] = []
    for spec in GRID_SPECS:
        if spec.steps == 1 and spec.span_beats > 1:
            if denominator % spec.span_beats != 0:
                continue
            if spec.span_beats > numerator:
                continue
        result.append(spec)
    return tuple(result)


def grid_from_legacy_subdivision(value: int) -> str:
    return LEGACY_SUBDIVISION_TO_GRID.get(int(value), "quad")


@dataclass(frozen=True)
class CellPreset:
    key: str
    grid: str
    steps: tuple[str, ...]

    @property
    def subdivision(self) -> int:
        return grid_spec(self.grid).steps

    @property
    def family(self) -> str:
        return self.grid

    @property
    def human(self) -> str:
        names = {TI: TI_MARK, TA: "ТА", OFF: "·"}
        return " ".join(names[s] for s in self.steps)


SIXTEENTH_KEYS = [
    "TI-ta-ta-ta",
    "TI-TI-ta-ta",
    "TI-TI-TI-ta",
    "TI-TI-TI-TI",
    "ta-TI-ta-ta",
    "ta-TI-TI-ta",
    "ta-ta-ta-TI",
    "TI-ta-TI-ta",
    "TI-ta-ta-TI",
    "TI-ta-TI-TI",
    "ta-ta-TI-ta",
    "ta-ta-TI-TI",
    "ta-TI-TI-TI",
    "ta-ta-ta-ta",
    "TI-TI-ta-TI",
    "ta-TI-ta-TI",
]

TRIPLET_KEYS = [
    "TI-ta-ta",
    "TI-TI-ta",
    "TI-TI-TI",
    "ta-TI-TI",
    "ta-ta-TI",
    "ta-TI-ta",
    "TI-ta-TI",
    "ta-ta-ta",
]


def parse_key(key: str) -> tuple[str, ...]:
    return tuple(TI if token == "TI" else TA for token in key.split("-"))


SIXTEENTH_PRESETS = tuple(CellPreset(k, "quad", parse_key(k)) for k in SIXTEENTH_KEYS)
TRIPLET_PRESETS = tuple(CellPreset(k, "triplet", parse_key(k)) for k in TRIPLET_KEYS)
EIGHTH_PRESETS = tuple(
    CellPreset("-".join("TI" if s == TI else "ta" for s in steps), "duplet", steps)
    for steps in product((TI, TA), repeat=2)
)
SINGLE_HIT_PRESETS = {
    key: (
        CellPreset(f"{key}-TI", key, (TI,)),
        CellPreset(f"{key}-ta", key, (TA,)),
    )
    for key in ("long16", "long8", "long4", "long2", "beat")
}

CORE_PRACTICE_PRESETS = SIXTEENTH_PRESETS + TRIPLET_PRESETS


def presets_for_grid(grid: str) -> tuple[CellPreset, ...]:
    grid = normalize_grid_key(grid)
    if grid == "quad":
        return SIXTEENTH_PRESETS
    if grid == "triplet":
        return TRIPLET_PRESETS
    if grid == "duplet":
        return EIGHTH_PRESETS
    if grid in SINGLE_HIT_PRESETS:
        return SINGLE_HIT_PRESETS[grid]
    return ()


def preset_from_steps(grid: str, steps: Iterable[str]) -> CellPreset | None:
    target = tuple(steps)
    for preset in presets_for_grid(grid):
        if preset.steps == target:
            return preset
    return None


def all_binary_patterns(length: int) -> list[tuple[str, ...]]:
    return list(product((TI, TA), repeat=length))
