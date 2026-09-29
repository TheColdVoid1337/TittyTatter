# TittyTatter documentation

This directory contains the living technical and product documentation for TittyTatter.

The root `README.md` stays concise and user-facing. Detailed project knowledge belongs here.

## Canonical documents

- [PROJECT_STATE.md](PROJECT_STATE.md) — current baseline, scope, limitations, and working rules.
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and timing model.
- [USER_GUIDE.md](USER_GUIDE.md) — intended user workflow and controls.
- [ROADMAP.md](ROADMAP.md) — near-term and later development direction.
- [DECISIONS.md](DECISIONS.md) — durable project decisions and rationale.
- [TEST_MATRIX.md](TEST_MATRIX.md) — automated and manual regression gates.
- [CHANGELOG.md](CHANGELOG.md) — version-by-version history.

## Documentation rule

Documentation is updated in place. New releases should extend the existing documents rather than recreate an unrelated documentation set.

The repository is the source of truth. When implementation and documentation disagree, the mismatch must be resolved explicitly rather than silently documented around.
