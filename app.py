from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
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
    QGroupBox,
    QHBoxLayout,
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

APP_NAME = "TittyTatter"
VERSION_FILE = Path(__file__).with_name("VERSION")
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.1"

STATE_TEXT = {TI: TI_MARK, TA: "ТА", OFF: "·"}
STATE_STYLE = {
    TI: "background:#3169c6;color:white;font-weight:700;border:2px solid #72a5ff;border-radius:18px;padding:8px;",
    TA: "background:#42464f;color:white;font-weight:700;border:2px solid #666b75;border-radius:8px;padding:8px;",
    OFF: "background:#22252a;color:#8e949e;border:2px solid #343941;border-radius:8px;padding:8px;",
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
        self.flash_enabled = True
        self.flash_brightness = 100
        self.needle_width = 4
        self.show_beat_lamps = True
        self.swing_angle = 42
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
        flash_enabled: bool | None = None,
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
        if flash_enabled is not None:
            self.flash_enabled = bool(flash_enabled)
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

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        pivot_y = h - (25 if self.show_beat_lamps else 14)
        length = min(0.66 * h, h - 36.0)
        painter.fillRect(self.rect(), QColor(28, 31, 36))

        if self.running:
            direction = 1.0 if self.beat % 2 == 0 else -1.0
            sweep = (-1.0 + 2.0 * self.phase) * direction
        else:
            sweep = 0.0

        angle = math.radians(float(self.swing_angle) * sweep)
        tip_x = cx + math.sin(angle) * length
        tip_y = pivot_y - math.cos(angle) * length

        flash = 0.0
        if self.running and self.flash_enabled and self.phase < 0.18:
            flash = (1.0 - self.phase / 0.18) * (self.flash_brightness / 100.0)

        if self.flash_enabled:
            radius = max(18, int(26 * self.scale_percent / 100))
            alpha = max(12, min(240, int(24 + 150 * flash)))
            flash_color = QColor(self.needle_color)
            flash_color.setAlpha(alpha)
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
            painter.drawText(self.rect().adjusted(0, 0, -14, 0), Qt.AlignRight | Qt.AlignTop, self.timer_text)


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
            self.mute.setToolTip("Эта доля перекрыта длинной нотой предыдущей доли")
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
        self.quality.addItem("Standard · 44.1 kHz / 16-bit", (44_100, 16))
        self.quality.addItem("High · 48 kHz / 24-bit", (48_000, 24))
        self.quality.addItem("Studio · 96 kHz / 24-bit", (96_000, 24))
        self.quality.addItem("Studio · 96 kHz / 32-bit PCM", (96_000, 32))
        self.quality.setCurrentIndex(1)
        form.addRow("Качество:", self.quality)
        layout.addLayout(form)

        note = QLabel("Экспортируется текущий рисунок в петле с текущими звуками, BPM и метрономом.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#8f96a3;")
        layout.addWidget(note)

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
        self.resize(1240, 840)
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.engine = AudioEngine()
        self.tap_times: list[float] = []
        self.metro_color = QColor("#e8ebf0")
        self.editors: list[BeatEditor] = []

        self._build_ui()
        self._shortcuts()
        self._restore()
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

        random_row = QHBoxLayout()
        self.random_four = QPushButton()
        self.random_four.clicked.connect(self.randomize_beats)
        random_row.addWidget(self.random_four)
        random_row.addStretch()
        out.addLayout(random_row)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_practice_tab(), "Тренировка")
        self.tabs.addTab(self._build_sound_tab(), "Звук")
        self.tabs.addTab(self._build_metronome_tab(), "Метроном")
        self.tabs.addTab(self._build_export_tab(), "Экспорт")
        out.addWidget(self.tabs)

        footer = QHBoxLayout()
        save = QPushButton("Сохранить сессию")
        load = QPushButton("Загрузить сессию")
        reset = QPushButton("Сброс")
        save.clicked.connect(self.save_session)
        load.clicked.connect(self.load_session)
        reset.clicked.connect(self.reset)
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
        form.addRow("Режим тренировки:", self.mode)

        self.bars = QSpinBox()
        self.bars.setRange(1, 64)
        self.bars.setValue(8)
        form.addRow("Тактов на этап:", self.bars)

        self.count = QSpinBox()
        self.count.setRange(0, 8)
        self.count.setValue(1)
        form.addRow("Count-in, тактов:", self.count)

        self.inactive = QCheckBox("ТА-пульс на временно незаполненных долях")
        self.inactive.setChecked(True)
        form.addRow("", self.inactive)
        root.addWidget(main, 1)

        trainer = QGroupBox("Разгон темпа")
        form = QFormLayout(trainer)
        self.tempo_train = QCheckBox("Включить tempo trainer")
        form.addRow("", self.tempo_train)

        self.tempo_step = QSpinBox()
        self.tempo_step.setRange(1, 20)
        self.tempo_step.setValue(2)
        form.addRow("Шаг BPM:", self.tempo_step)

        self.tempo_every = QSpinBox()
        self.tempo_every.setRange(1, 64)
        self.tempo_every.setValue(4)
        form.addRow("Менять каждые, тактов:", self.tempo_every)

        self.tempo_target = QSpinBox()
        self.tempo_target.setRange(20, 320)
        self.tempo_target.setValue(140)
        form.addRow("Целевой BPM:", self.tempo_target)
        root.addWidget(trainer, 1)

        timer_box = QGroupBox("Таймер")
        form = QFormLayout(timer_box)
        self.practice_timer = QCheckBox("Остановить тренировку по таймеру")
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
        form = QFormLayout(tab)

        self.ti_on = QCheckBox(TI_MARK)
        self.ti_on.setChecked(True)
        self.ti_sound = QComboBox()
        self.ti_sound.addItems(SOUND_NAMES)
        self._combo(self.ti_sound, "Wood")
        self.ti_vol = self._volume_slider(100)

        ti_row = QWidget()
        ti_layout = QHBoxLayout(ti_row)
        ti_layout.setContentsMargins(0, 0, 0, 0)
        ti_layout.addWidget(self.ti_on)
        ti_layout.addWidget(self.ti_sound, 1)
        ti_layout.addWidget(self.ti_vol, 2)
        form.addRow("(ТИ):", ti_row)

        self.ta_on = QCheckBox("ТА")
        self.ta_sound = QComboBox()
        self.ta_sound.addItems(SOUND_NAMES)
        self._combo(self.ta_sound, "Low tick")
        self.ta_vol = self._volume_slider(70)

        ta_row = QWidget()
        ta_layout = QHBoxLayout(ta_row)
        ta_layout.setContentsMargins(0, 0, 0, 0)
        ta_layout.addWidget(self.ta_on)
        ta_layout.addWidget(self.ta_sound, 1)
        ta_layout.addWidget(self.ta_vol, 2)
        form.addRow("ТА:", ta_row)

        self.metro_on = QCheckBox("Звук метронома")
        self.metro_on.setChecked(True)
        self.accent = QCheckBox("Акцент первой доли")
        self.accent.setChecked(True)
        metro_row = QWidget()
        metro_layout = QHBoxLayout(metro_row)
        metro_layout.setContentsMargins(0, 0, 0, 0)
        metro_layout.addWidget(self.metro_on)
        metro_layout.addWidget(self.accent)
        form.addRow("Метроном:", metro_row)

        self.metro_vol = self._volume_slider(70)
        form.addRow("Громкость метронома:", self.metro_vol)

        self.master = self._volume_slider(100)
        form.addRow("Master:", self.master)

        hint = QLabel("Все уровни 0–200%. Один и тот же звук нельзя назначить одновременно на (ТИ) и ТА.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8f96a3;")
        form.addRow("", hint)
        return tab

    def _build_metronome_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        visual = QGroupBox("Визуальный метроном")
        form = QFormLayout(visual)

        self.metro_size = QSlider(Qt.Horizontal)
        self.metro_size.setRange(60, 180)
        self.metro_size.setValue(100)
        form.addRow("Размер:", self.metro_size)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.metro_color_btn = QPushButton("Выбрать цвет")
        self.metro_color_btn.clicked.connect(self.choose_metronome_color)
        self.metro_color_sample = QLabel("      ")
        self.metro_color_sample.setFixedWidth(42)
        color_layout.addWidget(self.metro_color_btn)
        color_layout.addWidget(self.metro_color_sample)
        color_layout.addStretch()
        form.addRow("Цвет иглы:", color_row)

        self.metro_flash = QCheckBox("Мигалка на ударе")
        self.metro_flash.setChecked(True)
        form.addRow("", self.metro_flash)

        self.metro_flash_brightness = QSlider(Qt.Horizontal)
        self.metro_flash_brightness.setRange(0, 200)
        self.metro_flash_brightness.setValue(100)
        form.addRow("Яркость мигалки:", self.metro_flash_brightness)

        self.metro_width = QSpinBox()
        self.metro_width.setRange(1, 12)
        self.metro_width.setValue(4)
        form.addRow("Толщина иглы:", self.metro_width)

        self.metro_angle = QSpinBox()
        self.metro_angle.setRange(15, 70)
        self.metro_angle.setValue(42)
        self.metro_angle.setSuffix("°")
        form.addRow("Размах иглы:", self.metro_angle)

        self.metro_lamps = QCheckBox("Показывать индикаторы долей")
        self.metro_lamps.setChecked(True)
        form.addRow("", self.metro_lamps)
        root.addWidget(visual, 1)

        hint = QGroupBox("Подсказка")
        hint_layout = QVBoxLayout(hint)
        text = QLabel(
            "Игла синхронизирована с sample-clock аудиодвижка. "
            "При включенном таймере оставшееся время показывается справа в зоне метронома."
        )
        text.setWordWrap(True)
        hint_layout.addWidget(text)
        hint_layout.addStretch()
        root.addWidget(hint, 1)

        for widget in (
            self.metro_size,
            self.metro_flash,
            self.metro_flash_brightness,
            self.metro_width,
            self.metro_angle,
            self.metro_lamps,
        ):
            signal = getattr(widget, "valueChanged", None) or getattr(widget, "toggled", None)
            if signal:
                signal.connect(self._visual_config_changed)

        self._refresh_color_sample()
        return tab

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        midi = QPushButton("Экспорт MIDI (.mid)")
        midi.clicked.connect(self.export_current_midi)
        gp = QPushButton("Экспорт Guitar Pro 5 (.gp5)")
        gp.clicked.connect(self.export_current_gp5)
        wav = QPushButton("Экспорт аудио (.wav)")
        wav.clicked.connect(self.export_current_wav)

        layout.addWidget(midi)
        layout.addWidget(gp)
        layout.addWidget(wav)

        info = QLabel(
            "MIDI/GP5 экспортируют текущий такт. (ТИ) = E3, 5-я струна, 7-й лад. "
            "ТА = глушеная 6-я струна. GP5 использует Overdriven Guitar и текстовые подписи."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#8f96a3;")
        layout.addWidget(info)
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
        color = QColorDialog.getColor(self.metro_color, self, "Цвет визуального метронома")
        if color.isValid():
            self.metro_color = color
            self._refresh_color_sample()
            self._visual_config_changed()

    def _refresh_color_sample(self) -> None:
        self.metro_color_sample.setStyleSheet(
            f"background:{self.metro_color.name()};border:1px solid #666;border-radius:4px;"
        )

    def _visual_config_changed(self, *_args) -> None:
        self.visual.configure(
            scale_percent=self.metro_size.value(),
            needle_color=self.metro_color,
            flash_enabled=self.metro_flash.isChecked(),
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

        self.beats_group.setTitle(f"Такт {numerator}/{denominator} — сетка выбирается отдельно для каждой доли")
        self.random_four.setText(f"🎲 Случайные {numerator}")
        self._update_mode_labels()
        self._mode_changed()
        self._pattern_changed()

    def _meter_changed(self, *_args) -> None:
        old = [editor.pattern() for editor in self.editors]
        if self.engine.is_running:
            self.engine.stop()
            self.play.setText("▶ Старт")
            self.clear_playhead()
        self._rebuild_editors(old)

    def _update_mode_labels(self) -> None:
        numerator, denominator = self._meter()
        self.mode.setItemText(0, f"Петля {numerator}/{denominator}")
        self.mode.setItemText(1, f"Разгон 1 → 2 → … → {numerator} долей")
        self.mode.setItemText(2, f"Разгон 2 → {numerator} долей")

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
                self._stop_playback("Готов")
            else:
                if self.practice_timer.isChecked() and self._timer_limit() <= 0:
                    QMessageBox.information(self, "Таймер", "Укажи длительность тренировки больше нуля.")
                    return
                self._sync()
                self.engine.start()
                self.play.setText("■ Стоп")
        except Exception as exc:
            self.engine.stop()
            self.play.setText("▶ Старт")
            QMessageBox.critical(self, "Ошибка аудио", str(exc))

    def _stop_playback(self, message: str) -> None:
        self.engine.stop()
        self.play.setText("▶ Старт")
        self.clear_playhead()
        self._set_ramp_visual(self.meter_num.value())
        numerator, denominator = self._meter()
        timer_text = "00:00" if message == "Тренировка завершена" and self.practice_timer.isChecked() else ""
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
                self._stop_playback("Тренировка завершена")
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

        if st["count_in"]:
            self.status.setText(f"COUNT-IN · {numerator}/{denominator} · {bpm} BPM")
            self._set_ramp_visual(numerator)
            self.highlight(beat, None)
            return

        self._set_ramp_visual(active_beats)
        stage = f"{active_beats}/{numerator}" if self.mode.currentData() != "loop" else f"{numerator}/{denominator}"
        self.status.setText(
            f"Такт {st['bar']} · этап {stage} · доля {beat + 1} · {bpm} BPM"
            + (f" · {timer_text}" if timer_text else "")
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

    def export_current_midi(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт MIDI", "tittytatter.mid", "MIDI (*.mid)")
        if not path:
            return
        try:
            export_midi(path, self.current_pattern(), self.bpm.value())
            self.status.setText(f"MIDI сохранён: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка экспорта MIDI", str(exc))

    def export_current_gp5(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт Guitar Pro 5", "tittytatter.gp5", "Guitar Pro 5 (*.gp5)")
        if not path:
            return
        try:
            export_gp5(path, self.current_pattern(), self.bpm.value())
            self.status.setText(f"GP5 сохранён: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка экспорта Guitar Pro", str(exc))

    def export_current_wav(self) -> None:
        dialog = AudioExportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        duration, sample_rate, bits = dialog.values()
        if duration <= 0:
            QMessageBox.information(self, "Экспорт WAV", "Укажи длительность больше нуля.")
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
            self.status.setText(f"WAV сохранён: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка экспорта WAV", str(exc))

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
                "color": self.metro_color.name(),
                "flash": self.metro_flash.isChecked(),
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
            QMessageBox.warning(self, "Ошибка", str(exc))

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
        self.ta_on.setChecked(bool(sound.get("ta_on", False)))
        self._combo(self.ta_sound, sound.get("ta_sound", "Low tick"))
        self.ta_vol.setValue(int(sound.get("ta_vol", 70)))
        self._ensure_unique_sound("ti")
        self.metro_on.setChecked(bool(sound.get("metro_on", True)))
        self.accent.setChecked(bool(sound.get("accent", True)))
        self.metro_vol.setValue(int(sound.get("metro_vol", 70)))
        self.master.setValue(int(sound.get("master", 100)))

        vm = data.get("visual_metronome", {})
        self.metro_size.setValue(int(vm.get("size", 100)))
        color = QColor(str(vm.get("color", "#e8ebf0")))
        if color.isValid():
            self.metro_color = color
        self.metro_flash.setChecked(bool(vm.get("flash", True)))
        self.metro_flash_brightness.setValue(int(vm.get("flash_brightness", 100)))
        self.metro_width.setValue(int(vm.get("width", 4)))
        self.metro_angle.setValue(int(vm.get("angle", 42)))
        self.metro_lamps.setChecked(bool(vm.get("lamps", True)))
        self._refresh_color_sample()
        self._mode_changed()
        self._sync()

    @staticmethod
    def _combo(combo: QComboBox, text: str) -> None:
        index = combo.findText(str(text))
        if index >= 0:
            combo.setCurrentIndex(index)

    def reset(self) -> None:
        self.engine.stop()
        self.play.setText("▶ Старт")
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
        self.practice_timer.setChecked(False)
        self.timer_minutes.setValue(10)
        self.timer_seconds.setValue(0)

        self.ti_on.setChecked(True)
        self._combo(self.ti_sound, "Wood")
        self.ti_vol.setValue(100)
        self.ta_on.setChecked(False)
        self._combo(self.ta_sound, "Low tick")
        self.ta_vol.setValue(70)
        self.metro_on.setChecked(True)
        self.metro_vol.setValue(70)
        self.master.setValue(100)

        self.metro_color = QColor("#e8ebf0")
        self.metro_size.setValue(100)
        self.metro_flash.setChecked(True)
        self.metro_flash_brightness.setValue(100)
        self.metro_width.setValue(4)
        self.metro_angle.setValue(42)
        self.metro_lamps.setChecked(True)
        self._refresh_color_sample()
        self._sync()

    def _restore(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.bpm.setValue(60)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
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
