from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QTimer, Signal
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
    QKeySequenceEdit,
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
from model import BarPattern, BeatPattern
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

GAME_WINDOWS_MS = {
    "low": 180,
    "mid": 110,
    "high": 60,
}


class StepButton(QPushButton):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.state = OFF
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

    def refresh(self) -> None:
        extra = "border:3px solid #ffd56a;" if self.playing else ""
        self.setText(STATE_TEXT[self.state])
        self.setStyleSheet(f"QPushButton{{{STATE_STYLE[self.state]}{extra}}}")


class MetronomeVisual(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.phase = 0.0
        self.beat = 0
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
        self.game_recent: list[float] = []
        self.game_feedback_kind = ""
        self.game_feedback_main = ""
        self.game_feedback_detail = ""
        self.game_feedback_until = 0.0
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
        self.active_beats = max(0, min(self.numerator, int(active_beats)))
        self.count_in = bool(count_in)
        self.running = bool(running)
        self.timer_text = str(timer_text)
        self.update()

    def set_game_stats(self, visible: bool, hits: int, misses: int, recent: list[float]) -> None:
        self.game_visible = bool(visible)
        self.game_hits = int(hits)
        self.game_misses = int(misses)
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

        if self.game_visible:
            self._paint_game_panels(painter)

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
        painter.drawText(left, top, f"GAME  hit {self.game_hits}  miss {self.game_misses}  {accuracy:.0f}%")

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
        self.body.setEnabled(not self._span_covered)
        self._refresh_mute_enabled()
        self._refresh_visual_state()

    def set_ramp_inactive(self, value: bool) -> None:
        self._ramp_inactive = bool(value)
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
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1240, 860)

        self.engine = AudioEngine()
        self.tap_times: list[float] = []
        self.metro_color = QColor("#e8ebf0")
        self.flash_color = QColor("#ffd56a")
        self.editors: list[BeatEditor] = []
        self._settings = load_settings()

        self.game_active = False
        self.game_stats_visible = False
        self.game_hits = 0
        self.game_misses = 0
        self.game_recent: list[float] = []
        self.game_offsets_ms: list[float] = []
        self.game_pending: list[dict[str, object]] = []
        self.last_game_stats = {
            "hits": 0,
            "misses": 0,
            "accuracy": 0.0,
            "mean_abs_ms": 0.0,
            "early": 0,
            "late": 0,
        }

        self._build_ui()
        self._shortcuts()
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

        self.game_difficulty = QComboBox()
        self.game_difficulty.addItem("Low · ±180 ms", "low")
        self.game_difficulty.addItem("Mid · ±110 ms", "mid")
        self.game_difficulty.addItem("High · ±60 ms", "high")
        self.game_difficulty.setCurrentIndex(1)
        form.addRow("Сложность:", self.game_difficulty)

        self.game_start = QPushButton("▶ Запустить игру")
        self.game_start.setEnabled(False)
        self.game_start.clicked.connect(self.toggle_game)
        form.addRow("", self.game_start)
        root.addWidget(mode_box, 1)

        controls_box = QGroupBox("Управление")
        controls = QFormLayout(controls_box)
        self.game_ti_key = QKeySequenceEdit(QKeySequence("F"))
        self.game_ti_key.setMaximumSequenceLength(1)
        controls.addRow("(ТИ):", self.game_ti_key)

        self.game_ta_key = QKeySequenceEdit(QKeySequence("J"))
        self.game_ta_key.setMaximumSequenceLength(1)
        controls.addRow("ТА:", self.game_ta_key)
        root.addWidget(controls_box, 1)

        stats_box = QGroupBox("Последняя игра")
        stats = QFormLayout(stats_box)
        self.last_game_hits = QLabel("0")
        self.last_game_misses = QLabel("0")
        self.last_game_accuracy = QLabel("—")
        self.last_game_timing = QLabel("—")
        self.last_game_balance = QLabel("—")
        stats.addRow("Попадания:", self.last_game_hits)
        stats.addRow("Промахи:", self.last_game_misses)
        stats.addRow("Точность:", self.last_game_accuracy)
        stats.addRow("Среднее |Δ|:", self.last_game_timing)
        stats.addRow("Рано / поздно:", self.last_game_balance)
        root.addWidget(stats_box, 1)

        self._refresh_last_game_stats()
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
        self._pattern_changed()

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
        numerator, denominator = self._meter()
        timer_text = "00:00" if timer_finished and self.practice_timer.isChecked() else ""
        self.visual.set_state(
            phase=0.0,
            beat=0,
            active_beats=numerator,
            numerator=numerator,
            denominator=denominator,
            count_in=False,
            running=False,
            timer_text=timer_text,
        )
        self.status.setText(message)
        if timer_finished:
            self.engine.play_notification("Bell", 0.9)

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
        self.game_stats_visible = enabled
        self.game_start.setEnabled(enabled)

        if not enabled:
            if self.game_active:
                self.stop_game("Игра остановлена")
            self.visual.set_game_stats(False, self.game_hits, self.game_misses, self.game_recent)
            self.visual.clear_game_feedback()
        else:
            self.visual.set_game_stats(True, self.game_hits, self.game_misses, self.game_recent)

    def toggle_game(self) -> None:
        if not self.game_enabled.isChecked():
            return

        if self.game_active:
            self.stop_game("Игра остановлена")
            return

        ti_key = self._configured_game_key(self.game_ti_key)
        ta_key = self._configured_game_key(self.game_ta_key)
        if not ti_key or not ta_key:
            QMessageBox.information(self, "Игра", "Назначь клавиши для (ТИ) и ТА.")
            return
        if ti_key == ta_key:
            QMessageBox.information(self, "Игра", "Клавиши (ТИ) и ТА должны отличаться.")
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
        self.game_difficulty.setEnabled(False)
        self.engine.start_game_tracking()
        self.engine.start()
        self.play.setText("■ Стоп")
        self.visual.set_game_stats(True, 0, 0, [])
        self.status.setText("Игра · COUNT-IN")

    def stop_game(self, message: str) -> None:
        self._game_update_misses(force=False)
        self._finalize_game_stats()
        self.game_active = False
        self.game_start.setText("▶ Запустить игру")
        self.game_ti_key.setEnabled(True)
        self.game_ta_key.setEnabled(True)
        self.game_difficulty.setEnabled(True)
        self._stop_playback(message)
        self.visual.set_game_stats(
            self.game_enabled.isChecked(),
            self.game_hits,
            self.game_misses,
            self.game_recent,
        )

    def _reset_game_stats(self) -> None:
        self.game_hits = 0
        self.game_misses = 0
        self.game_recent = []
        self.game_offsets_ms = []
        self.game_pending = []
        self.engine.drain_game_targets()
        self.visual.clear_game_feedback()

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
        }
        self._refresh_last_game_stats()

    def _refresh_last_game_stats(self) -> None:
        if not hasattr(self, "last_game_hits"):
            return
        stats = self.last_game_stats
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        total = hits + misses
        self.last_game_hits.setText(str(hits))
        self.last_game_misses.setText(str(misses))
        self.last_game_accuracy.setText(f"{float(stats.get('accuracy', 0.0)):.1f}%" if total else "—")
        self.last_game_timing.setText(
            f"{float(stats.get('mean_abs_ms', 0.0)):.1f} ms" if hits else "—"
        )
        self.last_game_balance.setText(
            f"{int(stats.get('early', 0))} / {int(stats.get('late', 0))}" if hits else "—"
        )

    def _game_window_seconds(self) -> float:
        key = str(self.game_difficulty.currentData())
        return GAME_WINDOWS_MS.get(key, 110) / 1000.0

    def _drain_game_targets(self) -> None:
        for dac_time, state, bar, beat, sub in self.engine.drain_game_targets():
            self.game_pending.append({
                "time": float(dac_time),
                "state": str(state),
                "bar": int(bar),
                "beat": int(beat),
                "sub": int(sub),
            })
        self.game_pending.sort(key=lambda item: float(item["time"]))

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
        show_feedback: bool = True,
    ) -> None:
        if hit:
            self.game_hits += 1
            self.game_recent.append(max(0.0, min(1.0, quality)))
            if offset_ms is not None:
                self.game_offsets_ms.append(float(offset_ms))
            if show_feedback:
                timing = self._timing_description(float(offset_ms or 0.0))
                self.visual.set_game_feedback("hit", "HIT", timing)
        else:
            self.game_misses += 1
            self.game_recent.append(0.0)
            if show_feedback:
                self.visual.set_game_feedback("miss", "MISS", detail or "промах")

        self.game_recent = self.game_recent[-28:]
        self.visual.set_game_stats(
            self.game_enabled.isChecked(),
            self.game_hits,
            self.game_misses,
            self.game_recent,
        )

    def _game_update_misses(self, force: bool = False) -> None:
        self._drain_game_targets()
        if not self.game_pending:
            return
        now = self.engine.stream_time()
        window = self._game_window_seconds()
        while self.game_pending:
            target_time = float(self.game_pending[0]["time"])
            if not force and target_time >= now - window:
                break
            target = self.game_pending.pop(0)
            expected = TI_MARK if target["state"] == TI else "ТА"
            self._record_game_result(
                False,
                0.0,
                detail=f"пропуск · ожидалось {expected}",
                show_feedback=not force,
            )

    @staticmethod
    def _configured_game_key(editor: QKeySequenceEdit) -> str:
        return editor.keySequence().toString().strip().upper()

    def _handle_game_input(self, state: str) -> None:
        if not self.game_active:
            return
        st = self.engine.status()
        if st["count_in"]:
            return

        self._drain_game_targets()
        now = self.engine.stream_time()
        window = self._game_window_seconds()
        if now <= 0:
            return

        within: list[tuple[float, int]] = []
        matching: list[tuple[float, int]] = []
        for index, target in enumerate(self.game_pending):
            signed = now - float(target["time"])
            distance = abs(signed)
            if distance <= window:
                within.append((distance, index))
                if target["state"] == state:
                    matching.append((distance, index))

        if matching:
            _distance, index = min(matching, key=lambda pair: pair[0])
            target = self.game_pending.pop(index)
            offset = now - float(target["time"])
            quality = max(0.0, 1.0 - abs(offset) / window)
            self._record_game_result(
                True,
                quality,
                offset_ms=offset * 1000.0,
            )
        elif within:
            _distance, index = min(within, key=lambda pair: pair[0])
            target = self.game_pending.pop(index)
            offset_ms = (now - float(target["time"])) * 1000.0
            expected = TI_MARK if target["state"] == TI else "ТА"
            entered = TI_MARK if state == TI else "ТА"
            self._record_game_result(
                False,
                0.0,
                detail=f"{entered} вместо {expected} · {self._timing_description(offset_ms)}",
            )
        else:
            entered = TI_MARK if state == TI else "ТА"
            self._record_game_result(False, 0.0, detail=f"{entered} · вне окна")

    def keyPressEvent(self, event) -> None:
        if self.game_active and not event.isAutoRepeat():
            pressed = QKeySequence(event.keyCombination()).toString().strip().upper()
            if pressed == self._configured_game_key(self.game_ti_key):
                self._handle_game_input(TI)
                event.accept()
                return
            if pressed == self._configured_game_key(self.game_ta_key):
                self._handle_game_input(TA)
                event.accept()
                return
        super().keyPressEvent(event)

    def _poll(self) -> None:
        st = self.engine.status()
        if not st["running"]:
            return

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
                    self.game_active = False
                    self.game_start.setText("▶ Запустить игру")
                    self.game_ti_key.setEnabled(True)
                    self.game_ta_key.setEnabled(True)
                    self.game_difficulty.setEnabled(True)
                self._stop_playback("Тренировка завершена", timer_finished=True)
                self.visual.set_game_stats(
                    self.game_enabled.isChecked(),
                    self.game_hits,
                    self.game_misses,
                    self.game_recent,
                )
                return
            timer_text = self._time_text(remaining)

        self.visual.set_state(
            phase=float(st["beat_phase"]),
            beat=int(st["beat"]),
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
            self.status.setText(f"COUNT-IN · {numerator}/{denominator} · {bpm} BPM")
            self._set_ramp_visual(numerator)
            self.highlight(beat, None)
            return

        self._set_ramp_visual(active_beats)
        stage = f"{active_beats}/{numerator}" if self.mode.currentData() != "loop" else f"{numerator}/{denominator}"
        game_text = f" · hit {self.game_hits} miss {self.game_misses}" if self.game_active else ""
        self.status.setText(
            f"Такт {st['bar']} · {stage} · доля {beat + 1} · {bpm} BPM"
            + (f" · {timer_text}" if timer_text else "")
            + game_text
        )
        self.highlight(beat, int(st["sub"]))

    def _set_ramp_visual(self, active_beats: int) -> None:
        ramp = self.mode.currentData() != "loop" and self.engine.is_running
        for i, editor in enumerate(self.editors):
            editor.set_ramp_inactive(ramp and i >= active_beats)

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
            "version": 3,
            "bpm": self.bpm.value(),
            "pattern": self.current_pattern().to_dict(),
            "practice": {
                "mode": self.mode.currentData(),
                "bars": self.bars.value(),
                "count": self.count.value(),
                "inactive": self.inactive.isChecked(),
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
                "ti_key": self.game_ti_key.keySequence().toString(),
                "ta_key": self.game_ta_key.keySequence().toString(),
                "difficulty": self.game_difficulty.currentData(),
                "last_game": dict(self.last_game_stats),
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
        self.game_ti_key.setKeySequence(QKeySequence(str(game.get("ti_key", "F"))))
        self.game_ta_key.setKeySequence(QKeySequence(str(game.get("ta_key", "J"))))
        self._combo_data(self.game_difficulty, game.get("difficulty", "mid"))
        saved_last = game.get("last_game", {})
        if isinstance(saved_last, dict):
            self.last_game_stats = {
                "hits": int(saved_last.get("hits", 0)),
                "misses": int(saved_last.get("misses", 0)),
                "accuracy": float(saved_last.get("accuracy", 0.0)),
                "mean_abs_ms": float(saved_last.get("mean_abs_ms", 0.0)),
                "early": int(saved_last.get("early", 0)),
                "late": int(saved_last.get("late", 0)),
            }
        self._refresh_last_game_stats()
        self.game_enabled.setChecked(bool(game.get("enabled", False)))
        self._game_mode_toggled(self.game_enabled.isChecked())

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
        self.game_ti_key.setKeySequence(QKeySequence("F"))
        self.game_ta_key.setKeySequence(QKeySequence("J"))
        self.game_difficulty.setCurrentIndex(self.game_difficulty.findData("mid"))
        self.last_game_stats = {
            "hits": 0,
            "misses": 0,
            "accuracy": 0.0,
            "mean_abs_ms": 0.0,
            "early": 0,
            "late": 0,
        }
        self._refresh_last_game_stats()
        self.visual.set_game_stats(False, 0, 0, [])

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
        self._save_app_settings()
        self.engine.close()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
