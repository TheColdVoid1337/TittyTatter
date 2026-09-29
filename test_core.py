from model import BarPattern, BeatPattern
from presets import ALL_PRESETS, SIXTEENTH_PRESETS, TRIPLET_PRESETS, TI, TA, all_binary_patterns

assert len(SIXTEENTH_PRESETS) == 16
assert len(TRIPLET_PRESETS) == 8
assert len(ALL_PRESETS) == 24
assert {p.steps for p in SIXTEENTH_PRESETS} == set(all_binary_patterns(4))
assert {p.steps for p in TRIPLET_PRESETS} == set(all_binary_patterns(3))

bar = BarPattern([
    BeatPattern(4, [TI, TA, TI, TA]),
    BeatPattern(3, [TA, TI, TA]),
    BeatPattern(4, [TA, TA, TI, TI]),
    BeatPattern(3, [TI, TI, TA]),
])
raw = bar.to_dict()
assert BarPattern.from_dict(raw).to_dict() == raw
print("core tests OK")
