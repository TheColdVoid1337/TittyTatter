# Illustrated Training Mode designs

**Status: ENGINEERING CANDIDATE ON work / LOCAL ACCEPTANCE PENDING.** All seven post-v0.0.5 Training Modes have source implementations in the work branch. The code and new automated gate have **not yet been run/accepted in the owner's native Windows environment**. Diagrams remain illustrative; actual candidate behavior is specified below, and the published v0.0.5 build does not contain these features.

The first three design studies are intentionally more detailed; the remaining four have compact practice cards. See [ROADMAP.md](ROADMAP.md) for priorities and [ARCHITECTURE.md](ARCHITECTURE.md) for current application contracts.

## Reading the diagrams

- `|` separates beats, bars, or stages (as labeled).
- `X` = generic played attack; `x` = regular/soft attack; `!` = conceptual accent; `.` = blank spacing.
- These glyphs are **not** stored TittyTatter states (`TI`, `TA`, `OFF`), and do not specify string assignment.
- Numerical BPM and bar examples help explain the exercise; they are not recommended universal thresholds.
- Diagrams show the **musician's exercise**, not a confirmed transformation algorithm for the editor's Pattern.

**Shared product contract:** The PATTERN defines *what* to play; the Training Mode defines *how* to practice it. Training and Game must use the same callback-clock-driven exercise timeline. Focus is presentation; Picking Guide is information, not another mode. The stored pattern, TI/TA sounds, existing Game lane matching, and established Picking semantics must not silently change.

---

## 1. Лестница делений — Subdivision Ladder

**Status:** First implementation candidate; stage mapping selected provisionally, pending native validation.

**Purpose:** Shift between rhythmic subdivisions while the metric pulse remains steady.

### Illustrated exercise

```text
METRONOME:            steady 80 BPM (illustrative)

ONE METRIC BEAT:
Quarter      | X           |  1 attack
Eighths      | X     X     |  2 attacks
Triplets     | X   X   X   |  3 attacks
Sixteenths   | X  X  X  X  |  4 attacks

BARS:         1–2          3–4          5–6             7–8
STAGE:       QUARTERS  -> EIGHTHS   -> TRIPLETS    -> SIXTEENTHS
                ^                                         |
                +---------------- repeat ----------------+
```

**What it trains:** Internal pulse while attack density changes, switching accurately between straight and triplet timing, right-hand coordination and consistency, and maintaining relaxation when subdivisions become denser.

**How to practice (example):**

1. Select a comfortable fixed pulse at which the densest level stays clean.
2. Perform one level for two full bars, using the metronome as the unchanged reference.
3. Switch subdivision exactly at a bar boundary, without rushing or delaying the beat.
4. Return to the first level and listen for drift, especially after the triplet stage.
5. Start with a simple single-string exercise; add TI/TA string changes only once the rhythmic transition is stable.

**Example:** Two bars each of quarters, eighths, triplets and sixteenths at 80 BPM. This increases **attacks per beat**, not BPM.

**Unresolved design decisions:**

- How does a density-changing mode respect the user's existing mixed-grid TI/TA/OFF Pattern? Does it need a dedicated generated exercise/reference tone, or a documented deterministic transformation of the stored Pattern?
- Which levels, order, reverse direction and bars-per-stage controls are useful without producing an oversized UI?
- What does "one beat" mean for denominators 2, 4, 8 and 16, including unusual/one-beat meters?
- Should editor and Focus display the stored or stage-effective Pattern, or both?
- How do stage-generated attacks affect Game targets, picking-stroke identity and loop closure?
- What exactly is persisted/exported to MIDI, GP5 and WAV?

**Proposed acceptance checks:** deterministic stage changes, uninterrupted pulse, correct straight/triplet grid timing, usable one-beat and odd meters, coherent Game/Focus/Picking output from a single effective exercise. These are candidates, not approved implementation requirements.

---

## 2. Рывки темпа — Burst Trainer

**Status:** First implementation candidate; bar-aligned base/fast phases.

**Purpose:** Keep the same rhythmic Pattern but introduce short faster sections between comfortable-tempo blocks.

### Illustrated exercise

