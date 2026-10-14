# TittyTatter — MAIN engineering chat handoff

**Snapshot:** 2026-10-14, directly after public release v0.0.5  
**Purpose:** Transfer the current engineering/orchestration chat into a fresh ChatGPT conversation with the least possible loss of continuity.  
**Audience:** Successor assistant collaborating with the repository owner. **This is an internal engineering document, not public product marketing.**

> The live GitHub repository is the source of truth. This handoff records the accepted baseline, workflow conventions, validation evidence, and next design topic. Always read the current `work` branch and verify HEAD/refs; do not treat this snapshot as proof that no newer change has happened.

## 1. Mandatory behavior in the new conversation

You are continuing a substantial Russian-language TittyTatter engineering conversation; don't restart from zero.

- **Speak Russian to the user.** Be technically precise, reasonably concise, practical and direct.
- **Write code, commits, technical docs, issue/release notes and any final prompt for other AI tools in English.** The GUI is Russian. Default public product `README.md` is Russian; `README.en.md` is a synchronized English version.
- **Direct GitHub writes are already authorized until the user explicitly revokes authorization.** Use the connected GitHub integration for actual requested edits on `work`. Do not make the user paste patch contents manually if an appropriate repo action exists.
- Reading this file is **not** permission to start an unrequested feature. Wait for the user's concrete next request; design/discuss before implementing ambiguous work.
- **Do not use or suggest Codex, GitHub Actions, or remote CI by default.** Do not duplicate local tests remotely or start speculative CI infrastructure.
- GitHub commits are not evidence that the user-tested native Windows build works. Report actual local acceptance separately.
- **Never silently bump `VERSION`, move `main`, force-update released branches, alter an existing tag, or delete a branch/file with uncertain contents.**
- Preserve the current training product model, live audio timing, stable timbres, input matching, Focus behavior, real Picking constraints and export compatibility.
- Inspect actual files before patching. Diagnose bugs from evidence; write deterministic regression checks and commit narrowly.
- After every GitHub write report the **exact new commit SHA and message**, what changed, copy/pasteable WSL sync/check commands, and whether local validation is pending.
- Do not repeatedly ask for already established repository, machine, workflow or product details. They are in this handoff and canonical repository documentation.
- Screenshots are useful for GUI geometry. For picking algorithms, prefer `./tt picking-log` over screenshot-by-screenshot arrow comparisons.

If user requests planning or reasoning about a new feature, discuss realistic options and acceptance criteria before committing a design without agreement.

## 2. Repo, published release, branch policy

- GitHub repository: https://github.com/TheColdVoid1337/TittyTatter
- Clone: https://github.com/TheColdVoid1337/TittyTatter.git
- Active engineering/dev branch: `work`
- Published/integration branch: `main`
- Published version / root `VERSION` at release: **0.0.5**
- Released annotated tag: **v0.0.5**
- Immutable release commit: **21c33aa2680c8c25fafccde90bf292cb1390440a**, message `Release TittyTatter 0.0.5`.
- Tag object SHA: `149036228bad052f47b911cdc6d18d2aa69f318b`. Tag **peels to** release commit `21c33aa...`.
- Published GitHub Release: https://github.com/TheColdVoid1337/TittyTatter/releases/tag/v0.0.5
- Older tags `v0.0.1` through `v0.0.4` remain immutable.
- At release close: both `main` and `work` pointed to `21c33aa`, and branches were identical. Only `main` and `work` remained.
- **After this handoff file is committed, `work` advances with a documentation-only handoff commit; `main` and `v0.0.5` stay frozen at `21c33aa`.** The successor MUST query the new actual `work` HEAD; don't assume that handoff HEAD equals the published release SHA.
- GitHub writes are authorized by established `#writegh` project convention until explicitly revoked. Successful push/commit still requires user-local checks for changed runtime.
- Repo About description verified after user CLI update:
  `Guitar rhythm trainer for Windows with custom patterns, seven practice modes, advanced picking guidance, timing practice, and MIDI/GP5/WAV export.`
- Repo topics reached **20/20**, with added `guitar-practice`, `rhythm-trainer`, `economy-picking`, `alternate-picking`, `pyside6`; previous topics were preserved. GitHub's maximum is 20. Redundant old topics exist; tidying is optional, not a release blocker.
- No pending 0.0.5 tag/publishing action remains. This release is CLOSED.

