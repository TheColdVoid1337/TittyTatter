# vFLOW project workflow

This document defines the canonical development, validation, reporting, and release workflow for TittyTatter.

It is intentionally operational. A future maintainer or AI-assisted development session should be able to continue the project from this document without inventing a new process.

## 1. Core principles

TittyTatter development follows **vFLOW**.

The rules are:

1. **GitHub is the source/history.**
2. **The local Windows runtime is the canonical validation environment.**
3. **The `work` branch is the normal active-development branch.**
4. **`main` is the integration/published-release branch.**
5. Prefer **small, meaningful, semantic commits**.
6. Do not claim that a local runtime check succeeded until the user provides the local result.
7. Diagnose failures from evidence before changing code.
8. Do not introduce GitHub Actions or remote CI by default.
9. Do not redesign stable architecture or UI without a concrete reason.
10. Do not change the numeric application version during ordinary development.
11. Do not delete branches or uncertain files silently.
12. Technical documentation, commit messages, identifiers, and release notes are written in English. The application GUI is primarily Russian.
13. Conversation with the project owner is in Russian.
14. Do not suggest or introduce Codex unless explicitly requested.

## 2. Product hierarchy that development must preserve

The project is first and foremost a **guitar rhythm training tool**.

The conceptual hierarchy is:

```text
PATTERN
  what is played

TRAINING MODE
  how the pattern is trained over time

TRAINING
  execute that training on guitar

GAME
  execute the same training timeline through computer input and score timing

PICKING GUIDE / ШТРИХ
  optional informational aid for guitar practice
```

The selected Training Mode is the source of truth for both normal Training and Game.

Game must not grow a parallel progression/timeline system.

Picking Guide is not a third top-level training mode.

## 3. Branch model

### `work`

Normal development branch.

Use it for:

- feature work;
- targeted fixes;
- UI refinements;
- documentation updates before a release;
- release preparation before final integration.

Do not delete `work` by default.

### `main`

Integration and release branch.

Normal development should not be performed directly on `main` unless there is a deliberate reason.

At release time, prefer a **fast-forward** from `main` to the accepted `work` commit when the history allows it. Do not create an unnecessary merge commit.

### Old release/development branches

Old branches may be deleted only after verifying that they contain no unique commits that need preservation.

The safe check is a commit comparison against the final release `main`.

If the old branch is fully contained in `main`, it is a cleanup candidate. If it has unique commits, stop and inspect those commits before deletion.

## 4. GitHub write authorization

GitHub writes are not assumed silently.

Project convention:

- `#writegh` explicitly authorizes direct GitHub writes;
- once granted, that authorization remains active until the user explicitly revokes it;
- while write access is active, use the GitHub connector directly for requested project changes;
- do not substitute a speculative patch description when a direct repository edit was requested and authorized.

A write operation should still be narrow, reviewable, and semantically committed.

## 5. Commit policy

Prefer **frequent semantic commits**.

Good commit boundaries:

- one independently useful UI fix;
- one logic fix;
- one documentation concern;
- one release asset;
- one critical regression correction.

Examples:

```text
Refine focus rhythm strip and beat lamps
Add transparent README logo asset
Rewrite README for end users
Document vFLOW development workflow
Fix About tab instance method
```

A one-line regression fix may be a microcommit when it restores broken behavior.

Do not accumulate unrelated changes merely to reduce commit count. Session interruption must not be able to discard a large amount of completed work.

## 6. Required report after every GitHub edit

After each repository write, report:

1. **Commit SHA and exact commit message.**
2. **What changed**, in a short concrete summary.
3. **Exact local sync/validation commands** relevant to that change.
4. **Validation status**, clearly distinguishing repository changes from local runtime confirmation.

Canonical wording should follow this structure:

```text
Committed:
<short-sha> <commit message>

Changed:
- ...
- ...

Pull/test:
git switch work
git pull --ff-only origin work
git log -1 --oneline
./tt check
./tt run

Local validation:
Pending. Do not treat the change as locally confirmed until the user pastes the result or explicitly accepts the manual check.
```

For documentation-only changes, `./tt run` may be unnecessary, but the report must say why rather than pretending it was run.

## 7. Bug-fix workflow

When a bug is reported:

### Step 1 — collect evidence

Use the most concrete available evidence:

