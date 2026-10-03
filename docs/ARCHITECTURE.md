# Architecture

## Design goal

TittyTatter separates rhythm representation, Training Mode timeline logic, realtime audio scheduling, Game judgement, input binding, Picking Guide logic, UI state, export, diagnostics, and persistence.

The central product rule is:

> The selected Training Mode is the source of truth for both normal guitar Training and Game.

Game does not own a parallel exercise progression system.

## Product model

```text
PATTERN
  rhythm data

TRAINING MODE
  temporal method applied to that pattern

TRAINING
  guitarist performs the resulting exercise

GAME
  computer input executes the same resulting exercise and receives timing grades

PICKING GUIDE / ШТРИХ
  optional guitar-practice information layered on the exercise
```

Focus mode is a presentation state, not a new exercise mode.

## Modules

### `app.py`

Owns the PySide6 application shell and cross-module coordination:

- transport and BPM controls;
- meter controls;
- horizontally scrollable beat editor;
- top-level Training/Game selector;
- Training Mode configuration and help UI;
- count-in, tempo-trainer, and timer options;
- sound controls;
- visual metronome;
- Focus mode;
- read-only Focus rhythm strip;
- Game UI, input capture, score/statistics presentation, and feedback sounds;
- Picking Guide presentation;
- audio-device settings UI;
- session save/load;
- export dialogs;
- About tab;
- optional Game-diagnostic coordination.

Qt timers are used for presentation/polling, not as the musical clock.

### `model.py`

Owns the serializable rhythm-domain model:

- `BeatPattern`;
- `BarPattern`;
- time signature;
- per-beat grid;
- per-step TI/TA/OFF;
- per-beat mute;
- span/coverage normalization;
- legacy session migration.

A bar may contain 1–16 metric beats. The denominator controls the musical duration of each metric beat.

### `presets.py`

Owns rhythm-grid definitions and built-in pattern cells.

Presets are ordinary model data. They do not create a second playback path.

### `training_modes.py`

Owns Training Mode definitions and timeline helpers.

Current Training Modes:

- `loop` — Повтор;
- `ramp_1_4` — Разгон с 1 доли;
- `ramp_2_4` — Разгон с 2 долей;
- `gap` — Пропуски;
- `progressive_gap` — Нарастающие пропуски;
- `sparse_click` — Редкий метроном;
- `displaced_click` — Смещённый метроном.

The old internal ramp names are retained for compatibility, but ramp semantics are meter-aware rather than hard-coded to 4/4.

For numerator `N`:

- `ramp_1_4` stages are `1, 2, ..., N`;
- `ramp_2_4` begins at `min(2, N)` and then uses the full bar.

Gap helpers calculate audible/silent phases while preserving the continuous exercise timeline.

Sparse-click helpers decide which metric beat receives the metronome.

Displaced-click helpers describe the fine-grid click position independently of the pattern subdivision.

### `audio_engine.py`

Owns realtime sequencing, synthesized sound playback, output-device selection, callback timing, and short notification cues.

Core rules:

- musical scheduling is performed in the PortAudio callback;
- the engine prefers the Windows WASAPI default endpoint when appropriate;
- device, sample rate, block size, latency mode, and optional WASAPI exclusive mode are explicit runtime settings;
- GUI timing does not schedule musical events;
- Game targets are stamped from PortAudio output/DAC timing rather than Qt polling;
- short in-stream cues are queued into realtime playback;
- offline export continues to reuse established sound/model semantics.

The established TI/TA training sound bank is sensitive project behavior and should not drift during unrelated work.

### Fine timing grid

Training modes such as displaced metronome must coexist with the current pattern grid.

The audio engine therefore derives a common fine timing grid / LCM rather than assuming that metronome positions use the same subdivision as the edited rhythm.

This allows, for example, a sixteenth displaced click to coexist with a triplet pattern.

### `game_logic.py`

Owns deterministic Game judgement primitives.

Current constants:

