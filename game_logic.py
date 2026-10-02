from __future__ import annotations

from dataclasses import dataclass
from statistics import median


# One deliberately playable mode. The window is broad enough to learn the
# rhythm; accuracy inside it controls the grade and score.
HIT_WINDOW_MS = 420.0
CALIBRATION_WINDOW_MS = 520.0
PERFECT_MS = 70.0
GREAT_MS = 145.0
GOOD_MS = 260.0


@dataclass(frozen=True)
class TimingGrade:
    accepted: bool
    label: str
    quality: float
    points: int


def timing_bias(samples_ms: list[float]) -> float:
    """Rolling median latency/player offset used to centre the judgement lane."""
    if not samples_ms:
        return 0.0
    recent = samples_ms[-12:]
    return max(-300.0, min(300.0, float(median(recent))))


def grade_timing(offset_ms: float) -> TimingGrade:
    distance = abs(float(offset_ms))
    if distance > HIT_WINDOW_MS:
        return TimingGrade(False, "MISS", 0.0, 0)

    if distance <= PERFECT_MS:
        quality = 1.0 - 0.08 * (distance / PERFECT_MS)
        return TimingGrade(True, "PERFECT", quality, 100)

    if distance <= GREAT_MS:
        progress = (distance - PERFECT_MS) / (GREAT_MS - PERFECT_MS)
        quality = 0.91 - 0.16 * progress
        return TimingGrade(True, "GREAT", quality, 75)

    if distance <= GOOD_MS:
        progress = (distance - GREAT_MS) / (GOOD_MS - GREAT_MS)
        quality = 0.74 - 0.20 * progress
        return TimingGrade(True, "GOOD", quality, 50)

    progress = (distance - GOOD_MS) / (HIT_WINDOW_MS - GOOD_MS)
    quality = 0.53 - 0.18 * progress
    return TimingGrade(True, "HIT", max(0.35, quality), 25)


def progress_bar(current: int, total: int, width: int = 8) -> str:
    total = max(1, int(total))
    current = max(0, min(total, int(current)))
    width = max(3, int(width))
    filled = int(round(width * current / total))
    return "■" * filled + "□" * (width - filled)
