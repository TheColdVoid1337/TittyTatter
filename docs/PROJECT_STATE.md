# Project state

## Baseline

- Project: **TittyTatter**
- Version: **0.0.1**
- Status: early development / working prototype baseline
- Primary platform: desktop, Windows-first
- Language: Python
- GUI direction: PySide6
- Audio direction: callback-driven realtime playback

## Product scope

TittyTatter is a focused rhythm-practice tool built around user-defined TI / TA cells.

The current baseline supports or is intended to preserve:

- four beats per 4/4 bar;
- independent subdivision choice per beat;
- straight sixteenths and eighth-note triplets;
- TI / TA / silence per subdivision;
- built-in pattern presets;
- A/B construction;
- practice ramps such as 1/4 → 2/4 → 3/4 → 4/4 and 2/4 → 4/4;
- live BPM changes and tap tempo;
- count-in and tempo trainer;
- independent TI / TA / metronome / master sound controls;
- TI clap-like sound;
- optional complete TA muting;
- visual playhead;
- session persistence.

## Current limitations

The project is still pre-stable. Before any claim of a production-ready release, the application needs broad real-device audio testing and hands-on practice feedback.

Not yet considered stable commitments:

- audio-device selection UX;
- timing-input scoring;
- MIDI input;
- practice playlists;
- statistics/history;
- export formats;
- installer/release packaging.

## Repository rules

1. Root `VERSION` is the canonical SemVer source.
2. Root `README.md` is the public project entry point.
3. Detailed documentation lives under `docs/`.
4. Technical filenames, identifiers, branch names, commits, and documentation are English-first.
5. Published versions are never reused.
6. Feedback from actual practice outranks speculative feature expansion.