```text
BAR:        | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |10 |
BPM:        |80 |80 |80 |80 |120|80 |80 |80 |80 |120|
PHASE:      |--- COMFORT ---|FAST|--- COMFORT ---|FAST|
OUTLINE:      ▁    ▁    ▁    ▁   █   ▁    ▁    ▁    ▁   █
```

**What it trains:** Clean speed bursts, controlling entry and exit from fast playing, restoring relaxed motion afterward, and retaining attack accuracy under brief extra load.

**How to practice (example):**

1. Choose a riff that is fully comfortable at the base tempo.
2. Play four bars with clean, even articulation.
3. Play one bar faster while keeping the **same notes and subdivision structure**.
4. Immediately return to base speed; notice tension and timing errors.
5. Raise burst speed or duration only if the complete cycle remains controlled.

**Example:** Four bars at 80 BPM, one at 120 BPM, looped. This is a **tempo change**, not Subdivision Ladder.

**Unresolved design decisions:** Base/fast BPM absolute vs relative multiplier; bars vs seconds per block; stage-transition signaling; coexistence with the existing Tempo Trainer, Timer and count-in; BPM changes at exact callback-clock bar boundaries; Game DAC-time targets; tempo-change representation in export.

**Proposed acceptance checks:** no duplicated/missed attacks across speed boundaries; identical Pattern at both tempos; callback timing and Game targets stay synchronized; Focus shows current phase clearly.

---

## 3. Сдвиг акцента — Accent Trainer

**Status:** First implementation candidate; only the first existing attack of a selected beat is louder.

**Purpose:** Shift emphasis through successive rhythmic positions without changing the underlying attack placement.

### Illustrated exercise

```text
Four attacks each 4/4 bar:  ! = emphasis, x = ordinary attack

BEAT:         1  2  3  4
BAR 1:       |!  x  x  x|   accent beat 1
BAR 2:       |x  !  x  x|   accent beat 2
BAR 3:       |x  x  !  x|   accent beat 3
BAR 4:       |x  x  x  !|   accent beat 4

Possible advanced subdivision movement:
GRID:        |1  &  2  &  3  &  4  &|
PHASE A:     |!  .  .  .  .  .  .  .|
PHASE B:     |.  !  .  .  .  .  .  .|
PHASE C:     |.  .  !  .  .  .  .  .|
```

**What it trains:** Dynamic independence from the strong first beat, internal pulse, syncopation awareness and controlled picking emphasis without moving attack onsets.

**How to practice (example):**

1. Pick a familiar even Pattern and steady, manageable pulse.
2. Emphasize the first position for one bar; keep other attacks in their original places.
3. On each next bar, move the accent one position forward.
4. Return to the start after the last position.
5. Check that accents do not become **extra** attacks or cause rushing.

**Important distinction:** Implemented `Смещённый метроном` moves the click's position. Proposed Accent Trainer instead focuses on **emphasis**; which channels express it requires a decision.

**Unresolved design decisions:**

- Stronger TI/TA attack, accented metronome, visual-only coaching, or independent toggles?
- What if the intended position is OFF, covered by a span, muted, or has no attack?
- Shift by metric beats or by an explicitly chosen fine subdivision grid?
- Does the effective event model require accent metadata separate from TI/TA/OFF?
- Should Game judge accents (unlikely with simple key input), merely show them, or ignore them for scoring? How do Focus, Picking and export behave?

**Proposed acceptance checks:** original attack times unchanged, deterministic accent movement, no extra Game targets, consistent accents on mixed grids, no accidental interaction with Displaced Click.

---

## 4. Волна темпа — Tempo Wave

**Status:** First implementation candidate; native validation pending.

**Purpose:** Predictably increase and decrease tempo through a larger cycle, rather than jumping straight to a short burst.

```text
BAR:    | 1 | 2 | 3  | 4  | 5  | 6 | 7 |
BPM:    |80 |90 |100 |110 |100 |90 |80 |
SHAPE:    ▁   ▃   ▆    █    ▆   ▃   ▁
             rise -> peak -> descend
```

**What it trains:** Consistency during acceleration and deceleration, speed adaptation, and maintaining clarity on the way back down.

