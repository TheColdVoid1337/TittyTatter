# Roadmap

TittyTatter should continue to grow primarily as a **guitar rhythm training tool**.

The strongest product direction is:

> One PATTERN can be practised through many TRAINING METHODS.

Game remains an optional input/scoring layer over the same training timeline. Picking Guide remains an optional informational layer for guitar practice.

## Immediate release checkpoint

Before beginning the next feature cycle:

- finish release documentation/assets;
- select the next numeric version explicitly;
- run the final local release gate;
- fast-forward accepted `work` into `main`;
- create and verify the annotated release tag;
- synchronize `work` to the release commit;
- remove obsolete branches only after proving they contain no unique commits.

Do not start the future Training Mode backlog merely because it is documented here.

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
