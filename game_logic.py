from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence


# One intentionally forgiving game mode.
#
# Input matching is lane-based: a TI press first looks for the nearest TI
# target and a TA press first looks for the nearest TA target. This prevents
# one stale TA from making the following TI impossible to hit.
HIT_WINDOW_MS = 420.0
CALIBRATION_WINDOW_MS = 800.0
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
    return max(-400.0, min(400.0, float(median(recent))))


def choose_target_index(
    targets: Sequence[tuple[float, str]],
    input_state: str,
    now_seconds: float,
    bias_ms: float = 0.0,
    calibrating: bool = False,
) -> int | None:
    """Choose the nearest target, preferring the same TI/TA lane.

    During initial sync an already-sounded same-lane target is preferred over
    a numerically closer future note. This matters for repeated TA notes: a
    late press must not calibrate itself against the next subdivision.
    """
    if not targets:
        return None

    window_ms = CALIBRATION_WINDOW_MS if calibrating else HIT_WINDOW_MS
    candidates: list[tuple[float, float, int]] = []
    same_lane: list[tuple[float, float, int]] = []

    for index, (target_time, state) in enumerate(targets):
        corrected_ms = (float(now_seconds) - float(target_time)) * 1000.0 - float(bias_ms)
        distance = abs(corrected_ms)
        if distance > window_ms:
            continue
        item = (distance, corrected_ms, index)
        candidates.append(item)
        if state == input_state:
            same_lane.append(item)

    if calibrating and same_lane:
        sounded = [item for item in same_lane if item[1] >= 0.0]
        if sounded:
            return min(sounded, key=lambda item: item[0])[2]

    if same_lane:
        return min(same_lane, key=lambda item: item[0])[2]
    if candidates:
        return min(candidates, key=lambda item: item[0])[2]
    return None


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