```text
EARLY_HIT_WINDOW_MS = 180
LATE_HIT_WINDOW_MS  = 300
INPUT_BUFFER_MAX_MS = 180

PERFECT_MS = 30
GREAT_MS   = 70
GOOD_MS    = 120
```

Current rules:

- TI input can consume only TI targets;
- TA input can consume only TA targets;
- matching selects the nearest valid target in the same lane;
- PERFECT/GREAT/GOOD/HIT grade successful timing;
- opposite-lane fallback is intentionally absent;
- adaptive timing bias is intentionally absent.

The asymmetric acceptance window and early-input buffering exist because physical input and realtime target publication are not perfectly synchronous.

### `input_binding.py`

Owns normalized Game bindings.

Binding forms include:

- physical scan-code bindings;
- mouse-button bindings;
- logical-key fallback for uncommon legacy keys.

Common alphanumeric bindings migrate to Windows Set-1 scan-code identities, allowing the same physical key to keep working across keyboard layouts.

This is also used by the Focus-key priority logic.

### `picking_logic.py`

Owns Picking Guide direction selection.

Reference mapping:

- TI → string 5;
- TA → string 6.

The current post-0.0.4 implementation is **transitional**. It contains linear/cyclic optimization plus repeated-pattern and Ramp-specific stabilization added from real practice feedback. Those fixes are useful regression evidence, but they are not the final architecture.

The target design is canonical in [PICKING_LOGIC_V2.md](PICKING_LOGIC_V2.md).

**P1 is implemented:** `PickingEvent`, real-pattern vs Ramp-placeholder source identity, stable real-attack ids across stages, explicit covered slots, exact rhythmic phase, and explicit reset-boundary input are available as pure deterministic normalization helpers.

**P2 is implemented:** Alternate v2 consumes the normalized event stream and advances only on attacks. OFF/COVERED slots do not consume parity, string changes do not interrupt alternation, and Ramp placeholders count as attacks. Compatibility helpers can project event decisions back to the existing beat/subdivision UI shape.

Neither P1 nor P2 is yet wired to the visual arrow generator; runtime cutover remains a later integration step.

Picking Logic v2 changes the abstraction from "flatten states and assign arrows" to:

```text
effective training state
  -> normalized PickingEvent stream
  -> continuity / persistent identity / motif constraints
  -> stage + cyclic transition graph
  -> deterministic constrained optimizer
  -> PickDecision stream
```

Target behavior includes:

- **Alternate** = deterministic attack-alternate; rests do not consume a stroke;
- **Economy** = practical directional economy, not maximum sweeping;
- explicit same-string, alternate-crossing, sweep, reset, and future escape-aware transition types;
- start DOWN/UP evaluated as real candidates;
- parity and loop-boundary awareness;
- repeated motor motifs constrained during optimization rather than rewritten afterward;
- Ramp stages solved jointly, with persistent real attacks and stage-local placeholder attacks;
- future AUTO/USX/DSX/DBX scoring hook without inferring the player's mechanics;
- machine-readable decision reasons for regression/debug work.

The UI may continue to show only arrows initially. Internal sweep links and transition reasons are model data, not a requirement for a new user-facing control.

### `game_logger.py`

Owns optional per-Game diagnostics.

When the app is launched with `-log` or `--log`:

1. each Game creates a unique timestamped JSONL session;
2. timing/input/target/matching/result events are appended;
3. normal stop/finish/close archives the session to a unique `.tar.gz`;
4. the raw JSONL is deleted only after successful compression.

Without the CLI flag, no Game log should be created.

### `exports.py`

Owns offline export:

- Standard MIDI File;
- Guitar Pro 5 through PyGuitarPro;
- WAV PCM rendering.

Export uses the same rhythm model as realtime playback.

Current guitar reference mapping:

- TI: E3, string 5 fret 7;
- TA: dead/muted open string 6.

GP5 uses conservative text annotations for compatibility with the legacy format.

