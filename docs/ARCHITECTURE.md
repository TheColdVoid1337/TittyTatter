# Architecture

## Design goal

TittyTatter separates rhythm representation, realtime audio scheduling, UI state, export, and persistence so that GUI changes do not become timing changes.

## Modules

### `app.py`

Owns the PySide6 application shell:

- transport and BPM controls;
- variable time-signature controls;
- horizontally scrollable beat editor;
- practice configuration;
- sound controls;
- visual metronome;
- game-mode UI and scoring presentation;
- audio-device settings UI;
- session save/load;
- export dialogs.

Qt timers are used for display/polling, not as the musical clock.

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

Owns:

- TI / TA / OFF constants;
- rhythm-grid definitions;
- meter-aware grid labels;
- built-in straight/triplet TI/TA cells.

Presets are ordinary model data, not a separate playback path.

### `audio_engine.py`

Owns realtime sequencing, synthesized sound playback, output-device selection, and callback timing.

Core rules:

- musical scheduling is performed in the PortAudio callback;
- the engine prefers the Windows WASAPI default endpoint when available;
- the selected device, sample rate, block size, latency mode, and optional WASAPI exclusive mode are explicit runtime settings;
- GUI timing does not schedule musical events;
- game targets are stamped from PortAudio output/DAC timing rather than from Qt polling.

The synthesized sound bank is built at the selected output sample rate.

### `exports.py`

Owns offline export:

- Standard MIDI File;
- Guitar Pro 5 through PyGuitarPro;
- WAV PCM rendering.

Export uses the same rhythm model as realtime playback.

Current guitar mapping:

- **TI**: E3, string 5 fret 7;
- **TA**: dead/muted open string 6.

GP5 uses Overdriven Guitar and conservative ASCII annotations for compatibility with the legacy file format.

### `settings_store.py`

Owns the local ignored `tittytatter.settings.json` file.

The settings file stores application preferences such as geometry, audio device selection, sound/meter configuration, visual-metronome settings, game keys, difficulty, and the last-game summary.

It is user-local state and must not be committed.

### `test_core.py`

Deterministic model/preset/session checks that do not open the GUI or audio stream.

### `test_exports.py`

Offline export checks for MIDI, GP5, and WAV. GP5 is parsed back with PyGuitarPro to verify core structure, repeat count, annotation behavior, and dead-note semantics.

## Rhythm model

A metric beat uses one grid. Supported grid families include:

- one event spanning multiple metric beats where musically valid;
- one event per metric beat;
- duplet;
- triplet;
- four equal subdivisions;
- eight equal subdivisions.

Each subdivision state is:

- `TI`
- `TA`
- `OFF`

The meter denominator defines the metric-beat duration, so the same grid family adapts its displayed notation to 4-, 8-, or 16-based meters.

## Practice stages

Practice ramps operate on the current bar without creating a second pattern representation.

Current modes:

- full-bar loop;
- progressive 1 → 2 → … → full bar;
- 2 → full bar.

Inactive ramp beats may optionally retain the TA reference pulse. Manual per-beat Mute is disabled in ramp modes to keep those concepts unambiguous.

## Game timing

When game mode is running:

1. scheduled TI/TA events are timestamped against `outputBufferDacTime`;
2. configured keyboard inputs are compared with pending target timestamps;
3. difficulty selects the accepted time window;
4. successful hits record signed early/late offset and normalized quality;
5. expired targets and wrong/out-of-window inputs count as misses;
6. Qt renders feedback/statistics but is not the timing authority.

This is suitable for keyboard practice but is not yet a calibrated end-to-end latency measurement system.