**Repository operations:** Prefer the live connected GitHub integration, not cached summaries. Verify ref + current file content before writes; make semantic, reviewable commits; don't modify `main` while starting next feature. On a completed release prefer fast-forward `main` from a locally accepted `work` commit, never force.

## 3. Native Windows runtime from WSL — exact paths

The user operates a native Windows GUI/audio process launched by the WSL helper. WSL repository root:

~~~bash
cd /mnt/f/_PROJECT/TittyTatter
~~~

Windows equivalent: `F:\_PROJECT\TittyTatter`.

**Canonical interpreter:** `.venv/Scripts/python.exe` inside the project (Windows Python, NOT a Linux `.venv/bin` interpreter). The root executable WSL launcher `./tt` converts paths using `wslpath -w`. Never suggest `source .venv/bin/activate`.

Always give terminal instructions in a separate ready-to-paste fenced `bash` block. Typical sync/start block:

~~~bash
cd /mnt/f/_PROJECT/TittyTatter
git switch work
git pull --ff-only origin work
git log -4 --oneline
git status --short
~~~

Canonical automated regression gate:

~~~bash
./tt check
~~~

Native GUI / audio smoke:

~~~bash
./tt run
~~~

Picking mechanical diagnostic:

~~~bash
./tt picking-log
~~~

Optional game event log and environment diagnostics:

~~~bash
./tt run -log
./tt doctor
./tt audio-info
~~~

When app exits silently, ask for the real Windows traceback:

~~~bash
./.venv/Scripts/python.exe -X faulthandler -u "$(wslpath -w "$PWD/app.py")"
echo "EXIT=$?"
~~~

The helper also supports `install`, `install-dev`, `test`, `pip`, `python`, `build`, `update`, `status`, `help`. Read actual `tt` before assuming other flags. End-user Windows direct launch is `run.bat`.

Settings: `tittytatter.settings.json` in repo root, ignored by Git. Generated logs: `logs/`, ignored; picking output `logs/picking_v2_YYYYMMDD_HHMMSS.txt`. Local environment `.venv/` ignored. No need to transfer these machine-specific files between ChatGPT conversations.

For documentation-only GitHub commits, sync may suffice; don't demand a full GUI smoke without a code-related reason. For logic/test changes request `./tt check`. For UI/audio changes additionally request `./tt run` and focused manual behavior confirmation. The user's pasted command outputs are acceptance evidence; an assistant with GitHub access does not run the user's local Windows process.

**Known correct green ending:**

~~~text
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
~~~

## 4. Standard response formats to preserve

**GitHub change report:**

~~~text
Committed:
<short SHA> <exact commit message>

Changed:
- <specific change>
- <specific change>

Pull/test:
cd /mnt/f/_PROJECT/TittyTatter
git switch work
git pull --ff-only origin work
git log -1 --oneline
./tt check
./tt run

Local validation:
Pending — GitHub update succeeded; local Windows checks are not
confirmed until the user shares actual output or accepts GUI behavior.
~~~

Do not mechanically include `./tt run` for docs-only changes. Include only relevant checks and say why.

**Compact engineering status:**

~~~text
HEAD:
<short SHA> <commit message>

Repository state:
- branch: work
- GitHub write: completed
- local validation: pending / confirmed

Change:
- ...

Validate:
<exact commands>

Manual check:
- <focused behavior to verify>
~~~

**Failure analysis:**

~~~text
Failure:
<exact command/action>

Observed:
<verbatim relevant output / reproduction>

Diagnosis:
<concrete supported mechanism>

Next patch:
<smallest targeted and test-backed correction>
~~~

**Release report:**

~~~text
Release:
TittyTatter X.Y.Z

Release commit:
<full SHA> <message>

Main:
<full SHA>

Tag:
vX.Y.Z, annotated -> <exact release SHA>

Work:
<full SHA; synced or intentionally advanced>

Validation:
- ./tt check: user-confirmed PASS
- GUI/audio acceptance: user-confirmed
- full tag annotation/peel: verified

Remaining follow-up:
- ...
~~~

Keep responses in conversational Russian, not endless multi-block status narration. Give durable findings early; explicitly distinguish confirmed from proposed. When asking for evidence prefer one complete WSL block and one concise list of GUI actions. No screenshots for solver output when a log suffices.

## 5. Product contract, stable UI and engineering invariants

TittyTatter is **a guitar rhythm training application**, not mainly a rhythm video game, DAW or notation editor.

