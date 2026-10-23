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
            assert state["practice"]["burst_custom_beats"] == [
                False, True, False, True, False, True,
            ]
            assert window._collect_app_settings()["practice"]["burst_custom_beats"] == (
                state["practice"]["burst_custom_beats"]
            )
            window.apply_session(state)
            qt.processEvents()
            assert window.burst_variant.currentData() == "custom"
            assert [e.burst.isChecked() for e in window.editors] == state["practice"]["burst_custom_beats"]
            assert window.current_pattern().beats[1].muted

            # AB uses whole-bar blocks as before and ignores stored Custom flags.
            window._combo_data(window.burst_variant, "ab")
            qt.processEvents()
            assert not any(e.burst.isVisible() for e in window.editors)
            assert window.engine.get_config().burst_variant == "ab"
            assert window.engine.get_config().burst_custom_beats[5]
            window._combo_data(window.burst_variant, "custom")
            qt.processEvents()
            assert window.editors[5].burst.isVisible()
            assert window.editors[5].burst.isChecked()

            # Legacy session with neither new field reopens in original A/B mode.
            old = dict(state)
            old["practice"] = {
                k: v for k, v in state["practice"].items()
                if k not in ("burst_variant", "burst_custom_beats")
            }
            window.apply_session(old)
            assert window.burst_variant.currentData() == "ab"
            assert not any(e.burst.isChecked() for e in window.editors)

            # Reset clears flags, meter and variant, never touching audio.
            window._apply_defaults()
            assert window.burst_variant.currentData() == "ab"
            assert len(window.editors) == 4
            assert not any(e.burst.isChecked() for e in window.editors)
            assert not window.engine.is_running
            print("Custom Burst GUI smoke OK")
        finally:
            window.close()
            qt.processEvents()


if __name__ == "__main__":
    run()
