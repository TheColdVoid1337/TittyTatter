# Project state

## Release baseline

- Project: **TittyTatter**
- Application version in this release source: **0.0.6**
- Release identifier: **v0.0.6** — published and verified 2026-10-23
- Previous published tag: **v0.0.5**
- Previous release commit: `21c33aa2680c8c25fafccde90bf292cb1390440a`
- Active development branch: **work**
- Release/integration branch: **main**
- Primary platform: Windows desktop
- Runtime: Python / PySide6 / sounddevice and PortAudio (WASAPI preferred)
- Development workflow: **vFLOW**

### 0.0.6 release candidate acceptance evidence

On 2026-10-23 the owner reported a green `./tt check` (including Training Modes tests), a green `./tt burst-smoke`, and confirmed Custom Burst working in the live Windows GUI. The feature candidate was accepted, and the owner then confirmed both tests on the exact release commit `afc9edf2596ebc284e27fc09516b38cbd52324fb` before the annotated v0.0.6 tag and GitHub Release were published. Seven additional Training Modes were included; separate manual audition of each new mode was not individually recorded.

The Custom per-metric-beat «Рывок» option was **requested by Fulton97**. It switches between base and alternate BPM for selected beats, retaining the original A–B–A–B whole-bar schedule. See [release notes](RELEASE_NOTES_0.0.6.md).

### 0.0.5 acceptance evidence

The 0.0.5 release introduces Picking Logic v2 (P1–P7d) and bilingual public README documentation. On 2026-10-14, the user confirmed a clean working tree, a green `./tt check`, and a `./tt picking-log` with `SELF-TEST PASS` on candidate `da166fe`. The diagnostic demonstrated distinct Inside/Outside sequences, two valid sweep connections, differing USX/DSX solutions, and consistent Ramp-stage output. The user subsequently confirmed the live application/GUI/audio smoke passed.

The exact 0.0.5 release commit `21c33aa2680c8c25fafccde90bf292cb1390440a` subsequently passed the user's complete local `./tt check` with a clean working tree. `main` was fast-forwarded to that SHA; the full annotated tag `v0.0.5` was published and independently verified to peel to it. The GitHub Release is published. See [release notes](RELEASE_NOTES_0.0.5.md) for the complete record.

### Release history