~~~text
PATTERN       = WHAT is played/practiced.
TRAINING MODE = HOW that pattern is practiced over time.
ТРЕНИРОВКА    = perform the exercise on guitar.
ИГРА          = optional keyboard/mouse input and timing grades
                against that SAME training timeline.
ШТРИХ         = optional Picking Guide; not a third training mode.
ФОКУС         = larger read-only presentation; not new exercise logic.
~~~

- Rhythm editor: meters numerator 1–16, denominator 2/4/8/16, per-beat subdivisions and grids including triplets, pauses, long-note coverage and horizontal scrolling.
- States: `TI` = reference 5th string / E3; `TA` = muted 6th string / E2; `OFF` = silent. Guitar Pro export uses TI string 5 fret 7 and TA muted/dead string 6.
- **Seven first-class Training Modes**, Russian UI names: `Повтор`; `Разгон с 1 доли`; `Разгон с 2 долей`; `Пропуски`; `Нарастающие пропуски`; `Редкий метроном`; `Смещённый метроном`.
- Ramp 1..N or 2..N activation is meter-aware. Generated inactive-beat TA placeholders remain playable transient attacks. Training mode is the single source for both Training and Game.
- Gap/Progressive Gap: silence disables audio/visual guidance, **not time or Game targets**. Yellow current-position cue hides during silence and returns when audible guidance resumes.
- Sparse/Displaced Click: modify metronome guidance without changing original pattern subdivisions; displaced click can coexist with triplets by fine-grid/LCM timing.
- Count-in / Tempo Trainer / Timer are optional modifiers, not separate Training Modes.
- Realtime clock is **PortAudio callback** in `audio_engine.py`, not Qt timers; Windows WASAPI preferred. Stable TI/TA sound synthesis/defaults should not be casually changed (historical default TI Wood and TA Low tick).
- Game: keyboard physical scan-code normalization where possible, mouse inputs, TI/TA strict lane-only matching, no opposite-lane fallback, no adaptive timing bias. Accepted window 180 ms EARLY / 300 ms LATE; early buffer 180 ms. Grade thresholds PERFECT ≤30 ms, GREAT ≤70, GOOD ≤120, other accepted HIT.
- Focus physical F priority: keybinding capture wins; during active Game, F bound to Game input wins; otherwise F toggles Focus. Focus rhythm strip tracks **effective** pattern.
- Picking Guide and Game are mutually exclusive UI options.
- Sessions and application settings persist separately from semantic release `VERSION`.
- MIDI, Guitar Pro 5 and WAV export are implemented. Do not break existing samples or timing when introducing Training Modes.

## 6. Picking Logic v2 — FINISHED in v0.0.5

**P1–P6, P7a–P7d, and removal of the old transitional Picking engine are DONE. P7e is intentionally DEFERRED.** Do not reopen released Picking work without a concrete regression/feature request.

- **P1** normalized `PickingEvent` model: real vs temporary placeholder attacks, stable identities, OFF/covered slots, rhythmic phase and explicit reset boundaries.
- **P2** Strict Alternate: DOWN/UP alternates **on played attacks**; OFF/COVERED do not consume parity, string changes do not restart it; Ramp TA placeholders DO count as attacks.
- **P3** Economy: practical directional sweeps, stroke candidate optimization, loop closure, reset/transition classification, explainable decisions.
- **P4** repeated whole-beat motif equality is enforced **during** constrained optimization; A/A/A and A/B/A/B motor patterns must be stable.
- **P5** joint Ramp solver: persistent real attack strokes equal across expanding stages, cyclic stage boundaries, independently optimizable stage-local temporary TA placeholders.
- **P6** UI uses only v2 paths; transitional heuristic picking functions and corresponding old tests removed.
- **P7a** Strict Alternate-only first-stroke `Авто / Вниз / Вверх` control. Economy always optimizes its initial stroke automatically. UI hides first-stroke row for Economy.
- **P7b** explicit Economy mechanics profile `Auto / USX / DSX / DBX`. Not an inferred personal diagnosis. USX rewards alternate string crossings after UP and prefers DOWN sweeps; DSX after DOWN and prefers UP sweeps; DBX permits both escapes. Opposite sweep direction is a soft penalty, not impossible.
- **P7c** independent `Auto / Inside / Outside` preference for **alternating string crossings only**; it must not override sweeps, OFF behavior or same-string alternation.
- **P7d** optional `Показывать связи sweep`: presentation-only colored link between consecutive attacks of a valid directional sweep; toggling links cannot change solver arrows.
- **P7e** rhythmic/ghost-stroke Alternate remains deferred and must NOT be silently folded into public attack-alternate.

