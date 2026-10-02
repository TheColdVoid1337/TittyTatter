# Architecture

## Design goal

TittyTatter separates rhythm representation, realtime audio scheduling, game judgement, UI state, export, diagnostics, and persistence so that GUI changes do not become timing changes.

## Modules

### `app.py`

Owns the PySide6 application shell:

- transport and BPM controls;
- variable time-signature controls;
- horizontally scrollable beat editor;
- practice configuration;
- sound controls;
- visual metronome;
- game-mode UI, input capture, score/statistics presentation;
- picking overlay presentation;
- audio-device settings UI;
- session save/load;
- export dialogs;
- coordination of optional game diagnostics.

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

Owns realtime sequencing, synthesized sound playback, output-device selection, callback timing, and short notification cues.

Core rules:

- musical scheduling is performed in the PortAudio callback;
- the engine prefers the Windows WASAPI default endpoint when available;
- the selected device, sample rate, block size, latency mode, and optional WASAPI exclusive mode are explicit runtime settings;
- GUI timing does not schedule musical events;
- game targets are stamped from PortAudio output/DAC timing rather than from Qt polling;
- short in-stream cues are queued into the realtime callback;
- the timer-completion horn uses a separate one-shot output stream after transport stop.

The synthesized TI/TA sound bank is built at the selected output sample rate and should not be changed casually without explicit need.

### `game_logic.py`

Owns deterministic game judgement primitives.

Current rules:

- TI input can consume only TI targets; TA input can consume only TA targets;
- matching chooses the nearest valid target in the same lane;
- the overall acceptance window remains forgiving;
- PERFECT/GREAT/GOOD/HIT grades score precision inside that successful window;
- adaptive timing bias is currently disabled because diagnostic logs showed that it could drift by an entire subdivision.

### `picking_logic.py`

Owns economy-picking direction selection.

Current model:

- TI maps to string 5;
- TA maps to string 6;
- repeated notes on one string prefer alternate picking;
- 6 → 5 transitions prefer a downstroke sweep;
- 5 → 6 transitions prefer an upstroke sweep;
- rests split phrases and allow the next run to choose a new optimal starting direction.

The UI renders the resulting arrows as a fixed overlay; it does not participate in layout geometry.

### `game_logger.py`

Owns optional per-game diagnostics.

When the app is launched with `-log` or `--log`:

1. each game creates a unique timestamped JSONL session under `logs/`;
2. timing/input/target/matching/result events are appended while the game runs;
3. game completion packs the JSONL into `.tar.gz`;
4. the raw JSONL is deleted only after successful compression.

Without the CLI flag, no game log is created.

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

The settings file stores application preferences such as geometry, audio device selection, sound/meter configuration, visual-metronome settings, game keys, game feedback options, picking visibility, and the last-game summary.

It is user-local state and must not be committed.

### Tests

- `test_core.py` — deterministic rhythm/model/game checks that do not open the GUI or audio stream.
- `test_exports.py` — offline MIDI/GP5/WAV regression checks.
- `test_game_logger.py` — diagnostic-log creation/archive/cleanup checks.

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

Inactive ramp beats are represented semantically as TA followed by silence for both visual preview and game input. Their audio pulse remains controlled by the inactive-pulse option.

The UI shows stage progress and warns before both upward stage changes and full-stage wrap back to the first stage.

## Game timing

When game mode is running:

1. scheduled TI/TA events are timestamped against `outputBufferDacTime`;
2. callback-published targets are drained into the GUI-side pending list;
3. a short early-input buffer bridges the case where keyboard input arrives just before the audio callback publishes the corresponding future target;
4. matching is lane-only and nearest-target within the accepted early/late window;
5. successful hits record signed early/late offset, timing grade, quality, and Score;
6. expired targets and unmatched inputs count as misses;
7. Qt renders feedback/statistics but is not the musical timing authority.

The diagnostic logger was used to identify and remove two earlier failure modes: premature MISS on not-yet-published future targets and adaptive timing-bias drift.
