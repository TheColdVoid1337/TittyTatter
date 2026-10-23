# Changelog

All notable TittyTatter changes are recorded here.

Numeric headings are added when a release version is chosen. Future development remains under **Unreleased** until its release checkpoint.


## Unreleased (work branch; local validation pending)

### Added
- First candidates for seven additional Training Modes: Subdivision Ladder, Burst Trainer, Accent Trainer, Blind Pattern, Endurance Intervals, Tempo Wave and Random Tempo Blocks.
- Mode-specific Russian controls, practical in-app diagrams, callback-driven phase scheduling and shared Training/Game target handling.
- Stable seeded tempo-block generation, ladder effective-pattern projection, independent tempo-stage BPM, and new session/settings fields with legacy defaults.
- `test_training_modes.py` wired into the canonical `./tt check` gate.
- Burst Trainer on `work` now has two variants: **A–B–A–B** (unchanged whole-bar block schedule) and **Custom** (individual beat cards expose a «Рывок» checkbox). Custom repeats its meter-length selection mask every bar and uses the existing «Рывок, BPM» for marked beats; base BPM comes from the transport and can be higher or lower than the alternate tempo.
- Custom Burst changes BPM on callback-controlled metric-beat boundaries without changing subdivisions or shared Game targets. Beat mask/variant persist in new and legacy-compatible sessions and settings. A separate `./tt burst-smoke` checks Qt controls and persistence.

### Compatibility / pending
- Published v0.0.5 remains untouched; this work has not yet passed native Windows `./tt check` or `./tt run`.
- MIDI/GP5/WAV exports still represent the stored Pattern at base BPM; they do not export stage progressions.
- Public READMEs and end-user guide are not yet promoted to claim this unaccepted feature set.

## 0.0.5 — 2026-10-14

TittyTatter 0.0.5 delivers Picking Logic v2, new advanced Picking Guide settings, text diagnostics, and bilingual public READMEs. See [full release notes](RELEASE_NOTES_0.0.5.md).


### Added

- Picking Logic v2 normalized event model with explicit real-pattern vs Ramp-placeholder identity, covered slots, exact rhythmic phase, persistent real-attack ids, and explicit reset boundaries.
- Deterministic attack-alternate engine where OFF/COVERED slots do not consume stroke parity.
- Practical directional Economy optimizer with start-polarity search, cyclic loop scoring, directional-sweep classification, attack parity, machine-readable reasons, and linked sweep groups.
- Whole-beat motif constraints inside the optimizer so repeated motor patterns remain stable without post-hoc rewriting.
- Joint Ramp optimization: real attacks keep one stroke identity across stages while inactive-beat TA placeholders remain stage-local bridge attacks.
- Strict Alternate first-stroke control: Auto / Down / Up.
- Explicit Economy escape profiles: Auto / USX / DSX / DBX, without inferring player biomechanics.
- Explicit Economy alternate-crossing preference: Auto / Inside / Outside.
- Optional sweep-link visualization driven only by solved directional sweeps.
- `./tt picking-log` diagnostic report with Git HEAD, persisted Picking settings, profile-discriminating patterns, crossing probes, sweep-link probes, Ramp output, and PASS/FAIL self-tests. Logs are written as `logs/picking_v2_*.txt`.

### Changed

- The live Picking Guide now uses Picking Logic v2 only; the previous transitional picking implementation is no longer part of runtime behavior.
- Economy treats OFF slots as continuity rather than implicit phrase resets unless an explicit reset boundary is supplied.
- Ramp stages are solved as one constrained exercise, preserving already-learned real strokes as later beats open.
- Economy prioritizes stable repeated motor motifs over tiny local boundary savings.
- USX/DSX influence both alternate-crossing escape compatibility and one-way economy sweep direction; DBX accepts either escape direction and keeps sweep direction neutral.
- Advanced Picking controls are strategy-specific: first-stroke control is Strict Alternate-only; escape/crossing/sweep controls are Economy-only.

### Fixed