~~~text
6 DOWN -> 5 DOWN   valid DOWN sweep
5 UP   -> 6 UP     valid UP sweep

6 DOWN -> 5 UP     inside alternate crossing
5 UP   -> 6 DOWN   inside alternate crossing

6 UP   -> 5 DOWN   outside alternate crossing
5 DOWN -> 6 UP     outside alternate crossing

6 UP   -> 5 UP     wrong-direction same-stroke crossing
5 DOWN -> 6 DOWN   wrong-direction same-stroke crossing
~~~

Arrow colors: **↑ UP green**; **↓ DOWN red**.

**Acceptance evidence:**
- Last pre-release code candidate `da166fe`: user confirmed clean `git status --short`, complete `./tt check` PASS, and `./tt picking-log` ending `SELF-TEST PASS` (2026-10-14); subsequently explicitly confirmed native GUI/audio and P7c/P7d worked correctly.
- P7c diagnostic: `AUTO D U` = inside; `INSIDE D U` = inside; `OUTSIDE U D` = outside.
- P7d diagnostic: `link_count=2`; references `0.0 -> 0.1 DOWN` and `0.2 -> 0.3 UP` on the `TA TI TI TA` / `D D U U` fixture.
- USX/DSX output differs on cyclic reference corpus; Ramp real attacks remain stable.
- P7a local GUI acceptance on `10ab611`. P7b full gate/log acceptance on `fab918b`.
- Exact release commit `21c33aa` passed complete local `./tt check` with clean working tree. Full annotated tag and published GitHub Release verified separately.

See `picking_logic.py`, `picking_diagnostics.py`, `test_core.py` and `docs/PICKING_LOGIC_V2.md` for precise algorithms and constraints. Prefer `./tt picking-log` for future algorithm regression reports; logs appear in Git-ignored `logs/` and need not be transferred.

## 7. Source map and canonical docs

**Code and entry points:**  
`app.py` — PySide6 application and UI;  
`model.py` / `presets.py` — patterns and grids;  
`training_modes.py` — exercise mode/temporal helpers;  
`audio_engine.py` — callback clock/sound/output devices;  
`game_logic.py` / `input_binding.py` — Game scoring/input;  
`picking_logic.py` / `picking_diagnostics.py` — v2 optimizer/diagnostics;  
`settings_store.py` — local settings;  
`exports.py` — MIDI/GP5/WAV;  
`game_logger.py` — optional compressed JSONL Game logs;  
`test_core.py`, `test_exports.py`, `test_game_logger.py` — regression tests;  
`tt` — WSL Windows-runtime command helper; `run.bat` — Windows source launch; `build_exe.bat` — optional build helper; `VERSION` — published version.

**Read canonical technical docs from live GitHub `work`**:

1. `docs/WORKFLOW.md` — vFLOW GitHub writes, commits, release and local acceptance.
2. `docs/PROJECT_STATE.md` — current implementation, acceptance and baseline.
3. `docs/ROADMAP.md` — upcoming Training Modes and priorities.
4. `docs/ARCHITECTURE.md` — module boundaries / timing / Game / Picking.
5. `docs/DECISIONS.md` — durable D-001…D-044 constraints as of the release.
6. `docs/TEST_MATRIX.md` — automated and manual gates.
7. `docs/PICKING_LOGIC_V2.md` — released Picking architecture.
8. `docs/USER_GUIDE.md` — actual Russian UI labels and usage.
9. `docs/CHANGELOG.md` / `docs/RELEASE_NOTES_0.0.5.md` — version/release evidence.
10. `docs/README.md` — documentation index.

Public README policy: `README.md` in professional Russian, `README.en.md` faithful English counterpart, reciprocal links, **never add private user paths/personal context/internal phase notes** to those public product pages. Engineering-only details belong under `docs/`.

This handoff lives at `docs/dev/HANDOFF_TITTYTATTER_2026-10-14_v0.0.5.md`.

## 8. Release workflow and published metadata

v0.0.5 is **already complete**, including source commit, successful user-local gate, GUI smoke, fast-forwarded `main`, full annotated tag, public GitHub Release, About description, and topics. **Do not rerun those publish operations.**

