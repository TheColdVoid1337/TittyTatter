"""Native Windows smoke for the Tk GUI candidate.

This checks real Tk widget construction without starting an audio stream.
Run through ./tt tk-smoke with .venv-tk on the user's Windows desktop.
"""
from __future__ import annotations

import json
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from model import BarPattern, BeatPattern
from presets import OFF, TA, TI
from training_modes import TRAINING_MODES

import tk_app


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="tt-tk-test-") as directory:
        path = Path(directory) / "test_settings.json"
        with patch.object(tk_app, "SETTINGS", path):
            window = tk_app.TkApp(start_poll=False)
            try:
                window.update_idletasks()
                assert window.engine.is_running is False, "Smoke must never start audio"
                assert len(window.editors) == 4
                assert window.tabs.index("end") == 8
                assert len(TRAINING_MODES) == 14
                assert window.get("mode") == "loop"
                assert window.current_pattern().numerator == 4
                assert all(isinstance(card, tk.Widget) for card in window.editors)

                # Same editable step cycle and grid semantics as the Qt view.
                first = window.editors[0]
                assert first.pattern().steps == [TI, TA, TA, TA]
                first.cycle(0)
                assert first.pattern().steps[0] == TA
                first.cycle(0)
                assert first.pattern().steps[0] == OFF
                first.cycle(0)
                assert first.pattern().steps[0] == TI

                # Meter changes preserve the original beats where possible.
                window.meter_num.set(7)
                window.meter_den.set(8)
                window.change_meter()
                assert len(window.editors) == 7
                assert window.current_pattern().denominator == 8
                assert window.current_pattern().beats[0].steps[0] == TI

                window.set_option("mode", "burst")
                window.on_setting_changed()
                assert window.get("mode") == "burst"
                window.set_option("burst_base_bars", 4)
                window.set_option("burst_fast_bars", 2)
                window.set_option("burst_fast_bpm", 160)
                window.base_bpm.set(80)
                window.sync_engine()
                cfg = window.engine.get_config()
                assert cfg.practice_mode == "burst"
                assert cfg.bpm == 80
                assert cfg.burst_fast_bars == 2
                assert cfg.burst_fast_bpm == 160

                before = window.current_pattern().to_dict()
                session = window.session()
                assert session["pattern"] == before
                assert session["practice"]["mode"] == "burst"
                assert "PySide6" not in str(type(window))
                text = json.dumps(session, ensure_ascii=False)
                window.apply_session(json.loads(text))
                assert window.current_pattern().to_dict() == before
                assert window.get("mode") == "burst"

                # Reading a Qt-compatible session must not require Qt.
                qt_data = {
                    "version": 5,
                    "bpm": 104,
                    "pattern": BarPattern([
                        BeatPattern("triplet", [TI, OFF, TA]),
                        BeatPattern("quad", [TA, TA, TI, OFF]),
                    ], numerator=2, denominator=4).to_dict(),
                    "practice": {"mode": "loop", "count": 0},
                }
                window.apply_session(tk_app.existing_gui_session(qt_data))
                assert window.base_bpm.get() == 104
                assert len(window.editors) == 2
                assert window.editors[0].pattern().steps == [TI, OFF, TA]
                assert window.get("mode") == "loop"

                # Focus is presentation-only; it cannot erase rhythm data.
                snapshot = window.current_pattern().to_dict()
                window.toggle_focus()
                window.update_idletasks()
                assert window.focus.get()
                assert not window.tabs.winfo_manager()
                assert not window.cards.winfo_manager()
                window.toggle_focus()
                window.update_idletasks()
                assert not window.focus.get()
                assert window.tabs.winfo_manager() == "pack"
                assert window.cards.winfo_manager() == "pack"
                assert window.current_pattern().to_dict() == snapshot

                for width, height in ((1240, 860), (970, 820)):
                    window.geometry(f"{width}x{height}")
                    window.update()
                    assert window.winfo_width() == width and window.winfo_height() == height
                    assert window.visual.winfo_width() > 0
                    assert window.cards.winfo_width() > 0
                    assert window.tabs.winfo_height() > 0

                # No PySide6 package is ever loaded by this entrypoint.
                import sys
                assert not any(n == "PySide6" or n.startswith("PySide6.") for n in sys.modules)
                print("Tkinter GUI smoke OK (no PySide6)")
            finally:
                window.close_app()
                window.update_idletasks()


if __name__ == "__main__":
    run()
