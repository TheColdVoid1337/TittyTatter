# Test matrix

## Canonical local gate

Normal automated validation is local:

```bash
./tt check
```

The gate currently runs approximately:

1. `test_core.py`;
2. compile checks for the main Python modules;
3. `test_exports.py`;
4. `test_game_logger.py`;
5. dependency imports.

Expected green ending:

```text
== core tests ==
core tests OK
== compile ==
== export tests ==
export tests OK
== game log tests ==
game log tests OK
== imports ==
dependencies OK
== result ==
TittyTatter checks OK
```

GitHub Actions are not required for ordinary validation.

A green automated gate does **not** replace manual GUI/audio acceptance.

## Automated core coverage

| Area | Gate |
|---|---|
| Presets | expected straight/triplet binary spaces |
| Grid labels | meter-aware labels |
| Meter model | non-4/4 bars serialize/deserialize |
| Legacy sessions | old subdivision values migrate |
| Mute | serialized/restored where applicable |
| Span coverage | long notes cover expected metric beats |
| Defaults | established TI/TA audio defaults |
| Training modes | meter-aware ramp/gap/click helper behavior |
| Game lanes | TI/TA input cannot consume the opposite-lane target |
| Game matching | nearest same-lane target inside the accepted window |
| Game grading | PERFECT/GREAT/GOOD/HIT boundaries |
| Picking | representative economy/alternate/cyclic behavior |
| Picking v2 P1 | normalized real/OFF/covered slots, exact rhythmic phase, stable real-attack identity across Ramp stages, stage-local placeholder identity, explicit reset boundaries |
| Picking v2 P2 | attack-alternate on normalized events; OFF/COVERED do not consume parity; string changes preserve alternation; Ramp placeholders consume attacks; reset markers do not restart Alternate; deterministic start-polarity handling |
| Picking v2 P3 | same-string alternation, 6->5 and 5->6 directional sweeps, wrong-direction crossing classification, DOWN/UP start search, attack parity, OFF continuity, explicit reset behavior, cyclic last->first scoring, linked sweep groups, deterministic decision reasons |
| Picking v2 P4 | repeated whole-beat motif annotation and in-optimizer equality constraints for A/A/A/B, A/B/A/B, cyclic end/start repetition, OFF-containing motifs, sweep-preserving stable motifs, deterministic constrained output |
| Picking v2 P5 | joint Ramp 1->full and 2->full solving; persistent real-stroke equality across stages; P4 motif preservation; stage-local alternating TA placeholders; useful sweep retention; covered-beat handling; deterministic joint output |
| Picking v2 P6 | live app routes only v2 Alternate/Economy/Ramp solvers; Loop/Ramp/Alternate visual acceptance passed; transitional implementation removed in `debda3e`; post-cleanup `./tt check` passed on `0df6f88` |
| Picking v2 P7a | Strict Alternate Auto/DOWN/UP first-stroke control; Economy/Ramp UI ignores persisted start override and stays Auto; internal Economy constraint hook remains regression-tested; UI visibility/persistence/manual check pending |
| Syntax | application modules compile |

## Automated export coverage

| Export | Gate |
|---|---|
| MIDI | valid SMF structure / repeated pattern |
| GP5 | file writes and parses through PyGuitarPro |
| GP5 repeats | requested measures exist |
| GP5 labels | annotation placement remains controlled |
| GP5 dead note | TA exports as the intended dead-note representation |
| WAV | expected sample rate/sample width/channel/frame behavior |

## Automated diagnostic-log coverage

- logging disabled does not create a Game log;
- logging enabled creates a unique raw JSONL session;
- records serialize;
- finish/stop creates a `.tar.gz`;
- raw JSONL is deleted after successful archival;
- archived content reads back correctly.

## Manual release acceptance

Before tagging, verify the exact release commit locally.

### Startup / layout

- application opens without traceback;
- switching tabs does not cause unexpected window growth/shrink;
- normal editable beat cards remain correctly laid out;
- horizontal scrolling remains usable for wide meters;
- About tab opens correctly;
- TittyTatter icon renders correctly;
- TheColdVoid1337/repository link remains clickable.