Future releases only on explicit request:
1. Develop on `work`; no version bump in ordinary work. Verify local acceptance and Git history.
2. Prepare user-facing bilingual README updates, docs, full changelog, exact release notes, root `VERSION`; create clear release metadata commit.
3. User pulls **exact** commit and runs `./tt check`, with GUI/audio acceptance if applicable.
4. Fast-forward `main` from tested `work`, not a force push or gratuitous merge.
5. Create a **real annotated** tag `vX.Y.Z` with a comprehensive English message: purpose, highlights, technical changes, validation, and deferred scope. Source it from a release-notes Markdown file; **never** a one-line version title.
6. If connected GitHub connector cannot create the annotated tag, give copy-pasteable local commands:

~~~bash
git tag -a vX.Y.Z -F docs/RELEASE_NOTES_X.Y.Z.md <exact-release-sha>
git push origin vX.Y.Z
git cat-file -t vX.Y.Z
git rev-parse 'vX.Y.Z^{}'
~~~

7. GitHub Release may be created with `gh release create vX.Y.Z --verify-tag --title "TittyTatter vX.Y.Z" --notes-from-tag`. Verify tag peel and full message directly from GitHub after push.
8. The GitHub app may have repo admin access but not mutation endpoints for About/topics; use explicit user-facing `gh repo edit` / `gh api` where needed. Topics max = 20; avoid blindly deleting any.

v0.0.5 published tag's 5,621-character annotation comes from `docs/RELEASE_NOTES_0.0.5.md`. No binary release/installer is implied; source repository launch works.

## 9. NEXT DESIGN SUBJECT — no implementation yet

**Subdivision Ladder / «Лестница делений»** is next planned major Training Mode according to the roadmap. Example proposed progression:

~~~text
quarter → eighth → triplet → sixteenth
~~~

There is **no finalized specification** yet. The user has not selected exact stage timing, UI, beat-pattern mapping, loop/boundary behavior, sound/metronome relationship, how Game/Focus/Picking react, settings persistence, or exports. Discuss options and tradeoffs first; do not choose a rigid interpretation of "Ladder" without the user.

Recommended first design investigation: inspect `training_modes.py`, `model.py`, `presets.py`, `audio_engine.py`, `app.py`, relevant tests and roadmap; propose a simple and coherent design that **reuses the existing pattern and callback-driven timeline**, with clear practice usefulness and stage transition rules. Ask for decisions only where options materially differ. Then make regression criteria before implementation.

Other future Training Modes: Burst Trainer («Рывки темпа»), Tempo Wave («Волна темпа»), Random Tempo Blocks («Случайный темп»), Accent Trainer («Сдвиг акцента»), Endurance Intervals («Интервалы»), Blind Pattern («По памяти»). Separate backlog: player calibration, MIDI controller input, long-term history, saved presets, packaged Windows release. None is automatically approved work.

**Product invariant:** PATTERN specifies WHAT is played; the Training Mode changes HOW to practice it. No parallel Game progression engine, no alternate pattern editor, no Qt-based clock.

## 10. ZIP decision and first-activation checklist

**No extra ZIP is needed.** The committed code, tests, assets and all relevant design/release documentation are in GitHub. Moving `.venv/`, Git-ignored `tittytatter.settings.json`, or device-specific `logs/` is unnecessary and risks transferring personal or machine-specific data. Validation results are summarized here and in release docs. If a future task genuinely needs a non-repository private file, request that one explicitly rather than archiving everything.

**Successor chat activation:**
1. Use the connected GitHub integration to fetch the complete handoff file from `work`:
   https://github.com/TheColdVoid1337/TittyTatter/blob/work/docs/dev/HANDOFF_TITTYTATTER_2026-10-14_v0.0.5.md
2. Read current `docs/WORKFLOW.md`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and task-relevant code; inspect current branch refs and root `VERSION`.
3. Recognize `main` and tag `v0.0.5` as frozen at `21c33aa`, while `work` may have post-release docs commits.
4. Adopt Russian conversation, English source/docs, exact WSL bash blocks, strict separation of GitHub write success vs local Windows acceptance, and direct GitHub write authorization until revoked.
5. Identify current open design topic as **Subdivision Ladder** (not committed or approved implementation), with **P7e deferred**.
6. Briefly acknowledge readiness and wait for the user's next task. Do not create a new issue, branch, code change, or release solely because the handoff was loaded.
7. If something genuinely cannot be fetched, be transparent and ask only for that missing detail.

**Expected result:** the new assistant can resume the project without making the user repeat decisions, paths, test formats, published-version rules, or constraints.
