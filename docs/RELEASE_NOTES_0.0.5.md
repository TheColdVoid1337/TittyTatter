TittyTatter v0.0.5

Release date: 2026-10-14
Platform: Windows
Previous release: v0.0.4

Summary
-------
Version 0.0.5 is a substantial upgrade to TittyTatter's guitar-picking
guidance. Picking Logic v2 replaces the earlier pattern-specific picking
implementation with an event-based optimizer that understands directional
sweeps, repeated rhythmic motifs, complete loop boundaries, and progressive
Ramp stages. New controls allow musicians to choose explicit picking-motion
preferences without changing the underlying rhythm or training exercise.

Highlights
----------
- Rebuilt Picking Guide with deterministic Strict Alternate and practical
  string-aware Economy suggestions.
- Added a first-stroke control to Strict Alternate: Auto, Down, or Up.
  Economy automatically optimizes its own first attack.
- Added Economy escape profiles: Auto, USX, DSX, and DBX. These affect
  alternate string crossings and one-way economy sweep preferences;
  they are explicit, soft practice preferences rather than an inferred
  diagnosis of the player's picking mechanics.
- Added independent Auto / Inside / Outside string-crossing preferences
  for alternating attacks.
- Added optional colored visual links between attacks that are part of
  a genuine directional sweep. Displaying or hiding the links never
  changes the selected strokes.
- Improved repeated-pattern consistency so identical rhythmic motifs
  use repeatable picking motions, including across cyclic bar boundaries.
- Improved Ramp exercises: all configured stages are solved together,
  preserving already-learned real attacks as new beats are added.
- Added ./tt picking-log for deterministic text-based Picking diagnostics,
  including escape-profile comparisons, inside/outside crossings, sweep
  links, and Ramp outputs.
- Published a Russian default README.md consistent with the Russian GUI
  and a complete English README.en.md with reciprocal language links.

Technical changes
-----------------
- Normalized event representation distinguishes true pattern attacks,
  silent/covered slots, explicit reset boundaries, and stage-local Ramp
  placeholder attacks.
- Alternate picking advances stroke parity on real attacks; OFF slots
  do not implicitly consume a stroke or reset the sequence.
- Economy uses a deterministic optimizer with directional sweep
  classification, penalties for wrong-direction crossings, start-polarity
  search, and cyclic last-to-first transition scoring.
- Whole-beat recurring motifs are enforced as stroke-identity constraints
  inside the optimization rather than fixed by post-processing.
- All Ramp stages contribute to one optimization. Persistent real
  attacks retain identical strokes as stages open; temporary muted
  placeholders are optimized for each stage's transition and loop.
- USX/DSX/DBX escape profiles and inside/outside preferences are
  independent, additive scoring inputs. No player-specific mechanics
  are inferred automatically.
- SweepLink metadata is derived from the completed solution; rendering
  is presentation-only and never feeds back into the optimizer.
- Superseded transitional picking heuristics and their legacy tests
  have been removed, leaving the unified v2 path.
- Core test coverage, Picking diagnostics, architecture documentation,
  user guidance, and release workflows have been updated.

Compatibility and usage
-----------------------
- The seven existing Training Modes, rhythm editor, Game, Focus view,
  transport/audio configuration, and MIDI / Guitar Pro 5 / WAV export
  remain part of the application.
- Normal Training and Game continue to use the same selected exercise
  timeline; Picking Guide is optional and does not create a third mode.
- Strict Alternate continues to alternate played attacks, not ghost
  strokes tied to silent grid positions.
- Existing settings and sessions keep their established usage, with
  reasonable defaults for newly introduced Picking controls.
- The application remains Windows-first and launches from source
  through run.bat with Python dependencies installed locally.

Validation
----------
- The local working tree was clean on the validated runtime candidate
  da166fe (2026-10-14).
- ./tt check passed on da166fe: core tests, module compilation, Picking
  diagnostics, export tests, Game logging, and dependency imports.
- ./tt picking-log passed on da166fe, confirming different USX/DSX
  solutions, inside/outside pattern changes, two correctly directed
  sweep links in the reference fixture, and stable Ramp-stage output.
- Live application GUI/audio smoke passed, as confirmed by the user.
- Release policy requires a final ./tt check on the exact 0.0.5 release
  commit before this annotated tag is created and published.

Deferred work and limitations
-----------------------------
- Rhythmic/ghost-stroke Alternate (P7e) is deferred. Existing Strict
  Alternate remains attack-alternate.
- USX/DSX/DBX settings are explicit preferences, not automatic analysis
  or certification of the player's personal picking mechanics.
- The Picking Guide uses TittyTatter's reference TI/string-5 and muted
  TA/string-6 mapping.
- MIDI-controller Game input, device-specific latency calibration, and
  a packaged installer/updater are outside this release.
- Subdivision Ladder and the remaining Training Mode proposals are
  future roadmap items.

Documentation
-------------
Russian README: README.md
English README: README.en.md
User guide: docs/USER_GUIDE.md
Picking reference: docs/PICKING_LOGIC_V2.md
Changelog: docs/CHANGELOG.md
Roadmap: docs/ROADMAP.md

Repository: https://github.com/TheColdVoid1337/TittyTatter
