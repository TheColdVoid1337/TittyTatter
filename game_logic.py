from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# One deliberately forgiving game mode.
#
# Inputs are lane-specific: TI can only consume a TI target and TA can only
# consume a TA target. The previous adaptive timing-bias system was removed
# after diagnostics showed that it could drift by a whole subdivision and make
# an otherwise accurate player look late/early.
EARLY_HIT_WINDOW_MS = 180.0
LATE_HIT_WINDOW_MS = 300.0
HIT_WINDOW_MS = LATE_HIT_WINDOW_MS
INPUT_BUFFER_MAX_MS = 180.0

PERFECT_MS = 30.0
GREAT_MS = 70.0
GOOD_MS = 120.0


@dataclass(frozen=True)
class TimingGrade:
    accepted: bool
    label: str
    quality: float
    points: int


def choose_target_index(
    targets: Sequence[tuple[float, str]],
    input_state: str,
    now_seconds: float,
) -> int | None:
    """Choose the nearest target in the same TI/TA lane.

    Opposite-lane targets are never consumed. This avoids the cascading failure
    seen in diagnostics where one wrong/missed note shifted subsequent matches.
    """
    same_lane: list[tuple[float, int]] = []

    for index, (target_time, state) in enumerate(targets):
        if state != input_state:
            continue

        offset_ms = (float(now_seconds) - float(target_time)) * 1000.0
        if offset_ms < -EARLY_HIT_WINDOW_MS or offset_ms > LATE_HIT_WINDOW_MS:
            continue

        same_lane.append((abs(offset_ms), index))

    if not same_lane:
        return None
    return min(same_lane, key=lambda item: item[0])[1]


def grade_timing(offset_ms: float) -> TimingGrade:
    offset_ms = float(offset_ms)
    if offset_ms < -EARLY_HIT_WINDOW_MS or offset_ms > LATE_HIT_WINDOW_MS:
        return TimingGrade(False, "MISS", 0.0, 0)

    distance = abs(offset_ms)

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

    span = max(1.0, LATE_HIT_WINDOW_MS - GOOD_MS)
    progress = max(0.0, (distance - GOOD_MS) / span)
    quality = 0.53 - 0.18 * min(1.0, progress)
    return TimingGrade(True, "HIT", max(0.35, quality), 25)


def progress_bar(current: int, total: int, width: int = 8) -> str:
    total = max(1, int(total))
    current = max(0, min(total, int(current)))
    width = max(3, int(width))
    filled = int(round(width * current / total))
    return "■" * filled + "□" * (width - filled)
