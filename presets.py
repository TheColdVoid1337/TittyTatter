from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

TI = "TI"
TA = "TA"
OFF = "OFF"


@dataclass(frozen=True)
class CellPreset:
    key: str
    subdivision: int
    steps: tuple[str, ...]

    @property
    def family(self) -> str:
        return "16" if self.subdivision == 4 else "3"

    @property
    def human(self) -> str:
        names = {TI: "Ти", TA: "Та", OFF: "·"}
        return " ".join(names[s] for s in self.steps)

    @property
    def display_name(self) -> str:
        prefix = "16-е" if self.subdivision == 4 else "Триоль"
        return f"{prefix}  •  {self.human}"


SIXTEENTH_KEYS = [
    "TI-ta-ta-ta", "TI-TI-ta-ta", "TI-TI-TI-ta", "TI-TI-TI-TI",
    "ta-TI-ta-ta", "ta-TI-TI-ta", "ta-ta-ta-TI", "TI-ta-TI-ta",
    "TI-ta-ta-TI", "TI-ta-TI-TI", "ta-ta-TI-ta", "ta-ta-TI-TI",
    "ta-TI-TI-TI", "ta-ta-ta-ta", "TI-TI-ta-TI", "ta-TI-ta-TI",
]
TRIPLET_KEYS = [
    "TI-ta-ta", "TI-TI-ta", "TI-TI-TI", "ta-TI-TI",
    "ta-ta-TI", "ta-TI-ta", "TI-ta-TI", "ta-ta-ta",
]


def parse_key(key: str) -> tuple[str, ...]:
    return tuple(TI if token == "TI" else TA for token in key.split("-"))


SIXTEENTH_PRESETS = tuple(CellPreset(k, 4, parse_key(k)) for k in SIXTEENTH_KEYS)
TRIPLET_PRESETS = tuple(CellPreset(k, 3, parse_key(k)) for k in TRIPLET_KEYS)
ALL_PRESETS = SIXTEENTH_PRESETS + TRIPLET_PRESETS
PRESET_BY_KEY = {p.key: p for p in ALL_PRESETS}


def presets_for_subdivision(subdivision: int) -> tuple[CellPreset, ...]:
    return SIXTEENTH_PRESETS if subdivision == 4 else TRIPLET_PRESETS


def preset_from_steps(subdivision: int, steps: Iterable[str]) -> CellPreset | None:
    target = tuple(steps)
    for preset in presets_for_subdivision(subdivision):
        if preset.steps == target:
            return preset
    return None


def all_binary_patterns(subdivision: int) -> list[tuple[str, ...]]:
    return list(product((TI, TA), repeat=subdivision))
