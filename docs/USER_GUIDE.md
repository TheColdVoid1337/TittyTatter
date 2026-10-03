# User guide

TittyTatter is primarily a guitar rhythm trainer. The main workflow is:

1. build a rhythm pattern;
2. choose how that pattern should be trained;
3. practise it on guitar, or optionally execute the same exercise through Game input;
4. use Focus and Picking Guide when useful.

## Start

On Windows, the simplest source launch is:

```bat
run.bat
```

On first launch, `run.bat` creates the local `.venv`, installs `requirements.txt`, and starts the application.

Manual equivalent:

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

## Build a rhythm

Choose the time signature at the top of the window.

- Numerator: 1–16.
- Denominator: 2, 4, 8, or 16.

Each metric beat has its own editor. Choose a grid/preset or edit the individual subdivision buttons.

Subdivision states are:

```text
(ТИ) → ТА → OFF
```

Supported grids include whole-beat cells, straight subdivisions, triplets, sixteenths, and denser divisions where available.

Long-note coverage is represented by the model rather than duplicated as independent hits.

For wide meters, the beat row scrolls horizontally.

### Beat Mute

Individual beat cards can be muted where the current training mode allows it.

A muted beat becomes visually dim and produces no beat content/metronome guidance for that beat.

Ramp modes intentionally control their own effective beat activity, so Mute is not used there.

## Training / Game selector

The top-level selector is:

- **Тренировка**
- **Игра**

This selector changes how the current exercise is executed. It does **not** select a separate progression system.

The currently selected **Training Mode** remains the source of truth in both cases.

Example:

- Training Mode: **Пропуски**
- audible bars: 4
- silent bars: 2

In normal Training, audio guidance disappears for the two silent bars while the guitarist continues playing.

In Game, the same silent phase occurs, but the internal timeline and Game targets continue, so the player must continue entering TI/TA in time.

## Training tab

The Training tab is organized conceptually into three parts.

### Режим тренировки

Choose one Training Mode. Only the parameters relevant to that mode are shown.

Current modes:

#### Повтор

Repeats the complete current pattern continuously.

#### Разгон с 1 доли

Progressively exposes more metric beats:

```text
1 → 2 → ... → full bar
```

The number of bars per stage is configurable.

#### Разгон с 2 долей

Starts from the first two beats and then expands to the full bar.

For a one-beat meter, it starts from one beat.

#### Пропуски

Alternates audible and silent blocks.

During silent bars:

- TI/TA rhythmic guidance disappears;
- metronome guidance disappears;
- the exercise timeline continues;
- Game targets continue if Game is active;
- the yellow current-position/playhead guidance disappears;
- the playhead returns automatically when audible guidance returns.

#### Нарастающие пропуски

Keeps the audible block fixed while the silent block grows:

```text
1 silent bar → 2 → 3 → ... → configured maximum → restart
```

The same "timeline continues during silence" rule applies.

#### Редкий метроном

Reduces click density without changing the rhythm pattern.

Current choices:

- Все доли
- Только 2 и 4
- Только 1 и 3
- Только 1
- Только 1 раз в 2 такта

#### Смещённый метроном

Moves the click away from the normal beat positions.

Current positions:

- `&` between beats;
- `e` — second sixteenth;
- `&` — third sixteenth;
- `a` — fourth sixteenth.

The displaced click is independent of the pattern subdivision and can coexist with triplets, eighths, sixteenths, and other grids.

### Опции

These are modifiers, not Training Modes:

- Count-in;
- **Разгон темпа** / Tempo Trainer;
- **Таймер** / Timer.

Tempo Trainer and Timer subordinate settings remain visible when disabled, but are greyed out rather than removed.

### Как пользоваться

The help area describes:

- what the selected Training Mode does;
- how to use it;
- what guitar skill it is intended to train.

## Tempo

The top transport keeps the BPM control intentionally compact.

Available interaction:

- numeric BPM spinbox;
- Up / Down for small changes;
- Shift+Up / Shift+Down for larger changes;
- TAP **[T]**.

The old BPM slider and separate +/- button cluster are intentionally not part of the current UI.

## Focus mode

Use:

```text
Фокус режим [F]
```

Focus mode hides configuration-heavy UI and turns TittyTatter into a large practice display.

It keeps:

- top transport;
- large visual metronome;
- status;
- session buttons;
- a read-only rhythm strip inside the black metronome area.

The rhythm strip reflects the **effective** current training pattern, including ramp-stage activity.

Visual states:

- TI — compact rounded blue pill;
- TA — dark rectangular cell;
- rest — dark/subtle cell with a dot;
- current subdivision — yellow outline.

During count-in, the pattern may remain visible but no current-subdivision outline is active.

During silent Gap / Progressive Gap phases, the yellow guidance disappears and returns automatically when sound returns.

The Focus metronome scales its actual needle/pivot/lamp geometry with the size setting.

When Game is active, the Game graph remains a compact diagnostic panel rather than expanding to full height.

