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
- `test_game_logger.py`;
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
| Game lanes | TI/TA input cannot consume the opposite-lane target |
| Game matching | nearest same-lane target is selected inside the accepted window |
| Game grading | PERFECT/GREAT/GOOD/HIT boundaries |
| Picking | economy transitions for representative 5/6-string sequences |
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

## Automated diagnostic-log coverage

- logging disabled does not create the logs directory;
- logging enabled creates a raw JSONL session;
- input/event records serialize;
- finish creates a `.tar.gz` archive;
- raw JSONL is deleted after successful compression;
- archive content reads back correctly.

## Manual GUI checks

Before tagging:

- application opens without traceback;
- meter can change across representative signatures such as 4/4, 3/4, 6/8, 7/8, 5/16;
- beat editors rebuild correctly and horizontal scrolling works;
- established overall layout remains stable;
- playback auto-scroll keeps the active beat visible;
- grid/preset changes apply immediately;
- step buttons cycle (ТИ) → ТА → OFF;
- per-beat Mute dims the beat and remains visibly red;
- Mute is disabled in ramp modes;
- mode-dependent controls grey out when their parent option is disabled;
- random-bar generation fits the current meter;
- timer counts down and stops playback;
- factory-style timer completion horn sounds reliably;
- session save/load restores the exercise;
- local settings survive restart;
- settings reset requires exact DELETE confirmation.

## Manual ramp checks

- inactive ramp beats display TA followed by silence;
- game input expects TA for inactive ramp beats;
- stage progress shows completed/remaining repetitions;
- warning fires before every upward stage change;
- warning also fires before full-stage wrap back to the first stage;
- picking overlay updates as each new ramp beat becomes active.

## Manual picking checks

- overlay remains on the left side of the metronome and does not move layout;
- beat separators align across strings 5 and 6;
- upstroke arrows are green;
- downstroke arrows are red;
- suggested directions change according to TI/TA string transitions rather than fixed alternate picking.

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

- Game-mode checkbox hides/shows game overlays and dependent controls;
- Start game restarts playback/count-in;
- assigned TI and TA keys work;
- TI input matches only TI targets and TA input matches only TA targets;
- early valid input can be buffered briefly until its target is published;
- Score increments by grade;
- PERFECT/GREAT/GOOD/HIT grades feel appropriately strict while overall matching remains playable;
- correct hit flashes green;
- wrong/out-of-window/missed input flashes red;
- left feedback reports grade and early/late milliseconds;
- right graph updates quality/history;
- Current Game stats update while playing;
- Last Game preserves the completed-game summary;
- ordinary playback still works with game mode disabled.

## Manual diagnostic-log check

Optional when debugging game timing:

```bash
./tt run -log
```

After a game finishes:

- a new uniquely named archive exists under `logs/`;
- previous archives remain untouched;
- no raw JSONL remains after successful compression.

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

Only then should `work` be integrated into `main`, the numeric version be chosen/updated, and the annotated tag be created manually.
