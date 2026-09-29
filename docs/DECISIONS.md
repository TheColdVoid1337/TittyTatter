# Decisions

This file records durable project decisions. It is not a changelog.

## D-001 — Name and first version

**Decision:** the project is named **TittyTatter** and the first published baseline is **0.0.1**.

## D-002 — Documentation layout

**Decision:** keep a concise root `README.md` and detailed living documentation under `docs/`.

## D-003 — Version source and release timing

**Decision:** root `VERSION` is the canonical published version source. Numeric version changes happen only at release/tag checkpoints.

**Reason:** development work should not repeatedly rewrite version numbers before a release identity is chosen.

## D-004 — Rhythm vocabulary

**Decision:** each subdivision is `TI`, `TA`, or `OFF`. UI text renders TI as `(ТИ)` for visual distinction.

## D-005 — Meter-aware per-beat grids

**Decision:** the meter is variable and each metric beat independently selects its grid.

**Reason:** mixed rhythmic cells and non-4/4 practice are first-class use cases.

## D-006 — TI/TA audio independence

**Decision:** TI and TA have independent enable/sound/volume controls; metronome is a separate layer. TI and TA may not select the same sound simultaneously.

Current defaults are Wood for TI and Low tick for TA, with both enabled.

## D-007 — Audio callback is the timing source

**Decision:** playback scheduling is driven by the PortAudio callback/sample clock, not Qt timers.

## D-008 — Windows/WSL development model

**Decision:** WSL is the command/control environment and the app runs through the native Windows `.venv/Scripts/python.exe`.

`tt` is the canonical helper. A Linux virtual environment is not part of the supported workflow.

## D-009 — Local validation is canonical

**Decision:** normal tests and release gates run locally. GitHub Actions are not the default validation mechanism.

**Reason:** realtime GUI/audio work requires the actual local Windows environment, and GitHub CI added latency without validating the most important behavior.

## D-010 — WASAPI preference

**Decision:** on Windows, the audio engine prefers a WASAPI output endpoint when available and exposes device/sample-rate/block/latency controls.

## D-011 — Game scoring timestamp

**Decision:** rhythm-game targets use PortAudio output/DAC timestamps. GUI timer timestamps are not the scoring authority.

**Limitation:** keyboard/device input latency is not yet calibrated end-to-end.

## D-012 — Local settings file

**Decision:** application preferences are stored in ignored `tittytatter.settings.json`.

Resetting settings requires explicit `DELETE` confirmation.

## D-013 — GP5 compatibility text

**Decision:** Guitar Pro 5 annotations use conservative ASCII text.

**Reason:** legacy GP5 text encodings produced mojibake with Cyrillic annotations. Musical note semantics remain in the tablature itself.

## D-014 — Development commits

**Decision:** batch ordinary changes into meaningful functional/architectural commits. Microcommits are reserved for genuinely important isolated fixes or process changes.