- traceback;
- terminal output;
- screenshot;
- exact reproduction steps;
- current commit SHA;
- relevant log archive when timing diagnostics are involved.

Screenshots are first-class evidence for UI geometry/layout bugs.

### Step 2 — inspect current code

Read the exact current implementation on the active branch.

Do not patch from memory if the repository may have changed.

### Step 3 — diagnose

State the concrete failure mechanism before editing.

Avoid speculative broad refactors when a small targeted fix is sufficient.

### Step 4 — patch

Make the narrowest change that resolves the diagnosed failure while preserving established behavior.

### Step 5 — commit immediately

Use a semantic commit once the individual fix is coherent.

### Step 6 — request exact validation

Provide the exact pull/test commands and the specific manual behavior that needs checking.

### Step 7 — wait for local evidence

Do not say "fixed and validated" merely because the repository edit succeeded.

Repository success and local runtime acceptance are different states.

## 8. Canonical local development commands

Run from the repository root.

Primary helper:

```bash
./tt
```

Canonical automated gate:

```bash
./tt check
```

Canonical GUI/manual launch:

```bash
./tt run
```

Optional Game diagnostics:

```bash
./tt run -log
```

or:

```bash
./tt run --log
```

Picking Logic mechanics diagnostics:

```bash
./tt picking-log
```

Use the generated `logs/picking_v2_*.txt` as first-class evidence for advanced Picking Logic behavior. It covers escape profiles, inside/outside preference, and sweep-link metadata; screenshots are not required when the question is about solver output rather than UI geometry.

The project uses a native Windows virtual environment. From WSL the direct interpreter is:

```text
./.venv/Scripts/python.exe
```

Do not instruct this project to use `.venv/bin/activate`; that is not the canonical environment.

## 9. Canonical automated gate

`./tt check` currently covers approximately:

1. `test_core.py`;
2. Python compile checks for application modules, including `picking_diagnostics.py`;
3. Picking Logic diagnostic self-test;
4. `test_exports.py`;
5. `test_game_logger.py`;
6. dependency imports.

A normal green result ends with:

```text
== core tests ==
core tests OK
== compile ==
== picking diagnostics ==
picking diagnostics OK
== export tests ==
export tests OK
== game log tests ==
game log tests OK
== imports ==
dependencies OK
== result ==
TittyTatter checks OK
```

A green `./tt check` is necessary but not sufficient for GUI/audio release acceptance.

## 10. GUI/runtime validation

Always manually open the application after meaningful runtime/UI changes:

```bash
./tt run
```

This matters because structural Qt errors may not be caught by the automated gate.

If the application exits silently, collect a real traceback instead of applying a blind patch:

```bash
./.venv/Scripts/python.exe -X faulthandler -u "$(wslpath -w "$PWD/app.py")"
echo "EXIT=$?"
```

Then diagnose that output.

## 11. Local working-tree checks

The GitHub connector cannot see local untracked files.

Before release integration, explicitly request:

```bash
git status --short
```

Unknown local files must not be deleted without confirmation.

Tracked repository cleanup and local working-tree cleanup are separate tasks.

## 12. Documentation rules

The root `README.md` is the **public user-facing entry point**.

It must:

- describe the application for someone who downloaded or cloned it;
- explain the product and current features;
- contain generic installation/run instructions;
- avoid machine-specific paths, personal development layout, or private local workflow details.

Detailed project documentation belongs in `docs/`.

Documentation is updated **in place**. Do not create a new parallel documentation set for every release.

Important technical/project documents include:

- `PROJECT_STATE.md`;
- `ARCHITECTURE.md`;
- `WORKFLOW.md`;
- `USER_GUIDE.md`;
- `ROADMAP.md`;
- `DECISIONS.md`;
- `TEST_MATRIX.md`;
- `CHANGELOG.md`.

## 13. Versioning rules

The root `VERSION` file is the canonical application release version.

Rules:

- ordinary development does **not** bump `VERSION`;
- choose/confirm the numeric version only at an explicit release checkpoint;
- session/settings schema versions are separate from the application release version;
- published release numbers are not reused;
- published tags are immutable.

Before changing `VERSION`, confirm the intended release version if it has not already been explicitly stated.

## 14. Release-preparation workflow

A release is a deliberate checkpoint.

### Phase A — accept `work`

Update and inspect:

```bash
git switch work
git pull --ff-only origin work
git log -1 --oneline
git status --short
```

Run:

```bash
./tt check
./tt run
```

The manual acceptance scope is maintained in `TEST_MATRIX.md`.

Do not begin branch deletion or tagging until the current code/UI is accepted.

### Phase B — repository cleanup

Inspect for:

- accidental tracked temporary files;
- obsolete generated outputs;
- stale release artifacts;
- dead migration leftovers;
- outdated documentation references;
- obsolete branches.

Do not remove:

- canonical tests;
- required runtime directories;
- files whose purpose is uncertain.

Do not add GitHub Actions as part of cleanup.

### Phase C — prepare release documentation/assets

Update the public README and living docs to match the code that actually exists.

For the README logo, use a real transparent image asset that renders correctly on GitHub. Do not rely on runtime Qt image processing.

### Phase D — choose release version

If not already stated, ask for the version.

Only then:

- update `VERSION`;
- convert the changelog's Unreleased section into the dated release section;
- update project-state release metadata;
- update any README release label;
- commit release metadata as a dedicated semantic commit.

### Phase E — integrate `work` into `main`

Immediately before integration, compare the branches again.

If `work` is a clean descendant of `main`, fast-forward `main` to the accepted release commit.

Do not create a merge commit when a clean fast-forward is available.

### Phase F — final local release gate

Pull the exact release commit locally and run the required final checks.

Do not tag until the final release commit is accepted.

### Phase G — annotated tag

Release tags are annotated:

```text
vX.Y.Z
```

with message:

```text
TittyTatter vX.Y.Z
```

If the available GitHub tooling cannot safely create an annotated tag, provide exact local commands instead of pretending the tag was created.

After pushing the tag, verify:

- `main` points to the release commit;
- the tag exists;
- the annotated tag peels to exactly that same release commit.

### Phase H — post-release branch state

If `work` is retained, synchronize it to the final release commit so the next development cycle starts cleanly.

Only after release verification:

- compare obsolete branches with final `main`;
- delete branches that have no unique commits;
- preserve any branch that contains unique history until reviewed.

## 15. Release report format

At the end of a release, report:

```text
Release:
TittyTatter X.Y.Z

Release commit:
<sha> <message>

Main:
<sha>

Tag:
vX.Y.Z
annotated tag -> <sha>

Work:
<sha> (synchronized / intentionally different)

Removed branches:
- ...

Preserved branches:
- ...

Validation:
- ./tt check: user-confirmed green
- manual GUI/audio acceptance: user-confirmed
- tag peel verification: confirmed

Remaining follow-up:
- ...
```

Do not mark a validation line as confirmed unless there is actual evidence for it.

## 16. Change-report format during normal development

Use a compact status block:

```text
HEAD:
<short-sha> <message>

Repository state:
- branch: work
- GitHub write: completed
- local validation: pending/confirmed

Change:
- ...

Validate:
<commands>

Manual check:
- ...
```

This format keeps Git state, code state, and validation state separate.

## 17. Failure-report format

When validation fails, report:

```text
Failure:
<exact command or action>

Observed:
<exact error/traceback/screenshot fact>

Diagnosis:
<concrete mechanism supported by evidence>

Next patch:
<smallest targeted correction>
```

Do not skip directly from "Observed" to an unrelated refactor.

## 18. Release-safety rules

Never:

- claim local Windows validation succeeded without user evidence;
- silently bump the version;
- silently delete branches;
- force-update `main` for an ordinary release;
- rewrite a published tag;
- casually change stable TI/TA sound synthesis during unrelated work;
- reintroduce opposite-lane Game matching;
- reintroduce adaptive Game timing bias without a deliberate new design;
- make Game a separate independent training progression system;
- treat Picking Guide as a third top-level mode;
- stop the exercise timeline during silent-gap phases.

## 19. Handoff checklist for a new development session

A useful handoff should state at minimum:

- repository;
- active branch and exact HEAD;
- current published version/tag;
- branch relationship (`main...work`);
- whether GitHub writes are authorized;
- latest locally validated commit;
- latest unvalidated commit, if any;
- immediate next task;
- known regressions or manual checks still required;
- exact validation commands;
- release status;
- durable design constraints that the next session must not accidentally reverse.

The repository remains canonical. A handoff summary accelerates continuation but never overrides current source code or current Git history.