**How to practice:** Keep a small comfortable range at first; perform the same Pattern across the wave, noting whether deceleration causes uneven attacks. Increase range only when all phases are clean.

**Open questions:** Stepped per-bar BPM or continuous interpolation? Wave period and min/max? Overlap with existing Tempo Trainer? Callback timing, Game, Focus and tempo-map export semantics?

---

## 5. Случайный темп — Random Tempo Blocks

**Status:** First implementation candidate; native validation pending.

**Purpose:** Change tempo unpredictably between **stable blocks**, not on arbitrary individual attacks.

```text
BLOCK:     | A: 2 bars | B: 2 bars | C: 2 bars | D: 2 bars |
BPM:       |    80     |   100     |     90    |    110    |
PATTERN:   |----------- same rhythmic Pattern throughout ------|
```

**What it trains:** Regaining the pulse after a tempo change, rhythmic adaptability, and avoiding overreliance on a memorized acceleration sequence.

**How to practice:** Begin with a narrow safe tempo window. Keep the same riff and judge how quickly each new block becomes rhythmically stable. Do not treat unpredictable tempo as a reason to sacrifice clean technique.

**Open questions:** Seeded randomness for reproducible tests and repeatable exercises; tempo range, adjacent-step limits, length and signaling; interaction with Tempo Trainer; Game and export of a recorded random sequence.

---

## 6. Интервалы — Endurance Intervals

**Status:** First implementation candidate; native validation pending.

**Purpose:** Alternate defined work and recovery periods in a longer practice session.

```text
TIME:       |   45 sec   | 15 sec |   45 sec   | 15 sec |
PHASE:      |    WORK    |  REST  |    WORK    |  REST  |
EFFORT:     |   PLAY     |recover|   PLAY     |recover|
```

**What it trains:** Sustainable technique, awareness of fatigue, restarting without tension and consistent articulation over repeated sets.

**How to practice:** Choose a manageable work interval and truly recover during the rest period. Keep the motion controlled over multiple rounds rather than maximizing duration. Stop if discomfort or technique breakdown appears.

**Open questions:** Bar-based vs wall-clock timing; full rest/silence vs slower active recovery; does the timeline advance during rest? Game target behavior, Focus state, Timer relationship, transition cues and session reporting. Existing Gap silence is **not automatically** the same as physical recovery.

---

## 7. По памяти — Blind Pattern

**Status:** First implementation candidate; native validation pending.

**Purpose:** Withdraw selected guidance after an initial learning phase while the player retains the rhythm from memory.

```text
PHASE:          | LEARN | REDUCE | MEMORY | RESTORE |
VISUAL CUES:    |   ON  | partial|   OFF  |   ON    |
AUDIO CUES:     |   ON  |   ?    |   ?    |   ON    |
MUSICAL CLOCK:  |   ON  |   ON   |   ON   |   ON    |

? = future independently selected behavior
```

**What it trains:** Memorized attack placement, internal pulse and independence from constant visual/audio direction.

**How to practice:** Learn the Pattern with cues, remove one kind of guidance for a short block, continue playing and compare timing when full guidance returns. Extend the memory phase only while the underlying rhythm stays accurate.

**Open questions:** Hide only editor/Focus playhead or also suppress TI/TA/metronome; independent cue selections; learn/memory/restore durations; comparison with existing Gap modes; continuous Game targets and scoring; whether a phase cue compromises the memory exercise.

**Invariant:** Loss of guidance must never accidentally stop the callback musical clock.

---

## Implemented candidate semantics and acceptance gate

The first work-branch implementation intentionally chooses a small, repeatable exercise contract:

