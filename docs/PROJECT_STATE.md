# Project state

## Baseline

- Project: **TittyTatter**
- Current release version: **0.0.3**
- Current development branch: **work**
- Current integration branch: **main**
- Status: 0.0.3 release commit prepared after successful local validation; annotated `v0.0.3` tag pending manual creation
- Primary platform: Windows desktop
- Language: Python
- GUI: PySide6
- Audio: callback-driven realtime playback through python-sounddevice / PortAudio
- Preferred Windows backend: WASAPI
- Development shell: WSL
- Runtime: native Windows Python virtual environment

`main` contains the locally validated 0.0.3 release candidate. The annotated `v0.0.3` tag is created and pushed manually after one final metadata-only check.

## Implemented product scope

The current release candidate includes:

- flexible meters with numerator 1–16 and denominator 2/4/8/16;
- a horizontally scrollable per-beat editor for wide meters;
- per-beat selectable rhythm grids;
- (ТИ) / ТА / OFF subdivision states;
- built-in binary straight and triplet presets;
- per-beat Mute in non-ramp practice modes;
- random full-bar generation;
- count-in;
- practice ramps with stage progress and stage-change warnings;
- tempo trainer;
- optional timed practice with dedicated completion horn;
- live BPM controls and tap tempo;
- callback/sample-clock-driven playback;
- WASAPI-preferred output selection and audio-system controls;
- independent (ТИ), ТА, metronome, and master sound controls;
- configurable visual metronome;
- keyboard game scoring with Score, graded timing, current/last-game statistics, and optional hit/miss sounds;
- lane-only TI/TA matching with short early-input buffering;
- economy-picking guidance rendered in the metronome area;
- JSON session save/load;
- ignored persistent local application settings;
- opt-in timestamped archived game diagnostics;
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

Optional diagnostic game run:

```bash
./tt run -log
```

GitHub is used for source/history. Routine validation is performed locally; GitHub CI is not part of the current process.

## Release-candidate validation

The current `work` state has received iterative manual GUI/audio/game acceptance during development, including real game-play feedback and diagnostic-log review.

Before integration/tagging, the canonical final gate is still:

1. update local `work` to the release-prep commit;
2. run `./tt doctor`;
3. run `./tt check`;
4. run `./tt run` and confirm focused GUI/audio/game behavior on the Windows machine.

After that successful gate, `work` may be fast-forwarded into `main`. Only then is the next numeric version selected, committed, and manually tagged.

## Known limitations

- There is no user-facing manual keyboard/audio latency calibration profile yet.
- No MIDI-controller input scoring yet.
- Audio-device behavior still depends on the Windows/driver/PortAudio stack and requires real-device validation.
- Guitar Pro export intentionally uses conservative ASCII annotations for GP5 text compatibility.
- No installer/updater or packaged release workflow is finalized.
- Practice history is limited to the most recent game summary rather than a long-term statistics database.
- Economy-picking guidance is algorithmic and currently models TI as string 5 and TA as string 6 only.

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
10. Stable layout should not be changed without a concrete need; prefer additive changes over unnecessary rewrites.
