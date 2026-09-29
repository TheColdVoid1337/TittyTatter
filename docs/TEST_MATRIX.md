# Test matrix

## Automated core checks

These should run without opening the GUI or requiring an audio device.

| Area | Gate |
|---|---|
| Pattern model | 4-beat bars serialize and deserialize correctly |
| 16th presets | all expected four-step TI/TA cells are available |
| Triplet presets | all expected three-step TI/TA cells are available |
| Mixed subdivisions | a bar may contain both subdivision types |
| Practice stages | active-beat masks are deterministic |
| Session schema | save/load preserves pattern and configuration |
| Syntax | project Python files compile |

## Manual GUI checks

Before a release candidate:

- application opens without traceback;
- every beat can switch independently between 16ths and triplets;
- subdivision buttons cycle TI → TA → OFF;
- presets apply to the correct beat;
- A/B builder produces the requested order;
- play/stop can be repeated safely;
- BPM changes during playback;
- tap tempo updates BPM;
- playhead follows the current beat/subdivision;
- session save/load restores the exercise.

## Manual audio checks

Test on a real Windows audio device:

- TI clap is distinct and stable;
- TA can be completely silent;
- metronome can be enabled independently;
- first-beat accent is correct;
- mixed 16th/triplet bars remain locked to the same quarter-note pulse;
- changing BPM during playback does not crash or stall;
- long loops do not audibly drift;
- count-in transitions cleanly into the exercise;
- tempo trainer changes tempo only on intended boundaries.

## Release gate

A version should not be called stable solely because core tests pass. Realtime audio behavior needs manual acceptance on real hardware.
