# Project state

## Baseline

- Project: **TittyTatter**
- Current release version: **0.0.2**
- Current integration branch: **main**
- Status: release commit prepared and locally validated; annotated `v0.0.2` tag pending manual creation
- Primary platform: Windows desktop
- Language: Python
- GUI: PySide6
- Audio: callback-driven realtime playback through python-sounddevice / PortAudio
- Preferred Windows backend: WASAPI
- Development shell: WSL
- Runtime: native Windows Python virtual environment

The current `main` state is assigned **0.0.2** after successful local release validation. The annotated `v0.0.2` tag is created and pushed manually.

## Implemented product scope

The current application includes:

- flexible meters with numerator 1–16 and denominator 2/4/8/16;
- a horizontally scrollable per-beat editor for wide meters;
- per-beat selectable rhythm grids;
- (ТИ) / ТА / OFF subdivision states;
- built-in binary straight and triplet presets;
- per-beat Mute in non-ramp practice modes;
- random full-bar generation;
- count-in;
- practice ramps;
- tempo trainer;
- optional timed practice with end signal;
- live BPM controls and tap tempo;
- callback/sample-clock-driven playback;
- WASAPI-preferred output selection and audio-system controls;
- independent (ТИ), ТА, metronome, and master sound controls;
- configurable visual metronome;
- rhythm-game keyboard scoring with Low/Mid/High timing windows;
- DAC-time-based game targets, hit/miss feedback, early/late timing, graph, and last-game statistics;
- JSON session save/load;
- ignored persistent local application settings;
- MIDI export;
- Guitar Pro 5 export;
- WAV export.

## Canonical local workflow

Repository:

```text
Windows: F:\_PROJECT\TittyTatter
WSL:     /mnt/f/_PROJECT/TittyTatter
```

WSL is the command/control environment. TittyTatter itself runs through the Windows interpreter at `.venv/Scripts/python.exe`.

Canonical commands:

```bash
./tt install
./tt doctor
./tt check
./tt run
```

GitHub is used for source/history. Routine validation is performed locally; the removed GitHub smoke workflow is not part of the current process.

## Release validation

The 0.0.2 release candidate passed the canonical local gate on Windows through the WSL-controlled environment:

- `./tt install` completed successfully;
- `./tt doctor` confirmed the Windows Python environment and dependencies;
- `./tt check` passed core tests, compile checks, export tests, and dependency imports;
- manual GUI/audio acceptance was confirmed before the release commit.

The remaining release action is manual creation and push of the annotated `v0.0.2` tag from the validated `main` release commit.

## Known limitations

- Keyboard game scoring is not input-latency calibrated.
- No MIDI-controller input scoring yet.
- Audio-device behavior still depends on the Windows/driver/PortAudio stack and requires real-device validation.
- Guitar Pro export intentionally uses conservative ASCII annotations for GP5 text compatibility.
- No installer/updater or packaged release workflow is finalized.
- Practice history is limited to the most recent game summary rather than a long-term statistics database.

## Repository rules

1. Root `VERSION` is the canonical SemVer source for published builds.
2. Numeric versions change only at release/tag checkpoints.
3. Root `README.md` is the public project entry point.
4. Detailed living documentation lives under `docs/`.
5. Technical filenames, identifiers, branch names, commits, and documentation are English-first.
6. Published versions are never reused.
7. Actual practice feedback outranks speculative expansion.
8. Windows runtime + WSL command control is the canonical development workflow.
9. Local gates are canonical; GitHub CI is not required for ordinary development.
