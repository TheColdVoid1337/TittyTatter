# TittyTatter documentation

This directory contains the living technical and product documentation for TittyTatter.

The root [README.md](../README.md) is the primary **Russian-language** product overview. [README.en.md](../README.en.md) is its English-language counterpart. Both target GitHub visitors and application users; detailed engineering, validation, and release knowledge belongs here.

## Canonical documents

- [PROJECT_STATE.md](PROJECT_STATE.md) — current implementation, release baseline, and active development state.
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries, rhythm/training model, realtime timing, Game timing, Picking Guide, Focus view, export, and settings.
- [PICKING_LOGIC_V2.md](PICKING_LOGIC_V2.md) — canonical design and implementation reference for the live Picking Logic v2 engine: event/state model, Alternate/Economy semantics, escape/crossing preferences, Ramp constraints, sweep links, diagnostics, and regression matrix.
- [WORKFLOW.md](WORKFLOW.md) — canonical vFLOW development, GitHub write, validation, reporting, release, and handoff procedure.
- [USER_GUIDE.md](USER_GUIDE.md) — current application workflow and controls.
- [ROADMAP.md](ROADMAP.md) — post-release guitar-training direction and later work.
- [TRAINING_MODE_DESIGNS.md](TRAINING_MODE_DESIGNS.md) — illustrated seven-mode work candidate, actual draft semantics, practice guidance and local acceptance gate.
- [DECISIONS.md](DECISIONS.md) — durable project decisions and rationale.
- [TEST_MATRIX.md](TEST_MATRIX.md) — canonical automated gate plus manual GUI/audio/Game/export acceptance.
- [CHANGELOG.md](CHANGELOG.md) — published release history and noteworthy changes.
- [RELEASE_NOTES_0.0.5.md](RELEASE_NOTES_0.0.5.md) — full v0.0.5 release notes and source for the annotated tag message.
- [dev/HANDOFF_TITTYTATTER_2026-10-14_v0.0.5.md](dev/HANDOFF_TITTYTATTER_2026-10-14_v0.0.5.md) — post-release engineering chat handoff: machine paths, GitHub/WSL workflow, validation, accepted Picking v2 and next feature.

## Documentation rules

Documentation is updated in place. New releases extend the existing documents rather than creating parallel documentation sets.

The repository is the source of truth. When implementation and documentation disagree, inspect the current code/history and resolve the mismatch explicitly.

Both public READMEs must remain suitable for someone who downloads or clones the application. The default `README.md` is Russian to match the application interface; `README.en.md` provides equivalent English product documentation. Keep the language links reciprocal and both documents consistent with actual shipped functionality. Exclude personal details, project-owner-specific conventions, machine paths, internal planning terminology, and private development layout.

Numeric release versions are not guessed during ordinary development. Unreleased work remains marked **Unreleased** until the release checkpoint chooses the version. Annotated release tags carry a full release summary rather than a one-line version label.
