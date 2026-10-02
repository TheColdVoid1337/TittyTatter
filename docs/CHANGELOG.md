# Changelog

All notable TittyTatter changes are recorded here.

Numeric headings are added when a release version is chosen. Future development remains under **Unreleased** until its release checkpoint.

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
