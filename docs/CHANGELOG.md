# Changelog

All notable TittyTatter changes are recorded here.

Numeric headings are added when a release version is chosen. Future development remains under **Unreleased** until its release checkpoint.


## Unreleased

### Added

- Picking Logic v2 P7a first-stroke control is now scoped to Strict Alternate only. Economy always keeps automatic start-polarity optimization; the internal Economy start-direction parameter remains available only as a test/debug/future special-exercise hook.
- Picking Logic v2 P1 normalized event model with explicit real-pattern vs Ramp-placeholder sources, persistent real-attack identities across stages, explicit covered slots, exact rhythmic phase, and caller-controlled phrase-reset boundaries.
- Picking Logic v2 P2 deterministic attack-alternate engine on normalized events. OFF/COVERED slots do not consume parity, string changes do not interrupt alternation, Ramp placeholders count as attacks, and explicit phrase-reset markers do not restart the public Alternate strategy. Runtime UI cutover remains deferred until the v2 integration phase.
- Picking Logic v2 P3 event-based Economy transition engine with directional-sweep classification, wrong-direction crossing detection, full start-polarity search, attack parity, explicit reset handling, cyclic last-to-first scoring, linked sweep-group ids, and machine-readable decision reasons. Runtime UI cutover remains deferred.
- Picking Logic v2 P4 whole-beat motif constraints. Repeated A/A/A and A/B/A/B beat identities now share stroke variables during the Economy optimization itself, including cyclic end/start repetitions, so motif stability no longer depends on post-hoc rewriting and can coexist with valid sweeps. Subdivision-level motif detection remains future work.
- Picking Logic v2 P5 joint Ramp solver. All configured Ramp stages now contribute to one optimization: real attacks use shared persistent stroke variables across stages, whole-beat motif constraints remain active, every stage scores its cyclic boundary, and temporary inactive-beat TA placeholders remain stage-local and are optimized as their own bridge stream. Runtime UI cutover remains deferred to P6.
- Picking Logic v2 P6 runtime cutover: the Picking Guide now uses event-based Alternate v2 and Economy v2 in normal training, and Ramp Economy uses the joint P5 solver. The public two-strategy UI is unchanged; legacy transitional picking functions remain in the module only until manual acceptance confirms the v2 path.

### Fixed

- Removed the superseded transitional Picking Guide implementation and its legacy heuristic tests after Picking Logic v2 P6 runtime/manual acceptance; the live module now retains only the v2 event, Alternate, Economy, motif, and joint Ramp paths.
- Ramp v2 equal-cost placeholder bridges now prefer alternating cleanly from the last active same-string stroke, moving an unavoidable odd-cycle repeat to the loop boundary instead of placing it at the active-to-placeholder transition.
- Picking Guide now preserves the same whole-beat picking pattern for repeated active motifs separated by fully silent beats, including motifs that cross the bar boundary.
- Economy picking keeps consecutive identical beats as one stable motor pattern instead of flipping a later repetition for a small boundary-transition advantage; looping runs also stay consistent across the bar boundary.
- Ramp modes now keep one learned economy-picking scheme across stages without forcing the fully-open bar to define it: the latest incomplete stage anchors the pattern, preserving useful sweeps into temporary inactive TA pulses while earlier and later stages keep already-learned stroke directions stable.
- Repeated-beat stabilization now chooses the sweep-rich phrase-level Economy variant already found in context instead of re-optimizing the repeated beat as an isolated cycle, preventing common ramp patterns from degenerating into strict alternate picking.
- Generated TA pulses on still-inactive Ramp beats now preserve the first context-dependent transition and then alternate down/up across subsequent same-string pulses instead of restarting every pulse with a downstroke.

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