### Training / Game selector

- top **Тренировка / Игра** selector is mutually exclusive;
- normal Training launch works;
- when **Игра** is selected, Start starts Game execution of the current Training Mode;
- Space follows the same Training/Game execution state;
- Picking Guide and Game remain mutually exclusive.

### Meter / pattern editor

Check representative meters such as:

- 4/4;
- 3/4;
- 6/8;
- 7/8;
- 5/16.

Verify:

- beat editors rebuild correctly;
- step states cycle correctly;
- long-note/span coverage remains correct;
- Mute behavior remains correct where available;
- grid/preset changes apply as intended.

### Training modes

#### Повтор

- complete effective pattern repeats continuously.

#### Разгон с 1 доли

- stage sequence expands from beat 1 to the full numerator;
- bars-per-stage configuration works;
- stage status/warnings remain correct.

#### Разгон с 2 долей

- starts from `min(2, numerator)`;
- expands to the full bar;
- one-beat meters behave sensibly.

#### Пропуски

- configured audible/silent block lengths are respected;
- all rhythmic audio guidance disappears in silent bars;
- internal timeline continues;
- yellow playhead/current-cell guidance disappears during silence;
- guidance returns automatically when sound returns.

#### Нарастающие пропуски

- audible block remains fixed;
- silent block grows 1 → 2 → 3 ... to configured maximum;
- cycle then restarts;
- silent-phase timeline/playhead rules match normal Gap.

#### Редкий метроном

Verify each current option:

- Все доли;
- Только 2 и 4;
- Только 1 и 3;
- Только 1;
- Только 1 раз в 2 такта.

#### Смещённый метроном

Verify click positions:

- eighth `&`;
- sixteenth `e`;
- sixteenth `&`;
- sixteenth `a`.

Confirm that displaced click works correctly with pattern grids that do not share the same subdivision, including triplets.

### Training options

- Count-in works;
- Tempo Trainer enables/disables without collapsing its subordinate options;
- Timer enables/disables without collapsing its subordinate options;
- Tempo Trainer changes BPM at intended boundaries;
- timer completion stops playback and plays its completion cue;
- compact BPM controls work;
- TAP [T] works.

### Focus mode

- physical F toggles Focus with a non-English keyboard layout;
- Focus hide/show cycle is stable;
- configuration tabs and editable beat cards are hidden in Focus;
- large metronome remains centered/usable;
- size setting changes actual needle/pivot/lamp/flash geometry;
- check representative size settings such as 60%, 100%, 150%, 200%;
- Game graph remains compact in Focus;
- read-only rhythm strip spans the lower display cleanly;
- TI cells are compact rounded/pill-like;
- TA/rest cells remain rectangular;
- current subdivision has a clear yellow outline;
- beat lamps do not collide with the needle pivot/base;
- count-in does not show an active current-subdivision outline;
- Gap/Progressive Gap silence hides yellow guidance;
- no layout regression appears when leaving Focus.

### Game input

- keyboard TI/TA bindings work;
- bindings work with a non-English active keyboard layout where physical scan capture is expected;
- mouse Game bindings work;
- binding capture accepts physical F rather than toggling Focus;
- during an active Game, an F lane binding has priority over Focus toggle;
- TI input consumes TI targets only;
- TA input consumes TA targets only;
- short early input is buffered correctly when target publication is slightly delayed;
- opposite-lane fallback is not present;
- adaptive timing bias is not present.

### Game timing / feedback

- PERFECT/GREAT/GOOD/HIT grades appear at appropriate offsets;
- Score increments by grade;
- missed/out-of-window input becomes MISS;
- signed early/late timing is displayed;
- quality/history graph updates;
- Current Game stats update while playing;
- Last Game summary persists after stop;
- TI/TA split HIT feedback works;
- original TI Hit 1/2/3 sounds remain recognizably unchanged;
- TA lower variants work;
- guitar-style TI E3 / muted E2 set works;
- MISS choices work;
- feedback volumes behave correctly.

### Silent Game exercise

With Gap or Progressive Gap plus Game:

- audio guidance disappears in silent bars;
- Game targets continue;
- the player can still enter TI/TA and receive timing results;
- the yellow visual guidance remains hidden until audible guidance returns.

### Picking Guide

#### Picking Logic v2 P6 cutover

- live UI uses the v2 Alternate path;
- live non-Ramp Economy uses event-based v2 Economy;
- live Ramp Economy uses the joint P5 solver;
- already-open Ramp attacks keep identical directions as later beats appear;
- repeated motifs remain stable without losing valid sweeps;
- inactive Ramp TA placeholders alternate instead of restarting every beat with DOWN;
- compare the previously reported Ramp screenshots/cases against expected behavior before deleting transitional code.

Current manual status on `e611ec2`:

- PASS — Ramp 1->2->3->4 Economy, sweep-compatible `TA TI TI TA` motif: stable `DOWN DOWN UP UP`, both directional sweeps retained, real strokes unchanged across stages, placeholder entry/stream clean;
- PASS — Ramp 2->full Economy: the first two real beats preserve the same Economy strokes between the 2-beat and 4-beat stages, while inactive TA placeholders alternate cleanly;
- PASS — public Alternate with OFF slots: `TA . TA . | TI . TI . | TA . TI . | TA . . TI` renders attack-alternate `DOWN UP DOWN UP DOWN UP DOWN UP` without OFF consuming parity;
- PASS — non-Ramp Loop / Economy A B A B: beats 1/3 match and beats 2/4 match in the live GUI.

#### Economy

- TI/TA reference strings are correct;
- repeated single-beat pattern `A A A A` preserves period 1;
- repeated `A B A B` preserves period 2;
- cyclic boundary behaves correctly in Loop;
- cyclic boundary behaves correctly in Ramp stages;
- OFF slots preserve Economy continuity unless an explicit reset boundary is supplied.

#### Strict alternate

- attacks alternate ↓↑;
- rests do not consume a direction.

#### Presentation

- current large cue shows arrow/string;
- following-strokes row works;
- count 1–8 works;
- future strokes progress horizontally;
- upstroke remains green;
- downstroke remains red;
- current-beat highlight works.

### Audio

On the actual target Windows output device:

- selected output device is correct;
- WASAPI path is stable where supported;
- no recurring crackle at normal settings;
- TI/TA/metronome remain rhythmically locked;
- established TI/TA timbres are unchanged;
- BPM changes during playback remain stable;
- count-in transitions cleanly;
- audio-system changes while stopped work.

### Sessions / settings

- session save/load restores the exercise;
- Training Mode parameters persist appropriately;
- Game settings persist;
- Picking/Focus settings persist;
- older settings receive valid fallback defaults;
- session schema behavior remains independent of app semantic VERSION.

### Diagnostic log

Optional timing-debug acceptance:

```bash
./tt run -log
```

After a Game finishes:

- a new unique archive exists;
- previous archives remain untouched;
- no raw JSONL remains after successful compression.

### Export

Create real files and inspect them:

- MIDI opens with correct tempo/meter/pattern repetition;
- GP5 opens through a compatible Guitar Pro reader;
- TA is a dead/muted note as intended;
- TI maps to string 5 fret 7;
- legacy text does not produce unwanted encoding corruption;
- WAV duration/quality match the dialog;
- WAV sounds consistent with current realtime sound configuration.

## Silent-exit procedure

If `./tt run` exits without a useful traceback, run from the repository root:

```bash
./.venv/Scripts/python.exe -X faulthandler -u "$(wslpath -w "$PWD/app.py")"
echo "EXIT=$?"
```

Do not patch blindly before inspecting the resulting failure.

## Release gate

A release candidate is accepted only after:

1. exact `work` HEAD is known;
2. `git status --short` is reviewed locally;
3. `./tt check` is user-confirmed green;
4. `./tt run` receives focused manual GUI/audio/Game acceptance;
5. release documentation/assets are current;
6. release version is explicitly chosen;
7. the final release commit is pulled and rechecked as required;
8. `main` is fast-forwarded when history permits;
9. annotated tag points to exactly the final release commit.

Repository writes alone are not proof of local runtime success.
