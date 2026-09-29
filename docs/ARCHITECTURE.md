# Architecture

## Design goal

The architecture should keep **rhythm representation**, **audio scheduling**, and **GUI state** separate enough that UI changes do not redefine timing behavior.

## Planned baseline modules

### `app.py`
Owns the PySide6 application shell:

- beat editors;
- transport controls;
- BPM controls;
- A/B builder;
- practice-mode configuration;
- sound settings;
- session save/load;
- visual playhead.

The GUI should describe state and send configuration to the engine. It should not be the timing clock.

### `model.py`
Owns serializable rhythm-domain objects:

- beat subdivision;
- subdivision states;
- four-beat bar;
- normalization and session representation.

### `presets.py`
Owns built-in TI / TA cells.

Preset data must remain ordinary model data. A preset is a shortcut for constructing a pattern, not a separate execution path.

### `audio_engine.py`
Owns realtime sequencing and sound generation/playback.

Core rule: musical event timing is scheduled against the audio stream/callback clock rather than Qt timer cadence.

### `test_core.py`
Small deterministic smoke coverage for model and sequencing logic that does not require opening the GUI or an audio device.

## Rhythm model

A bar always has four quarter-note beats.

Each beat independently selects one subdivision mode:

- **16th**: four equal steps;
- **triplet**: three equal eighth-note-triplet steps.

Each step is one of:

- `TI`
- `TA`
- `OFF`

This allows mixed bars such as:

`16th | triplet | 16th | triplet`

without converting the whole bar to one global subdivision.

## Practice stages

Practice ramps are transformations of the same bar, not separate pattern formats.

Examples:

- `1/4 → 2/4 → 3/4 → 4/4`
- `2/4 → 4/4`

Inactive beats may optionally retain a quarter-note TA pulse to preserve the click/reference behavior used in the original Guitar Pro exercises.

## Audio semantics

TI and TA are musical events, not merely accents of the metronome.

The metronome is an independent layer.

This separation allows:

- TI = clap;
- TA = muted;
- metronome = audible;
- or any other mix without changing the rhythm pattern itself.
