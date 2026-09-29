# TittyTatter

> Current release: **0.0.2**

**TittyTatter** is a Windows-first desktop rhythm trainer for practicing custom **TI / TA** patterns with low-latency audio, visual metronome feedback, timed practice, rhythm-game scoring, flexible meters, and export to MIDI / Guitar Pro / WAV.

## Current feature set

- Variable meters: numerator **1–16**, denominator **2 / 4 / 8 / 16**.
- Per-beat rhythm grids including long notes, straight subdivisions, triplets, and dense subdivisions.
- Every step can be **(ТИ)**, **ТА**, or silent.
- Per-beat **Mute** for quiet-beat practice.
- Practice ramps, count-in, tempo trainer, and timed sessions.
- Low-latency Windows audio with WASAPI preference and selectable output-device settings.
- Independent **(ТИ)**, **ТА**, metronome, and master levels.
- Configurable visual metronome: needle, flash, colors, size, lamps, full-panel flash.
- Rhythm-game mode with assignable keys, Low / Mid / High timing windows, hit/miss feedback, early/late timing, and last-game statistics.
- Session save/load.
- Persistent local application settings.
- Export:
  - MIDI;
  - Guitar Pro 5;
  - WAV with selectable duration and PCM quality.

## Windows + WSL workflow

TittyTatter runs as a native Windows GUI/audio application while repository commands are issued from WSL.

Typical local paths:

- Windows: `F:\_PROJECT\TittyTatter`
- WSL: `/mnt/f/_PROJECT/TittyTatter`

The root `tt` helper is the canonical development entry point:

```bash
./tt install      # create/update the Windows .venv and install dependencies
./tt run          # launch the Windows GUI
./tt test         # run core model tests
./tt check        # core + compile + export + import gates
./tt doctor       # environment diagnostics
./tt audio-info   # PortAudio/output-device diagnostics
./tt pip list     # pip inside the Windows venv
./tt python       # Windows venv Python
./tt update       # ff-only pull of the current branch
```

Do **not** create or activate a Linux `.venv/bin` for this project. The supported interpreter is `.venv/Scripts/python.exe`.

`run.sh` remains only as a compatibility wrapper around `./tt run`. `run.bat` remains available for direct Windows launch.

## Local validation policy

Normal development validation is local. GitHub Actions are not used as the default test path.

Before a release/tag, run:

```bash
./tt install
./tt doctor
./tt check
./tt run
```

The final GUI/audio acceptance is manual because realtime audio behavior must be verified on the actual Windows device.

## Versioning

The canonical project version is stored in the root [`VERSION`](VERSION) file.

Current release version: **0.0.2**

Numeric version changes are made only at the release/tag checkpoint. Published version numbers are never reused.

## Repository layout

- `app.py` — PySide6 GUI, trainer controls, visual metronome, game mode.
- `audio_engine.py` — callback-driven realtime audio and output-device handling.
- `model.py` — serializable meter/rhythm model.
- `presets.py` — built-in rhythm cells and grid definitions.
- `exports.py` — MIDI, Guitar Pro 5, and WAV export.
- `settings_store.py` — ignored local application settings.
- `test_core.py` — deterministic rhythm/model checks.
- `test_exports.py` — export regression checks.
- `tt` — WSL-first Windows runtime/development helper.
- `docs/` — living documentation.

## Documentation

Start with [`docs/README.md`](docs/README.md).

- [Project state](docs/PROJECT_STATE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [User guide](docs/USER_GUIDE.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisions](docs/DECISIONS.md)
- [Test matrix](docs/TEST_MATRIX.md)
- [Changelog](docs/CHANGELOG.md)
