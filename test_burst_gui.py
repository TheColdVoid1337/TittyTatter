"""Offscreen Qt acceptance gate for the Burst variant and per-beat selectors.

Uses real MainWindow widgets and canonical AudioEngine config without opening a
PortAudio stream. Run with ./tt burst-smoke; live Windows playback remains a
separate human acceptance requirement.
"""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app import MainWindow


def run() -> None:
    qt = QApplication.instance() or QApplication([])
    with patch("app.load_settings", return_value={}), patch("app.save_settings"):
        window = MainWindow()
        try:
            window.show()
            qt.processEvents()
            assert len(window.editors) == 4
            assert not any(editor.burst.isVisible() for editor in window.editors)
            assert window.burst_variant.currentData() == "ab"

            window._combo_data(window.mode, "burst")
            qt.processEvents()
            assert window.burst_variant.isVisible()
            assert not any(editor.burst.isVisible() for editor in window.editors)
            window._combo_data(window.burst_variant, "custom")
            qt.processEvents()
            assert all(editor.burst.isVisible() for editor in window.editors)

            window.editors[1].burst.setChecked(True)
            window.editors[3].burst.setChecked(True)
            window.bpm.setValue(50)
            window.new_training_spins["burst_fast_bpm"].setValue(100)
            assert window.engine.get_config().burst_variant == "custom"
            assert window.engine.get_config().burst_custom_beats == (False, True, False, True)
            assert window.engine.get_config().bpm == 50

            # x2 is on the SAME row as «Рывок, BPM» in both variants.
            spin = window.new_training_spins["burst_fast_bpm"]
            assert window.burst_bpm_field.isVisible()
            assert spin.isEnabled()
            assert not window.burst_x2.isChecked()
            spin.setValue(135)  # distinct manual value must survive toggling
            window.burst_x2.setChecked(True)
            qt.processEvents()
            assert window.burst_x2.isChecked()
            assert window.burst_x2.isVisible()
            assert not spin.isEnabled()
            assert spin.value() == 135
            assert window.engine.get_config().burst_x2
            assert window.engine.get_config().burst_fast_bpm == 135

            # Manual BPM is not changed by x2; transport BPM controls 2x.
            window.bpm.setValue(200)
            assert window.engine.get_config().bpm == 200
            assert window.engine.get_config().burst_x2
            assert window.engine.get_config().burst_fast_bpm == 135
            window.bpm.setValue(50)

            # Switching variants preserves the toggle and disabled spin.
            window._combo_data(window.burst_variant, "ab")
            qt.processEvents()
            assert window.burst_x2.isVisible()
            assert not spin.isEnabled()
            assert window.engine.get_config().burst_x2
            window._combo_data(window.burst_variant, "custom")
            qt.processEvents()
            assert window.burst_x2.isChecked()
            assert not spin.isEnabled()

            # A 6/4 meter has six distinct beat selectors, not four bars.
            window.meter_num.setValue(6)
            qt.processEvents()
            assert len(window.editors) == 6
            assert [editor.burst.isChecked() for editor in window.editors] == [
                False, True, False, True, False, False,
            ]
            assert window.engine.get_config().burst_custom_beats == (
                False, True, False, True, False, False,
            )
            assert all(editor.burst.isVisible() for editor in window.editors)
            window.editors[5].burst.setChecked(True)
            assert window.engine.get_config().burst_custom_beats[-1]

            # Mute is separate from the per-beat tempo choice.
            window.editors[1].mute.setChecked(True)
            assert window.editors[1].burst.isChecked()
            assert window.current_pattern().beats[1].muted

            state = window.session()
            assert state["practice"]["burst_variant"] == "custom"
            assert state["practice"]["burst_x2"] is True
            assert state["practice"]["burst_fast_bpm"] == 135
            assert window._collect_app_settings()["practice"]["burst_x2"] is True
            assert state["practice"]["burst_custom_beats"] == [
                False, True, False, True, False, True,
            ]
            assert window._collect_app_settings()["practice"]["burst_custom_beats"] == (
                state["practice"]["burst_custom_beats"]
            )
            window.apply_session(state)
            qt.processEvents()
            assert window.burst_variant.currentData() == "custom"
            assert window.burst_x2.isChecked()
            assert not spin.isEnabled()
            assert spin.value() == 135
            assert [e.burst.isChecked() for e in window.editors] == state["practice"]["burst_custom_beats"]
            assert window.current_pattern().beats[1].muted

            # AB uses whole-bar blocks as before and ignores stored Custom flags.
            window._combo_data(window.burst_variant, "ab")
            qt.processEvents()
            assert window.burst_x2.isChecked()
            assert not spin.isEnabled()
            assert not any(e.burst.isVisible() for e in window.editors)
            assert window.engine.get_config().burst_variant == "ab"
            assert window.engine.get_config().burst_custom_beats[5]
            window._combo_data(window.burst_variant, "custom")
            qt.processEvents()
            assert window.editors[5].burst.isVisible()
            assert window.editors[5].burst.isChecked()

            # Uncheck x2: previously entered manual BPM returns without editing.
            window.burst_x2.setChecked(False)
            qt.processEvents()
            assert spin.isEnabled() and spin.value() == 135
            assert window.engine.get_config().burst_x2 is False
            window.burst_x2.setChecked(True)

            # Legacy session without new fields defaults to unchecked x2.
            # This does not change the existing manual Burst BPM.
            # Legacy session with neither new field reopens in original A/B mode.
            old = dict(state)
            old["practice"] = {
                k: v for k, v in state["practice"].items()
                if k not in ("burst_variant", "burst_custom_beats", "burst_x2")
            }
            window.apply_session(old)
            assert window.burst_variant.currentData() == "ab"
            assert not window.burst_x2.isChecked()
            assert window.new_training_spins["burst_fast_bpm"].isEnabled() is False
            assert not any(e.burst.isChecked() for e in window.editors)

            # Reset clears flags, meter and variant, never touching audio.
            window._apply_defaults()
            assert window.burst_variant.currentData() == "ab"
            assert not window.burst_x2.isChecked()
            assert len(window.editors) == 4
            assert not any(e.burst.isChecked() for e in window.editors)
            assert not window.engine.is_running
            print("Custom Burst GUI smoke OK")
        finally:
            window.close()
            qt.processEvents()


if __name__ == "__main__":
    run()
