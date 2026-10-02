from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from audio_engine import AudioEngine, SOUND_NAMES
from exports import export_gp5, export_midi, export_wav
from game_logger import GameLogSession
from game_logic import (
    EARLY_HIT_WINDOW_MS,
    HIT_WINDOW_MS,
    INPUT_BUFFER_MAX_MS,
    LATE_HIT_WINDOW_MS,
    choose_target_index,
    grade_timing,
    progress_bar,
)
from model import BarPattern, BeatPattern
from picking_logic import economy_pick_beats
from presets import (
    CORE_PRACTICE_PRESETS,
    OFF,
    TA,
    TI,
    TI_MARK,
    VALID_DENOMINATORS,
    CellPreset,
    grid_label,
    grid_spec,
    grid_specs_for_meter,
    presets_for_grid,
)
from settings_store import SETTINGS_PATH, delete_settings, load_settings, save_settings

APP_NAME = "TittyTatter"
VERSION_FILE = Path(__file__).with_name("VERSION")
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.1"

STATE_TEXT = {TI: TI_MARK, TA: "ТА", OFF: "·"}
STATE_STYLE = {
    TI: "background:#3169c6;color:white;font-weight:700;border:2px solid #72a5ff;border-radius:18px;padding:8px;",
    TA: "background:#42464f;color:white;font-weight:700;border:2px solid #666b75;border-radius:8px;padding:8px;",
    OFF: "background:#22252a;color:#8e949e;border:2px solid #343941;border-radius:8px;padding:8px;",
}

def _mouse_button_binding(button) -> str:
    try:
        value = int(button.value)
    except Exception:
        value = int(button)
    if value <= 0 or value & (value - 1):
        return ""
    # Qt mouse buttons are power-of-two flags: 1, 2, 4, 8, 16...
    # Present them as human-friendly Mouse 1, Mouse 2, Mouse 3...
    return f"mouse:{value.bit_length()}"


def _key_event_binding(event) -> str:
    sequence = QKeySequence(event.keyCombination()).toString().strip().upper()
    return f"key:{sequence}" if sequence else ""


def _binding_display(binding: str) -> str:
    value = str(binding or "").strip()
    if value.lower().startswith("mouse:"):
        try:
            return f"Mouse {int(value.split(':', 1)[1])}"
        except Exception:
            return value
    if value.lower().startswith("key:"):
        return value.split(":", 1)[1]
    return value


class GameBindEdit(QPushButton):
    bindingChanged = Signal(str)

    def __init__(self, binding: str) -> None:
        super().__init__()
        self._binding = ""
        self._capturing = False
        self.clicked.connect(self.begin_capture)
        self.set_binding(binding)

    def binding(self) -> str:
        return self._binding

    def set_binding(self, binding: str) -> None:
        value = str(binding or "").strip()
        # Backward compatibility with 0.0.3 settings that stored plain
        # QKeySequence text such as "F" or "J".
        if value and ":" not in value:
            value = f"key:{value.upper()}"
        elif value.lower().startswith("key:"):
            value = f"key:{value.split(':', 1)[1].upper()}"
        elif value.lower().startswith("mouse:"):
            try:
                value = f"mouse:{max(1, int(value.split(':', 1)[1]))}"
            except Exception:
                value = ""

        self._binding = value
        self._capturing = False
        self.setText(_binding_display(value) if value else "Не назначено")
        self.bindingChanged.emit(self._binding)

    def begin_capture(self) -> None:
        if not self.isEnabled():
            return
        self._capturing = True
        self.setText("Нажмите клавишу / кнопку мыши…")
        self.setFocus(Qt.OtherFocusReason)

    def keyPressEvent(self, event) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Escape:
            self._capturing = False
            self.setText(_binding_display(self._binding) if self._binding else "Не назначено")
            event.accept()
            return

        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.set_binding("")
            event.accept()
            return

        binding = _key_event_binding(event)
        if binding:
            self.set_binding(binding)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._capturing:
            binding = _mouse_button_binding(event.button())
            if binding:
                self.set_binding(binding)
                event.accept()
                return
        super().mousePressEvent(event)


class StepButton(QPushButton):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.state = OFF
        self.display_override: str | None = None
        self.playing = False
        self.setMinimumWidth(42)
        self.setMinimumHeight(42)
        self.clicked.connect(self.cycle)
        self.refresh()

    def cycle(self) -> None:
        order = (TI, TA, OFF)
        self.set_state(order[(order.index(self.state) + 1) % len(order)])
        self.changed.emit()

    def set_state(self, state: str) -> None:
        self.state = state if state in (TI, TA, OFF) else OFF
        self.refresh()

    def set_playing(self, value: bool) -> None:
        self.playing = bool(value)
        self.refresh()

    def set_display_override(self, state: str | None) -> None:
        self.display_override = state if state in (TI, TA, OFF) else None
        self.refresh()

    def refresh(self) -> None:
        shown = self.display_override or self.state
        extra = "border:3px solid #ffd56a;" if self.playing else ""
        self.setText(STATE_TEXT[shown])
        self.setStyleSheet(f"QPushButton{{{STATE_STYLE[shown]}{extra}}}")


