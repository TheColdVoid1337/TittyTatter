# Test matrix

## Canonical local gate

Normal validation is local:

```bash
./tt check
```

The gate currently runs:

- `test_core.py`;
- Python compile checks for application modules;
- `test_exports.py`;
- dependency imports.

GitHub Actions are not required for ordinary validation.

## Automated core coverage

| Area | Gate |
|---|---|
| Presets | expected straight/triplet binary spaces |
| Grid labels | meter-aware labels |
| Meter model | non-4/4 bars serialize/deserialize |
| Legacy sessions | old subdivision values migrate |
| Mute | serialized and restored |
| Span coverage | long notes cover expected metric beats |
| Defaults | TI and TA audio enabled by default |
| Syntax | application modules compile |

## Automated export coverage

| Export | Gate |
|---|---|
| MIDI | valid SMF header/chunk and repeated bar markers |
| GP5 | file writes and parses back through PyGuitarPro |
| GP5 repeats | requested number of measures exists |
| GP5 labels | annotations only occur in the first exported measure |
| GP5 dead note | TA parses as dead note without Palm Mute |
| WAV | expected sample rate, sample width, mono channel, frames |

## Manual GUI checks

Before tagging:

- application opens without traceback;
- meter can change across representative signatures such as 4/4, 3/4, 6/8, 7/8, 5/16;
- beat editors rebuild correctly and horizontal scrolling works;
- playback auto-scroll keeps the active beat visible;
- grid/preset changes apply immediately;
- step buttons cycle (ТИ) → ТА → OFF;
- per-beat Mute dims the beat and remains visibly red;
- Mute is disabled in ramp modes;
- random-bar generation fits the current meter;
- timer counts down and stops playback;
- timer completion signal sounds;
- session save/load restores the exercise;
- local settings survive restart;
- settings reset requires exact DELETE confirmation.

## Manual audio checks

On the actual Windows output device:

- selected output device is correct;
- WASAPI path is stable where supported;
- no recurring crackle at normal levels;
- TI/TA/metronome remain rhythmically locked;
- Wood and Low tick defaults are both audible/enabled;
- TI and TA cannot be assigned the same sound;
- BPM changes during playback remain stable;
- count-in transitions cleanly;
- tempo trainer changes tempo only on intended boundaries;
- changing device/system settings while stopped works;
- optional WASAPI exclusive mode is tested only on a compatible device.

## Manual game checks

- Game-mode checkbox hides/shows all game overlays;
- Start game restarts playback/count-in;
- assigned TI and TA keys work;
- Low/Mid/High windows become progressively stricter;
- correct hit flashes green;
- wrong/out-of-window/missed input flashes red;
- left feedback reports HIT/MISS and early/late milliseconds;
- right graph updates quality/history;
- disabling game mode removes all overlays;
- Last Game box preserves the completed-game summary;
- ordinary playback still works with game mode disabled.

## Manual export checks

Open produced files in real target applications:

- MIDI opens with correct tempo/meter and repeated pattern;
- GP5 opens in Guitar Pro without mojibake;
- GP5 annotation appears only over the first exported bar;
- GP5 TA is a plain dead-note `x` with no P.M.;
- GP5 TI maps to string 5 fret 7;
- WAV duration/quality match the export dialog and playback sounds correct.

## Release gate

A release candidate is accepted only after:

1. `./tt doctor`;
2. `./tt check`;
3. focused manual GUI/audio/game/export checks on the target Windows machine.

Only then should the numeric version be chosen/updated and the annotated tag be created.
