from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from presets import (
    OFF,
    TA,
    TI,
    VALID_DENOMINATORS,
    grid_from_legacy_subdivision,
    grid_spec,
    normalize_grid_key,
)

VALID_STATES = {TI, TA, OFF}


@dataclass
class BeatPattern:
    grid: str = "quad"
    steps: list[str] = field(default_factory=lambda: [TI, TA, TA, TA])
    muted: bool = False

    @property
    def subdivision(self) -> int:
        return grid_spec(self.grid).steps

    @property
    def span_beats(self) -> int:
        return grid_spec(self.grid).span_beats

    def normalize(self) -> None:
        self.grid = normalize_grid_key(self.grid)
        spec = grid_spec(self.grid)
        cleaned = [s if s in VALID_STATES else OFF for s in self.steps[: spec.steps]]
        while len(cleaned) < spec.steps:
            cleaned.append(OFF)
        self.steps = cleaned
        self.muted = bool(self.muted)

    def copy(self) -> "BeatPattern":
        return BeatPattern(self.grid, list(self.steps), self.muted)

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        return {
            "grid": self.grid,
            "subdivision": self.subdivision,
            "steps": list(self.steps),
            "muted": self.muted,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BeatPattern":
        grid = raw.get("grid")
        if not grid:
            grid = grid_from_legacy_subdivision(int(raw.get("subdivision", 4)))
        beat = cls(str(grid), list(raw.get("steps", [])), bool(raw.get("muted", False)))
        beat.normalize()
        return beat


@dataclass
class BarPattern:
    beats: list[BeatPattern] = field(default_factory=lambda: [BeatPattern() for _ in range(4)])
    numerator: int = 4
    denominator: int = 4

    def normalize(self) -> None:
        self.numerator = max(1, min(16, int(self.numerator)))
        self.denominator = int(self.denominator)
        if self.denominator not in VALID_DENOMINATORS:
            self.denominator = 4

        converted: list[BeatPattern] = []
        for beat in self.beats[: self.numerator]:
            if isinstance(beat, BeatPattern):
                converted.append(beat)
            elif isinstance(beat, dict):
                converted.append(BeatPattern.from_dict(beat))
        while len(converted) < self.numerator:
            converted.append(BeatPattern())
        self.beats = converted

        for beat in self.beats:
            beat.normalize()

    def coverage(self) -> list[int | None]:
        self.normalize()
        owners: list[int | None] = [None] * self.numerator
        for i, beat in enumerate(self.beats):
            if owners[i] is not None:
                continue
            owners[i] = i
            for j in range(i + 1, min(self.numerator, i + max(1, beat.span_beats))):
                if owners[j] is None:
                    owners[j] = i
        return owners

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        return {
            "time_signature": {
                "numerator": self.numerator,
                "denominator": self.denominator,
            },
            "beats": [b.to_dict() for b in self.beats],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BarPattern":
        ts = raw.get("time_signature", {})
        numerator = int(ts.get("numerator", raw.get("numerator", 4)))
        denominator = int(ts.get("denominator", raw.get("denominator", 4)))
        beats = [BeatPattern.from_dict(item) for item in raw.get("beats", [])[:16]]
        result = cls(beats, numerator, denominator)
        result.normalize()
        return result