- Repeated identical and periodic beat patterns no longer receive inconsistent Economy arrows from linear flattening or isolated re-optimization.
- Ramp-stage boundaries retain cyclic continuity and persistent real-attack strokes.
- Equal-cost placeholder bridges prefer a clean alternating temporary TA stream and move unavoidable odd-cycle repeats to the loop boundary.
- Corrected the first USX/DSX scoring model after diagnostics showed score differences without complete-solution differences.
- Removed superseded transitional Picking Guide functions and legacy heuristic tests after P6 acceptance.

### Validation

- Picking Logic v2 P1-P6 and cleanup passed their local automated/manual gates.
- P7a Strict Alternate first-stroke control passed `./tt check` and live GUI acceptance on `10ab611`.
- P7b escape profiles passed `./tt check` and `./tt picking-log` acceptance on `fab918b`.
- P7c/P7d passed the deterministic diagnostic gate on `da166fe` (2026-10-14): clean working tree, full `./tt check`, inside/outside sequence differences, and two valid sweep links. The user subsequently confirmed live GUI/audio smoke PASS. The final release commit must be checked locally again before tagging.

## 0.0.4 — 2026-10-04

### Added

- Seven first-class Training Modes driven by the same pattern/timeline: Повтор, Разгон с 1 доли, Разгон с 2 долей, Пропуски, Нарастающие пропуски, Редкий метроном, and Смещённый метроном.
- Top-level mutually exclusive **Тренировка / Игра** execution selector while keeping Training Mode as the source of truth.
- Training help panel that explains mode behavior, practical use, and the guitar skill being trained.
- Keyboard-layout-independent physical Game bindings where native scan information is available.
- Mouse-button Game bindings.
- Expanded Штрих / Picking Guide controls, including economy and strict-alternate strategies plus configurable upcoming-stroke cues.
- Configurable Game HIT/MISS feedback with separate TI/TA HIT selections and guitar-style TI E3 / muted E2 feedback.
- About tab with TittyTatter branding, version, author, and repository link.
- TittyTatter application icon.
- Focus mode with a large distraction-free practice display.
- Focus read-only rhythm strip reflecting the current effective training pattern.
- Focus-aware metronome geometry scaling and compact Game history graph.
- Dedicated transparent README logo asset for GitHub rendering.
- Canonical `docs/WORKFLOW.md` describing vFLOW development, reporting, validation, release, and handoff procedure.

### Changed

- Game is now presented explicitly as a secondary execution layer over the selected Training Mode instead of an independent training progression.
- Start/Space route through Game execution when the top-level selector is Игра.
- Training options are reorganized so Count-in, Tempo Trainer, and Timer remain modifiers rather than separate Training Modes.
- Tempo UI is intentionally compact: numeric BPM control, keyboard stepping, and TAP remain; the old slider and +/- button cluster are removed.
- Tempo Trainer and Timer subordinate controls remain visible but disabled when their parent option is off.
- Gap and Progressive Gap suppress rhythmic guidance while keeping the exercise timeline and Game targets running.
- Yellow current-position guidance disappears during silent Gap phases and returns with audible guidance.
- Picking suggestions now preserve cyclic repeated-beat periods and remain cyclic across Ramp stages.
- Normal beat-editor framing was simplified by removing the redundant outer bar group.
- Focus TI cells use compact rounded/pill styling while TA/rest cells retain rectangular styling.
- Focus beat lamps are separated from the needle pivot/base.
- Root README is now written as a universal end-user entry point rather than a description of one development machine/workflow.

### Fixed

- Repeated identical/periodic beats no longer receive inconsistent Picking Guide arrows from linear full-bar flattening.
- Ramp-stage Picking Guide boundaries no longer lose cyclic continuity.
- Alternate MISS synthesis no longer mixes incompatible layer lengths directly.
- `_volume_slider()` static helper decoration was restored after a GUI structural regression.
- About-tab instance method decoration was corrected after a startup regression.
- Corrupted application-icon data was repaired and runtime transparency/safe-area handling was added.
- Tab switching no longer redistributes window height unexpectedly.
- Focus scaling now affects actual metronome geometry rather than only widget size.
- Focus Game graph no longer expands into an oversized full-height panel.

