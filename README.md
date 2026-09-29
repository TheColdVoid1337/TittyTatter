# TittyTatter

> Version **0.0.1** · early development baseline

**TittyTatter** is a desktop rhythm-training tool for practicing custom **TI / TA** cells in 4/4.  
The core idea is simple: build a bar beat by beat, choose straight sixteenths or triplets independently for each beat, assign TI / TA / silence to every subdivision, and practice the result with a configurable audio engine.

## Current concept

- 4/4 bar editor with four independent beats.
- Each beat can use **4 sixteenths** or an **eighth-note triplet**.
- Every subdivision can be **TI**, **TA**, or silent.
- Built-in TI/TA pattern presets for fast setup.
- A/B pattern construction and practice ramps.
- Live BPM control and tap tempo.
- Separate TI, TA, metronome, and master sound controls.
- TI can use a clap-like sound.
- TA can be muted completely.
- Session save/load is part of the working prototype.
- Audio timing is designed around the audio callback rather than GUI timers.

## Windows + WSL development workflow

TittyTatter is a native Windows GUI/audio application, but the repository is managed from WSL.

Local path convention:

- Windows: `F:\_PROJECT\TittyTatter`
- WSL: `/mnt/f/_PROJECT/TittyTatter`

Use the root `tt` helper from WSL:

```bash
./tt install   # create Windows .venv and install dependencies
./tt run       # launch the Windows GUI
./tt test      # run core tests
./tt check     # tests + compile/import checks
./tt doctor    # show environment diagnostics
./tt pip list  # run pip inside the Windows venv
./tt python    # open the Windows venv Python
./tt update    # ff-only pull of the current branch
```

The helper intentionally does **not** source a Linux virtual environment. It launches `.venv/Scripts/python.exe`, so PySide6 and sounddevice remain native Windows packages while all commands are issued from WSL.

## Versioning

The canonical project version is stored in the root [`VERSION`](VERSION) file.

Current published version: **0.0.1**

Published version numbers are not reused.

## Repository layout

- `README.md` — public project entry point.
- `VERSION` — canonical SemVer version.
- `tt` — WSL-first development helper for the native Windows environment.
- `docs/` — living project documentation.
- Application source follows the architecture recorded in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Documentation

Start with [`docs/README.md`](docs/README.md).

Key documents:

- [Project state](docs/PROJECT_STATE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [User guide](docs/USER_GUIDE.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisions](docs/DECISIONS.md)
- [Test matrix](docs/TEST_MATRIX.md)
- [Changelog](docs/CHANGELOG.md)

## Development status

TittyTatter is in very early development. Version **0.0.1** establishes the first working-product baseline and the repository/documentation contract. Development after the `v0.0.1` tag continues on the unversioned `work` branch until the next release is ready.