- **0.0.4:** published 2026-10-04, annotated `v0.0.4`, commit `1722c0ac8ef9b73b88c2f3bf5aea7d4d6fa96015`.
- **0.0.5:** published 2026-10-14, annotated `v0.0.5` (full release notes), commit `21c33aa2680c8c25fafccde90bf292cb1390440a`. [GitHub Release](https://github.com/TheColdVoid1337/TittyTatter/releases/tag/v0.0.5).
- **0.0.6:** published 2026-10-23. Seven new Training Modes and Fulton97's Custom Burst. Annotated `v0.0.6` peels to `afc9edf2596ebc284e27fc09516b38cbd52324fb`; full release notes and [GitHub Release](https://github.com/TheColdVoid1337/TittyTatter/releases/tag/v0.0.6) confirmed.

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
8. Лестница делений
9. Рывки темпа (A–B–A–B / Custom)
10. Сдвиг акцента
11. По памяти
12. Интервалы
13. Волна темпа
14. Случайный темп

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

The preceding 0.0.4 release included:

- economy strategy;
- strict alternate strategy;
- current stroke/string cue;
- configurable 1–8 following strokes;
- current-beat highlighting;
- cyclic repeated-beat period preservation;
- cyclic Ramp-stage behavior.

Since version 0.0.5, **Picking Logic v2** is the only live Picking Guide implementation; v0.0.6 retains it.

Canonical design:

- [PICKING_LOGIC_V2.md](PICKING_LOGIC_V2.md)

Current v2 behavior includes:

- attack-alternate public Alternate semantics;
- event-based practical directional Economy;
- explicit directional-sweep classification;
- repeated whole-beat motif constraints inside optimization;
- joint Ramp-stage solving with persistent real attacks;
- stage-local inactive-beat TA placeholders;
- cyclic loop/stage boundary scoring;
- stable real-attack strokes as Ramp stages open.

P1-P6 were implemented and manually accepted in the live GUI. The superseded transitional picking implementation was removed in cleanup commit `debda3e` and locally validated green with `./tt check` on `0df6f88`.

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

## 0.0.6 Training Mode expansion

Seven post-v0.0.5 Training Modes are now included in the v0.0.6 source: Subdivision Ladder, Burst Trainer, Accent Shift, Blind Pattern, Endurance Intervals, Tempo Wave and Random Tempo Blocks. Pure training-phase helpers and the same PortAudio callback/Game timeline schedule all attacks; mode-specific controls, phase status, contextual advice, sessions/settings and regression tests are available. Detailed semantics and intentionally simplified Ladder behaviors are in [TRAINING_MODE_DESIGNS.md](TRAINING_MODE_DESIGNS.md).

### Fulton97 Custom Burst enhancement

**Requested by Fulton97** and implemented as a second Burst variant. The default A–B–A–B continues switching between configurable **whole-bar** blocks. Custom uses a checkbox next to Mute on each «Доля N» card: an independent tempo flag for each metric beat (1–16, e.g. six in 6/4). Selected beats use «Рывок, BPM» and unmarked beats use base BPM, with no fixed multiplier. The mask repeats each bar. Flags and variant are persistent and independent of TI/TA/OFF/Mute. Count-in stays at base BPM; callback-boundary timing and Game target identity are covered by regression tests. User confirmed the feature works on Windows.

Exports still render the **stored Pattern at base BPM**, not the effective Training Mode timeline. The `GUI_tkinter` branch is an independent, unmerged GUI experiment and is **not** part of v0.0.6.

## Unreleased Burst ×2 follow-up (work only)

The Burst A–B–A–B and Custom variants now share an optional inline «×2» control beside «Рывок, BPM». It computes the alternate tempo as exactly twice the current transport BPM; the manual 20–320 BPM value is preserved but disabled while checked. Automatic ×2 may reach 640 BPM when base BPM is 320, without rounding or capping at the manual limit. Count-in stays at base BPM, and the original whole-bar / per-beat switch boundaries remain authoritative. `practice.burst_x2` persists in JSON session and ignored app settings; old files default to false. **Tests and manual Windows acceptance are pending on this new post-release `work` change; `main` and `v0.0.6` remain unchanged.**

## Current development focus

Picking Logic v2 P1–P7d remains the accepted Picking Guide architecture. The next cycle should prioritize feedback-driven hardening of the fourteen Training Modes, review of richer practice-pattern workflows and focused timing regression tests rather than another GUI redesign. Rhythmic/ghost-stroke Alternate (P7e) remains deferred.

See [ROADMAP.md](ROADMAP.md) for upcoming features and [PICKING_LOGIC_V2.md](PICKING_LOGIC_V2.md) for the current Picking architecture.

## Validation state

### 0.0.6 release candidate

- Owner-confirmed `./tt check`: PASS on the post-0.0.5 feature candidate (2026-10-23).
- Owner-confirmed `./tt burst-smoke`: PASS; per-card Custom controls, 6/4 selection, legacy session and persistence checks.
- Owner-confirmed live Custom Burst: works on Windows.
- Full fourteen-mode individual manual-audio pass: not separately recorded.
- Exact v0.0.6 release commit `afc9edf`: owner-confirmed `./tt check` and `./tt burst-smoke` PASS; annotated `v0.0.6` tag peels to that commit, and GitHub Release is public.

### Published 0.0.5

- `git status --short`: clean on `da166fe`.
- `./tt check`: PASS on `da166fe`.
- `./tt picking-log`: `SELF-TEST PASS` on `da166fe`.
- Local GUI/audio smoke: user-confirmed PASS.
- Exact release commit `21c33aa`: `./tt check` PASS, clean working tree; user confirmed. Annotated `v0.0.5` tag/peel and published GitHub Release verified.

### Published 0.0.4

Confirmed:

- release commit `1722c0a`;
- `./tt check` green;
- manual GUI/audio smoke accepted;
- annotated `v0.0.4` verified to peel to the same commit.

### Post-0.0.4 work

P6 manual acceptance completed on the live v2 runtime path (including `e611ec2`):

- `./tt check` green;
- Ramp 1->2->3->4 Economy checked in the live GUI with the sweep-compatible control motif `TA TI TI TA` repeated for beats 1-3 and `TI TA TI TA` on beat 4;
- the repeated A motif stayed `DOWN DOWN UP UP` on every opened stage;
- the 6->5 DOWN/DOWN and 5->6 UP/UP directional sweeps were preserved;
- already-open real attacks did not change as later beats opened;
- inactive TA placeholders alternated cleanly, including the active->placeholder boundary after the `e611ec2` tie-break fix;
- public Alternate with OFF slots was checked in the live GUI using the 8-attack control pattern `TA . TA . | TI . TI . | TA . TI . | TA . . TI`; the visible attack sequence alternated `DOWN UP DOWN UP DOWN UP DOWN UP`, so OFF slots did not consume or reset parity.
- Ramp 2->full Economy was checked in the live GUI on the same sparse control pattern: the first two real beats kept the same Economy strokes from the 2-beat stage to the 4-beat stage, and the temporary inactive-beat TA placeholders alternated cleanly.
- Loop / Economy A B A B was checked in the live GUI: beat 1 matched beat 3 and beat 2 matched beat 4, confirming stable repeated motif identity in the live v2 path.

P6 manual acceptance is complete.

Picking Logic v2 P1-P6 behavior was validated through repeated `./tt check` gates plus live GUI screenshots for Ramp 1->full, Ramp 2->full, Alternate with OFF slots, directional sweeps, placeholders, and Loop A/B/A/B motif stability.

Cleanup commit `debda3e Remove transitional picking implementation` was pulled through `0df6f88` and explicitly passed the full local `./tt check` gate: core tests, compile, export tests, game log tests, and dependency imports all reported OK.

## Repository / branch state

Remote release cleanup is complete.

Expected retained remote branches:

```text
main
work
GUI_tkinter  # unmerged experimental GUI
```

The `v0.0.5` annotated tag remains immutable at its historical commit `21c33aa`. `main` was fast-forwarded to the 0.0.6 release commit `afc9edf2596ebc284e27fc09516b38cbd52324fb`; annotated `v0.0.6` tag and the public GitHub Release were independently verified. The `work` branch contains additional unreleased development changes.

`work` is the ongoing development branch; `GUI_tkinter` has unique experimental history and must not be deleted or merged as part of this release.

Obsolete remote branches `dev/0.0.2` and `release/0.0.1` were removed only after containment verification showed no unique commits.

Do not delete `work` by default.

## Documentation state

Current canonical project documents include:

- Russian public root README and English `README.en.md`;
- current User Guide;
- current Architecture;
- vFLOW Workflow;
- Picking Logic v2 design;
- Training-focused Roadmap;
- durable Decisions;
- Test Matrix;
- Changelog;
- this Project State;
- the historical post-v0.0.5 handoff at `docs/dev/HANDOFF_TITTYTATTER_2026-10-14_v0.0.5.md` (retained as history, not current instructions);
- complete v0.0.6 release notes at `docs/RELEASE_NOTES_0.0.6.md`.

Documentation is updated in place.

## Known limitations

- There is no user-facing end-to-end keyboard/audio latency calibration profile yet.
- No MIDI-controller input scoring yet.
- Audio-device behavior depends on the Windows/driver/PortAudio stack and still requires real-device validation.
- Guitar Pro export intentionally uses conservative text for legacy compatibility.
- No finalized installer/updater or packaged binary release workflow.
- Practice history is limited compared with a long-term statistics database.
- Picking Guide currently uses the project's TI/string-5 and TA/string-6 reference model.
- Player-specific USX/DSX/DBX behavior is never inferred. P7b exposes an explicit Economy profile and was locally/log validated on `fab918b`.
- P7a Strict-Alternate first-stroke control is locally validated on `10ab611`: `./tt check` passed and live GUI behavior was confirmed.

## Immediate sequence

1. Treat `docs/PICKING_LOGIC_V2.md` as the canonical Picking redesign specification.
2. Do not add another pattern-specific heuristic unless needed as a regression-preserving emergency fix.
3. **P1 complete:** normalized Picking events plus persistent real-attack / stage-local placeholder identities.
4. **P2 complete and locally validated:** deterministic attack-alternate engine on normalized events.
5. **P3 complete and locally validated:** Economy transition/scoring semantics with explicit transition types, start-polarity search, parity, loop-boundary scoring, linked sweeps, and explanations.
6. **P4 complete and locally validated:** motif consistency is enforced inside the optimizer rather than post-hoc.
7. **P5 complete and locally validated:** all Ramp stages are solved jointly with persistent real attacks, stage-local placeholders, motif constraints, and cyclic stage boundaries.
8. **P6 complete and manually accepted:** live Alternate/Economy/Ramp paths use Picking Logic v2.
9. **Cleanup complete and locally validated:** transitional implementation/tests were removed in `debda3e`; `./tt check` passed on `0df6f88`.
10. Picking Logic v2 core rollout is complete.
11. **P7a complete and locally/manual validated:** Auto / DOWN / UP first-stroke control is available only for Strict Alternate; Economy and joint Ramp keep automatic global start-polarity optimization. `./tt check` passed on `10ab611`, and the GUI correctly hides the row for Economy and flips Alternate polarity for DOWN/UP.
12. **P7b complete and locally/log validated:** Auto / USX / DSX / DBX Economy profiles influence alternate string-crossing escape compatibility and one-way sweep direction (USX downstroke sweep, DSX upstroke sweep) while keeping the opposite sweep direction as a soft fallback. On `fab918b`, `./tt check` passed including Picking diagnostics, the saved GUI profile was reported as `usx`, USX/DSX produced discriminating complete solutions, Ramp persistent strokes stayed stable, and the diagnostic ended with `SELF-TEST PASS`.
13. `./tt picking-log` is the canonical advanced-Picking evidence path: it records Git HEAD, saved Picking preferences, escape-profile and inside/outside probes, sweep-link metadata, Ramp output, and PASS/FAIL self-tests in an ignored text log.
14. **P7c ACCEPTED on `da166fe`:** Economy has Auto / Inside / Outside alternate-crossing preference. The diagnostic verified `AUTO D U`, `INSIDE D U`, and `OUTSIDE U D` with the expected inside/outside geometry. User-confirmed GUI smoke PASS.
15. **P7d ACCEPTED on `da166fe`:** sweep-link diagnostics detected exactly two valid connections (0.0→0.1 DOWN and 0.2→0.3 UP). User-confirmed GUI/audio smoke PASS.
16. **P7e deferred:** rhythmic/ghost-stroke Alternate remains future work; Strict Alternate continues to mean attack-alternate.

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
