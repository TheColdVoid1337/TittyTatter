# Project state

## Baseline

- Project: **TittyTatter**
- Published application version: **0.0.3**
- Published tag: **v0.0.3**
- Active development/release-preparation branch: **work**
- Integration/release branch: **main**
- Primary platform: Windows desktop
- Language: Python
- GUI: PySide6
- Audio: callback-driven realtime playback through python-sounddevice / PortAudio
- Preferred Windows backend: WASAPI
- Development workflow: **vFLOW**

The 0.0.3 release baseline is immutable.

The current functional post-0.0.3 runtime baseline was manually accepted at:

```text
2ffca5d Refine focus rhythm strip and beat lamps
```

The project owner also confirmed a green:

```text
./tt check
```

for that functional baseline.

Subsequent commits in the current release-preparation sequence are documentation/public-asset changes and do not by themselves constitute new local runtime validation.

The next numeric release version has **not yet been selected in this document**. Root `VERSION` remains `0.0.3` until the explicit release metadata checkpoint.

## Current product definition

TittyTatter is first and foremost a **guitar rhythm training tool**.

Core hierarchy:

```text
PATTERN
  what is played

TRAINING MODE
  how the pattern is trained over time

TRAINING
  play that exercise on guitar

GAME
  execute the same training timeline through keyboard/mouse input and score timing

PICKING GUIDE / ШТРИХ
  optional guitar-practice information
```

Game does not own a separate progression system.

Picking Guide is not a third peer mode.

## Implemented product scope

Current implementation includes:

- flexible meters with numerator 1–16 and denominator 2/4/8/16;
- horizontally scrollable per-beat pattern editor;
- per-beat selectable rhythm grids;
- TI / TA / OFF subdivision states;
- long-note/span coverage;
- per-beat Mute where the selected exercise permits it;
- count-in;
- Tempo Trainer;
- practice Timer;
- compact BPM/tap controls;
- callback/sample-clock-driven playback;
- WASAPI-preferred Windows output handling and audio-system controls;
- independent TI, TA, metronome, and master sound controls;
- configurable visual metronome;
- session save/load and persistent local settings;
- MIDI, Guitar Pro 5, and WAV export.

### Training Modes

Current first-class Training Modes:

1. Повтор
2. Разгон с 1 доли
3. Разгон с 2 долей
4. Пропуски
5. Нарастающие пропуски
6. Редкий метроном
7. Смещённый метроном

The Training Mode is the source of truth in both normal Training and Game.

Gap modes remove audible/visual rhythmic guidance during silence while the internal timeline continues.

### Game

Current Game layer includes:

- top-level Тренировка / Игра selector;
- keyboard bindings;
- mouse bindings;
- physical scan-code handling where available;
- lane-only TI/TA target matching;
- asymmetric accepted timing window;
- short early-input buffering;
- PERFECT / GREAT / GOOD / HIT grading;
- Score and timing feedback;
- recent-quality/history graph;
- configurable HIT/MISS feedback;
- separate TI/TA HIT options;
- guitar-style feedback set;
- opt-in archived diagnostics.

Opposite-lane fallback and adaptive timing bias remain intentionally absent.

### Picking Guide / Штрих

Current Picking Guide includes:

- economy strategy;
- strict alternate strategy;
- current stroke/string cue;
- configurable 1–8 following strokes;
- current-beat highlighting;
- cyclic repeated-beat period preservation;
- cyclic Ramp-stage behavior.

Picking Guide and Game are mutually exclusive in the UI.

### Focus mode

Current Focus view:

- hides configuration tabs/editable beat cards;
- expands the visual metronome;
- scales actual needle/pivot/lamp/flash geometry;
- keeps the Game graph compact;
- renders a read-only effective rhythm strip;
- uses rounded TI cells;
- uses yellow current-subdivision outlining;
- hides current-position guidance during silent Gap phases;
- preserves physical-F/Game-binding priority.

### About / branding

The application has:

- About tab;
- application/window icon;
- author/repository links;
- runtime icon transparency/safe-area handling.

The public README uses a dedicated transparent repository asset so GitHub does not depend on Qt runtime image conversion.

## Validation state

Confirmed by the project owner for the accepted functional baseline:

- `work @ 2ffca5d`;
- `./tt check` green;
- Focus visual state manually accepted;
- latest TI pill / beat-lamp positioning accepted.

Release-preparation documentation/asset commits were created after that acceptance.

Before the final tag, pull the exact release commit and perform the final release gate described in `TEST_MATRIX.md` and `WORKFLOW.md`.

## Repository / branch state

At the beginning of this release-preparation cycle:

- `main` was `ac0c83f` — Release TittyTatter 0.0.3;
- `work` was a clean descendant of `main`;
- `main...work` was 30 commits ahead / 0 behind at the accepted functional baseline.

Release-preparation commits are being added to `work`.

Old branches checked during release preparation:

- `dev/0.0.2` is fully contained in the current `main` history (no unique commits relative to `main`);
- `release/0.0.1` is fully contained in the current `main` history (no unique commits relative to `main`).

They are cleanup candidates **after** the new release is tagged and verified.

Do not delete `work` by default.

## Repository cleanup result so far

The tracked repository root and `docs/` listing were inspected during release preparation.

No obvious tracked temporary/generated junk was identified for deletion.

Local untracked files cannot be inspected through the GitHub connector, so final release preparation still requires the project owner to provide:

```bash
git status --short
```

Unknown local files must not be deleted automatically.

## Documentation state

The release-preparation cycle is updating documentation in place.

Current documentation goals:

- public root README written for end users;
- dedicated transparent README logo asset;
- current User Guide;
- current Architecture;
- current Training-focused Roadmap;
- durable Decisions;
- expanded Test Matrix;
- post-0.0.3 Unreleased Changelog;
- canonical vFLOW Workflow document.

## Known limitations

- There is no user-facing end-to-end keyboard/audio latency calibration profile yet.
- No MIDI-controller input scoring yet.
- Audio-device behavior depends on the Windows/driver/PortAudio stack and still requires real-device validation.
- Guitar Pro export intentionally uses conservative text for legacy compatibility.
- No finalized installer/updater or packaged binary release workflow.
- Practice history is limited compared with a long-term statistics database.
- Picking Guide currently uses the project's TI/string-5 and TA/string-6 reference model.

## Immediate release sequence

1. Finish documentation/public asset preparation on `work`.
2. Review local `git status --short`.
3. Confirm the intended next release version.
4. Apply dedicated release metadata update.
5. Pull the exact release candidate locally.
6. Run the final release gate.
7. Fast-forward `main` if the branch relationship remains clean.
8. Create/verify annotated `vX.Y.Z` tag.
9. Synchronize retained `work` to the final release commit.
10. Delete obsolete old branches only after final containment verification.

## Durable repository rules

1. Root `VERSION` is the canonical published application version.
2. Numeric version changes happen only at explicit release/tag checkpoints.
3. Root `README.md` is the public user entry point.
4. Detailed living documentation belongs under `docs/`.
5. Technical documentation/identifiers/commits are English-first.
6. Published versions/tags are immutable.
7. Local Windows GUI/audio validation is canonical.
8. GitHub CI is not the default validation path.
9. Prefer frequent semantic commits.
10. Do not silently delete files/branches.
11. Preserve backward-compatible settings where practical.
12. Stable TI/TA training sound synthesis should not drift during unrelated work.
13. Add functionality without unnecessarily replacing working functionality.
14. Do not claim local validation succeeded without user evidence.
