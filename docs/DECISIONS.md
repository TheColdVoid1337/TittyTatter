# Decisions

This file records durable project decisions. It is not a changelog.

## D-001 — Name and first version

**Decision:** the project is named **TittyTatter** and the first baseline is **0.0.1**.

**Reason:** this establishes a clean project identity before iterative feedback begins.

## D-002 — Documentation layout

**Decision:** keep a concise root `README.md`; place detailed living documentation in `docs/`.

**Reason:** the repository root stays readable while project context remains explicit and maintainable.

## D-003 — Version source

**Decision:** root `VERSION` is the canonical version source.

**Reason:** application code, packaging, and documentation can read one simple value instead of duplicating version constants.

## D-004 — Rhythm vocabulary

**Decision:** each subdivision is `TI`, `TA`, or `OFF`.

**Reason:** the model describes rhythm intent independently from the chosen sound.

## D-005 — Per-beat subdivision

**Decision:** subdivision is selected independently for every beat.

**Reason:** mixed sixteenth/triplet bars are a core use case and must not require separate special modes.

## D-006 — TI/TA audio independence

**Decision:** TI and TA have independent enable/sound/volume controls; the metronome is a separate layer.

**Reason:** a key practice mode is audible TI with silent TA while retaining meter.

## D-007 — Timing source

**Decision:** playback timing must be driven by the audio scheduling layer, not by GUI timers.

**Reason:** GUI scheduling jitter should not become musical timing jitter.

## D-008 — Development style

**Decision:** keep the early codebase and roadmap small; prioritize hands-on feedback.

**Reason:** the product is already useful enough to test, and premature architecture/features would slow learning.