### `settings_store.py`

Owns the ignored local application settings file.

Settings include Training Mode state, training parameters, tempo/timer options, Game configuration, feedback audio, Picking Guide, Focus state, last tab, visual configuration, and other preferences.

Session/settings schema versioning is independent of the application semantic `VERSION`.

### Tests

- `test_core.py` — deterministic rhythm/model/training/Game/picking checks that do not open the GUI or audio stream.
- `test_exports.py` — offline MIDI/GP5/WAV regression checks.
- `test_game_logger.py` — diagnostic-log creation/archive/cleanup checks.

## Rhythm model

Each subdivision state is:

- `TI`;
- `TA`;
- `OFF`.

A metric beat uses one selected grid. Supported families include whole-beat events, duplets, triplets, four-way subdivisions, eight-way subdivisions, and long-note/span coverage where musically valid.

The meter denominator defines metric-beat duration, so the same grid family adapts to different meters.

## Training Mode timeline semantics

### Loop

The complete current effective bar repeats continuously.

### Ramp modes

Ramp modes expose a meter-aware number of active beats without creating another stored pattern representation.

A ramp stage is conceptually a cyclic effective bar.

### Gap modes

Gap modes change **guidance**, not the exercise clock.

During a silent phase:

- TI/TA rhythmic audio guidance is suppressed;
- metronome guidance is suppressed;
- the internal timeline continues;
- Game targets continue;
- yellow current-position guidance is hidden;
- guidance returns when the audible phase resumes.

### Sparse click

The rhythm remains intact while metronome events are filtered to the selected beat/bar pattern.

### Displaced click

The rhythm remains intact while the metronome is scheduled on a separate off-beat/fine-grid phase.

## Top-level Training/Game execution

The UI stores concepts equivalent to:

```text
training_mode
game_enabled
picking_guide_enabled
```

not three peer "modes".

When Game is selected:

- Start/Space execute the Game version of the current training exercise;
- the selected Training Mode still controls ramps, gaps, click filtering, and the exercise timeline.

Picking Guide and Game are mutually exclusive because Picking is intended for guitar practice.

## Game timing path

When Game is active:

1. the realtime audio callback schedules exercise events;
2. eligible TI/TA events are published as DAC-timestamped targets;
3. GUI/input handling records physical keyboard or mouse input;
4. a short early-input buffer bridges input that arrives before a future target has been published;
5. the matcher selects the nearest same-lane target inside the valid asymmetric window;
6. accepted timing is graded;
7. missed/expired targets are recorded;
8. the GUI renders feedback/statistics without becoming the musical timing authority.

## Focus presentation

Focus is a presentation layer over the same application state.

It hides configuration-heavy controls and expands the visual metronome.

The Focus rhythm strip is read-only and is derived from the current **effective** pattern, including ramp-stage activity and long-note coverage.

Count-in may show the pattern without an active playhead.

Silent Gap phases hide the current-position outline.

Focus metronome geometry scales the actual needle, pivot, lamps, and flash rather than only changing the widget size.

The Game history graph is deliberately capped in Focus so it remains a diagnostic panel.

## Focus F-key priority

Focus uses the physical F key where possible.

Priority rules:

1. while a Game binding editor is capturing a key, capture wins;
2. during an active Game, if F is bound to a Game lane, Game input wins;
3. otherwise F toggles Focus.

This priority must be preserved when input handling changes.

## About/icon path

The application icon source is:

```text
assets/app_icon.png
```

Runtime Qt code applies transparency/safe-area handling for the window/About rendering.

The public README uses a separate repository asset with real PNG transparency because Markdown cannot execute the Qt runtime conversion.

## Validation architecture

Automated checks intentionally do not claim to validate all GUI/audio behavior.

The canonical project gate is:

```bash
./tt check
```

Meaningful GUI/runtime changes also require:

```bash
./tt run
```

Local Windows acceptance remains authoritative for realtime GUI/audio behavior.