| Mode | Work-branch behavior |
|---|---|
| Subdivision Ladder | 1/2/3/4 attacks per metric beat, in that order. A sounding beat cycles its TI/TA *attack sequence*, ignoring within-beat OFF gaps; completely silent/muted beats and sustained long-note spans are preserved. `ladder_bars` controls stage duration, default 2. This is a **generated exercise**, not a lossless resampling of arbitrary mixed-grid note/rest timing. |
| Burst Trainer | **A–B–A–B**: unchanged configurable 4 base bars / 1 alternative-BPM bar cycle. **Custom**: one «Рывок» checkbox per metric beat card, from 1–16 in the selected meter (e.g. six flags for 6/4). Each marked beat uses «Рывок, BPM», every other beat uses the base BPM. Mask repeats every bar. Both directions (fast or slow) allowed. Original Pattern is unchanged. |
| Accent Trainer | Move across metric beats each `accent_bars` bars (default 1). First existing attack in selected beat is 1.45× louder; no attack is created on a rest. Original metronome emphasis remains unchanged. |
| Blind Pattern | 4 guided bars / 2 memory bars by default. Hide editor/Focus pattern and Picking overlay and silence TI/TA guidance during memory; retain metronome and **Game targets**. |
| Endurance Intervals | 4 work bars / 1 rest bar by default. Rest mutes TI/TA guidance and removes Game targets but keeps metronome/callback timeline. |
| Tempo Wave | 7-step triangle, 2 bars per step by default, between selected min and max BPM. This is **stepwise**, not continuous interpolation. |
| Random Tempo Blocks | Deterministic seeded BPM within min/max bounds, default 2 bars per block; no per-note jitter. |

Custom Burst changes the duration of *a whole metric beat* at the beginning of that beat, not of a subdivision inside it. For example, 4/4 at base 50 and alternative 100 BPM with mask [off, on, off, on] lasts 1.2+0.6+1.2+0.6 seconds per bar. The next bar repeats the mask; 6/4 allows six independent tempo decisions. Mute and covered long-note beats may still have a tempo selection because beat duration remains musically meaningful. Count-in stays at base BPM. A/B blocks ignore any saved Custom flags, and switching back retains them. On playback, tempo-map edits stop the exercise rather than introducing an unsynchronized mid-beat change.

All settings persist in both session snapshots and ignored application settings with backward-compatible defaults. New tempo modes disable the independent Tempo Trainer modifier. Current MIDI/GP5/WAV exports deliberately continue to export the **stored Pattern at base BPM** rather than render variable Training Mode stages. They remain pattern exports, not whole-session exercise renders. A later export-mode feature would require its own specification and tests. Existing v0.0.5 release/version remain unchanged.

**Important visual distinction:** The normal editable beat cards represent the *stored* Pattern. Ladder hides those cards during playback because its effective beat grids differ; Focus renders the generated stage. Blind and recovery phases hide their note guidance; the visible pulse/phase label continues.

### Validation requirements

- `./tt check` must include `test_training_modes.py` and pass without local errors.
- `./tt burst-smoke` must verify original A/B default, Custom-only card checkboxes, 4/4→6/4 selection retention, JSON session and application-settings round-trip, legacy defaults, and reset; no audio device is opened by this offscreen Qt smoke.
- Manual Custom checks: 4/4 mask 2+4, 50→100 BPM at beat boundaries; 6/4 mask 2+4+6, including triplet/eighth/sixteenth card subdivisions; 100→50 slowdown; Game timing; Focus rhythm; Stop restores base BPM. Confirm unchanged A/B bar schedule.
- `./tt run` needs native Windows smoke across all seven modes, stage boundaries, meters, Game and Focus.
- Round-trip save/load of new settings and old sessions must work, including when modes are switched while stopped.
- User must explicitly confirm native acceptance before moving the modes into the published-product sections of `USER_GUIDE.md` or the bilingual READMEs, or attempting a new release.

The implementation choices above are testable initial behavior, **not** evidence of local acceptance. Earlier open questions in the design studies remain future extension considerations rather than blockers to testing this first candidate.

## Implementation order and specification gate

The seven modes were implemented together at the owner's request. The next phase is local verification and narrowly scoped fixes; no additional Training Mode implementation should be assumed accepted yet.

Before implementation, agree on: intended guitar-learning outcome; exact phase/state and transition rules; stored vs effective Pattern semantics; meter and mixed-grid edge cases; callback-clock scheduling and click behavior; Game targets; Focus; Picking Guide; settings/session migration; MIDI/GP5/WAV export; deterministic tests and user-local Windows GUI/audio acceptance.

**Documentation promotion:** Do not describe the seven candidate modes as already shipped in `README.md`, `README.en.md` or `USER_GUIDE.md` until the native Windows gate is accepted. Revise this engineering study in place as actual behavior changes.
