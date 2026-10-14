<p align="center">
  <img src="assets/readme_logo.png" width="160" alt="TittyTatter logo">
</p>

<h1 align="center">TittyTatter</h1>

<p align="center"><strong>Customizable guitar rhythm trainer for Windows</strong></p>

<p align="center">
  <a href="README.md">Русский</a> · <strong>English</strong>
</p>

**Version 0.0.5** · [What's new](docs/RELEASE_NOTES_0.0.5.md)

TittyTatter helps guitarists practice rhythmic accuracy, picking consistency, and their internal sense of pulse. Create a rhythm pattern, choose a training method, and practice with audio and visual guidance. An optional input-based mode lets you practice timing without a guitar.

## Features

- **Rhythm editor.** Time signatures with 1–16 beats and denominators of 2, 4, 8, or 16; per-beat subdivisions including triplets, rests, and sustained-note coverage.
- **Seven training modes.** Full repetition, progressive pattern building, silent-bar exercises, and alternative metronome techniques.
- **Tempo and session tools.** Adjustable BPM, count-in, progressive tempo training, and a practice timer.
- **Audio and display.** Independent rhythm and metronome levels, output-device selection, configurable visual metronome, and an expanded Focus view.
- **Picking guidance.** Alternate and economy picking, string-crossing preferences, upcoming-stroke previews, and optional sweep connections.
- **Timing practice.** An optional Game mode with customizable keyboard/mouse inputs, timing grades, and performance statistics.
- **Saved exercises and export.** Session save/load, persistent preferences, and MIDI, Guitar Pro 5, and WAV export.

## Getting started

### Requirements

- Windows;
- Python 3 with support for creating a virtual environment;
- a working audio output device.

TittyTatter can be run from source. Clone or download the repository, open the project folder, and run:

```bat
run.bat
```

On first launch, the script creates a local `.venv` environment, installs `requirements.txt`, and starts the application. Use the same `run.bat` for subsequent launches.

**Manual setup** is also supported:

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

[Versions and releases](https://github.com/TheColdVoid1337/TittyTatter/releases) · [Source repository](https://github.com/TheColdVoid1337/TittyTatter)

## Basic workflow

1. **Build a pattern.** Select a time signature, then configure the rhythmic subdivisions and attacks for each beat. The editor uses the labels **(ТИ)**, **ТА**, and rest.
2. **Select a training mode.** Repeat the full pattern, build it up progressively, or reduce metronome and audio guidance.
3. **Set the tempo and audio.** Choose a BPM and optionally enable count-in, tempo training, or a timer.
4. **Practice.** Select **Тренировка** (Training) to play along on guitar. Select **Игра** (Game) for keyboard/mouse timing practice using the same exercise.
5. **Enable picking guidance or Focus when useful.** The first provides suggested picking motions; the second enlarges the practice display.

## Training modes

The application interface is in Russian. Its current training modes are:

| Interface label | What it does |
|---|---|
| **Повтор** (Repeat) | Continuously repeats the complete pattern |
| **Разгон с 1 доли** (Build from one beat) | Adds beats progressively, starting with the first |
| **Разгон с 2 долей** (Build from two beats) | Expands the pattern progressively, starting with two beats |
| **Пропуски** (Silent gaps) | Alternates guided and silent bars |
| **Нарастающие пропуски** (Progressive gaps) | Progressively increases the number of silent bars |
| **Редкий метроном** (Sparse metronome) | Reduces click frequency to develop an internal pulse |
| **Смещённый метроном** (Displaced metronome) | Places clicks on offbeats or finer subdivisions |

Silent-bar exercises **continue the internal timeline** even when audio guidance disappears. When Game mode is active, timing targets continue through the silent portions.

## Picking Guide

The **Штрих** (Picking Guide) tab provides optional guitar-technique guidance. It does not change the underlying rhythm.

- **Строго переменный** (Strict Alternate): downstrokes and upstrokes alternate across played attacks, with an optional starting direction.
- **Экономный** (Economy): picking suggestions take string changes, directional sweeps, repeated motifs, and progressive training stages into account.
- **Advanced Economy controls:** explicit USX / DSX / DBX profiles, inside/outside string-crossing preference, and optional sweep-link indicators.

For the current two-string exercise model, **ТИ** represents string 5 and **ТА** represents a muted string 6. Picking suggestions are educational guidance and do not automatically infer an individual player's physical technique.

## Game and Focus modes

**Игра** (Game) provides a way to assess rhythm accuracy with keyboard or mouse input. It grades timing, displays performance statistics, and follows the selected training mode rather than creating a separate exercise.

**Фокус** (Focus) hides editing controls and expands the visual metronome. The current effective rhythm remains visible. Press **F** to toggle Focus unless that key is currently assigned to Game input.

## Export and saved sessions

- **MIDI** — edit or arrange the rhythm in compatible music software.
- **Guitar Pro 5 (.gp5)** — view and edit exercises in compatible applications.
- **WAV** — render the exercise to an audio file.

Sessions can be saved and reopened. Application preferences are stored locally.

## Documentation

- [Detailed user guide](docs/USER_GUIDE.md)
- [Changelog](docs/CHANGELOG.md)
- [Technical documentation](docs/README.md)

## License

The repository does not currently contain a separate license granting redistribution or modification rights. Public visibility of source code alone does not imply an open-source license.
