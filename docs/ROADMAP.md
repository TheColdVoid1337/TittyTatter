# Roadmap

TittyTatter should continue to grow primarily as a **guitar rhythm training tool**.

The strongest product direction is:

> One PATTERN can be practised through many TRAINING METHODS.

Game remains an optional input/scoring layer over the same training timeline. Picking Guide remains an optional informational layer for guitar practice.

## Immediate post-0.0.4 focus — Picking Logic v2

The 0.0.4 release is complete. Picking Logic v2 P1-P6 is implemented, manually accepted, and the superseded transitional implementation has been removed and locally validated.

Implementation order:

1. **DONE — P1:** normalize Picking events and persistent/placeholder identities;
2. **DONE — P2:** deterministic attack-alternate engine on the normalized event stream;
3. **DONE — P3:** practical directional Economy transitions, start-polarity search, parity, loop-boundary scoring, linked sweep groups, and explainable transition types;
4. **DONE — P4:** repeated whole-beat motifs are shared constraints inside Economy optimization; subdivision-level cross-beat motifs remain evidence-driven future work;
5. **DONE — P5:** all Ramp stages are solved jointly so real attacks keep one learned direction while stage-local placeholders remain independently optimizable;
6. **DONE — P6:** the live Picking Guide uses v2 and the automated/manual Loop, Ramp, Alternate, sweep, placeholder, and repeated-motif acceptance checks passed.
7. **DONE — CLEANUP:** transitional Picking code/tests were removed in `debda3e`; the full local `./tt check` gate passed on `0df6f88`.
8. **OPTIONAL — P7:** advanced mechanics such as explicit USX/DSX/DBX profiles, sweep-link visualization, or ghost-stroke Alternate are future enhancements, not required for v2 completion.

Do not add more screenshot-specific picking heuristics when the failure belongs to the v2 model. Convert new failures into regression cases first.

The future Training Mode backlog remains valid, but Picking Logic v2 is the current practice-quality priority unless explicitly reprioritized.

## Priority post-release Training Modes

### Лестница делений — Subdivision Ladder

Move through rhythmic subdivision levels while preserving the same overall exercise concept.

Example direction:

```text
quarter → eighth → triplet → sixteenth
```

The exact transition/configuration model still needs design.

### Рывки темпа — Burst Trainer

Normal-tempo blocks interrupted by short faster bursts.

Goal: practise controlled acceleration without turning the whole exercise into a permanent high-tempo run.

### Волна темпа — Tempo Wave

BPM rises and falls cyclically.

Goal: practise stability while tempo changes continuously/predictably over a larger cycle.

### Случайный темп — Random Tempo Blocks

Tempo changes by multi-bar blocks inside a configured range.

The changes should be structured enough to remain a musical training exercise rather than random jitter.

### Сдвиг акцента — Accent Trainer

Move the accent through beats/subdivisions while keeping the underlying pattern.

Goal: improve internal pulse and independence from habitual metric emphasis.

### Интервалы — Endurance Intervals

Configurable work/recovery cycles.

Goal: support longer technique/endurance practice without requiring a separate exercise editor.

### По памяти — Blind Pattern

After several guided repetitions, remove selected visual and/or audible guidance while the timeline continues.

Goal: transfer the pattern from external guidance to internal memory.

## General Training Mode design rule

New Training Modes should reuse:

- the existing PATTERN;
- the existing exercise timeline;
- existing Game target generation;
- existing Focus presentation where applicable;
- existing export/session concepts where they make sense.

Do not create a separate pattern editor or duplicate progression engine for each Training Mode.

## Reliability / practice-quality backlog

Continue improving actual practice quality when evidence justifies it:

- real-device regression testing across Windows audio devices/backends;
- optional explicit/manual input/audio latency calibration if future diagnostics show a stable need;
- MIDI-controller/pad input for Game execution;
- richer long-term practice history and trend statistics;
- user presets/favorites;
- controlled pattern rotation or exercise sequencing;
- further Picking Guide heuristics driven by real guitar practice;
- broader Guitar Pro compatibility testing;
- packaged Windows release flow;
- additional session/export compatibility tests where useful.

## Game direction

Game should remain secondary.

Future Game work should primarily improve:

- input reliability;
- timing diagnostics;
- useful feedback;
- compatibility with Training Modes.

Do not turn Game into an independent rhythm videogame with its own unrelated progression system.

## Picking Guide direction

Picking Guide should remain informational and guitar-oriented.

Potential improvements should come from observed weaknesses in real playing rather than arbitrary complexity.

## Non-goals

Do not turn TittyTatter into:

- a DAW;
- a general-purpose notation editor;
- a standalone rhythm videogame that competes with the guitar-training workflow.

The project should remain focused on repeatable, configurable rhythm practice.
