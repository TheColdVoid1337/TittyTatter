from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

TI = "TI"
TA = "TA"
OFF = "OFF"
TI_MARK = "ⓉⒾ"


@dataclass(frozen=True)
class GridSpec:
    key: str
    label: str
    steps: int
    span_beats: int = 1


GRID_SPECS = (
    GridSpec("whole", "Целая 1/1", 1, 4),
    GridSpec("half", "Половина 1/2", 1, 2),
    GridSpec("quarter", "Четверть 1/4", 1, 1),
    GridSpec("eighth", "Восьмые 1/8 ×2", 2, 1),
    GridSpec("triplet", "Триоль ×3", 3, 1),
    GridSpec("sixteenth", "16-е ×4", 4, 1),
    GridSpec("thirtysecond", "32-е ×8", 8, 1),
)
GRID_BY_KEY = {spec.key: spec for spec in GRID_SPECS}

LEGACY_SUBDIVISION_TO_GRID = {
    1: "quarter",
    2: "eighth",
    3: "triplet",
    4: "sixteenth",
    8: "thirtysecond",
}


def grid_spec(key: str) -> GridSpec:
    return GRID_BY_KEY.get(key, GRID_BY_KEY["sixteenth"])


def grid_from_legacy_subdivision(value: int) -> str:
    return LEGACY_SUBDIVISION_TO_GRID.get(int(value), "sixteenth")


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

    @property
    def display_name(self) -> str:
        return f"{grid_spec(self.grid).label}  •  {self.human}"


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


SIXTEENTH_PRESETS = tuple(CellPreset(k, "sixteenth", parse_key(k)) for k in SIXTEENTH_KEYS)
TRIPLET_PRESETS = tuple(CellPreset(k, "triplet", parse_key(k)) for k in TRIPLET_KEYS)
EIGHTH_PRESETS = tuple(
    CellPreset("-".join("TI" if s == TI else "ta" for s in steps), "eighth", steps)
    for steps in product((TI, TA), repeat=2)
)
SINGLE_HIT_PRESETS = {
    key: (
        CellPreset(f"{key}-TI", key, (TI,)),
        CellPreset(f"{key}-ta", key, (TA,)),
    )
    for key in ("whole", "half", "quarter")
}

CORE_PRACTICE_PRESETS = SIXTEENTH_PRESETS + TRIPLET_PRESETS
ALL_PRESETS = CORE_PRACTICE_PRESETS + EIGHTH_PRESETS + tuple(
    p for key in ("whole", "half", "quarter") for p in SINGLE_HIT_PRESETS[key]
)


def presets_for_grid(grid: str) -> tuple[CellPreset, ...]:
    if grid == "sixteenth":
        return SIXTEENTH_PRESETS
    if grid == "triplet":
        return TRIPLET_PRESETS
    if grid == "eighth":
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
