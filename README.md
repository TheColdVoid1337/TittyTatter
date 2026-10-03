<p align="center">
  <img src="assets/readme_logo.png" width="160" alt="TittyTatter logo">
</p>

# TittyTatter

> Current release: **0.0.3**

**TittyTatter** is a Windows-first desktop **guitar rhythm trainer** for building and practising custom TI / TA rhythm patterns.

The same pattern can be trained in several ways: full repetition, progressive beat ramps, silent-gap exercises, sparse or displaced metronome practice, and optional tempo/timer modifiers. A secondary **Game** layer lets you practise the same exercise with keyboard or mouse input and timing grades when a guitar is not available.

## Highlights

- Flexible meters: numerator **1–16**, denominator **2 / 4 / 8 / 16**.
- Per-beat rhythm grids with straight subdivisions, triplets, dense subdivisions, rests, and long-note coverage.
- Every subdivision can be **(ТИ)**, **ТА**, or silent.
- Multiple guitar-training methods driven by the same pattern and timeline.
- Count-in, tempo trainer, practice timer, stage progress, and ramp warnings.
- Low-latency Windows audio with selectable output-device settings.
- Independent TI, TA, metronome, and master levels.
- Configurable visual metronome with scalable Focus view.
- Optional **Штрих / Picking Guide** with economy and strict-alternate strategies.
- Secondary **Game** layer with keyboard/mouse bindings, timing grades, score, graph, and configurable HIT/MISS feedback.
- Session save/load and persistent local settings.
- MIDI, Guitar Pro 5, and WAV export.

## Training modes

TittyTatter separates **what you play** from **how you train it**. The pattern editor defines the rhythm; the selected Training Mode defines how that pattern behaves over time.

Current modes:

- **Повтор** — repeat the complete pattern continuously.
- **Разгон с 1 доли** — expand from the first beat to the full bar.
- **Разгон с 2 долей** — start from two beats (or one in a one-beat meter), then expand to the full bar.
- **Пропуски** — alternate configurable audible and silent bar blocks while the internal timeline continues.
- **Нарастающие пропуски** — keep the audible block fixed while the silent block grows progressively.
- **Редкий метроном** — reduce metronome guidance to selected beats or bars.
- **Смещённый метроном** — move the click onto off-beat/eighth/sixteenth positions independently of the pattern subdivision.

When **Игра** is selected, the current Training Mode still controls the exercise. Game mode does not have a separate progression system.

## Focus mode

**Фокус режим [F]** turns the application into a distraction-free practice display:

- configuration tabs and editable beat cards are hidden;
- the visual metronome expands;
- the current effective rhythm appears as a read-only strip;
- ramp stages and silent-gap behaviour remain visible correctly;
- Game statistics stay compact when Game is active.

## Штрих / Picking Guide

The Picking Guide is an optional guitar-practice aid, not a separate training mode.

It can show:

- economy-picking suggestions;
- strict alternating down/up strokes;
- the current stroke and string;
- several upcoming strokes;
- current-beat highlighting.

TI is modelled as the 5th string reference and TA as the muted 6th-string reference used by the current trainer design.

## Game layer

Game is a secondary way to execute the same training exercise through computer input.

Features include:

- assignable TI / TA keyboard bindings;
- physical-key handling that is independent of the active keyboard layout where scan-code information is available;
- mouse-button bindings;
- lane-specific TI/TA target matching;
- PERFECT / GREAT / GOOD / HIT timing grades;
- score, accuracy, recent-quality graph, and last-game summary;
- optional separate TI/TA HIT sounds and MISS sounds;
- optional diagnostic logging.

The currently accepted timing grades are:

| Grade | Timing distance | Points |
|---|---:|---:|
| PERFECT | up to 30 ms | 100 |
| GREAT | up to 70 ms | 75 |
| GOOD | up to 120 ms | 50 |
| HIT | other accepted timing | 25 |

## Run from source on Windows

Requirements:

- Windows;
- a current Python 3 installation;
- an audio output device supported by PortAudio/sounddevice.

Clone or download the repository, then run:

```bat
run.bat
```

On first launch, `run.bat` creates a local `.venv`, installs `requirements.txt`, and starts TittyTatter.

Manual equivalent:

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

## Optional diagnostics

Game logging is opt-in. Launch with:

```bat
.venv\Scripts\python.exe app.py -log
```

or use `--log`. Normal runs do not create game diagnostic logs.

## Export

TittyTatter can export the current pattern to:

- **MIDI**
- **Guitar Pro 5**
- **WAV**

Export uses the same rhythm model as realtime playback.

## Documentation

Detailed documentation lives under [`docs/`](docs/README.md):

- [User guide](docs/USER_GUIDE.md)
- [Project state](docs/PROJECT_STATE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development workflow](docs/WORKFLOW.md)
- [Roadmap](docs/ROADMAP.md)
- [Durable decisions](docs/DECISIONS.md)
- [Test matrix](docs/TEST_MATRIX.md)
- [Changelog](docs/CHANGELOG.md)

## Project structure

- `app.py` — PySide6 GUI and application coordination.
- `audio_engine.py` — realtime audio scheduling and synthesized sounds.
- `model.py` / `presets.py` — rhythm model and built-in grid/pattern data.
- `training_modes.py` — Training Mode definitions and timeline helpers.
- `game_logic.py` / `input_binding.py` — Game timing and input bindings.
- `picking_logic.py` — picking-direction logic.
- `exports.py` — MIDI / GP5 / WAV export.
- `game_logger.py` — optional diagnostic logging.
- `docs/` — living project documentation.

## License

No explicit open-source license has been added yet. Repository visibility alone does not grant redistribution or modification rights beyond those provided by applicable law.
