# User guide

## Start

From WSL:

```bash
cd /mnt/f/_PROJECT/TittyTatter
./tt install
./tt run
```

TittyTatter runs through the Windows interpreter at `.venv/Scripts/python.exe`. Do not activate a Linux virtual environment for this project.

## Build a rhythm

Choose the time signature at the top of the window.

- Numerator: 1–16.
- Denominator: 2, 4, 8, or 16.

Each metric beat has its own editor. Choose a grid, choose a preset when available, or click individual step buttons to cycle:

```text
(ТИ) → ТА → OFF
```

For wide meters, the beat row scrolls horizontally. During playback it follows the currently active beat.

### Mute

Each beat has a red `Mute` toggle. A muted beat becomes visually dim and produces no beat content/metronome click for that beat.

Mute is unavailable in practice-ramp modes.

## Practice tab

Contains:

- loop/ramp mode;
- bars per stage;
- count-in;
- optional TA pulse on inactive ramp beats;
- random full-bar generation;
- tempo trainer;
- optional practice timer.

When the timer expires, playback stops and a short end signal sounds.

## Sound tab

(ТИ), ТА, metronome, and master levels are independent.

Current defaults:

- (ТИ): **Wood**, enabled;
- ТА: **Low tick**, enabled;
- metronome: enabled.

(ТИ) and ТА cannot use the same sound simultaneously.

## Metronome tab

The visual metronome can configure:

- size;
- needle color;
- flash color;
- flash circle;
- whole-panel flash;
- flash brightness;
- needle width;
- swing angle;
- beat lamps.

Whole-panel flashing works independently from the flash-circle toggle.

## Game tab

Enable **Game mode** first. When disabled, all game overlays disappear from the metronome.

Configure:

- key for (ТИ);
- key for ТА;
- difficulty:
  - Low: ±180 ms;
  - Mid: ±110 ms;
  - High: ±60 ms.

Press **Start game**. This restarts playback/count-in so scoring begins from a clean timeline.

During the game:

- correct input flashes the metronome area green;
- incorrect input/miss flashes it red;
- the left side shows HIT/MISS plus early/late timing;
- the right side shows hit/miss count, accuracy, and recent-quality graph.

The Game tab also keeps the summary of the most recently completed game.

## Audio tab

Select:

- output device;
- sample rate;
- block size;
- low/high latency request;
- WASAPI exclusive mode.

Stop playback before changing audio-system settings.

`./tt audio-info` provides a command-line view of available output devices and the engine selection.

## Export tab

### MIDI

Choose repeat count and whether to include labels, then save a `.mid` file.

### Guitar Pro 5

Choose repeat count and labels, then save `.gp5`.

Current mapping:

- TI: string 5, fret 7, E3;
- TA: dead note `x` on string 6;
- track instrument: Overdriven Guitar.

Pattern annotations are written only above the first exported bar and deliberately avoid legacy-GP encoding-sensitive Cyrillic.

### WAV

Choose duration and PCM quality in the export dialog. WAV export loops the current pattern using the current BPM, sounds, levels, and metronome configuration.

## Sessions and settings

**Session files** are explicit exercise snapshots saved/loaded from the UI.

**Application settings** are stored automatically in:

```text
tittytatter.settings.json
```

This file is ignored by Git.

The Audio tab contains **Reset settings…**. Reset requires typing exactly:

```text
DELETE
```

before the settings file is removed/reset.

## Keyboard shortcuts

- Space — start/stop.
- T — tap tempo.
- Up / Down — ±1 BPM.
- Shift+Up / Shift+Down — ±5 BPM.
