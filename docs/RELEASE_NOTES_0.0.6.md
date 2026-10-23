TittyTatter v0.0.6

Release date: 2026-10-23
Platform: Windows
Previous release: v0.0.5
Version: 0.0.6

Summary
-------
Version 0.0.6 expands TittyTatter from seven to fourteen Training Modes
and adds a per-beat Custom Burst tempo map. The release retains the original
PySide6 interface, shared guitar-training/Game playback timeline, Picking
Logic v2, and existing rhythm-pattern editing features. It is a training
upgrade, not a UI redesign.

A special thank-you to **Fulton97**: the Custom option in "Рывки темпа"
(Burst Trainer) was added at Fulton97's request, allowing an alternate BPM
to be assigned individually to selected metric beats within the bar.

Highlights
----------
- Added seven Training Modes:
  * "Лестница делений" (Subdivision Ladder): quarter -> eighth -> triplet
    -> sixteenth attack-density stages without overwriting the saved Pattern.
  * "Рывки темпа" (Burst Trainer): alternating base/alternate tempo blocks.
  * "Сдвиг акцента" (Accent Shift): successive metric-beat accents.
  * "По памяти" (Blind Pattern): guided and memory-only phases.
  * "Интервалы" (Endurance Intervals): playing and recovery blocks.
  * "Волна темпа" (Tempo Wave): deterministic stepped rise and fall.
  * "Случайный темп" (Random Tempo Blocks): reproducible seeded tempo changes.
- **Requested by Fulton97:** Burst Trainer now offers two variants:
  * "A–B–A–B" (default) preserves the original behavior: a selectable
    number of whole bars at base BPM, then a selectable number of whole
    bars at "Рывок, BPM", repeating indefinitely.
  * "Custom" reveals a "Рывок" checkbox next to "Mute" in each
    "Доля N" (Beat N) editor card. For example, 6/4 displays six
    checkboxes. Checked beats run at "Рывок, BPM" and unselected beats
    at transport BPM. The same selection is repeated each bar.
- Custom does not force a ×2 multiplier: any allowed alternate BPM
  can be selected, higher or lower than the base tempo.
- Saved sessions and application preferences retain the Burst variant
  and Custom beat mask. Older files continue to default to A–B–A–B.
- Kept the familiar PySide6 layout and Picking Guide / Focus workflow.

How to use Custom Burst
-----------------------
1. Set transport BPM, e.g. 50.
2. Select "Рывки темпа" on the Training tab.
3. Select "Custom" in "Режим рывка".
4. Set "Рывок, BPM", e.g. 100.
5. Check "Рывок" above beats 2 and 4 in a 4/4 Pattern.
6. The callback repeats 50 -> 100 -> 50 -> 100 BPM across beat
   positions within each bar. Other configurations work in 1–16
   numerator meters; 6/4 has six independent selections.
7. To return to the original whole-bar block arrangement, choose
   "A–B–A–B" and configure base/alternate bar counts.

Tempo changes occur exactly at metric-beat boundaries. The complete
subdivision inside each beat follows the selected BPM. The rhythmic
TI/TA/OFF pattern and Mute states are not rewritten. Count-in plays
at the base BPM. Existing Game targets remain on the same PortAudio
sample-clock timeline as the training audio.

Technical changes
-----------------
- Added deterministic phase helpers for all seven Training Modes.
- Retained PortAudio callback/sample-clock scheduling for all audio,
  effective tempo changes and Game target timestamps.
- Added a Custom Burst beat-mask and tempo selector in EngineConfig.
  Selected BPM applies to the full metric beat, including triplet and
  other subdivision grids; covered/muted beats retain their duration.
- Preserved old Burst whole-bar timing, even if Custom flags are saved.
- Extended UI, settings and JSON sessions with backward-compatible
  Burst variant/beat-mask fields; meter resizing keeps overlapping
  beat selections.
- Added deterministic callback regression tests for mixed subdivisions,
  6/4, count-in, Game target identity and legacy Burst behavior, plus
  an optional offscreen Qt smoke command: ./tt burst-smoke.
- Added .gitattributes to pin Unix LF endings for the WSL shell helper,
  avoiding the CRLF shebang error on Windows/WSL checkouts.
- Expanded user-facing Russian/English documentation, technical
  specifications and the manual validation matrix.

Compatibility and intentional limitations
-----------------------------------------
- The original PySide6 interface remains the supported desktop GUI.
  The separate GUI_tkinter branch remains an unmerged experiment and
  is NOT part of this release or a new runtime dependency.
- The existing seven Training Modes, TI/TA/Mute patterns, Picking
  Logic v2, Game, Focus, sound preferences and JSON sessions are kept.
- Existing sessions without Burst Custom fields load into A–B–A–B
  mode with no selected Custom beats.
- MIDI, Guitar Pro 5 and WAV export the SAVED PATTERN at BASE BPM.
  They do not yet render tempo changes from Burst, Wave or Random
  Tempo stages. This release does not add variable-tempo export.
- The output device and PySide6 runtime remain required by the
  supported Windows application; no installer or bundled EXE is
  attached merely by publishing this source release.
- Player-specific picking analysis, ghost-stroke Alternate, MIDI
  controller Game input and calibrated end-to-end input latency are
  not included.

Validation and publication policy
---------------------------------
- The owner reported a green ./tt check (core, Training Modes,
  compile, Picking diagnostics, export, Game logs and imports),
  a green ./tt burst-smoke, and successful live Custom Burst
  playback on Windows on the development candidate (2026-10-23).
- The deterministic tests additionally exercise tempo transitions
  across 4/4 and 6/4, alternating base/alternate BPM, 3/4 mixed
  subdivisions, existing whole-bar Burst, and count-in base BPM.
- Exact release-commit ./tt check and ./tt burst-smoke are the final
  gate before tagging; do not mark them as independently executed
  in the publishing environment without user evidence.
- Release tags must be annotated and contain these complete notes.
  Publication via GitHub Release follows successful tag verification.

References
----------
Russian README: README.md
English README: README.en.md
User guide: docs/USER_GUIDE.md
Technical Training Modes: docs/TRAINING_MODE_DESIGNS.md
Test matrix: docs/TEST_MATRIX.md
Changelog: docs/CHANGELOG.md
Architecture: docs/ARCHITECTURE.md
Repository: https://github.com/TheColdVoid1337/TittyTatter
