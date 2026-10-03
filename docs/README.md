# TittyTatter documentation

This directory contains the living technical and product documentation for TittyTatter.

The root `README.md` is the public user-facing project entry point. Detailed implementation, development, validation, and release knowledge belongs here.

## Canonical documents

- [PROJECT_STATE.md](PROJECT_STATE.md) — current implementation and release-preparation state.
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries, rhythm/training model, realtime timing, Game timing, Picking Guide, Focus view, export, and settings.
- [WORKFLOW.md](WORKFLOW.md) — canonical vFLOW development, GitHub write, validation, reporting, release, and handoff procedure.
- [USER_GUIDE.md](USER_GUIDE.md) — current application workflow and controls.
- [ROADMAP.md](ROADMAP.md) — post-release guitar-training direction and later work.
- [DECISIONS.md](DECISIONS.md) — durable project decisions and rationale.
- [TEST_MATRIX.md](TEST_MATRIX.md) — canonical automated gate plus manual GUI/audio/Game/export acceptance.
- [CHANGELOG.md](CHANGELOG.md) — published history and current Unreleased changes.

## Documentation rules

Documentation is updated in place. New releases extend the existing documents rather than creating parallel documentation sets.

The repository is the source of truth. When implementation and documentation disagree, inspect the current code/history and resolve the mismatch explicitly.

The public root README must remain suitable for a user who downloads or clones the project. Personal machine paths and private development layout do not belong there.

Numeric release versions are not guessed during ordinary development. Unreleased work remains marked **Unreleased** until the release checkpoint chooses the version.