class MetronomeVisual(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.phase = 0.0
        self.beat = 0
        self.sub = 0
        self.active_beats = 4
        self.numerator = 4
        self.denominator = 4
        self.count_in = False
        self.running = False
        self.timer_text = ""

        self.scale_percent = 100
        self.needle_color = QColor("#e8ebf0")
        self.flash_color = QColor("#ffd56a")
        self.flash_enabled = True
        self.flash_whole_panel = False
        self.flash_brightness = 100
        self.needle_width = 4
        self.show_beat_lamps = True
        self.swing_angle = 42

        self.game_visible = False
        self.game_hits = 0
        self.game_misses = 0
        self.game_score = 0
        self.game_recent: list[float] = []
        self.game_feedback_kind = ""
        self.game_feedback_main = ""
        self.game_feedback_detail = ""
        self.game_feedback_until = 0.0

        self.ramp_warning_text = ""
        self.ramp_warning_until = 0.0

        self.picking_visible = False
        self.picking_row_5: list[list[str]] = []
        self.picking_row_6: list[list[str]] = []
        self.picking_show_next = True
        self.picking_highlight_current = True
        self.picking_cue_size = 52

        self._apply_height()

    def _apply_height(self) -> None:
        height = max(84, int(125 * self.scale_percent / 100))
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)

    def configure(
        self,
        *,
        scale_percent: int | None = None,
        needle_color: QColor | None = None,
        flash_color: QColor | None = None,
        flash_enabled: bool | None = None,
        flash_whole_panel: bool | None = None,
        flash_brightness: int | None = None,
        needle_width: int | None = None,
        show_beat_lamps: bool | None = None,
        swing_angle: int | None = None,
    ) -> None:
        if scale_percent is not None:
            self.scale_percent = max(60, min(200, int(scale_percent)))
            self._apply_height()
        if needle_color is not None and needle_color.isValid():
            self.needle_color = QColor(needle_color)
        if flash_color is not None and flash_color.isValid():
            self.flash_color = QColor(flash_color)
        if flash_enabled is not None:
            self.flash_enabled = bool(flash_enabled)
        if flash_whole_panel is not None:
            self.flash_whole_panel = bool(flash_whole_panel)
        if flash_brightness is not None:
            self.flash_brightness = max(0, min(200, int(flash_brightness)))
        if needle_width is not None:
            self.needle_width = max(1, min(12, int(needle_width)))
        if show_beat_lamps is not None:
            self.show_beat_lamps = bool(show_beat_lamps)
        if swing_angle is not None:
            self.swing_angle = max(15, min(70, int(swing_angle)))
        self.update()

    def set_state(
        self,
        *,
        phase: float,
        beat: int,
        sub: int = 0,
        active_beats: int,
        numerator: int,
        denominator: int,
        count_in: bool,
        running: bool,
        timer_text: str = "",
    ) -> None:
        self.phase = max(0.0, min(0.999, float(phase)))
        self.numerator = max(1, int(numerator))
        self.denominator = int(denominator)
        self.beat = max(0, min(self.numerator - 1, int(beat)))
        self.sub = max(0, int(sub))
        self.active_beats = max(0, min(self.numerator, int(active_beats)))
        self.count_in = bool(count_in)
        self.running = bool(running)
        self.timer_text = str(timer_text)
        self.update()

    def set_game_stats(
        self,
        visible: bool,
        hits: int,
        misses: int,
        recent: list[float],
        score: int = 0,
    ) -> None:
        self.game_visible = bool(visible)
        self.game_hits = int(hits)
        self.game_misses = int(misses)
        self.game_score = int(score)
        self.game_recent = [max(0.0, min(1.0, float(x))) for x in recent[-28:]]
        if not self.game_visible:
            self.clear_game_feedback()
        self.update()

    def set_game_feedback(self, kind: str, main: str, detail: str) -> None:
        if not self.game_visible:
            return
        self.game_feedback_kind = str(kind)
        self.game_feedback_main = str(main)
        self.game_feedback_detail = str(detail)
        self.game_feedback_until = time.perf_counter() + 0.22
        self.update()
        QTimer.singleShot(240, self.update)

    def clear_game_feedback(self) -> None:
        self.game_feedback_kind = ""
        self.game_feedback_main = ""
        self.game_feedback_detail = ""
        self.game_feedback_until = 0.0
        self.update()

    def trigger_ramp_warning(self, current_active_beats: int, next_active_beats: int) -> None:
        current = int(current_active_beats)
        next_value = int(next_active_beats)
        arrow = "↑" if next_value > current else "↓"
        unit = "ДОЛЯ" if next_value == 1 else "ДОЛИ"
        self.ramp_warning_text = f"{arrow} СЛЕДУЮЩИЙ УРОВЕНЬ: {next_value} {unit}"
        self.ramp_warning_until = time.perf_counter() + 0.65
        self.update()
        QTimer.singleShot(700, self.update)

    def set_picking_pattern(
        self,
        visible: bool,
        row_5: list[list[str]] | None = None,
        row_6: list[list[str]] | None = None,
    ) -> None:
        self.picking_visible = bool(visible)
        self.picking_row_5 = [list(beat) for beat in (row_5 or [])]
        self.picking_row_6 = [list(beat) for beat in (row_6 or [])]
        self.update()

    def configure_picking(
        self,
        *,
        show_next: bool | None = None,
        highlight_current: bool | None = None,
        cue_size: int | None = None,
    ) -> None:
        if show_next is not None:
            self.picking_show_next = bool(show_next)
        if highlight_current is not None:
            self.picking_highlight_current = bool(highlight_current)
        if cue_size is not None:
            self.picking_cue_size = max(36, min(96, int(cue_size)))
        self.update()

    def _picking_token_at(self, beat: int, sub: int) -> tuple[str, int] | None:
        if beat < 0:
            return None
        for string_number, rows in ((5, self.picking_row_5), (6, self.picking_row_6)):
            if beat >= len(rows):
                continue
            row = rows[beat]
            if sub < 0 or sub >= len(row):
                continue
            token = row[sub]
            if token in ("↑", "↓"):
                return token, string_number
        return None

    def _next_picking_token(self) -> tuple[str, int] | None:
        beat_count = max(len(self.picking_row_5), len(self.picking_row_6))
        if beat_count <= 0:
            return None

        slots: list[tuple[int, int]] = []
        for beat_index in range(beat_count):
            len5 = len(self.picking_row_5[beat_index]) if beat_index < len(self.picking_row_5) else 0
            len6 = len(self.picking_row_6[beat_index]) if beat_index < len(self.picking_row_6) else 0
            for sub_index in range(max(len5, len6, 1)):
                slots.append((beat_index, sub_index))

        if not slots:
            return None

        try:
            current_index = slots.index((self.beat, self.sub))
        except ValueError:
            current_index = -1

        for offset in range(1, len(slots) + 1):
            beat_index, sub_index = slots[(current_index + offset) % len(slots)]
            token = self._picking_token_at(beat_index, sub_index)
            if token is not None:
                return token
        return None

    def _paint_picking_cue(self, painter: QPainter) -> None:
        if not self.picking_visible:
            return

        painter.save()
        panel_w = min(250, max(175, self.width() // 4))
        left = self.width() - panel_w - 12
        top = 28
        bottom = self.height() - 10
        rect = QRectF(left, top, panel_w, max(52, bottom - top))

        painter.setPen(QColor(165, 172, 182))
        label_font = self.font()
        label_font.setBold(True)
        label_font.setPointSize(8)
        painter.setFont(label_font)
        painter.drawText(rect.adjusted(0, 0, 0, -rect.height() + 18), Qt.AlignHCenter, "ТЕКУЩИЙ ШТРИХ")

        if self.count_in and self.running:
            painter.setPen(QColor(125, 132, 143))
            painter.drawText(rect, Qt.AlignCenter, "COUNT-IN")
            painter.restore()
            return

        reserved_bottom = 22.0 if self.picking_show_next else 4.0
        cue_rect = rect.adjusted(0, 18, 0, -reserved_bottom)

        current = self._picking_token_at(self.beat, self.sub)
        if current is None:
            painter.setPen(QColor(125, 132, 143))
            rest_font = self.font()
            rest_font.setBold(True)
            rest_font.setPixelSize(max(20, min(36, int(cue_rect.height() * 0.75))))
            painter.setFont(rest_font)
            painter.drawText(cue_rect, Qt.AlignCenter, "·")
        else:
            direction, string_number = current
            color = QColor(75, 220, 115) if direction == "↑" else QColor(235, 80, 80)
            cue_font = self.font()
            cue_font.setBold(True)
            cue_font.setPixelSize(
                max(24, min(self.picking_cue_size, int(cue_rect.height() * 0.92)))
            )
            painter.setFont(cue_font)
            painter.setPen(color)
            painter.drawText(cue_rect.adjusted(-12, 0, -12, 0), Qt.AlignCenter, direction)

            string_font = self.font()
            string_font.setBold(True)
            string_font.setPixelSize(12)
            painter.setFont(string_font)
            painter.setPen(QColor(205, 211, 220))
            painter.drawText(cue_rect.adjusted(panel_w * 0.60, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, f"{string_number}")

        if self.picking_show_next:
            nxt = self._next_picking_token()
            if nxt is not None:
                next_direction, next_string = nxt
                color = QColor(75, 220, 115) if next_direction == "↑" else QColor(235, 80, 80)
                next_font = self.font()
                next_font.setBold(True)
                next_font.setPixelSize(13)
                painter.setFont(next_font)
                painter.setPen(QColor(155, 162, 172))
                painter.drawText(
                    rect.adjusted(0, rect.height() - 20, -panel_w * 0.56, 0),
                    Qt.AlignLeft | Qt.AlignBottom,
                    "ДАЛЕЕ",
                )
                painter.setPen(color)
                painter.drawText(
                    rect.adjusted(panel_w * 0.45, rect.height() - 21, 0, 0),
                    Qt.AlignLeft | Qt.AlignBottom,
                    f"{next_direction}  {next_string}",
                )

        painter.restore()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        pivot_y = h - (25 if self.show_beat_lamps else 14)
        length = min(0.66 * h, h - 36.0)
        painter.fillRect(self.rect(), QColor(28, 31, 36))

        beat_flash = 0.0
        if self.running and self.phase < 0.18 and (self.flash_enabled or self.flash_whole_panel):
            beat_flash = (1.0 - self.phase / 0.18) * (self.flash_brightness / 100.0)

        if self.flash_whole_panel and beat_flash > 0:
            whole = QColor(self.flash_color)
            whole.setAlpha(max(0, min(180, int(72 * beat_flash))))
            painter.fillRect(self.rect(), whole)

        if self.game_visible and time.perf_counter() < self.game_feedback_until:
            if self.game_feedback_kind == "hit":
                result_color = QColor(40, 205, 95, 112)
            else:
                result_color = QColor(225, 55, 55, 118)
            painter.fillRect(self.rect(), result_color)

        if time.perf_counter() < self.ramp_warning_until:
            warning = QColor(242, 172, 45, 82)
            painter.fillRect(self.rect(), warning)
            painter.setPen(QPen(QColor(255, 205, 90), 3))
            painter.drawRect(self.rect().adjusted(2, 2, -3, -3))

        if self.running:
            direction = 1.0 if self.beat % 2 == 0 else -1.0
            sweep = (-1.0 + 2.0 * self.phase) * direction
        else:
            sweep = 0.0

        angle = math.radians(float(self.swing_angle) * sweep)
        tip_x = cx + math.sin(angle) * length
        tip_y = pivot_y - math.cos(angle) * length

        if self.flash_enabled:
            radius = max(18, int(26 * self.scale_percent / 100))
            flash_color = QColor(self.flash_color)
            flash_color.setAlpha(max(12, min(240, int(24 + 150 * beat_flash))))
            painter.setPen(Qt.NoPen)
            painter.setBrush(flash_color)
            painter.drawEllipse(int(cx - radius), 6, radius * 2, radius * 2)

        painter.setPen(QPen(self.needle_color, self.needle_width, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(cx), int(pivot_y), int(tip_x), int(tip_y))
        painter.setBrush(self.needle_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - 6), int(pivot_y - 6), 12, 12)

        if self.show_beat_lamps:
            count = max(1, self.numerator)
            usable = max(80.0, w - 120.0)
            gap = 0.0 if count == 1 else min(34.0, usable / (count - 1))
            start_x = cx - gap * (count - 1) / 2
            lamp_y = h - 12
            radius = 5 if count > 8 else 6
            for i in range(count):
                x = start_x + i * gap
                if not self.count_in and i >= self.active_beats:
                    color = QColor(80, 84, 90)
                elif self.running and i == self.beat:
                    color = QColor(self.needle_color)
                else:
                    color = QColor(155, 162, 172)
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(x - radius), int(lamp_y - radius), radius * 2, radius * 2)

        painter.setPen(QColor(175, 181, 190))
        painter.drawText(12, 23, "COUNT-IN" if self.count_in and self.running else f"{self.numerator}/{self.denominator}")

        if self.timer_text:
            painter.setPen(QColor(235, 238, 244))
            painter.drawText(self.rect().adjusted(0, 5, -14, 0), Qt.AlignRight | Qt.AlignTop, self.timer_text)

        if self.picking_visible:
            self._paint_picking_pattern(painter)
            self._paint_picking_cue(painter)

        if self.game_visible:
            self._paint_game_panels(painter)

        if time.perf_counter() < self.ramp_warning_until:
            painter.setPen(QColor(255, 220, 125))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect().adjusted(0, 8, 0, 0), Qt.AlignHCenter | Qt.AlignTop, self.ramp_warning_text)
            font.setBold(False)
            painter.setFont(font)

    def _paint_picking_pattern(self, painter: QPainter) -> None:
        if not self.picking_row_5 and not self.picking_row_6:
            return

        # Keep picking typography isolated from other overlays (especially the
        # Game panels). Game visibility must never change the picking font.
        painter.save()

        # Picking is an overlay inside the left side of the metronome. It must
        # never participate in layout/geometry, so enabling it cannot move UI.
        panel_left = 12.0
        panel_right = max(panel_left + 120.0, self.width() / 2.0 - 26.0)
        panel_width = max(120.0, panel_right - panel_left)
        y5 = max(58.0, self.height() - 54.0)
        y6 = y5 + 20.0

        font = self.font()
        font.setBold(True)
        font.setFamily("Consolas")

        total_cells = max(
            1,
            sum(max(1, len(beat)) for beat in self.picking_row_5),
        )
        boundaries = max(0, len(self.picking_row_5) - 1)
        label_width = 18.0
        boundary_width = 5.0
        usable = max(
            70.0,
            panel_width - label_width - boundaries * boundary_width,
        )
        cell_width = max(6.0, min(14.0, usable / total_cells))
        font.setPointSize(max(7, min(10, int(cell_width * 0.82))))
        painter.setFont(font)

        painter.setPen(QColor(225, 230, 238))
        painter.drawText(QRectF(panel_left, y5 - 13, label_width, 18), Qt.AlignCenter, "5")
        painter.drawText(QRectF(panel_left, y6 - 13, label_width, 18), Qt.AlignCenter, "6")

        x = panel_left + label_width

        def draw_cell(token: str, cx: float, cy: float) -> None:
            if token == "↑":
                color = QColor(75, 220, 115)
            elif token == "↓":
                color = QColor(235, 80, 80)
            else:
                color = QColor(125, 132, 143)
            painter.setPen(color)
            painter.drawText(
                QRectF(cx, cy - 13, cell_width, 18),
                Qt.AlignCenter,
                token,
            )

        beat_count = max(len(self.picking_row_5), len(self.picking_row_6))
        for beat_index in range(beat_count):
            beat5 = self.picking_row_5[beat_index] if beat_index < len(self.picking_row_5) else []
            beat6 = self.picking_row_6[beat_index] if beat_index < len(self.picking_row_6) else []
            cells = max(1, len(beat5), len(beat6))
            beat_start_x = x

            if (
                self.picking_highlight_current
                and self.running
                and not self.count_in
                and beat_index == self.beat
            ):
                beat_width = cells * cell_width
                highlight = QColor(255, 255, 255, 18)
                painter.fillRect(
                    QRectF(beat_start_x, y5 - 14, beat_width, (y6 - y5) + 20),
                    highlight,
                )
                painter.setPen(QPen(QColor(210, 216, 225, 80), 1))
                painter.drawRect(
                    QRectF(beat_start_x, y5 - 14, beat_width, (y6 - y5) + 20)
                )

            for cell_index in range(cells):
                token5 = beat5[cell_index] if cell_index < len(beat5) else " "
                token6 = beat6[cell_index] if cell_index < len(beat6) else " "
                draw_cell(token5, x, y5)
                draw_cell(token6, x, y6)
                x += cell_width

            if beat_index < beat_count - 1:
                # One physical separator line spans both strings, so beat
                # boundaries can never drift between row 5 and row 6.
                painter.setPen(QPen(QColor(105, 112, 122), 1))
                sep_x = x + boundary_width / 2.0
                painter.drawLine(
                    int(sep_x),
                    int(y5 - 11),
                    int(sep_x),
                    int(y6 + 4),
                )
                x += boundary_width

        painter.restore()

    def _paint_game_panels(self, painter: QPainter) -> None:
        top = 38

        if self.game_feedback_main:
            if self.game_feedback_kind == "hit":
                color = QColor(95, 235, 135)
            else:
                color = QColor(245, 95, 95)
            painter.setPen(color)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(14, top + 16, self.game_feedback_main)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor(210, 215, 224))
            painter.drawText(14, top + 36, self.game_feedback_detail)

        panel_w = min(250, max(175, self.width() // 4))
        left = self.width() - panel_w - 12
        bottom = self.height() - 28
        graph_top = top + 10
        graph_h = max(22, bottom - graph_top)

        painter.setPen(QColor(185, 191, 200))
        total = self.game_hits + self.game_misses
        accuracy = 100.0 * self.game_hits / total if total else 0.0
        painter.drawText(
            left,
            top,
            f"GAME  {self.game_score} pts  hit {self.game_hits}  miss {self.game_misses}  {accuracy:.0f}%",
        )

        recent = self.game_recent[-28:]
        if not recent:
            return

        bar_w = max(3, min(7, (panel_w - 4) // max(1, len(recent))))
        x = left
        for quality in recent:
            q = max(0.0, min(1.0, quality))
            red = int(225 * (1.0 - q) + 35)
            green = int(65 + 185 * q)
            color = QColor(min(255, red), min(255, green), 70)
            bar_h = max(3, int(graph_h * q))
            painter.fillRect(x, bottom - bar_h, max(2, bar_w - 1), bar_h, color)
            x += bar_w


class BeatEditor(QGroupBox):
    changed = Signal()

    def __init__(self, number: int, numerator: int, denominator: int) -> None:
        super().__init__()
        self.beat_index = number - 1
        self.numerator = int(numerator)
        self.denominator = int(denominator)
        self._span_covered = False
        self._ramp_inactive = False
        self._mute_allowed = True
        self.setMinimumWidth(235)

        outer = QVBoxLayout(self)

        header = QHBoxLayout()
        self.title = QLabel(f"Доля {number}")
        self.title.setStyleSheet("font-weight:700;font-size:14px;")
        header.addWidget(self.title)
        header.addStretch()

        self.mute = QToolButton()
        self.mute.setText("Mute")
        self.mute.setCheckable(True)
        self.mute.setToolTip("Сделать эту долю полностью тихой")
        self.mute.setStyleSheet(
            "QToolButton{padding:3px 9px;border:1px solid #555b66;border-radius:9px;color:#b8bec8;}"
            "QToolButton:checked{background:#8e3f3f;border-color:#ef7777;color:white;font-weight:700;}"
            "QToolButton:disabled{color:#686d75;border-color:#3b3f46;background:#292c31;}"
        )
        self.mute.toggled.connect(self._mute_toggled)
        header.addWidget(self.mute)
        outer.addLayout(header)

        self.body = QWidget()
        self.body_opacity = QGraphicsOpacityEffect(self.body)
        self.body.setGraphicsEffect(self.body_opacity)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        grid_row = QHBoxLayout()
        grid_row.addWidget(QLabel("Сетка:"))
        self.grid = QComboBox()
        grid_row.addWidget(self.grid, 1)
        body_layout.addLayout(grid_row)

        self.preset = QComboBox()
        self.preset.setToolTip("Выбор рисунка применяется сразу")
        body_layout.addWidget(self.preset)

        self.steps_row = QHBoxLayout()
        self.steps = [StepButton() for _ in range(8)]
        for button in self.steps:
            button.changed.connect(self.changed.emit)
            self.steps_row.addWidget(button)
        body_layout.addLayout(self.steps_row)
        outer.addWidget(self.body)

        self._populate_grid()
        self.grid.currentIndexChanged.connect(self._grid_changed)
        self.preset.activated.connect(self._preset_activated)
        self.set_pattern(BeatPattern())

    def _populate_grid(self, preferred: str | None = None) -> None:
        self.grid.blockSignals(True)
        self.grid.clear()
        remaining = self.numerator - self.beat_index
        for spec in grid_specs_for_meter(self.numerator, self.denominator):
            if spec.span_beats <= remaining:
                self.grid.addItem(grid_label(spec.key, self.denominator), spec.key)
        index = self.grid.findData(preferred) if preferred else -1
        if index < 0:
            index = self.grid.findData("quad")
        if index < 0:
            index = self.grid.findData("beat")
        self.grid.setCurrentIndex(max(0, index))
        self.grid.blockSignals(False)

    def _reload_presets(self) -> None:
        self.preset.blockSignals(True)
        self.preset.clear()
        presets = presets_for_grid(str(self.grid.currentData()))
        if not presets:
            self.preset.addItem("Ручная сетка", None)
            self.preset.setEnabled(False)
        else:
            self.preset.setEnabled(True)
            for preset in presets:
                self.preset.addItem(preset.human, preset)
            self.preset.setCurrentIndex(-1)
        self.preset.blockSignals(False)

    def _grid_changed(self) -> None:
        spec = grid_spec(str(self.grid.currentData()))
        self._reload_presets()
        for i, button in enumerate(self.steps):
            button.setVisible(i < spec.steps)
            if i >= spec.steps:
                button.set_state(OFF)
        self.changed.emit()

    def _preset_activated(self, index: int) -> None:
        preset = self.preset.itemData(index)
        if isinstance(preset, CellPreset):
            self.set_pattern(BeatPattern(preset.grid, list(preset.steps), self.mute.isChecked()))
            self.changed.emit()

    def _mute_toggled(self, _checked: bool) -> None:
        self._refresh_visual_state()
        self.changed.emit()

    def pattern(self) -> BeatPattern:
        key = str(self.grid.currentData())
        spec = grid_spec(key)
        return BeatPattern(key, [button.state for button in self.steps[: spec.steps]], self.mute.isChecked())

    def set_pattern(self, pattern: BeatPattern) -> None:
        pattern.normalize()
        self._populate_grid(pattern.grid)
        if self.grid.findData(pattern.grid) < 0:
            pattern = BeatPattern("beat", pattern.steps[:1] or [OFF], pattern.muted)
            pattern.normalize()
            self._populate_grid("beat")

        self._reload_presets()
        self.mute.blockSignals(True)
        self.mute.setChecked(pattern.muted)
        self.mute.blockSignals(False)

        spec = grid_spec(str(self.grid.currentData()))
        for i, button in enumerate(self.steps):
            button.setVisible(i < spec.steps)
            button.set_state(pattern.steps[i] if i < len(pattern.steps) and i < spec.steps else OFF)

        for i in range(self.preset.count()):
            preset = self.preset.itemData(i)
            if isinstance(preset, CellPreset) and preset.steps == tuple(pattern.steps):
                self.preset.setCurrentIndex(i)
                break
        self._refresh_visual_state()

    def playhead(self, sub: int | None) -> None:
        spec = grid_spec(str(self.grid.currentData()))
        for i, button in enumerate(self.steps):
            button.set_playing(sub is not None and i == sub and i < spec.steps)

    def set_span_covered(self, value: bool) -> None:
        self._span_covered = bool(value)
        self.body.setEnabled(not self._span_covered and not self._ramp_inactive)
        self._refresh_mute_enabled()
        self._refresh_visual_state()

    def set_ramp_inactive(self, value: bool) -> None:
        self._ramp_inactive = bool(value)
        self.body.setEnabled(not self._span_covered and not self._ramp_inactive)
        spec = grid_spec(str(self.grid.currentData()))
        for i, button in enumerate(self.steps):
            if i >= spec.steps:
                continue
            if self._ramp_inactive:
                button.set_display_override(TA if i == 0 else OFF)
            else:
                button.set_display_override(None)
        self._refresh_visual_state()

    def set_mute_allowed(self, allowed: bool) -> None:
        self._mute_allowed = bool(allowed)
        if not allowed and self.mute.isChecked():
            self.mute.setChecked(False)
        self._refresh_mute_enabled()

    def _refresh_mute_enabled(self) -> None:
        self.mute.setEnabled(self._mute_allowed and not self._span_covered)
        if not self._mute_allowed:
            self.mute.setToolTip("Mute недоступен в режиме разгона")
        elif self._span_covered:
            self.mute.setToolTip("Доля перекрыта длинной нотой")
        else:
            self.mute.setToolTip("Сделать эту долю полностью тихой")

    def _refresh_visual_state(self) -> None:
        if self._span_covered:
            opacity = 0.18
        elif self._ramp_inactive or self.mute.isChecked():
            opacity = 0.30
        else:
            opacity = 1.0
        self.body_opacity.setOpacity(opacity)


class PatternExportDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.repeats = QSpinBox()
        self.repeats.setRange(1, 999)
        self.repeats.setValue(4)
        form.addRow("Повторов такта:", self.repeats)

        self.labels = QCheckBox("Добавить подписи")
        self.labels.setChecked(True)
        form.addRow("", self.labels)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, bool]:
        return self.repeats.value(), self.labels.isChecked()


class AudioExportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Экспорт WAV")
        layout = QVBoxLayout(self)
        form = QFormLayout()

        duration_row = QWidget()
        duration_layout = QHBoxLayout(duration_row)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        self.minutes = QSpinBox()
        self.minutes.setRange(0, 180)
        self.minutes.setValue(5)
        self.minutes.setSuffix(" мин")
        self.seconds = QSpinBox()
        self.seconds.setRange(0, 59)
        self.seconds.setSuffix(" сек")
        duration_layout.addWidget(self.minutes)
        duration_layout.addWidget(self.seconds)
        form.addRow("Длительность:", duration_row)

        self.quality = QComboBox()
        self.quality.addItem("44.1 kHz / 16-bit", (44_100, 16))
        self.quality.addItem("48 kHz / 24-bit", (48_000, 24))
        self.quality.addItem("96 kHz / 24-bit", (96_000, 24))
        self.quality.addItem("96 kHz / 32-bit PCM", (96_000, 32))
        self.quality.setCurrentIndex(1)
        form.addRow("Качество:", self.quality)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, int, int]:
        duration = self.minutes.value() * 60 + self.seconds.value()
        sample_rate, bits = self.quality.currentData()
        return duration, int(sample_rate), int(bits)


class MainWindow(QMainWindow):
    def __init__(self, game_log_enabled: bool = False) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1240, 860)

        self.engine = AudioEngine()
        self.tap_times: list[float] = []
        self.metro_color = QColor("#e8ebf0")
        self.flash_color = QColor("#ffd56a")
        self.editors: list[BeatEditor] = []
        self._settings = load_settings()
        self.game_log_enabled = bool(game_log_enabled)
        self.game_log: GameLogSession | None = None
        self._game_log_last_position: tuple | None = None

        self.game_active = False
        self.game_stats_visible = False
        self.game_hits = 0
        self.game_misses = 0
        self.game_score = 0
        self.game_recent: list[float] = []
        self.game_offsets_ms: list[float] = []
        self.game_calibration_samples_ms: list[float] = []
        self.game_timing_bias_ms = 0.0
        self._last_ramp_warning_key: tuple[int, int] | None = None
        self.game_pending: list[dict[str, object]] = []
        self.game_pending_inputs: list[dict[str, object]] = []
        self.last_game_stats = {
            "hits": 0,
            "misses": 0,
            "accuracy": 0.0,
            "mean_abs_ms": 0.0,
            "early": 0,
            "late": 0,
            "score": 0,
        }

        self._build_ui()
        self._shortcuts()
        QApplication.instance().installEventFilter(self)
        self._restore_app_settings()
        self._sync()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(16)

    def _build_ui(self) -> None:
        root = QWidget()
        out = QVBoxLayout(root)

        transport = QHBoxLayout()
        self.play = QPushButton("▶ Старт")
        self.play.clicked.connect(self.toggle)
        transport.addWidget(self.play)
        transport.addWidget(QLabel("BPM"))

        self.bpm = QSpinBox()
        self.bpm.setRange(20, 320)
        self.bpm.setValue(60)
        transport.addWidget(self.bpm)

        self.bpm_slider = QSlider(Qt.Horizontal)
        self.bpm_slider.setRange(20, 320)
        self.bpm_slider.setValue(60)
        transport.addWidget(self.bpm_slider, 1)

        for delta in (-5, -1, 1, 5):
            button = QPushButton(f"{delta:+d}")
            button.clicked.connect(lambda _=False, d=delta: self.bpm.setValue(self.bpm.value() + d))
            transport.addWidget(button)

        self.tap = QPushButton("TAP [T]")
        self.tap.clicked.connect(self.tap_tempo)
        transport.addWidget(self.tap)

        transport.addWidget(QLabel("Размер"))
        self.meter_num = QSpinBox()
        self.meter_num.setRange(1, 16)
        self.meter_num.setValue(4)
        self.meter_num.setFixedWidth(58)
        transport.addWidget(self.meter_num)
        transport.addWidget(QLabel("/"))
        self.meter_den = QComboBox()
        for value in VALID_DENOMINATORS:
            self.meter_den.addItem(str(value), value)
        self.meter_den.setCurrentIndex(self.meter_den.findData(4))
        self.meter_den.setFixedWidth(62)
        transport.addWidget(self.meter_den)
        out.addLayout(transport)

        self.visual = MetronomeVisual()
        out.addWidget(self.visual)

        self.status = QLabel("Готов")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:16px;font-weight:700;padding:5px")
        out.addWidget(self.status)

        self.beats_group = QGroupBox()
        beats_outer = QVBoxLayout(self.beats_group)
        self.beat_scroll = QScrollArea()
        self.beat_scroll.setWidgetResizable(True)
        self.beat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.beat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.beats_container = QWidget()
        self.beats_layout = QHBoxLayout(self.beats_container)
        self.beats_layout.setContentsMargins(2, 2, 2, 2)
        self.beat_scroll.setWidget(self.beats_container)
        beats_outer.addWidget(self.beat_scroll)
        out.addWidget(self.beats_group)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_practice_tab(), "Тренировка")
        self.tabs.addTab(self._build_sound_tab(), "Звук")
        self.tabs.addTab(self._build_metronome_tab(), "Метроном")
        self.tabs.addTab(self._build_game_tab(), "Игра")
        self.tabs.addTab(self._build_picking_tab(), "Picking")
        self.tabs.addTab(self._build_audio_tab(), "Аудио")
        self.tabs.addTab(self._build_export_tab(), "Экспорт")
        out.addWidget(self.tabs)

        footer = QHBoxLayout()
        save = QPushButton("Сохранить сессию")
        load = QPushButton("Загрузить сессию")
        reset = QPushButton("Сброс сессии")
        save.clicked.connect(self.save_session)
        load.clicked.connect(self.load_session)
        reset.clicked.connect(self.reset_session)
        footer.addWidget(save)
        footer.addWidget(load)
        footer.addWidget(reset)
        footer.addStretch()
        out.addLayout(footer)

        self.setCentralWidget(root)

        self._rebuild_editors()

        self.bpm.valueChanged.connect(self._bpm_from_spin)
        self.bpm_slider.valueChanged.connect(self._bpm_from_slider)
        self.meter_num.valueChanged.connect(self._meter_changed)
        self.meter_den.currentIndexChanged.connect(self._meter_changed)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.tempo_train.toggled.connect(self._refresh_dependent_controls)
        self.practice_timer.toggled.connect(self._refresh_dependent_controls)
        self.ramp_warning.toggled.connect(self._refresh_dependent_controls)
        self.ti_on.toggled.connect(self._refresh_dependent_controls)
        self.ta_on.toggled.connect(self._refresh_dependent_controls)
        self.metro_on.toggled.connect(self._refresh_dependent_controls)

        self.ti_sound.currentTextChanged.connect(lambda _text: self._ensure_unique_sound("ti"))
        self.ta_sound.currentTextChanged.connect(lambda _text: self._ensure_unique_sound("ta"))

        for widget in (
            self.mode,
            self.bars,
            self.count,
            self.inactive,
            self.tempo_train,
            self.tempo_step,
            self.tempo_every,
            self.tempo_target,
            self.ti_on,
            self.ti_sound,
            self.ti_vol,
            self.ta_on,
            self.ta_sound,
            self.ta_vol,
            self.metro_on,
            self.accent,
            self.metro_vol,
            self.master,
        ):
            signal = (
                getattr(widget, "valueChanged", None)
                or getattr(widget, "toggled", None)
                or getattr(widget, "currentIndexChanged", None)
            )
            if signal:
                signal.connect(self._config_changed)

    def _build_practice_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        main = QGroupBox("Режим")
        form = QFormLayout(main)
        self.mode = QComboBox()
        self.mode.addItem("Петля", "loop")
        self.mode.addItem("Разгон по долям", "ramp_1_4")
        self.mode.addItem("Разгон 2 → полный такт", "ramp_2_4")
        form.addRow("Режим:", self.mode)

        self.bars = QSpinBox()
        self.bars.setRange(1, 64)
        self.bars.setValue(8)
        form.addRow("Тактов/этап:", self.bars)

        self.count = QSpinBox()
        self.count.setRange(0, 8)
        self.count.setValue(1)
        form.addRow("Count-in:", self.count)

        self.inactive = QCheckBox("ТА-пульс на пустых долях разгона")
        self.inactive.setChecked(True)
        form.addRow("", self.inactive)

        self.ramp_warning = QCheckBox("Предупреждать перед следующим уровнем")
        self.ramp_warning.setChecked(True)
        form.addRow("", self.ramp_warning)

        random_button = QPushButton("🎲 Случайный такт")
        random_button.clicked.connect(self.randomize_beats)
        form.addRow("", random_button)
        root.addWidget(main, 1)

        trainer = QGroupBox("Разгон темпа")
        form = QFormLayout(trainer)
        self.tempo_train = QCheckBox("Включить")
        form.addRow("", self.tempo_train)

        self.tempo_step = QSpinBox()
        self.tempo_step.setRange(1, 20)
        self.tempo_step.setValue(2)
        form.addRow("Шаг BPM:", self.tempo_step)

        self.tempo_every = QSpinBox()
        self.tempo_every.setRange(1, 64)
        self.tempo_every.setValue(4)
        form.addRow("Каждые такты:", self.tempo_every)

        self.tempo_target = QSpinBox()
        self.tempo_target.setRange(20, 320)
        self.tempo_target.setValue(140)
        form.addRow("Цель BPM:", self.tempo_target)
        root.addWidget(trainer, 1)

        timer_box = QGroupBox("Таймер")
        form = QFormLayout(timer_box)
        self.practice_timer = QCheckBox("Остановить по таймеру")
        form.addRow("", self.practice_timer)

        self.timer_minutes = QSpinBox()
        self.timer_minutes.setRange(0, 180)
        self.timer_minutes.setValue(10)
        self.timer_minutes.setSuffix(" мин")
        form.addRow("Минуты:", self.timer_minutes)

        self.timer_seconds = QSpinBox()
        self.timer_seconds.setRange(0, 59)
        self.timer_seconds.setSuffix(" сек")
        form.addRow("Секунды:", self.timer_seconds)
        root.addWidget(timer_box, 1)
        return tab

    def _build_sound_tab(self) -> QWidget:
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.ti_on = QCheckBox("On")
        self.ti_on.setChecked(True)
        self.ti_sound = QComboBox()
        self.ti_sound.addItems(SOUND_NAMES)
        self.ti_sound.setFixedWidth(165)
        self._combo(self.ti_sound, "Wood")
        self.ti_vol = self._volume_slider(100)
        self.ti_vol.setMaximumWidth(300)

        self.ta_on = QCheckBox("On")
        self.ta_on.setChecked(True)
        self.ta_sound = QComboBox()
        self.ta_sound.addItems(SOUND_NAMES)
        self.ta_sound.setFixedWidth(165)
        self._combo(self.ta_sound, "Low tick")
        self.ta_vol = self._volume_slider(70)
        self.ta_vol.setMaximumWidth(300)

        grid.addWidget(QLabel("(ТИ)"), 0, 0)
        grid.addWidget(self.ti_on, 0, 1)
        grid.addWidget(self.ti_sound, 0, 2)
        grid.addWidget(QLabel("Громкость"), 0, 3)
        grid.addWidget(self.ti_vol, 0, 4)

        grid.addWidget(QLabel("ТА"), 1, 0)
        grid.addWidget(self.ta_on, 1, 1)
        grid.addWidget(self.ta_sound, 1, 2)
        grid.addWidget(QLabel("Громкость"), 1, 3)
        grid.addWidget(self.ta_vol, 1, 4)

        self.metro_on = QCheckBox("Звук метронома")
        self.metro_on.setChecked(True)
        self.accent = QCheckBox("Акцент первой доли")
        self.accent.setChecked(True)
        self.metro_vol = self._volume_slider(70)
        self.metro_vol.setMaximumWidth(300)
        self.master = self._volume_slider(100)
        self.master.setMaximumWidth(300)

        grid.addWidget(self.metro_on, 2, 0, 1, 2)
        grid.addWidget(self.accent, 2, 2)
        grid.addWidget(QLabel("Громкость"), 2, 3)
        grid.addWidget(self.metro_vol, 2, 4)

        grid.addWidget(QLabel("Master"), 3, 3)
        grid.addWidget(self.master, 3, 4)

        grid.setColumnStretch(5, 1)
        grid.setRowStretch(4, 1)
        return tab

    def _build_metronome_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        visual = QGroupBox("Визуализация")
        form = QFormLayout(visual)

        self.metro_size = QSlider(Qt.Horizontal)
        self.metro_size.setRange(60, 180)
        self.metro_size.setValue(100)
        form.addRow("Размер:", self.metro_size)

        self.metro_color_btn = QPushButton("Цвет иглы")
        self.metro_color_btn.clicked.connect(self.choose_metronome_color)
        self.metro_color_sample = QLabel("      ")
        self.metro_color_sample.setFixedWidth(42)
        needle_row = QWidget()
        needle_layout = QHBoxLayout(needle_row)
        needle_layout.setContentsMargins(0, 0, 0, 0)
        needle_layout.addWidget(self.metro_color_btn)
        needle_layout.addWidget(self.metro_color_sample)
        needle_layout.addStretch()
        form.addRow("Игла:", needle_row)

        self.flash_color_btn = QPushButton("Цвет мигалки")
        self.flash_color_btn.clicked.connect(self.choose_flash_color)
        self.flash_color_sample = QLabel("      ")
        self.flash_color_sample.setFixedWidth(42)
        flash_row = QWidget()
        flash_layout = QHBoxLayout(flash_row)
        flash_layout.setContentsMargins(0, 0, 0, 0)
        flash_layout.addWidget(self.flash_color_btn)
        flash_layout.addWidget(self.flash_color_sample)
        flash_layout.addStretch()
        form.addRow("Мигалка:", flash_row)

        self.metro_flash = QCheckBox("Кружок")
        self.metro_flash.setChecked(True)
        form.addRow("", self.metro_flash)

        self.metro_flash_whole = QCheckBox("Мигать всем окном метронома")
        form.addRow("", self.metro_flash_whole)

        self.metro_flash_brightness = QSlider(Qt.Horizontal)
        self.metro_flash_brightness.setRange(0, 200)
        self.metro_flash_brightness.setValue(100)
        form.addRow("Яркость:", self.metro_flash_brightness)

        self.metro_width = QSpinBox()
        self.metro_width.setRange(1, 12)
        self.metro_width.setValue(4)
        form.addRow("Толщина иглы:", self.metro_width)

        self.metro_angle = QSpinBox()
        self.metro_angle.setRange(15, 70)
        self.metro_angle.setValue(42)
        self.metro_angle.setSuffix("°")
        form.addRow("Размах:", self.metro_angle)

        self.metro_lamps = QCheckBox("Индикаторы долей")
        self.metro_lamps.setChecked(True)
        form.addRow("", self.metro_lamps)
        root.addWidget(visual, 1)
        root.addStretch(1)

        for widget in (
            self.metro_size,
            self.metro_flash,
            self.metro_flash_whole,
            self.metro_flash_brightness,
            self.metro_width,
            self.metro_angle,
            self.metro_lamps,
        ):
            signal = getattr(widget, "valueChanged", None) or getattr(widget, "toggled", None)
            if signal:
                signal.connect(self._visual_config_changed)
        self.metro_flash.toggled.connect(self._refresh_dependent_controls)
        self.metro_flash_whole.toggled.connect(self._refresh_dependent_controls)

        self._refresh_color_samples()
        return tab

    def _build_game_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        mode_box = QGroupBox("Режим")
        form = QFormLayout(mode_box)
        self.game_enabled = QCheckBox("Игровой режим")
        self.game_enabled.setChecked(False)
        self.game_enabled.toggled.connect(self._game_mode_toggled)
        form.addRow("", self.game_enabled)

        self.game_hit_sound = QCheckBox("Звук HIT")
        self.game_hit_sound.setChecked(True)
        form.addRow("", self.game_hit_sound)

        self.game_miss_sound = QCheckBox("Звук MISS")
        self.game_miss_sound.setChecked(True)
        form.addRow("", self.game_miss_sound)

        self.game_start = QPushButton("▶ Запустить игру")
        self.game_start.setEnabled(False)
        self.game_start.clicked.connect(self.toggle_game)
        form.addRow("", self.game_start)
        root.addWidget(mode_box, 1)

        controls_box = QGroupBox("Управление")
        controls = QFormLayout(controls_box)
        self.game_ti_key = GameBindEdit("key:F")
        controls.addRow("(ТИ):", self.game_ti_key)

        self.game_ta_key = GameBindEdit("key:J")
        controls.addRow("ТА:", self.game_ta_key)

        bind_hint = QLabel("Нажми поле, затем клавишу или кнопку мыши. Esc — отмена, Delete — очистить.")
        bind_hint.setWordWrap(True)
        bind_hint.setStyleSheet("color:#7f8792;")
        controls.addRow("", bind_hint)
        root.addWidget(controls_box, 1)

        self.game_stats_box = QGroupBox("Последняя игра")
        stats = QFormLayout(self.game_stats_box)
        self.last_game_score = QLabel("0")
        self.last_game_hits = QLabel("0")
        self.last_game_misses = QLabel("0")
        self.last_game_accuracy = QLabel("—")
        self.last_game_timing = QLabel("—")
        self.last_game_balance = QLabel("—")
        stats.addRow("Score:", self.last_game_score)
        stats.addRow("Попадания:", self.last_game_hits)
        stats.addRow("Промахи:", self.last_game_misses)
        stats.addRow("Точность:", self.last_game_accuracy)
        stats.addRow("Среднее |Δ|:", self.last_game_timing)
        stats.addRow("Рано / поздно:", self.last_game_balance)
        root.addWidget(self.game_stats_box, 1)

        self._refresh_last_game_stats()
        self._game_mode_toggled(False)
        return tab

    def _build_picking_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self.picking_enabled = QCheckBox("Показывать экономный picking pattern в метрономе")
        self.picking_enabled.setChecked(False)
        self.picking_enabled.toggled.connect(self._picking_settings_changed)
        form.addRow("", self.picking_enabled)

        self.picking_show_next = QCheckBox("Показывать следующий штрих справа")
        self.picking_show_next.setChecked(True)
        self.picking_show_next.toggled.connect(self._picking_settings_changed)
        form.addRow("", self.picking_show_next)

        self.picking_highlight_current = QCheckBox("Подсвечивать текущую долю в схеме")
        self.picking_highlight_current.setChecked(True)
        self.picking_highlight_current.toggled.connect(self._picking_settings_changed)
        form.addRow("", self.picking_highlight_current)

        self.picking_cue_size = QSpinBox()
        self.picking_cue_size.setRange(32, 80)
        self.picking_cue_size.setValue(52)
        self.picking_cue_size.setSuffix(" px")
        self.picking_cue_size.valueChanged.connect(self._picking_settings_changed)
        form.addRow("Размер большой стрелки:", self.picking_cue_size)

        self._refresh_picking_controls()
        return tab

    def _build_audio_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        audio_box = QGroupBox("Аудио устройство")
        form = QFormLayout(audio_box)

        device_row = QWidget()
        device_layout = QHBoxLayout(device_row)
        device_layout.setContentsMargins(0, 0, 0, 0)
        self.audio_device = QComboBox()
        refresh = QPushButton("↻")
        refresh.setFixedWidth(38)
        refresh.clicked.connect(self._refresh_audio_devices)
        device_layout.addWidget(self.audio_device, 1)
        device_layout.addWidget(refresh)
        form.addRow("Выход:", device_row)

        self.audio_rate = QComboBox()
        self.audio_rate.addItem("Default", 0)
        for rate in (44_100, 48_000, 88_200, 96_000):
            self.audio_rate.addItem(f"{rate / 1000:g} kHz", rate)
        form.addRow("Sample rate:", self.audio_rate)

        self.audio_block = QComboBox()
        for label, value in (("Auto", 0), ("128", 128), ("256", 256), ("512", 512), ("1024", 1024)):
            self.audio_block.addItem(label, value)
        form.addRow("Block size:", self.audio_block)

        self.audio_latency = QComboBox()
        self.audio_latency.addItem("Low", "low")
        self.audio_latency.addItem("High", "high")
        form.addRow("Latency:", self.audio_latency)

        self.audio_exclusive = QCheckBox("WASAPI exclusive")
        form.addRow("", self.audio_exclusive)

        apply_button = QPushButton("Применить аудио")
        apply_button.clicked.connect(self.apply_audio_settings)
        form.addRow("", apply_button)

        self.audio_status = QLabel("")
        self.audio_status.setWordWrap(True)
        form.addRow("Текущее:", self.audio_status)
        root.addWidget(audio_box, 2)

        system_box = QGroupBox("Система")
        system_form = QFormLayout(system_box)
        reset_settings = QPushButton("Обнулить настройки…")
        reset_settings.clicked.connect(self.reset_app_settings)
        system_form.addRow("Settings:", QLabel(SETTINGS_PATH.name))
        system_form.addRow("", reset_settings)
        root.addWidget(system_box, 1)

        self._refresh_audio_devices()
        return tab

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        midi = QPushButton("MIDI (.mid)")
        midi.clicked.connect(self.export_current_midi)
        gp = QPushButton("Guitar Pro 5 (.gp5)")
        gp.clicked.connect(self.export_current_gp5)
        wav = QPushButton("Audio (.wav)")
        wav.clicked.connect(self.export_current_wav)

        layout.addWidget(midi)
        layout.addWidget(gp)
        layout.addWidget(wav)
        layout.addStretch()
        return tab

    @staticmethod
    def _volume_slider(value: int) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 200)
        slider.setValue(value)
        slider.setToolTip("0–200%")
        return slider

    def _shortcuts(self) -> None:
        QShortcut(QKeySequence("Space"), self, self.toggle)
        QShortcut(QKeySequence("T"), self, self.tap_tempo)
        QShortcut(QKeySequence("Up"), self, lambda: self.bpm.setValue(self.bpm.value() + 1))
        QShortcut(QKeySequence("Down"), self, lambda: self.bpm.setValue(self.bpm.value() - 1))
        QShortcut(QKeySequence("Shift+Up"), self, lambda: self.bpm.setValue(self.bpm.value() + 5))
        QShortcut(QKeySequence("Shift+Down"), self, lambda: self.bpm.setValue(self.bpm.value() - 5))

    def choose_metronome_color(self) -> None:
        color = QColorDialog.getColor(self.metro_color, self, "Цвет иглы")
        if color.isValid():
            self.metro_color = color
            self._refresh_color_samples()
            self._visual_config_changed()

    def choose_flash_color(self) -> None:
        color = QColorDialog.getColor(self.flash_color, self, "Цвет мигалки")
        if color.isValid():
            self.flash_color = color
            self._refresh_color_samples()
            self._visual_config_changed()

    def _refresh_color_samples(self) -> None:
        self.metro_color_sample.setStyleSheet(
            f"background:{self.metro_color.name()};border:1px solid #666;border-radius:4px;"
        )
        self.flash_color_sample.setStyleSheet(
            f"background:{self.flash_color.name()};border:1px solid #666;border-radius:4px;"
        )

    def _visual_config_changed(self, *_args) -> None:
        self.visual.configure(
            scale_percent=self.metro_size.value(),
            needle_color=self.metro_color,
            flash_color=self.flash_color,
            flash_enabled=self.metro_flash.isChecked(),
            flash_whole_panel=self.metro_flash_whole.isChecked(),
            flash_brightness=self.metro_flash_brightness.value(),
            needle_width=self.metro_width.value(),
            show_beat_lamps=self.metro_lamps.isChecked(),
            swing_angle=self.metro_angle.value(),
        )

    def _meter(self) -> tuple[int, int]:
        return self.meter_num.value(), int(self.meter_den.currentData())

    def _rebuild_editors(self, patterns: list[BeatPattern] | None = None) -> None:
        while self.beats_layout.count():
            item = self.beats_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        numerator, denominator = self._meter()
        patterns = list(patterns or [])
        self.editors = []
        for i in range(numerator):
            editor = BeatEditor(i + 1, numerator, denominator)
            if i < len(patterns):
                editor.set_pattern(patterns[i])
            editor.changed.connect(self._pattern_changed)
            self.beats_layout.addWidget(editor)
            self.editors.append(editor)
        self.beats_layout.addStretch()

        self.beats_group.setTitle(f"Такт {numerator}/{denominator}")
        self._update_mode_labels()
        self._mode_changed()
        self._pattern_changed()

    def _meter_changed(self, *_args) -> None:
        old = [editor.pattern() for editor in self.editors]
        if self.engine.is_running:
            self._stop_playback("Готов")
        self._rebuild_editors(old)

    def _update_mode_labels(self) -> None:
        numerator, denominator = self._meter()
        self.mode.setItemText(0, f"Петля {numerator}/{denominator}")
        self.mode.setItemText(1, f"Разгон 1 → 2 → … → {numerator}")
        self.mode.setItemText(2, f"Разгон 2 → {numerator}")

    def _mode_changed(self, *_args) -> None:
        ramp = self.mode.currentData() != "loop"
        for editor in self.editors:
            editor.set_mute_allowed(not ramp)
        if not self.engine.is_running:
            self._set_ramp_visual(self.meter_num.value())
        self._refresh_dependent_controls()
        self._pattern_changed()

    def _refresh_dependent_controls(self, *_args) -> None:
        ramp = self.mode.currentData() != "loop"

        self.bars.setEnabled(ramp)
        self.inactive.setEnabled(ramp)
        self.ramp_warning.setEnabled(ramp)

        tempo_enabled = self.tempo_train.isChecked()
        for widget in (self.tempo_step, self.tempo_every, self.tempo_target):
            widget.setEnabled(tempo_enabled)

        timer_enabled = self.practice_timer.isChecked()
        self.timer_minutes.setEnabled(timer_enabled)
        self.timer_seconds.setEnabled(timer_enabled)

        self.ti_sound.setEnabled(self.ti_on.isChecked())
        self.ti_vol.setEnabled(self.ti_on.isChecked())
        self.ta_sound.setEnabled(self.ta_on.isChecked())
        self.ta_vol.setEnabled(self.ta_on.isChecked())
        self.accent.setEnabled(self.metro_on.isChecked())
        self.metro_vol.setEnabled(self.metro_on.isChecked())

        any_flash = self.metro_flash.isChecked() or self.metro_flash_whole.isChecked()
        self.flash_color_btn.setEnabled(any_flash)
        self.flash_color_sample.setEnabled(any_flash)
        self.metro_flash_brightness.setEnabled(any_flash)


    def _ensure_unique_sound(self, source: str) -> None:
        if self.ti_sound.currentText() != self.ta_sound.currentText():
            return

        if source == "ti":
            target = self.ta_sound
            forbidden = self.ti_sound.currentText()
        else:
            target = self.ti_sound
            forbidden = self.ta_sound.currentText()

        for index in range(target.count()):
            if target.itemText(index) != forbidden:
                target.blockSignals(True)
                target.setCurrentIndex(index)
                target.blockSignals(False)
                break
        self._config_changed()

    def current_pattern(self) -> BarPattern:
        numerator, denominator = self._meter()
        return BarPattern([editor.pattern() for editor in self.editors], numerator, denominator)

    def _pattern_changed(self) -> None:
        if not self.editors:
            return
        pattern = self.current_pattern()
        self.engine.set_pattern(pattern)
        self._refresh_span_visuals(pattern)
        if hasattr(self, "picking_enabled"):
            self._update_picking_pattern()

    def _refresh_span_visuals(self, pattern: BarPattern | None = None) -> None:
        pattern = pattern or self.current_pattern()
        owners = pattern.coverage()
        for i, editor in enumerate(self.editors):
            editor.set_span_covered(owners[i] is not None and owners[i] != i)

    def _config_changed(self, *_args) -> None:
        if self.ti_sound.currentText() == self.ta_sound.currentText():
            self._ensure_unique_sound("ti")
            return
        self.engine.set_config(
            bpm=self.bpm.value(),
            practice_mode=self.mode.currentData(),
            bars_per_stage=self.bars.value(),
            count_in_bars=self.count.value(),
            inactive_pulse=self.inactive.isChecked(),
            tempo_trainer_enabled=self.tempo_train.isChecked(),
            tempo_step=self.tempo_step.value(),
            tempo_every_bars=self.tempo_every.value(),
            tempo_target=self.tempo_target.value(),
            ti_enabled=self.ti_on.isChecked(),
            ti_sound=self.ti_sound.currentText(),
            ti_volume=self.ti_vol.value() / 100.0,
            ta_enabled=self.ta_on.isChecked(),
            ta_sound=self.ta_sound.currentText(),
            ta_volume=self.ta_vol.value() / 100.0,
            metronome_enabled=self.metro_on.isChecked(),
            accent_first_beat=self.accent.isChecked(),
            metronome_volume=self.metro_vol.value() / 100.0,
            master_volume=self.master.value() / 100.0,
        )

    def _sync(self) -> None:
        self._pattern_changed()
        self._config_changed()
        self._visual_config_changed()
        self._refresh_dependent_controls()
        self._update_picking_pattern()

    def _bpm_from_spin(self, value: int) -> None:
        self.bpm_slider.blockSignals(True)
        self.bpm_slider.setValue(value)
        self.bpm_slider.blockSignals(False)
        self.engine.set_config(bpm=value)

    def _bpm_from_slider(self, value: int) -> None:
        self.bpm.blockSignals(True)
        self.bpm.setValue(value)
        self.bpm.blockSignals(False)
        self.engine.set_config(bpm=value)

    def _timer_limit(self) -> int:
        return self.timer_minutes.value() * 60 + self.timer_seconds.value()

    @staticmethod
    def _time_text(seconds: float) -> str:
        seconds = max(0, int(math.ceil(seconds)))
        minutes, sec = divmod(seconds, 60)
        return f"{minutes:02d}:{sec:02d}"

    def toggle(self) -> None:
        try:
            if self.engine.is_running:
                if self.game_active:
                    self.stop_game("Игра остановлена")
                else:
                    self._stop_playback("Готов")
            else:
                self.game_stats_visible = self.game_enabled.isChecked()
                self.visual.set_game_stats(
                    self.game_stats_visible,
                    self.game_hits,
                    self.game_misses,
                    self.game_recent,
                )
                if self.practice_timer.isChecked() and self._timer_limit() <= 0:
                    QMessageBox.information(self, "Таймер", "Укажи длительность больше нуля.")
                    return
                self._sync()
                self.engine.start()
                self.play.setText("■ Стоп")
        except Exception as exc:
            self.engine.stop()
            self.play.setText("▶ Старт")
            QMessageBox.critical(self, "Ошибка аудио", str(exc))

    def _stop_playback(self, message: str, timer_finished: bool = False) -> None:
        self.engine.stop()
        self.engine.stop_game_tracking()
        self.play.setText("▶ Старт")
        self.clear_playhead()
        self._set_ramp_visual(self.meter_num.value())
        self._last_ramp_warning_key = None
        self._update_picking_pattern(self.meter_num.value())
        numerator, denominator = self._meter()
        timer_text = "00:00" if timer_finished and self.practice_timer.isChecked() else ""
        self.visual.set_state(
            phase=0.0,
            beat=0,
            sub=0,
            active_beats=numerator,
            numerator=numerator,
            denominator=denominator,
            count_in=False,
            running=False,
            timer_text=timer_text,
        )
        self.status.setText(message)
        if timer_finished:
            self.engine.play_notification("Finish horn", 0.95)

    def tap_tempo(self) -> None:
        now = time.perf_counter()
        if self.tap_times and now - self.tap_times[-1] > 2.5:
            self.tap_times = []
        self.tap_times.append(now)
        self.tap_times = self.tap_times[-7:]
        if len(self.tap_times) > 1:
            intervals = [b - a for a, b in zip(self.tap_times, self.tap_times[1:])]
            if len(intervals) >= 4:
                intervals = sorted(intervals)[1:-1]
            self.bpm.setValue(round(60.0 / (sum(intervals) / len(intervals))))

    def randomize_beats(self) -> None:
        for editor in self.editors:
            preset = random.choice(CORE_PRACTICE_PRESETS)
            editor.set_pattern(BeatPattern(preset.grid, list(preset.steps), False))
        self._pattern_changed()

    def _game_mode_toggled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled and hasattr(self, "picking_enabled") and self.picking_enabled.isChecked():
            self.picking_enabled.setChecked(False)

        self.game_stats_visible = enabled
        self.game_start.setEnabled(enabled)

        for widget in (
            self.game_ti_key,
            self.game_ta_key,
            self.game_hit_sound,
            self.game_miss_sound,
        ):
            widget.setEnabled(enabled and not self.game_active)

        if not enabled:
            if self.game_active:
                self.stop_game("Игра остановлена")
            self.visual.set_game_stats(False, self.game_hits, self.game_misses, self.game_recent, self.game_score)
            self.visual.clear_game_feedback()
        else:
            self.visual.set_game_stats(True, self.game_hits, self.game_misses, self.game_recent, self.game_score)

    def toggle_game(self) -> None:
        if not self.game_enabled.isChecked():
            return

        if self.game_active:
            self.stop_game("Игра остановлена")
            return

        ti_key = self._configured_game_binding(self.game_ti_key)
        ta_key = self._configured_game_binding(self.game_ta_key)
        if not ti_key or not ta_key:
            QMessageBox.information(self, "Игра", "Назначь клавиши или кнопки мыши для (ТИ) и ТА.")
            return
        if ti_key == ta_key:
            QMessageBox.information(self, "Игра", "Кнопки (ТИ) и ТА должны отличаться.")
            return

        if self.engine.is_running:
            self.engine.stop()

        self._sync()
        self._reset_game_stats()
        self.game_active = True
        self.game_stats_visible = True
        self.game_start.setText("■ Остановить игру")
        self.game_ti_key.setEnabled(False)
        self.game_ta_key.setEnabled(False)
        self.engine.start_game_tracking()
        self.engine.start()
        self._start_game_log()
        self.play.setText("■ Стоп")
        self.visual.set_game_stats(True, 0, 0, [], 0)
        self.status.setText("Игра · COUNT-IN")

    def stop_game(self, message: str) -> None:
        self._game_update_misses(force=False)
        self._finalize_game_stats()
        self.game_active = False
        self.game_start.setText("▶ Запустить игру")
        self.game_ti_key.setEnabled(True)
        self.game_ta_key.setEnabled(True)
        self._stop_playback(message)
        self._finish_game_log("game_stopped")
        self.visual.set_game_stats(
            self.game_enabled.isChecked(),
            self.game_hits,
            self.game_misses,
            self.game_recent,
            self.game_score,
        )

    def _reset_game_stats(self) -> None:
        self.game_hits = 0
        self.game_misses = 0
        self.game_score = 0
        self.game_recent = []
        self.game_offsets_ms = []
        self.game_calibration_samples_ms = []
        self.game_timing_bias_ms = 0.0
        self.game_pending = []
        self.game_pending_inputs = []
        self._game_log_last_position = None
        self.engine.drain_game_targets()
        self.visual.clear_game_feedback()
        self.game_stats_box.setTitle("Текущая игра")
        self._refresh_current_game_stats()

    def _finalize_game_stats(self) -> None:
        total = self.game_hits + self.game_misses
        accuracy = 100.0 * self.game_hits / total if total else 0.0
        mean_abs = (
            sum(abs(value) for value in self.game_offsets_ms) / len(self.game_offsets_ms)
            if self.game_offsets_ms
            else 0.0
        )
        early = sum(1 for value in self.game_offsets_ms if value < -4.0)
        late = sum(1 for value in self.game_offsets_ms if value > 4.0)
        self.last_game_stats = {
            "hits": self.game_hits,
            "misses": self.game_misses,
            "accuracy": accuracy,
            "mean_abs_ms": mean_abs,
            "early": early,
            "late": late,
            "score": self.game_score,
        }
        self.game_stats_box.setTitle("Последняя игра")
        self._refresh_last_game_stats()

    def _refresh_last_game_stats(self) -> None:
        if not hasattr(self, "last_game_hits"):
            return
        stats = self.last_game_stats
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        total = hits + misses
        self.last_game_score.setText(str(int(stats.get("score", 0))))
        self.last_game_hits.setText(str(hits))
        self.last_game_misses.setText(str(misses))
        self.last_game_accuracy.setText(f"{float(stats.get('accuracy', 0.0)):.1f}%" if total else "—")
        self.last_game_timing.setText(
            f"{float(stats.get('mean_abs_ms', 0.0)):.1f} ms" if hits else "—"
        )
        self.last_game_balance.setText(
            f"{int(stats.get('early', 0))} / {int(stats.get('late', 0))}" if hits else "—"
        )

    def _refresh_current_game_stats(self) -> None:
        if not hasattr(self, "last_game_hits"):
            return
        total = self.game_hits + self.game_misses
        accuracy = 100.0 * self.game_hits / total if total else 0.0
        mean_abs = (
            sum(abs(value) for value in self.game_offsets_ms) / len(self.game_offsets_ms)
            if self.game_offsets_ms
            else 0.0
        )
        early = sum(1 for value in self.game_offsets_ms if value < -4.0)
        late = sum(1 for value in self.game_offsets_ms if value > 4.0)
        self.last_game_score.setText(str(self.game_score))
        self.last_game_hits.setText(str(self.game_hits))
        self.last_game_misses.setText(str(self.game_misses))
        self.last_game_accuracy.setText(f"{accuracy:.1f}%" if total else "—")
        self.last_game_timing.setText(f"{mean_abs:.1f} ms" if self.game_hits else "—")
        self.last_game_balance.setText(f"{early} / {late}" if self.game_hits else "—")

    def _game_window_seconds(self) -> float:
        return HIT_WINDOW_MS / 1000.0

    def _drain_game_targets(self) -> None:
        stream_now = self.engine.stream_time()
        added = False
        for dac_time, state, bar, beat, sub in self.engine.drain_game_targets():
            target = {
                "time": float(dac_time),
                "state": str(state),
                "bar": int(bar),
                "beat": int(beat),
                "sub": int(sub),
            }
            self.game_pending.append(target)
            added = True
            self._log_game_event(
                "target_scheduled",
                target=target,
                stream_time=stream_now,
                drain_offset_ms=(stream_now - float(dac_time)) * 1000.0 if stream_now > 0 else None,
                pending_after=len(self.game_pending),
                buffered_inputs=len(self.game_pending_inputs),
            )
        self.game_pending.sort(key=lambda item: float(item["time"]))
        if added and self.game_pending_inputs:
            self._resolve_buffered_game_inputs()

    def _select_game_target(self, state: str, input_now: float) -> int | None:
        compact_targets = [
            (float(target["time"]), str(target["state"]))
            for target in self.game_pending
        ]
        return choose_target_index(
            compact_targets,
            state,
            input_now,
        )

    def _judge_game_input(
        self,
        state: str,
        input_now: float,
        target_index: int,
        *,
        buffered: bool = False,
    ) -> None:
        target = self.game_pending.pop(target_index)
        raw_offset_ms = (input_now - float(target["time"])) * 1000.0

        self._log_game_event(
            "target_selected",
            input_state=state,
            target=target,
            target_index=target_index,
            stream_time=input_now,
            raw_offset_ms=raw_offset_ms,
            corrected_offset_ms=raw_offset_ms,
            timing_bias_before_ms=0.0,
            calibration_enabled=False,
            buffered_input=buffered,
        )

        # choose_target_index is lane-only, so a different target state here
        # would indicate a programming error rather than a player judgement.
        if target["state"] != state:
            self._log_game_event(
                "matcher_invariant_failed",
                input_state=state,
                target=target,
            )
            self._record_game_result(
                False,
                0.0,
                detail="внутренняя ошибка сопоставления",
            )
            return

        grade = grade_timing(raw_offset_ms)
        self._record_game_result(
            grade.accepted,
            grade.quality,
            offset_ms=raw_offset_ms,
            grade_label=grade.label,
            points=grade.points,
            detail="вне окна",
        )

    def _resolve_buffered_game_inputs(self) -> None:
        if not self.game_pending_inputs or not self.game_pending:
            return

        stream_now = self.engine.stream_time()
        remaining: list[dict[str, object]] = []
        for pending_input in self.game_pending_inputs:
            state = str(pending_input["state"])
            input_now = float(pending_input["time"])
            waited_ms = (stream_now - input_now) * 1000.0

            if waited_ms > INPUT_BUFFER_MAX_MS:
                remaining.append(pending_input)
                continue

            target_index = self._select_game_target(state, input_now)
            if target_index is None:
                remaining.append(pending_input)
                continue

            target = self.game_pending[target_index]
            raw_offset_ms = (input_now - float(target["time"])) * 1000.0
            if raw_offset_ms < -EARLY_HIT_WINDOW_MS:
                remaining.append(pending_input)
                continue

            self._log_game_event(
                "input_buffer_resolved",
                state=state,
                input_stream_time=input_now,
                waited_ms=waited_ms,
                target_index=target_index,
                raw_offset_ms=raw_offset_ms,
                buffered_before=len(self.game_pending_inputs),
            )
            self._judge_game_input(
                state,
                input_now,
                target_index,
                buffered=True,
            )

        self.game_pending_inputs = remaining

    def _expire_buffered_game_inputs(self, now: float, force: bool = False) -> None:
        if not self.game_pending_inputs:
            return

        keep: list[dict[str, object]] = []
        for pending_input in self.game_pending_inputs:
            input_time = float(pending_input["time"])
            age_ms = (now - input_time) * 1000.0
            if not force and age_ms <= INPUT_BUFFER_MAX_MS:
                keep.append(pending_input)
                continue

            state = str(pending_input["state"])
            entered = TI_MARK if state == TI else "ТА"
            self._log_game_event(
                "input_buffer_expired",
                state=state,
                input_stream_time=input_time,
                stream_time=now,
                age_ms=age_ms,
                calibration_enabled=False,
            )
            self._record_game_result(
                False,
                0.0,
                detail=f"{entered} · нет цели рядом",
            )
        self.game_pending_inputs = keep

    @staticmethod
    def _timing_description(offset_ms: float) -> str:
        amount = abs(offset_ms)
        if amount <= 4.0:
            return f"точно · {amount:.0f} ms"
        if offset_ms < 0:
            return f"рано · {amount:.0f} ms"
        return f"поздно · {amount:.0f} ms"

    def _record_game_result(
        self,
        hit: bool,
        quality: float,
        *,
        offset_ms: float | None = None,
        detail: str = "",
        grade_label: str = "HIT",
        points: int = 0,
        show_feedback: bool = True,
    ) -> None:
        if hit:
            self.game_hits += 1
            self.game_score += max(0, int(points))
            self.game_recent.append(max(0.0, min(1.0, quality)))
            if offset_ms is not None:
                self.game_offsets_ms.append(float(offset_ms))
            if show_feedback:
                timing = self._timing_description(float(offset_ms or 0.0))
                self.visual.set_game_feedback("hit", grade_label, f"{timing} · +{int(points)}")
            if self.game_hit_sound.isChecked():
                self.engine.queue_notification("game_hit", 0.70)
        else:
            self.game_misses += 1
            self.game_recent.append(0.0)
            if show_feedback:
                self.visual.set_game_feedback("miss", "MISS", detail or "промах")
            if self.game_miss_sound.isChecked():
                self.engine.queue_notification("game_miss", 0.68)

        self.game_recent = self.game_recent[-28:]
        self._log_game_event(
            "result",
            hit=bool(hit),
            grade=grade_label if hit else "MISS",
            quality=float(quality),
            points=int(points) if hit else 0,
            offset_ms=offset_ms,
            detail=detail,
            score=self.game_score,
            hits=self.game_hits,
            misses=self.game_misses,
            timing_bias_ms=0.0,
            calibration_samples=list(self.game_calibration_samples_ms),
        )
        self._refresh_current_game_stats()
        self.visual.set_game_stats(
            self.game_enabled.isChecked(),
            self.game_hits,
            self.game_misses,
            self.game_recent,
            self.game_score,
        )

    def _game_update_misses(self, force: bool = False) -> None:
        self._drain_game_targets()
        now = self.engine.stream_time()
        self._expire_buffered_game_inputs(now, force=force)
        if not self.game_pending:
            return

        late_window = LATE_HIT_WINDOW_MS / 1000.0
        while self.game_pending:
            target_time = float(self.game_pending[0]["time"])
            if not force and target_time >= now - late_window:
                break
            target = self.game_pending.pop(0)
            expected = TI_MARK if target["state"] == TI else "ТА"
            lateness_ms = (now - float(target["time"])) * 1000.0
            self._log_game_event(
                "target_expired",
                target=target,
                stream_time=now,
                raw_lateness_ms=lateness_ms,
                corrected_lateness_ms=lateness_ms,
                calibration_enabled=False,
            )
            self._record_game_result(
                False,
                0.0,
                detail=f"пропуск · ожидалось {expected}",
                show_feedback=not force,
            )

    @staticmethod
    def _configured_game_binding(editor: GameBindEdit) -> str:
        return editor.binding().strip().lower()

    def _handle_game_input(self, state: str) -> None:
        if not self.game_active:
            return
        st = self.engine.status()
        if st["count_in"]:
            self._log_game_event(
                "input_ignored",
                state=state,
                reason="count_in",
                stream_time=self.engine.stream_time(),
            )
            return

        input_now = self.engine.stream_time()
        if input_now <= 0:
            self._log_game_event(
                "input_ignored",
                state=state,
                reason="invalid_stream_time",
                stream_time=input_now,
            )
            return

        binding = (
            self._configured_game_binding(self.game_ti_key)
            if state == TI
            else self._configured_game_binding(self.game_ta_key)
        )
        key = _binding_display(binding)
        self._log_game_event(
            "input",
            state=state,
            key=key,
            stream_time=input_now,
            timing_bias_ms=0.0,
            calibration_count=0,
            engine_status=st,
            pending_targets=len(self.game_pending),
            buffered_inputs=len(self.game_pending_inputs),
        )

        self._drain_game_targets()
        self._game_update_misses()

        target_index = self._select_game_target(state, input_now)
        self._log_game_event(
            "match_search",
            state=state,
            stream_time=input_now,
            calibrating=False,
            hit_window_ms=HIT_WINDOW_MS,
            input_buffer_max_ms=INPUT_BUFFER_MAX_MS,
            timing_bias_ms=0.0,
            target_index=target_index,
            pending_targets=[
                {
                    "index": index,
                    "state": str(target["state"]),
                    "bar": int(target["bar"]),
                    "beat": int(target["beat"]),
                    "sub": int(target["sub"]),
                    "target_time": float(target["time"]),
                    "raw_offset_ms": (input_now - float(target["time"])) * 1000.0,
                    "corrected_offset_ms": (
                        (input_now - float(target["time"])) * 1000.0
                    ),
                }
                for index, target in enumerate(self.game_pending[:32])
            ],
        )

        if target_index is not None:
            self._judge_game_input(state, input_now, target_index)
            return

        # Crucial: an early key press may happen before PortAudio's callback
        # publishes that future target. Buffer it instead of calling it MISS.
        pending_input = {
            "time": float(input_now),
            "state": str(state),
            "key": key,
        }
        self.game_pending_inputs.append(pending_input)
        self.game_pending_inputs.sort(key=lambda item: float(item["time"]))
        self._log_game_event(
            "input_buffered",
            input=pending_input,
            buffered_after=len(self.game_pending_inputs),
        )

    def eventFilter(self, watched, event) -> bool:
        if self.game_active:
            binding = ""
            if event.type() == QEvent.KeyPress and not event.isAutoRepeat():
                binding = _key_event_binding(event).lower()
            elif event.type() == QEvent.MouseButtonPress:
                binding = _mouse_button_binding(event.button()).lower()

            if binding:
                if binding == self._configured_game_binding(self.game_ti_key):
                    self._handle_game_input(TI)
                    event.accept()
                    return True
                if binding == self._configured_game_binding(self.game_ta_key):
                    self._handle_game_input(TA)
                    event.accept()
                    return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)

    def _refresh_picking_controls(self) -> None:
        if not hasattr(self, "picking_enabled"):
            return
        enabled = self.picking_enabled.isChecked()
        for widget in (
            getattr(self, "picking_show_next", None),
            getattr(self, "picking_highlight_current", None),
            getattr(self, "picking_cue_size", None),
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def _picking_settings_changed(self, *_args) -> None:
        if self.picking_enabled.isChecked() and self.game_enabled.isChecked():
            self.game_enabled.setChecked(False)

        self._refresh_picking_controls()
        self.visual.configure_picking(
            show_next=self.picking_show_next.isChecked(),
            highlight_current=self.picking_highlight_current.isChecked(),
            cue_size=self.picking_cue_size.value(),
        )
        self._update_picking_pattern()

    def _update_picking_pattern(self, active_beats: int | None = None) -> None:
        if not hasattr(self, "picking_enabled") or not self.picking_enabled.isChecked():
            self.visual.set_picking_pattern(False)
            return

        pattern = self.current_pattern()
        if active_beats is None:
            if self.mode.currentData() == "ramp_1_4":
                active = min(1, pattern.numerator)
            elif self.mode.currentData() == "ramp_2_4":
                active = min(2, pattern.numerator)
            else:
                active = pattern.numerator
        else:
            active = max(0, min(pattern.numerator, int(active_beats)))

        coverage = pattern.coverage()
        beat_states: list[list[str]] = []

        for beat_index, beat in enumerate(pattern.beats):
            if coverage[beat_index] != beat_index:
                states: list[str] = []
            elif self.mode.currentData() != "loop" and beat_index >= active:
                # The next not-yet-opened ramp beat is shown exactly as it is
                # practised: TA on the beat, then silence for the remaining
                # subdivisions. The scheme is rebuilt as each new beat opens.
                states = [TA] + [OFF] * max(0, beat.subdivision - 1)
            elif beat.muted:
                states = [OFF] * beat.subdivision
            else:
                states = list(beat.steps)

            beat_states.append(states)

        # Every practice stage repeats its current effective bar. Treat the
        # picking problem as cyclic in loop and ramp modes alike; ramp simply
        # rebuilds beat_states whenever the active-beat level changes.
        directions_by_beat = economy_pick_beats(
            beat_states,
            TI,
            TA,
            OFF,
            loop=True,
        )
        row5: list[list[str]] = []
        row6: list[list[str]] = []

        for states, directions in zip(beat_states, directions_by_beat):
            if not states:
                row5.append([" "])
                row6.append([" "])
                continue

            beat5: list[str] = []
            beat6: list[str] = []
            for state, direction in zip(states, directions):
                if state == TI and direction:
                    beat5.append(direction)
                    beat6.append("─")
                elif state == TA and direction:
                    beat5.append("─")
                    beat6.append(direction)
                else:
                    beat5.append("·")
                    beat6.append("·")

            row5.append(beat5)
            row6.append(beat6)

        self.visual.set_picking_pattern(True, row5, row6)

    def _maybe_warn_ramp(self, st: dict) -> None:
        if self.mode.currentData() == "loop" or not self.ramp_warning.isChecked():
            return
        if st["count_in"]:
            return
        if int(st["next_active_beats"]) == int(st["active_beats"]):
            return
        if int(st["stage_bar"]) != int(st["bars_per_stage"]):
            return
        if int(st["beat"]) != 0 or int(st["sub"]) != 0 or float(st["beat_phase"]) > 0.18:
            return

        key = (int(st["stage_index"]), int(st["bar"]))
        if key == self._last_ramp_warning_key:
            return
        self._last_ramp_warning_key = key
        self.visual.trigger_ramp_warning(
            int(st["active_beats"]),
            int(st["next_active_beats"]),
        )
        self.engine.queue_notification("ramp_warn", 0.72)

    def _start_game_log(self) -> None:
        if not self.game_log_enabled:
            return

        self.game_log = GameLogSession(True, APP_VERSION)
        config = self.engine.get_config()
        metadata = {
            "bpm": self.bpm.value(),
            "pattern": self.current_pattern().to_dict(),
            "practice_mode": self.mode.currentData(),
            "count_in_bars": self.count.value(),
            "bars_per_stage": self.bars.value(),
            "tempo_trainer": self.tempo_train.isChecked(),
            "timer_enabled": self.practice_timer.isChecked(),
            "timer_seconds": self._timer_limit(),
            "keys": {
                "ti": self._configured_game_binding(self.game_ti_key),
                "ta": self._configured_game_binding(self.game_ta_key),
            },
            "game": {
                "early_hit_window_ms": EARLY_HIT_WINDOW_MS,
                "late_hit_window_ms": LATE_HIT_WINDOW_MS,
                "input_buffer_max_ms": INPUT_BUFFER_MAX_MS,
                "auto_timing_bias": False,
                "lane_only_matching": True,
                "hit_sound": self.game_hit_sound.isChecked(),
                "miss_sound": self.game_miss_sound.isChecked(),
            },
            "audio": self.engine.stream_info(),
            "engine_config": dict(config.__dict__),
            "picking_enabled": self.picking_enabled.isChecked(),
        }
        self.game_log.start(metadata)
        self._log_game_event(
            "engine_started",
            stream_time=self.engine.stream_time(),
            engine_status=self.engine.status(),
        )

    def _log_game_event(self, event: str, **data) -> None:
        logger = self.game_log
        if logger is not None:
            logger.log(event, **data)

    def _game_log_summary(self) -> dict:
        total = self.game_hits + self.game_misses
        return {
            "score": self.game_score,
            "hits": self.game_hits,
            "misses": self.game_misses,
            "accuracy": (100.0 * self.game_hits / total) if total else 0.0,
            "timing_bias_ms": 0.0,
            "calibration_samples_ms": [],
            "auto_timing_bias": False,
            "hit_offsets_ms": list(self.game_offsets_ms),
            "pending_targets": len(self.game_pending),
            "pending_inputs": len(self.game_pending_inputs),
            "last_game_stats": dict(self.last_game_stats),
        }

    def _finish_game_log(self, reason: str) -> None:
        logger = self.game_log
        self.game_log = None
        self._game_log_last_position = None
        if logger is None:
            return
        archive = logger.finish(reason, self._game_log_summary())
        if archive is not None:
            self.status.setToolTip(f"Game log: {archive}")

    def _log_game_clock_snapshot(self, st: dict) -> None:
        logger = self.game_log
        if logger is None or not logger.active:
            return
        key = (
            bool(st.get("count_in")),
            int(st.get("bar", 0)),
            int(st.get("beat", 0)),
            int(st.get("sub", 0)),
            int(st.get("stage_index", 0)),
            int(st.get("stage_bar", 0)),
        )
        if key == self._game_log_last_position:
            return
        self._game_log_last_position = key
        self._log_game_event(
            "clock_position",
            stream_time=self.engine.stream_time(),
            status=st,
            pending_targets=len(self.game_pending),
            timing_bias_ms=0.0,
        )

    def _poll(self) -> None:
        st = self.engine.status()
        if not st["running"]:
            return

        if self.game_active:
            self._log_game_clock_snapshot(st)

        bpm = round(st["bpm"])
        if bpm != self.bpm.value():
            self.bpm.setValue(bpm)

        numerator = int(st["numerator"])
        denominator = int(st["denominator"])
        active_beats = numerator if st["count_in"] else int(st["active_beats"])

        timer_text = ""
        if self.practice_timer.isChecked():
            remaining = self._timer_limit() - float(st["practice_elapsed_seconds"])
            if not st["count_in"] and remaining <= 0:
                if self.game_active:
                    self._game_update_misses(force=False)
                    self._finalize_game_stats()
                    self._finish_game_log("timer_finished")
                    self.game_active = False
                    self.game_start.setText("▶ Запустить игру")
                    self._game_mode_toggled(self.game_enabled.isChecked())
                self._stop_playback("Тренировка завершена", timer_finished=True)
                self.visual.set_game_stats(
                    self.game_enabled.isChecked(),
                    self.game_hits,
                    self.game_misses,
                    self.game_recent,
                    self.game_score,
                )
                return
            timer_text = self._time_text(remaining)

        self.visual.set_state(
            phase=float(st["beat_phase"]),
            beat=int(st["beat"]),
            sub=int(st["sub"]),
            active_beats=active_beats,
            numerator=numerator,
            denominator=denominator,
            count_in=bool(st["count_in"]),
            running=True,
            timer_text=timer_text,
        )

        beat = int(st["beat"])
        if 0 <= beat < len(self.editors):
            self.beat_scroll.ensureWidgetVisible(self.editors[beat], 70, 0)

        if self.game_active:
            self._game_update_misses()

        if st["count_in"]:
            self.status.setText(f"COUNT-IN · {bpm} BPM")
            self._set_ramp_visual(numerator)
            self._update_picking_pattern(numerator)
            self.highlight(beat, None)
            return

        self._set_ramp_visual(active_beats)
        self._update_picking_pattern(active_beats)
        self._maybe_warn_ramp(st)

        if self.mode.currentData() != "loop":
            stage_bar = int(st["stage_bar"])
            bars_per_stage = int(st["bars_per_stage"])
            remaining_bars = max(0, bars_per_stage - stage_bar)
            stage_progress = progress_bar(stage_bar, bars_per_stage)
            status_text = (
                f"Уровень: {active_beats} доли · [{stage_progress}] "
                f"{stage_bar}/{bars_per_stage} · осталось {remaining_bars} · "
                f"доля {beat + 1} · {bpm} BPM"
            )
            if (
                self.ramp_warning.isChecked()
                and int(st["next_active_beats"]) != active_beats
                and stage_bar == bars_per_stage
            ):
                next_active = int(st["next_active_beats"])
                arrow = "↑" if next_active > active_beats else "↓"
                unit = "доля" if next_active == 1 else "доли"
                status_text += f" · {arrow} далее {next_active} {unit}"
        else:
            status_text = f"Доля {beat + 1} · {bpm} BPM"

        if timer_text:
            status_text += f" · {timer_text}"
        if self.game_active:
            status_text += f" · Score {self.game_score}"

        self.status.setText(status_text)
        self.highlight(beat, int(st["sub"]))

    def _set_ramp_visual(self, active_beats: int) -> None:
        ramp = self.mode.currentData() != "loop" and self.engine.is_running
        pattern = self.current_pattern()
        owners = pattern.coverage()
        for i, editor in enumerate(self.editors):
            covered_by_active_note = (
                owners[i] is not None
                and owners[i] != i
                and int(owners[i]) < int(active_beats)
            )
            editor.set_ramp_inactive(
                ramp and i >= active_beats and not covered_by_active_note
            )

    def highlight(self, beat: int, sub: int | None) -> None:
        for i, editor in enumerate(self.editors):
            editor.playhead(sub if i == beat else None)

    def clear_playhead(self) -> None:
        for editor in self.editors:
            editor.playhead(None)

    def _refresh_audio_devices(self) -> None:
        selected_index = None
        current = self.audio_device.currentData() if hasattr(self, "audio_device") else None
        if isinstance(current, dict):
            selected_index = current.get("index")

        self.audio_device.blockSignals(True)
        self.audio_device.clear()
        for device in AudioEngine.list_output_devices():
            label = f"{device['name']} · {device['host_api']}"
            self.audio_device.addItem(label, device)
            if selected_index is not None and device["index"] == selected_index:
                self.audio_device.setCurrentIndex(self.audio_device.count() - 1)

        if self.audio_device.count() and self.audio_device.currentIndex() < 0:
            self.audio_device.setCurrentIndex(0)
        self.audio_device.blockSignals(False)
        self._select_engine_audio_device_in_combo()
        self._update_audio_status()

    def _select_engine_audio_device_in_combo(self) -> None:
        for i in range(self.audio_device.count()):
            data = self.audio_device.itemData(i)
            if isinstance(data, dict) and data.get("index") == self.engine.device_index:
                self.audio_device.setCurrentIndex(i)
                return

    def _update_audio_status(self) -> None:
        info = self.engine.stream_info()
        self.audio_status.setText(
            f"{info.get('host_api')} · {info.get('sample_rate', 0):g} Hz · "
            f"block {info.get('blocksize')} · {info.get('latency_mode')}"
        )

    def apply_audio_settings(self, _checked: bool = False, silent: bool = False) -> None:
        if self.engine.is_running:
            QMessageBox.information(self, "Аудио", "Останови воспроизведение перед сменой аудио настроек.")
            return

        data = self.audio_device.currentData()
        if not isinstance(data, dict):
            return

        requested_rate = int(self.audio_rate.currentData())
        rate = float(requested_rate) if requested_rate > 0 else float(data["sample_rate"])

        try:
            self.engine.configure_output(
                device_index=int(data["index"]),
                sample_rate=rate,
                blocksize=int(self.audio_block.currentData()),
                latency_mode=str(self.audio_latency.currentData()),
                exclusive=self.audio_exclusive.isChecked(),
            )
            self._update_audio_status()
            if not silent:
                self.status.setText("Аудио настройки применены")
            self._save_app_settings()
        except Exception as exc:
            if not silent:
                QMessageBox.warning(self, "Аудио", str(exc))
            self._select_engine_audio_device_in_combo()
            self._update_audio_status()

    def _apply_saved_audio_device(self, audio: dict) -> None:
        wanted_name = str(audio.get("device_name", ""))
        wanted_host = str(audio.get("host_api", ""))
        for i in range(self.audio_device.count()):
            data = self.audio_device.itemData(i)
            if not isinstance(data, dict):
                continue
            if data.get("name") == wanted_name and data.get("host_api") == wanted_host:
                self.audio_device.setCurrentIndex(i)
                break

        self._combo_data(self.audio_rate, int(audio.get("sample_rate", 0)))
        self._combo_data(self.audio_block, int(audio.get("blocksize", 0)))
        self._combo_data(self.audio_latency, str(audio.get("latency", "low")))
        self.audio_exclusive.setChecked(bool(audio.get("exclusive", False)))
        self.apply_audio_settings(silent=True)

    def export_current_midi(self) -> None:
        dialog = PatternExportDialog("Экспорт MIDI", self)
        if dialog.exec() != QDialog.Accepted:
            return
        repeats, labels = dialog.values()

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт MIDI", "tittytatter.mid", "MIDI (*.mid)")
        if not path:
            return
        try:
            export_midi(path, self.current_pattern(), self.bpm.value(), repeats, labels)
            self.status.setText(f"MIDI: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "MIDI", str(exc))

    def export_current_gp5(self) -> None:
        dialog = PatternExportDialog("Экспорт Guitar Pro 5", self)
        if dialog.exec() != QDialog.Accepted:
            return
        repeats, labels = dialog.values()

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт Guitar Pro 5", "tittytatter.gp5", "Guitar Pro 5 (*.gp5)")
        if not path:
            return
        try:
            export_gp5(path, self.current_pattern(), self.bpm.value(), repeats, labels)
            self.status.setText(f"GP5: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Guitar Pro", str(exc))

    def export_current_wav(self) -> None:
        dialog = AudioExportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        duration, sample_rate, bits = dialog.values()
        if duration <= 0:
            QMessageBox.information(self, "WAV", "Укажи длительность больше нуля.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт WAV", "tittytatter.wav", "WAV (*.wav)")
        if not path:
            return

        try:
            self._config_changed()
            export_wav(
                path,
                self.current_pattern(),
                self.engine.get_config(),
                duration,
                sample_rate,
                bits,
            )
            self.status.setText(f"WAV: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "WAV", str(exc))

    def session(self) -> dict:
        return {
            "version": 4,
            "bpm": self.bpm.value(),
            "pattern": self.current_pattern().to_dict(),
            "practice": {
                "mode": self.mode.currentData(),
                "bars": self.bars.value(),
                "count": self.count.value(),
                "inactive": self.inactive.isChecked(),
                "ramp_warning": self.ramp_warning.isChecked(),
                "trainer": self.tempo_train.isChecked(),
                "step": self.tempo_step.value(),
                "every": self.tempo_every.value(),
                "target": self.tempo_target.value(),
                "timer_enabled": self.practice_timer.isChecked(),
                "timer_minutes": self.timer_minutes.value(),
                "timer_seconds": self.timer_seconds.value(),
            },
            "sound": {
                "ti_on": self.ti_on.isChecked(),
                "ti_sound": self.ti_sound.currentText(),
                "ti_vol": self.ti_vol.value(),
                "ta_on": self.ta_on.isChecked(),
                "ta_sound": self.ta_sound.currentText(),
                "ta_vol": self.ta_vol.value(),
                "metro_on": self.metro_on.isChecked(),
                "accent": self.accent.isChecked(),
                "metro_vol": self.metro_vol.value(),
                "master": self.master.value(),
            },
            "visual_metronome": {
                "size": self.metro_size.value(),
                "needle_color": self.metro_color.name(),
                "flash_color": self.flash_color.name(),
                "flash": self.metro_flash.isChecked(),
                "flash_whole": self.metro_flash_whole.isChecked(),
                "flash_brightness": self.metro_flash_brightness.value(),
                "width": self.metro_width.value(),
                "angle": self.metro_angle.value(),
                "lamps": self.metro_lamps.isChecked(),
            },
        }

    def save_session(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", "tittytatter_session.json", "JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps(self.session(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.apply_session(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception as exc:
            QMessageBox.warning(self, "Сессия", str(exc))

    def apply_session(self, data: dict) -> None:
        self.bpm.setValue(int(data.get("bpm", 60)))
        bar = BarPattern.from_dict(data.get("pattern", {}))

        self.meter_num.blockSignals(True)
        self.meter_den.blockSignals(True)
        self.meter_num.setValue(bar.numerator)
        self.meter_den.setCurrentIndex(max(0, self.meter_den.findData(bar.denominator)))
        self.meter_num.blockSignals(False)
        self.meter_den.blockSignals(False)
        self._rebuild_editors(bar.beats)

        practice = data.get("practice", {})
        self.mode.setCurrentIndex(max(0, self.mode.findData(practice.get("mode", "loop"))))
        self.bars.setValue(int(practice.get("bars", 8)))
        self.count.setValue(int(practice.get("count", 1)))
        self.inactive.setChecked(bool(practice.get("inactive", True)))
        self.ramp_warning.setChecked(bool(practice.get("ramp_warning", True)))
        self.tempo_train.setChecked(bool(practice.get("trainer", False)))
        self.tempo_step.setValue(int(practice.get("step", 2)))
        self.tempo_every.setValue(int(practice.get("every", 4)))
        self.tempo_target.setValue(int(practice.get("target", 140)))
        self.practice_timer.setChecked(bool(practice.get("timer_enabled", False)))
        self.timer_minutes.setValue(int(practice.get("timer_minutes", 10)))
        self.timer_seconds.setValue(int(practice.get("timer_seconds", 0)))

        sound = data.get("sound", {})
        self.ti_on.setChecked(bool(sound.get("ti_on", True)))
        self._combo(self.ti_sound, sound.get("ti_sound", "Wood"))
        self.ti_vol.setValue(int(sound.get("ti_vol", 100)))
        self.ta_on.setChecked(bool(sound.get("ta_on", True)))
        self._combo(self.ta_sound, sound.get("ta_sound", "Low tick"))
        self.ta_vol.setValue(int(sound.get("ta_vol", 70)))
        self._ensure_unique_sound("ti")
        self.metro_on.setChecked(bool(sound.get("metro_on", True)))
        self.accent.setChecked(bool(sound.get("accent", True)))
        self.metro_vol.setValue(int(sound.get("metro_vol", 70)))
        self.master.setValue(int(sound.get("master", 100)))

        vm = data.get("visual_metronome", {})
        self.metro_size.setValue(int(vm.get("size", 100)))
        needle = QColor(str(vm.get("needle_color", vm.get("color", "#e8ebf0"))))
        flash = QColor(str(vm.get("flash_color", "#ffd56a")))
        if needle.isValid():
            self.metro_color = needle
        if flash.isValid():
            self.flash_color = flash
        self.metro_flash.setChecked(bool(vm.get("flash", True)))
        self.metro_flash_whole.setChecked(bool(vm.get("flash_whole", False)))
        self.metro_flash_brightness.setValue(int(vm.get("flash_brightness", 100)))
        self.metro_width.setValue(int(vm.get("width", 4)))
        self.metro_angle.setValue(int(vm.get("angle", 42)))
        self.metro_lamps.setChecked(bool(vm.get("lamps", True)))
        self._refresh_color_samples()
        self._mode_changed()
        self._sync()

    @staticmethod
    def _combo(combo: QComboBox, text: str) -> None:
        index = combo.findText(str(text))
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _combo_data(combo: QComboBox, data) -> None:
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _collect_app_settings(self) -> dict:
        device = self.audio_device.currentData()
        if not isinstance(device, dict):
            device = {}

        geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
        return {
            "geometry": geometry,
            "last_tab": self.tabs.currentIndex(),
            "bpm": self.bpm.value(),
            "meter": {
                "numerator": self.meter_num.value(),
                "denominator": int(self.meter_den.currentData()),
            },
            "practice": {
                "mode": self.mode.currentData(),
                "bars": self.bars.value(),
                "count": self.count.value(),
                "inactive": self.inactive.isChecked(),
                "ramp_warning": self.ramp_warning.isChecked(),
                "tempo_train": self.tempo_train.isChecked(),
                "tempo_step": self.tempo_step.value(),
                "tempo_every": self.tempo_every.value(),
                "tempo_target": self.tempo_target.value(),
                "timer_enabled": self.practice_timer.isChecked(),
                "timer_minutes": self.timer_minutes.value(),
                "timer_seconds": self.timer_seconds.value(),
            },
            "sound": {
                "ti_on": self.ti_on.isChecked(),
                "ti_sound": self.ti_sound.currentText(),
                "ti_vol": self.ti_vol.value(),
                "ta_on": self.ta_on.isChecked(),
                "ta_sound": self.ta_sound.currentText(),
                "ta_vol": self.ta_vol.value(),
                "metro_on": self.metro_on.isChecked(),
                "accent": self.accent.isChecked(),
                "metro_vol": self.metro_vol.value(),
                "master": self.master.value(),
            },
            "visual": {
                "size": self.metro_size.value(),
                "needle_color": self.metro_color.name(),
                "flash_color": self.flash_color.name(),
                "flash": self.metro_flash.isChecked(),
                "flash_whole": self.metro_flash_whole.isChecked(),
                "flash_brightness": self.metro_flash_brightness.value(),
                "width": self.metro_width.value(),
                "angle": self.metro_angle.value(),
                "lamps": self.metro_lamps.isChecked(),
            },
            "game": {
                "enabled": self.game_enabled.isChecked(),
                "ti_key": self.game_ti_key.binding(),
                "ta_key": self.game_ta_key.binding(),
                "hit_sound": self.game_hit_sound.isChecked(),
                "miss_sound": self.game_miss_sound.isChecked(),
                "last_game": dict(self.last_game_stats),
            },
            "picking": {
                "enabled": self.picking_enabled.isChecked(),
                "show_next": self.picking_show_next.isChecked(),
                "highlight_current": self.picking_highlight_current.isChecked(),
                "cue_size": self.picking_cue_size.value(),
            },
            "audio": {
                "device_name": device.get("name", self.engine.device_name),
                "host_api": device.get("host_api", self.engine.host_api_name),
                "sample_rate": int(self.audio_rate.currentData()),
                "blocksize": int(self.audio_block.currentData()),
                "latency": self.audio_latency.currentData(),
                "exclusive": self.audio_exclusive.isChecked(),
            },
        }

    def _save_app_settings(self) -> None:
        try:
            save_settings(self._collect_app_settings())
        except Exception as exc:
            self.status.setText(f"Settings error: {exc}")

    def _restore_app_settings(self) -> None:
        data = self._settings
        if not data:
            self.bpm.setValue(60)
            self._update_audio_status()
            return

        geometry = data.get("geometry")
        if isinstance(geometry, str) and geometry:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
            except Exception:
                pass

        self.bpm.setValue(int(data.get("bpm", 60)))

        meter = data.get("meter", {})
        self.meter_num.blockSignals(True)
        self.meter_den.blockSignals(True)
        self.meter_num.setValue(int(meter.get("numerator", 4)))
        denominator = int(meter.get("denominator", 4))
        index = self.meter_den.findData(denominator)
        self.meter_den.setCurrentIndex(index if index >= 0 else self.meter_den.findData(4))
        self.meter_num.blockSignals(False)
        self.meter_den.blockSignals(False)
        self._rebuild_editors()

        practice = data.get("practice", {})
        self._combo_data(self.mode, practice.get("mode", "loop"))
        self.bars.setValue(int(practice.get("bars", 8)))
        self.count.setValue(int(practice.get("count", 1)))
        self.inactive.setChecked(bool(practice.get("inactive", True)))
        self.ramp_warning.setChecked(bool(practice.get("ramp_warning", True)))
        self.tempo_train.setChecked(bool(practice.get("tempo_train", False)))
        self.tempo_step.setValue(int(practice.get("tempo_step", 2)))
        self.tempo_every.setValue(int(practice.get("tempo_every", 4)))
        self.tempo_target.setValue(int(practice.get("tempo_target", 140)))
        self.practice_timer.setChecked(bool(practice.get("timer_enabled", False)))
        self.timer_minutes.setValue(int(practice.get("timer_minutes", 10)))
        self.timer_seconds.setValue(int(practice.get("timer_seconds", 0)))

        sound = data.get("sound", {})
        self.ti_on.setChecked(bool(sound.get("ti_on", True)))
        self._combo(self.ti_sound, sound.get("ti_sound", "Wood"))
        self.ti_vol.setValue(int(sound.get("ti_vol", 100)))
        self.ta_on.setChecked(bool(sound.get("ta_on", True)))
        self._combo(self.ta_sound, sound.get("ta_sound", "Low tick"))
        self.ta_vol.setValue(int(sound.get("ta_vol", 70)))
        self._ensure_unique_sound("ti")
        self.metro_on.setChecked(bool(sound.get("metro_on", True)))
        self.accent.setChecked(bool(sound.get("accent", True)))
        self.metro_vol.setValue(int(sound.get("metro_vol", 70)))
        self.master.setValue(int(sound.get("master", 100)))

        visual = data.get("visual", {})
        self.metro_size.setValue(int(visual.get("size", 100)))
        needle = QColor(str(visual.get("needle_color", "#e8ebf0")))
        flash = QColor(str(visual.get("flash_color", "#ffd56a")))
        if needle.isValid():
            self.metro_color = needle
        if flash.isValid():
            self.flash_color = flash
        self.metro_flash.setChecked(bool(visual.get("flash", True)))
        self.metro_flash_whole.setChecked(bool(visual.get("flash_whole", False)))
        self.metro_flash_brightness.setValue(int(visual.get("flash_brightness", 100)))
        self.metro_width.setValue(int(visual.get("width", 4)))
        self.metro_angle.setValue(int(visual.get("angle", 42)))
        self.metro_lamps.setChecked(bool(visual.get("lamps", True)))
        self._refresh_color_samples()

        game = data.get("game", {})
        self.game_ti_key.set_binding(str(game.get("ti_key", "F")))
        self.game_ta_key.set_binding(str(game.get("ta_key", "J")))
        self.game_hit_sound.setChecked(bool(game.get("hit_sound", True)))
        self.game_miss_sound.setChecked(bool(game.get("miss_sound", True)))
        saved_last = game.get("last_game", {})
        if isinstance(saved_last, dict):
            self.last_game_stats = {
                "hits": int(saved_last.get("hits", 0)),
                "misses": int(saved_last.get("misses", 0)),
                "accuracy": float(saved_last.get("accuracy", 0.0)),
                "mean_abs_ms": float(saved_last.get("mean_abs_ms", 0.0)),
                "early": int(saved_last.get("early", 0)),
                "late": int(saved_last.get("late", 0)),
                "score": int(saved_last.get("score", 0)),
            }
        self._refresh_last_game_stats()
        self.game_enabled.setChecked(bool(game.get("enabled", False)))
        self._game_mode_toggled(self.game_enabled.isChecked())

        picking = data.get("picking", {})
        self.picking_show_next.setChecked(bool(picking.get("show_next", True)))
        self.picking_highlight_current.setChecked(bool(picking.get("highlight_current", True)))
        self.picking_cue_size.setValue(int(picking.get("cue_size", 52)))
        self.picking_enabled.setChecked(bool(picking.get("enabled", False)))
        self._picking_settings_changed()

        audio = data.get("audio", {})
        self._apply_saved_audio_device(audio)

        last_tab = int(data.get("last_tab", 0))
        self.tabs.setCurrentIndex(max(0, min(self.tabs.count() - 1, last_tab)))
        self._mode_changed()

    def reset_app_settings(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            "Обнулить настройки",
            f"Будет удалён только {SETTINGS_PATH.name}.\nДля подтверждения введи DELETE:",
        )
        if not ok:
            return
        if text.strip() != "DELETE":
            QMessageBox.information(self, "Настройки", "Отмена: слово DELETE не совпало.")
            return

        if not delete_settings():
            QMessageBox.warning(self, "Настройки", "Не удалось удалить файл настроек.")
            return

        self._settings = {}
        self._apply_defaults()
        self.status.setText("Настройки обнулены")

    def _apply_defaults(self) -> None:
        if self.engine.is_running:
            self.engine.stop()

        self.bpm.setValue(60)
        self.meter_num.blockSignals(True)
        self.meter_den.blockSignals(True)
        self.meter_num.setValue(4)
        self.meter_den.setCurrentIndex(self.meter_den.findData(4))
        self.meter_num.blockSignals(False)
        self.meter_den.blockSignals(False)
        self._rebuild_editors()

        self.mode.setCurrentIndex(0)
        self.bars.setValue(8)
        self.count.setValue(1)
        self.inactive.setChecked(True)
        self.ramp_warning.setChecked(True)
        self.tempo_train.setChecked(False)
        self.tempo_step.setValue(2)
        self.tempo_every.setValue(4)
        self.tempo_target.setValue(140)
        self.practice_timer.setChecked(False)
        self.timer_minutes.setValue(10)
        self.timer_seconds.setValue(0)

        self.ti_on.setChecked(True)
        self._combo(self.ti_sound, "Wood")
        self.ti_vol.setValue(100)
        self.ta_on.setChecked(True)
        self._combo(self.ta_sound, "Low tick")
        self.ta_vol.setValue(70)
        self.metro_on.setChecked(True)
        self.accent.setChecked(True)
        self.metro_vol.setValue(70)
        self.master.setValue(100)

        self.metro_color = QColor("#e8ebf0")
        self.flash_color = QColor("#ffd56a")
        self.metro_size.setValue(100)
        self.metro_flash.setChecked(True)
        self.metro_flash_whole.setChecked(False)
        self.metro_flash_brightness.setValue(100)
        self.metro_width.setValue(4)
        self.metro_angle.setValue(42)
        self.metro_lamps.setChecked(True)
        self._refresh_color_samples()

        self.game_enabled.setChecked(False)
        self.game_ti_key.set_binding("key:F")
        self.game_ta_key.set_binding("key:J")
        self.game_hit_sound.setChecked(True)
        self.game_miss_sound.setChecked(True)
        self.last_game_stats = {
            "hits": 0,
            "misses": 0,
            "accuracy": 0.0,
            "mean_abs_ms": 0.0,
            "early": 0,
            "late": 0,
            "score": 0,
        }
        self._refresh_last_game_stats()
        self.visual.set_game_stats(False, 0, 0, [], 0)

        self.picking_show_next.setChecked(True)
        self.picking_highlight_current.setChecked(True)
        self.picking_cue_size.setValue(52)
        self.picking_enabled.setChecked(False)
        self._picking_settings_changed()

        self.audio_rate.setCurrentIndex(self.audio_rate.findData(0))
        self.audio_block.setCurrentIndex(self.audio_block.findData(0))
        self.audio_latency.setCurrentIndex(self.audio_latency.findData("low"))
        self.audio_exclusive.setChecked(False)
        self._select_engine_audio_device_in_combo()

        self.tabs.setCurrentIndex(0)
        self._sync()

    def reset_session(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        self._rebuild_editors()
        self.status.setText("Готов")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.game_active:
            self._game_update_misses(force=False)
            self._finalize_game_stats()
            self._finish_game_log("window_close")
        elif self.game_log is not None:
            self._finish_game_log("window_close")
        self._save_app_settings()
        self.engine.close()
        event.accept()


def main() -> int:
    log_flags = {"-log", "--log"}
    game_log_enabled = any(arg.lower() in log_flags for arg in sys.argv[1:])
    qt_argv = [sys.argv[0]] + [
        arg for arg in sys.argv[1:] if arg.lower() not in log_flags
    ]

    app = QApplication(qt_argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    window = MainWindow(game_log_enabled=game_log_enabled)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
