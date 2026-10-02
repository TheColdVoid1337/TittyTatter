# User guide

## Start

From WSL:

```bash
cd /mnt/f/_PROJECT/TittyTatter
./tt install
./tt run
```

TittyTatter runs through the Windows interpreter at `.venv/Scripts/python.exe`. Do not activate a Linux virtual environment for this project.

For game diagnostics only:

```bash
./tt run -log
```

Without `-log` / `--log`, no diagnostic files are written.

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
- optional audible/visual warning before each ramp-stage change;
- random full-bar generation;
- tempo trainer;
- optional practice timer.

Ramp status shows the current active-beat level, stage progress, repetitions remaining, and the next level on the final repetition.

Inactive ramp beats are displayed as TA followed by silence rather than revealing the future full-pattern content.

When the timer expires, playback stops and a dedicated factory-style completion horn sounds.

## Sound tab

(ТИ), ТА, metronome, and master levels are independent.

Current defaults:

- (ТИ): **Wood**, enabled;
- ТА: **Low tick**, enabled;
- metronome: enabled.

(ТИ) and ТА cannot use the same sound simultaneously.

Controls that depend on an enable checkbox remain disabled until their parent option is enabled.

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

Enable **Game mode** first. When disabled, game controls/overlays are inactive.

Configure:

- key for (ТИ);
- key for ТА;
- optional HIT sound;
- optional MISS sound.

There is currently one deliberately playable scoring mode rather than Low/Mid/High difficulties.

Press **Start game**. This restarts playback/count-in so scoring begins from a clean timeline.

During the game:

- a matching TI key is judged only against TI targets;
- a matching TA key is judged only against TA targets;
- short early-input buffering handles the case where a key arrives just before the audio callback publishes its future target;
- successful hits are graded PERFECT / GREAT / GOOD / HIT;
- PERFECT gives 100 points, GREAT 75, GOOD 50, HIT 25;
- correct input flashes the metronome area green;
- incorrect input/miss flashes it red;
- the left side shows the grade plus early/late timing;
- the right side shows Score, hit/miss count, accuracy, and recent-quality graph.

Current grading thresholds are intentionally stricter than the overall acceptance window:

- PERFECT: within 30 ms;
- GREAT: within 70 ms;
- GOOD: within 120 ms;
- HIT: other accepted timings.

The Game tab shows **Current Game** statistics while playing and returns to **Last Game** after the game ends.

## Picking tab

Enable the economy-picking overlay to show suggested pick directions inside the left side of the metronome area.

Current mapping:

- TI → string 5;
- TA → string 6.

The optimizer chooses directions automatically. It alternates efficiently on one string and can keep the same pick direction across a string change when that produces an economy/sweep motion.

Display colors:

- `↑` upstroke — green;
- `↓` downstroke — red;
- rests/fillers — gray.

In ramp modes the scheme is recalculated as each new beat becomes active. Not-yet-active beats show the TA reference hit plus silence.

## Audio tab

Select:

- output device;
- sample rate;
- block size;
- low/high latency request;
- WASAPI exclusive mode.

Stop playback before changing audio-system settings.

`./tt audio-info` provides a command-line view of available output devices and the engine selection.

## Diagnostic logs

Launch with:

```bash
./tt run -log
```

Each started game creates its own diagnostic session. On normal game completion/stop, the raw JSONL is compressed into a uniquely named archive such as:

```text
logs/game_2026-10-02_23-51-06_239053.tar.gz
```

Previous logs are never overwritten. The raw JSONL is removed after successful compression. `logs/` is ignored by Git.

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
