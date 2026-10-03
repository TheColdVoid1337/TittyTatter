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

**Decision:** prefer frequent small but meaningful semantic commits. Each independently useful/fixable UI, logic, documentation, or release change may be committed separately. Critical one-line regression fixes may be microcommits.

**Reason:** completed work should remain recoverable even if a long development session is interrupted.

## D-015 — Preserve established layout

**Decision:** once the current desktop layout has stabilized, prefer additive changes and targeted replacements. Do not restructure existing layout without a concrete functional or usability need.

## D-016 — Game matching is lane-only

**Decision:** TI keyboard input can consume only TI targets, and TA keyboard input can consume only TA targets.

**Reason:** real diagnostic logs showed that cross-lane consumption caused cascading desynchronization after one miss.

## D-017 — Buffer early input, do not immediately miss it

**Decision:** a short GUI-side input buffer bridges the period where a correct early key press may arrive before the PortAudio callback has published its future DAC-timestamped target.

**Reason:** diagnostics showed that otherwise accurate early hits were being rejected solely because the target did not yet exist in the GUI pending queue.

## D-018 — No adaptive timing bias for current game scoring

**Decision:** the current game matcher does not learn or apply an automatic timing offset.

**Reason:** diagnostic sessions showed that the learned bias could drift by a whole subdivision and make otherwise accurate play appear systematically early/late. Explicit calibration may be reconsidered later as a separate feature.

## D-019 — Diagnostics are opt-in and archived

**Decision:** game diagnostics are enabled only with `-log` / `--log`. Each game writes a unique timestamped session that is compressed to `.tar.gz`; successful compression removes the raw JSONL.

**Reason:** diagnostics should be available for timing investigation without adding normal-run disk churn or overwriting prior evidence.

## D-020 — Picking guidance is algorithmic

**Decision:** TI is modeled as string 5 and TA as string 6 for picking guidance. The system chooses economy-picking directions automatically rather than asking the user for a fixed first stroke.

**Reason:** the displayed pattern should suggest an efficient playable picking path, not merely alternate up/down mechanically.


## D-021 — Training Mode is the exercise source of truth

**Decision:** the selected Training Mode controls exercise behaviour for both normal guitar Training and Game execution.

**Reason:** Pattern defines what is played; Training Mode defines how it is trained. Game is only another execution/input layer and must not own a parallel progression system.

## D-022 — Game is secondary to guitar training

**Decision:** TittyTatter is primarily a guitar rhythm trainer. Game remains a secondary convenience for keyboard/mouse timing practice.

**Reason:** new development should improve transferable guitar practice rather than turn the project into a standalone rhythm videogame.

## D-023 — Picking Guide is informational, not a Training Mode

**Decision:** Штрих / Picking Guide is an optional guitar-practice aid. It is not a third peer mode beside Training and Game.

**Reason:** Picking suggestions annotate how to execute the exercise on guitar; they do not define a separate exercise timeline.

## D-024 — Silence removes guidance, not time

**Decision:** Gap and Progressive Gap silent phases suppress rhythmic guidance while the internal exercise timeline continues.

Game targets continue through silence. Yellow current-position guidance disappears during the silent phase and returns with audible guidance.

**Reason:** the exercise is intended to train internal time, not pause the musical clock.

## D-025 — Focus is presentation, not exercise logic

**Decision:** Focus mode hides configuration UI and enlarges practice presentation without creating a separate pattern/timeline state.

The Focus rhythm strip must reflect the current effective training pattern.

## D-026 — Physical-key bindings should survive keyboard layout changes

**Decision:** common Game bindings and the Focus shortcut use physical scan information where available, with logical-key fallback only when necessary.

**Reason:** guitar/rhythm practice should not break when the active Windows keyboard layout changes.

## D-027 — Focus F-key priority

**Decision:** while a Game binding editor is capturing input, capture has priority. During an active Game, an F binding used by a Game lane has priority over Focus toggle. Otherwise physical F toggles Focus.

## D-028 — Public README is user-facing

**Decision:** root `README.md` is written for people who download/clone the project.

It must not contain personal machine paths or private development-layout details. Detailed internal development workflow belongs in `docs/WORKFLOW.md`.

## D-029 — README logo must be a real transparent asset

**Decision:** GitHub README rendering uses a repository PNG with actual transparency.

**Reason:** the application runtime can transform the source icon through Qt, but GitHub Markdown cannot execute that runtime helper.

## D-030 — Direct GitHub write authorization persists until revoked

**Decision:** `#writegh` authorizes direct GitHub project writes and remains active until the project owner explicitly revokes it.

Repository writes still follow semantic commits, reporting, and local-validation rules.

## D-031 — No default remote CI

**Decision:** do not add GitHub Actions or other remote CI as a default project workflow.

**Reason:** the canonical acceptance environment is the real local Windows GUI/audio runtime. Automated local tests remain useful but cannot replace manual realtime validation.

## D-032 — Release integration prefers fast-forward

**Decision:** when `work` is a clean descendant of `main`, release integration should fast-forward `main` rather than create an unnecessary merge commit.

## D-033 — Old branches are deleted only after containment verification

**Decision:** branch cleanup happens after release verification and only after proving the candidate branch has no unique commits relative to the final `main`.

## D-034 — Application version and settings schema are independent

**Decision:** root `VERSION` changes only at explicit release/tag checkpoints. Session/settings schema versions may change independently for persistence compatibility.

## D-035 — Alternate means attack-alternate

**Decision:** the normal user-facing **Переменный / Alternate** strategy alternates consecutive attacks, not rhythmic grid slots.

OFF and covered long-note positions do not consume a pick direction. Training-generated Ramp placeholder attacks do consume a direction.

**Reason:** this matches the intended exercise semantics and avoids silently turning sparse attacks into a ghost-stroke/continuous-strumming interpretation.

## D-036 — Economy is practical and practice-oriented

**Decision:** the normal user-facing **Экономный / Economy** strategy is practical directional economy, not maximum-sweep optimization.

It should prefer same-string alternation, use valid directional sweeps when useful, and preserve stable repeated motor motifs. Motif/stage stability outranks a tiny local transition saving.

**Reason:** TittyTatter is a trainer. A player should not have to relearn an otherwise identical repeated figure only because a later boundary admits a marginally cheaper transition.

## D-037 — Ramp picking is one constrained exercise

**Decision:** Picking Logic v2 must treat all Ramp stages as one constrained optimization problem.

Real stored-pattern attacks keep persistent identities and therefore one stroke direction across every stage in which they exist. Temporary Ramp placeholder attacks are stage-local and may be optimized separately.

**Reason:** independently optimizing each stage teaches conflicting motor patterns; choosing one arbitrary stage as the global truth can also destroy useful Economy transitions.

## D-038 — Do not infer a player's escape mechanics

**Decision:** Picking Logic v2 reserves an internal escape-profile hook for AUTO / USX / DSX / DBX, but the default product must not pretend to know the player's actual picking mechanics.

**Reason:** stroke direction alone does not determine escape behavior. Personalized mechanics may become an advanced preference later, but they require an explicit user choice rather than inference.