## Штрих / Picking Guide

The tab is named **Штрих**.

Picking Guide is an informational guitar-practice aid, not a Training Mode.

Current controls include:

- enable/disable Picking Guide;
- picking strategy;
- show following strokes;
- number of following strokes;
- current-beat highlighting;
- large cue size.

Current strategies:

### Экономный

Uses the string-aware economy-picking optimizer.

Current reference mapping:

- TI → string 5;
- TA → string 6.

Repeated whole-beat patterns preserve their minimal repeating beat period, so identical repeated beats do not receive inconsistent arrows merely because the full bar was flattened.

Ramp stages are treated as cyclic effective bars.

Rests split picking continuity.

### Строго переменный ↓↑

Alternates down/up across attacks.

Rests do not consume a picking direction.

### Following strokes

The guide can show 1–8 upcoming strokes in a horizontal row.

The large cue shows the current arrow and string.

Current colors:

- `↑` — green;
- `↓` — red.

Picking Guide and Game are mutually exclusive in the UI. Enabling Picking while Game is selected returns the application to Training.

## Game

Game is a secondary way to practise the same exercise without a guitar.

When the top selector is **Игра**, Start and Space start the Game version of the currently selected Training Mode.

### Input

TI and TA can be bound to:

- keyboard keys;
- mouse buttons.

Common historical defaults are:

- TI = F
- TA = J

Keyboard handling uses physical scan information where possible, so common bindings continue to work independently of English/Russian/Thai keyboard layout.

### Focus-key priority

Physical F toggles Focus in normal use.

During an active Game session, if F is bound to a Game lane, Game input has priority.

While a Game binding control is capturing a new key, F can be captured instead of toggling Focus.

### Timing model

Matching is lane-specific:

- TI input consumes only TI targets;
- TA input consumes only TA targets.

The nearest same-lane target inside the valid acceptance window is selected.

Current acceptance window:

- up to 180 ms early;
- up to 300 ms late.

Current grades:

| Grade | Distance | Points |
|---|---:|---:|
| PERFECT | <= 30 ms | 100 |
| GREAT | <= 70 ms | 75 |
| GOOD | <= 120 ms | 50 |
| HIT | other accepted timing | 25 |
| MISS | outside acceptance window | 0 |

A short early-input buffer exists because the physical input can arrive slightly before the realtime callback publishes the corresponding future target.

The current matcher deliberately does not use opposite-lane fallback or adaptive timing bias.

### HIT / MISS feedback

Game feedback sounds are separate from the normal TI/TA training sound bank.

TI HIT choices include:

- Hit 1
- Hit 2
- Hit 3
- Гитара E3

TA HIT choices include lower variants and:

- Глушёная E2

MISS choices include:

- Miss 1
- Miss 2
- Miss 3
- Мимо струны

The original Hit 1/2/3 timbres remain the TI reference set.

An option allows TI and TA to use different HIT feedback.

### Statistics

Game shows:

- score;
- hit/miss count;
- accuracy;
- timing grade and signed early/late offset;
- recent-quality graph;
- current/last Game statistics.

## Sound / audio

TI, TA, metronome, and master levels are independent.

The established TI/TA training sound bank is intentionally stable.

Current historical defaults:

- TI Wood enabled;
- TA Low tick enabled.

Audio settings expose the available output-device/system controls, including sample rate, block size, latency request, and WASAPI options where supported.

Stop playback before changing audio-system settings.

## Diagnostic logs

Game diagnostics are opt-in.

Launch the application with:

```text
-log
```

or:

```text
--log
```

Without one of those flags, no Game diagnostic log is created.

When enabled:

1. each Game creates a unique JSONL session;
2. events are appended while the Game runs;
3. normal completion/stop archives the session to a unique `.tar.gz`;
4. the raw JSONL is removed after successful archival.

## Export

### MIDI

Exports the current pattern as a Standard MIDI File.

### Guitar Pro 5

Exports a `.gp5` file through PyGuitarPro.

Current reference guitar mapping:

- TI: E3, string 5 fret 7;
- TA: dead/muted open string 6.

Text annotations are intentionally conservative for legacy GP5 encoding compatibility.

### WAV

Renders the current exercise audio to WAV with selectable duration/quality.

Export uses the same rhythm model as realtime playback.

## Sessions and settings

Session files are explicit exercise snapshots saved/loaded from the UI.

Application settings persist local preferences such as:

- Training Mode and its parameters;
- tempo trainer;
- timer;
- Game configuration;
- Game sounds/volumes and last statistics;
- Picking Guide options;
- Focus state;
- selected tab;
- visual/audio settings.

Older settings use fallback defaults where practical.

The settings/session schema version is separate from the TittyTatter application release version.

## Keyboard shortcuts

Current important shortcuts:

- Space — start/stop according to the selected Training/Game top-level state;
- F — Focus toggle, subject to active-Game binding priority;
- T — tap tempo;
- Up / Down — BPM step;
- Shift+Up / Shift+Down — larger BPM step.
