# Project state

## Baseline

- Project: **TittyTatter**
- Published application version: **0.0.4**
- Published tag: **v0.0.4**
- Published release commit: `1722c0ac8ef9b73b88c2f3bf5aea7d4d6fa96015`
- Active development branch: **work**
- Integration/release branch: **main**
- Primary platform: Windows desktop
- Language: Python
- GUI: PySide6
- Audio: callback-driven realtime playback through python-sounddevice / PortAudio
- Preferred Windows backend: WASAPI
- Development workflow: **vFLOW**

The 0.0.4 release is complete and immutable.

At release close:

```text
main -> 1722c0a Release TittyTatter 0.0.4
work -> 1722c0a Release TittyTatter 0.0.4
tag  -> v0.0.4 (annotated) -> 1722c0a
```

The project owner confirmed both:

```text
./tt check
TittyTatter checks OK
```

and the manual GUI/audio smoke for that exact release commit.

Post-0.0.4 development continues on `work`. Root `VERSION` remains `0.0.4` until a future explicit release checkpoint.

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

Gap modes remove audible/visual rhythmic guidance while the internal timeline continues.

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

The published 0.0.4 baseline includes:

- economy strategy;
- strict alternate strategy;
- current stroke/string cue;
- configurable 1–8 following strokes;
- current-beat highlighting;
- cyclic repeated-beat period preservation;
- cyclic Ramp-stage behavior.

Post-0.0.4 `work` contains additional transitional picking fixes derived from manual practice screenshots:

- repeated active motifs are stabilized;
- repeated patterns may preserve a sweep-rich phrase-level variant;
- Ramp stages attempt to keep already-learned strokes stable;
- inactive Ramp TA pulses are treated as a continuing attack stream rather than unrelated one-note phrases.

These fixes are useful regression evidence, but they are **not** the final Picking architecture.

The canonical next design is:

- [PICKING_LOGIC_V2.md](PICKING_LOGIC_V2.md)

Picking Logic v2 is currently at **P6 runtime cutover implemented; automated and manual acceptance pending**.

P1-P4 are locally validated. P5 joint Ramp solving was locally validated green on `eed6ddb`. The live Picking Guide now calls the v2 Alternate, Economy, and joint Ramp solvers. The old transitional functions remain only as regression/reference code until P6 acceptance is complete.

The current UI/runtime arrow generator still uses the transitional path; v2 visual cutover remains deferred until the integration phase.

Picking Guide and Game remain mutually exclusive in the UI.

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

## Current development focus

Immediate focus after 0.0.4:

> **Picking Logic v2**

The purpose is to replace accumulating pattern-specific Picking heuristics with one coherent, testable optimizer.

The accepted design direction includes:

- Alternate = attack-alternate;
- Economy = practical directional economy, not maximum sweeping;
- stable repeated motor motifs;
- explicit continuity rather than OFF-always-reset behavior;
- start-polarity search;
- parity and loop-boundary awareness;
- transition classification including real directional sweeps;
- future escape-profile hook without pretending to infer user biomechanics;
- joint Ramp-stage optimization with persistent real attacks and stage-local placeholders;
- deterministic explanations/regression cases.

See `docs/PICKING_LOGIC_V2.md` for the complete state model, scoring priorities, 42-case regression matrix, and phased implementation plan.

## Validation state

### Published 0.0.4

Confirmed:

- release commit `1722c0a`;
- `./tt check` green;
- manual GUI/audio smoke accepted;
- annotated `v0.0.4` verified to peel to the same commit.

### Post-0.0.4 work

P6 partial manual acceptance on `e611ec2`:

- `./tt check` green;
- Ramp 1->2->3->4 Economy checked in the live GUI with the sweep-compatible control motif `TA TI TI TA` repeated for beats 1-3 and `TI TA TI TA` on beat 4;
- the repeated A motif stayed `DOWN DOWN UP UP` on every opened stage;
- the 6->5 DOWN/DOWN and 5->6 UP/UP directional sweeps were preserved;
- already-open real attacks did not change as later beats opened;
- inactive TA placeholders alternated cleanly, including the active->placeholder boundary after the `e611ec2` tie-break fix;
- public Alternate with OFF slots was checked in the live GUI using the 8-attack control pattern `TA . TA . | TI . TI . | TA . TI . | TA . . TI`; the visible attack sequence alternated `DOWN UP DOWN UP DOWN UP DOWN UP`, so OFF slots did not consume or reset parity.

P6 is not fully accepted yet: Ramp 2->full Economy and a non-Ramp Economy repetition case still need manual GUI confirmation.

Recent Picking changes on `work` were investigated through manual screenshots and direct practice feedback.

The last runtime Picking commit before the v2 design-document commits is:

```text
cdda56a Alternate inactive ramp TA pulses
```

That exact runtime change still requires normal local confirmation if it has not yet been checked after pull.

The later Picking Logic v2 commits are documentation-only and do not themselves validate or alter runtime behavior.

Do not report post-release runtime code as locally validated without explicit user evidence.

## Repository / branch state

Remote release cleanup is complete.

Expected remote branches:

```text
main
work
```

Published `main` remains on the immutable 0.0.4 release commit.

`work` is a clean descendant of `main` and contains post-release Picking experiments plus the Picking Logic v2 specification/documentation.

Obsolete remote branches `dev/0.0.2` and `release/0.0.1` were removed only after containment verification showed no unique commits.

Do not delete `work` by default.

## Documentation state

Current canonical project documents include:

- public root README for end users;
- current User Guide;
- current Architecture;
- vFLOW Workflow;
- Picking Logic v2 design;
- Training-focused Roadmap;
- durable Decisions;
- Test Matrix;
- Changelog;
- this Project State.

Documentation is updated in place.

## Known limitations

- There is no user-facing end-to-end keyboard/audio latency calibration profile yet.
- No MIDI-controller input scoring yet.
- Audio-device behavior depends on the Windows/driver/PortAudio stack and still requires real-device validation.
- Guitar Pro export intentionally uses conservative text for legacy compatibility.
- No finalized installer/updater or packaged binary release workflow.
- Practice history is limited compared with a long-term statistics database.
- Picking Guide currently uses the project's TI/string-5 and TA/string-6 reference model.
- Current Picking runtime logic remains transitional until Picking Logic v2 replaces the accumulated post-0.0.4 heuristics.
- Player-specific USX/DSX/DBX behavior is not inferred or configured yet.

## Immediate sequence

1. Treat `docs/PICKING_LOGIC_V2.md` as the canonical Picking redesign specification.
2. Do not add another pattern-specific heuristic unless needed as a regression-preserving emergency fix.
3. **P1 complete:** normalized Picking events plus persistent real-attack / stage-local placeholder identities.
4. **P2 complete and locally validated:** deterministic attack-alternate engine on normalized events.
5. **P3 complete and locally validated:** Economy transition/scoring semantics with explicit transition types, start-polarity search, parity, loop-boundary scoring, linked sweeps, and explanations.
6. **P4 complete and locally validated:** motif consistency is enforced inside the optimizer rather than post-hoc.
7. **P5 complete and locally validated:** all Ramp stages are solved jointly with persistent real attacks, stage-local placeholders, motif constraints, and cyclic stage boundaries.
8. **P6 cutover implemented; acceptance pending:** run `./tt check`, then `./tt run` and manually verify Loop/Alternate/Economy plus both Ramp modes and the known sweep/placeholder cases.
9. Delete or quarantine the transitional picking path only after that manual acceptance.

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
15. New Picking failures should become regression cases against the v2 model instead of accumulating ad-hoc special cases.
