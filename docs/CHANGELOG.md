# Changelog

All notable TittyTatter changes are recorded here.

Numeric headings are added only when a release version is chosen. Development that has not yet been tagged remains under **Unreleased**.

## Unreleased

### Added

- WSL-first `tt` helper for the native Windows runtime.
- Flexible meters with numerator 1–16 and denominator 2/4/8/16.
- Meter-aware rhythm grids and horizontal beat-editor scrolling.
- Per-beat Mute.
- Timed practice with countdown and completion signal.
- Configurable visual metronome with independent needle/flash colors and full-panel flash.
- Audio-device/system settings including output device, sample rate, block size, latency mode, and WASAPI exclusive option.
- Expanded shared TI/TA sound selection while preserving distinct TI/TA assignments.
- Keyboard rhythm-game mode with assignable keys, difficulty windows, DAC-time targets, early/late feedback, hit/miss graph, and last-game summary.
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
