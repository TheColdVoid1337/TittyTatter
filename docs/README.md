# TittyTatter documentation

This directory contains the living technical and product documentation for TittyTatter.

The root `README.md` is the public project entry point. Detailed project knowledge belongs here.

## Canonical documents

- [PROJECT_STATE.md](PROJECT_STATE.md) — current implementation state, release-preparation status, limitations, and workflow.
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries, rhythm model, realtime timing, game timing, export, and settings.
- [USER_GUIDE.md](USER_GUIDE.md) — current application workflow and controls.
- [ROADMAP.md](ROADMAP.md) — next reliability/calibration work and later direction.
- [DECISIONS.md](DECISIONS.md) — durable project decisions and rationale.
- [TEST_MATRIX.md](TEST_MATRIX.md) — canonical local gate plus manual GUI/audio/game/export acceptance.
- [CHANGELOG.md](CHANGELOG.md) — published history and current Unreleased changes.

## Documentation rule

Documentation is updated in place. New releases extend the existing documents rather than creating parallel documentation sets.

The repository is the source of truth. When implementation and documentation disagree, resolve the mismatch explicitly.

Numeric release versions are not guessed during development. Unreleased work remains marked **Unreleased** until the release/tag checkpoint chooses the version.