## 0.0.3 — 2026-10-03

### Added

- One-mode rhythm-game scoring with Score and live current-game statistics.
- Optional HIT and MISS feedback sounds.
- Lane-only TI/TA target matching so an input can only consume a target of the same type.
- Short early-input buffering to bridge PortAudio callback target-publication delay.
- Narrower PERFECT/GREAT/GOOD grading while keeping a forgiving overall hit window.
- Economy-picking guidance for TI on string 5 and TA on string 6.
- Automatic pick-direction optimization with sweep/economy transitions and ramp-aware picking preview.
- Colored picking arrows: upstroke green, downstroke red.
- Stage-progress indicator for ramp practice.
- Audible/visual warning before every ramp-stage change, including full-stage reset back to the first stage.
- Factory-style completion horn for timed practice.
- Opt-in `-log` / `--log` game diagnostics with timestamped JSONL sessions compressed to `logs/*.tar.gz`.
- Regression test for game-log creation, archival, and raw-file cleanup.

### Changed

- Game difficulty selector and Low/Mid/High windows were removed while the single scoring model is tuned.
- Game matching no longer uses adaptive timing bias; diagnostics showed that bias drift could misalign repeated subdivisions.
- Successful game input is graded by timing quality rather than using a tiny acceptance window as the difficulty mechanism.
- Current-game statistics replace Last Game statistics while a game is running; the panel returns to Last Game when the game ends.
- Exercise status no longer shows the absolute bar number.
- Ramp status uses explicit level wording and progress instead of fraction-like stage labels that could be confused with time signatures.
- Ramp-inactive beats are shown as TA followed by silence and are treated as TA game targets.
- Mode-dependent controls are disabled/greyed until their parent option is enabled.
- Picking display is rendered as a fixed left-side metronome overlay with shared beat separators for both string rows.
- Timer completion playback uses a dedicated one-shot output stream for reliability.

## 0.0.2 — 2026-09-30

### Added

- WSL-first `tt` helper for the native Windows runtime.
- Flexible meters with numerator 1–16 and denominator 2/4/8/16.
- Meter-aware rhythm grids and horizontal beat-editor scrolling.
- Per-beat Mute.
- Timed practice with countdown and completion signal.
- Configurable visual metronome with independent needle/flash colors and full-panel flash.
- Audio-device/system settings including output device, sample rate, block size, latency mode, and WASAPI exclusive option.
- Expanded shared TI/TA sound selection while preserving distinct TI/TA assignments.
- Keyboard rhythm-game mode with assignable keys, DAC-time targets, early/late feedback, hit/miss graph, and last-game summary.
- Persistent ignored local settings file with guarded DELETE reset.
- MIDI export with configurable repeats.
- Guitar Pro 5 export with configurable repeats, guitar mapping, first-bar annotations, and dead-note TA.
- WAV export with configurable duration and PCM quality.
- Export regression tests.

### Changed

- Default BPM is 60.
- Default TI sound is Wood and default TA sound is Low tick; both layers are enabled.
- Realtime audio prefers WASAPI on Windows and uses low-latency callback scheduling.
- A/B constructor was removed in favor of direct per-beat editing and random full-bar generation.
- Pattern selection applies immediately without a separate Apply button.
- TI text is rendered as `(ТИ)` in the UI.
- Ramp-inactive and muted beats receive clearer visual dimming.
- GP5 text annotations use ASCII-compatible labels to avoid legacy encoding mojibake.
- Routine validation moved from GitHub Actions to local `tt` gates.

### Removed

- Automatic GitHub smoke workflow.
- Legacy A/B builder.
- Redundant per-beat TI/TA and pause helper buttons.
- Linux-venv behavior from `run.sh`.

## 0.0.1

Initial published project baseline.

### Added

- TittyTatter project identity.
- Canonical root `VERSION`.
- Repository documentation structure under `docs/`.
- Initial 4/4 TI/TA rhythm model.
- Initial per-beat sixteenth/triplet subdivision.
- Independent TI, TA, and metronome audio semantics.
- Callback-driven timing architecture.
- First working GUI prototype.
