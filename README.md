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

## Versioning

The canonical project version is stored in the root [`VERSION`](VERSION) file.

Current version: **0.0.1**

Published version numbers are not reused.

## Repository layout

- `README.md` — public project entry point.
- `VERSION` — canonical SemVer version.
- `docs/` — living project documentation.
- Application source will follow the architecture recorded in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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

TittyTatter is in very early development. Version **0.0.1** establishes the first working-product baseline and the repository/documentation contract. The next passes are expected to be driven by hands-on feedback from actual rhythm practice.

