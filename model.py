from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from presets import OFF, TA, TI

VALID_STATES = {TI, TA, OFF}


@dataclass
class BeatPattern:
    subdivision: int = 4
    steps: list[str] = field(default_factory=lambda: [TI, TA, TA, TA])

    def normalize(self) -> None:
        self.subdivision = 3 if int(self.subdivision) == 3 else 4
        cleaned = [s if s in VALID_STATES else OFF for s in self.steps[: self.subdivision]]
        while len(cleaned) < self.subdivision:
            cleaned.append(OFF)
        self.steps = cleaned

    def copy(self) -> "BeatPattern":
        return BeatPattern(self.subdivision, list(self.steps))


@dataclass
class BarPattern:
    beats: list[BeatPattern] = field(default_factory=lambda: [BeatPattern() for _ in range(4)])

    def normalize(self) -> None:
        self.beats = (self.beats + [BeatPattern() for _ in range(4)])[:4]
        for beat in self.beats:
            beat.normalize()

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        return {"beats": [asdict(b) for b in self.beats]}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BarPattern":
        beats: list[BeatPattern] = []
        for item in raw.get("beats", [])[:4]:
            beats.append(BeatPattern(int(item.get("subdivision", 4)), list(item.get("steps", []))))
        result = cls(beats)
        result.normalize()
        return result
