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
    QFileDialog,
    QFormLayout,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from audio_engine import AudioEngine
from model import BarPattern, BeatPattern
from presets import (
    CORE_PRACTICE_PRESETS,
    GRID_SPECS,
    OFF,
    TA,
    TI,
    TI_MARK,
    CellPreset,
    grid_spec,
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
        self.count_in = False
        self.running = False
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

    def set_state(self, *, phase: float, beat: int, active_beats: int, count_in: bool, running: bool) -> None:
        self.phase = max(0.0, min(0.999, float(phase)))
        self.beat = max(0, min(3, int(beat)))
        self.active_beats = max(0, min(4, int(active_beats)))
        self.count_in = bool(count_in)
        self.running = bool(running)
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
            lamp_y = h - 12
            gap = 34
            start_x = cx - gap * 1.5
            for i in range(4):
                x = start_x + i * gap
                if not self.count_in and i >= self.active_beats:
                    color = QColor(80, 84, 90)
                elif self.running and i == self.beat:
                    color = QColor(self.needle_color)
                else:
                    color = QColor(155, 162, 172)
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(x - 6), int(lamp_y - 6), 12, 12)

        painter.setPen(QColor(175, 181, 190))
        painter.drawText(12, 23, "COUNT-IN" if self.count_in and self.running else "4/4")


class BeatEditor(QGroupBox):
    changed = Signal()

    def __init__(self, number: int) -> None:
        super().__init__()
        self.beat_index = number - 1
        self._span_covered = False
        self._ramp_inactive = False
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)

        box = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel(f"Доля {number}")
        title.setStyleSheet("font-weight:700;font-size:14px;")
        header.addWidget(title)
        header.addStretch()

        self.mute = QToolButton()
        self.mute.setText("Mute")
        self.mute.setCheckable(True)
        self.mute.setToolTip("Сделать эту долю полностью тихой")
        self.mute.setStyleSheet(
            "QToolButton{padding:3px 9px;border:1px solid #555b66;border-radius:9px;color:#b8bec8;}"
            "QToolButton:checked{background:#7d3b3b;border-color:#d66a6a;color:white;font-weight:700;}"
        )
        self.mute.toggled.connect(lambda _checked: self.changed.emit())
        header.addWidget(self.mute)
        box.addLayout(header)

        row = QHBoxLayout()
        row.addWidget(QLabel("Сетка:"))
        self.grid = QComboBox()
        for spec in GRID_SPECS:
            self.grid.addItem(spec.label, spec.key)
        self._apply_grid_item_constraints()
        row.addWidget(self.grid, 1)
        box.addLayout(row)

        self.preset = QComboBox()
        self.preset.setToolTip("Выбор рисунка применяется сразу")
        box.addWidget(self.preset)

        self.steps_row = QHBoxLayout()
        self.steps = [StepButton() for _ in range(8)]
        for button in self.steps:
            button.changed.connect(self.changed.emit)
            self.steps_row.addWidget(button)
        box.addLayout(self.steps_row)

        self.grid.currentIndexChanged.connect(self._grid_changed)
        self.preset.activated.connect(self._preset_activated)
        self.set_pattern(BeatPattern("sixteenth", [TI, TA, TA, TA]))

    def _apply_grid_item_constraints(self) -> None:
        model = self.grid.model()
        for i in range(self.grid.count()):
            key = self.grid.itemData(i)
            allowed = True
            if key == "whole":
                allowed = self.beat_index == 0
            elif key == "half":
                allowed = self.beat_index in (0, 2)
            item = model.item(i)
            if item is not None:
                item.setEnabled(allowed)

    def _grid_allowed(self, key: str) -> bool:
        if key == "whole":
            return self.beat_index == 0
        if key == "half":
            return self.beat_index in (0, 2)
        return True

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
        self.preset.blockSignals(False)

    def _grid_changed(self) -> None:
        key = str(self.grid.currentData())
        if not self._grid_allowed(key):
            self.grid.setCurrentIndex(self.grid.findData("quarter"))
            return

        spec = grid_spec(key)
        self._reload_presets()
        for i, button in enumerate(self.steps):
            button.setVisible(i < spec.steps)
            if i >= spec.steps:
                button.set_state(OFF)
        self.changed.emit()

    def _preset_activated(self, index: int) -> None:
        preset = self.preset.itemData(index)
        if isinstance(preset, CellPreset):
            muted = self.mute.isChecked()
            self.set_pattern(BeatPattern(preset.grid, list(preset.steps), muted))
            self.changed.emit()

    def pattern(self) -> BeatPattern:
        key = str(self.grid.currentData())
        spec = grid_spec(key)
        return BeatPattern(key, [b.state for b in self.steps[: spec.steps]], self.mute.isChecked())

    def set_pattern(self, pattern: BeatPattern) -> None:
        pattern.normalize()
        key = pattern.grid if self._grid_allowed(pattern.grid) else "quarter"
        if key != pattern.grid:
            pattern = BeatPattern(key, pattern.steps[:1] or [OFF], pattern.muted)
            pattern.normalize()

        self.grid.blockSignals(True)
        self.grid.setCurrentIndex(self.grid.findData(key))
        self.grid.blockSignals(False)
        self._reload_presets()

        self.mute.blockSignals(True)
        self.mute.setChecked(pattern.muted)
        self.mute.blockSignals(False)

        spec = grid_spec(key)
        for i, button in enumerate(self.steps):
            button.setVisible(i < spec.steps)
            button.set_state(pattern.steps[i] if i < len(pattern.steps) and i < spec.steps else OFF)

        for i in range(self.preset.count()):
            preset = self.preset.itemData(i)
            if isinstance(preset, CellPreset) and preset.steps == tuple(pattern.steps):
                self.preset.setCurrentIndex(i)
                break

    def playhead(self, sub: int | None) -> None:
        spec = grid_spec(str(self.grid.currentData()))
        for i, button in enumerate(self.steps):
            button.set_playing(sub is not None and i == sub and i < spec.steps)

    def set_span_covered(self, value: bool) -> None:
        self._span_covered = bool(value)
        self.setEnabled(not self._span_covered)
        self._refresh_visual_state()

    def set_ramp_inactive(self, value: bool) -> None:
        self._ramp_inactive = bool(value)
        self._refresh_visual_state()

    def _refresh_visual_state(self) -> None:
        if self._span_covered:
            self._opacity.setOpacity(0.22)
        elif self._ramp_inactive:
            self._opacity.setOpacity(0.32)
        else:
            self._opacity.setOpacity(1.0)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1220, 820)
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.engine = AudioEngine()
        self.tap_times: list[float] = []
        self.metro_color = QColor("#e8ebf0")

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
        out.addLayout(transport)

        self.visual = MetronomeVisual()
        out.addWidget(self.visual)

        self.status = QLabel("Готов")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:16px;font-weight:700;padding:5px")
        out.addWidget(self.status)

        group = QGroupBox("Такт 4/4 — сетка выбирается отдельно для каждой доли")
        row = QHBoxLayout(group)
        self.editors = [BeatEditor(i + 1) for i in range(4)]
        for editor in self.editors:
            editor.changed.connect(self._pattern_changed)
            row.addWidget(editor, 1)
        out.addWidget(group)

        random_row = QHBoxLayout()
        self.random_four = QPushButton("🎲 Случайные 4")
        self.random_four.clicked.connect(self.randomize_four)
        random_row.addWidget(self.random_four)
        random_row.addStretch()
        out.addLayout(random_row)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_practice_tab(), "Тренировка")
        self.tabs.addTab(self._build_sound_tab(), "Звук")
        self.tabs.addTab(self._build_metronome_tab(), "Метроном")
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

        self.bpm.valueChanged.connect(self._bpm_from_spin)
        self.bpm_slider.valueChanged.connect(self._bpm_from_slider)

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
        self.mode.addItem("Петля 4/4", "loop")
        self.mode.addItem("Разгон 1/4 → 2/4 → 3/4 → 4/4", "ramp_1_4")
        self.mode.addItem("Разгон 2/4 → 4/4", "ramp_2_4")
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
        return tab

    def _build_sound_tab(self) -> QWidget:
        tab = QWidget()
        g = QGridLayout(tab)

        self.ti_on = QCheckBox(TI_MARK)
        self.ti_on.setChecked(True)
        self.ti_sound = QComboBox()
        self.ti_sound.addItems(["Clap", "Wood", "Click", "Beep"])
        self.ti_vol = self._volume_slider(100)

        self.ta_on = QCheckBox("ТА")
        self.ta_sound = QComboBox()
        self.ta_sound.addItems(["Muted click", "Rim", "Low tick"])
        self.ta_vol = self._volume_slider(70)

        self.metro_on = QCheckBox("Метроном")
        self.metro_on.setChecked(True)
        self.accent = QCheckBox("Акцент первой доли")
        self.accent.setChecked(True)
        self.metro_vol = self._volume_slider(70)
        self.master = self._volume_slider(100)

        g.addWidget(self.ti_on, 0, 0)
        g.addWidget(self.ti_sound, 0, 1)
        g.addWidget(QLabel("Громкость"), 0, 2)
        g.addWidget(self.ti_vol, 0, 3)

        g.addWidget(self.ta_on, 1, 0)
        g.addWidget(self.ta_sound, 1, 1)
        g.addWidget(QLabel("Громкость"), 1, 2)
        g.addWidget(self.ta_vol, 1, 3)

        g.addWidget(self.metro_on, 2, 0)
        g.addWidget(self.accent, 2, 1)
        g.addWidget(QLabel("Громкость"), 2, 2)
        g.addWidget(self.metro_vol, 2, 3)

        g.addWidget(QLabel("Master"), 3, 0, 1, 2)
        g.addWidget(self.master, 3, 2, 1, 2)

        note = QLabel("Все уровни: 0–200%. При перегрузе движок ограничивает цифровой пик без hard clipping.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#8f96a3;")
        g.addWidget(note, 4, 0, 1, 4)
        g.setColumnStretch(3, 1)
        return tab

    def _build_metronome_tab(self) -> QWidget:
        tab = QWidget()
        root = QHBoxLayout(tab)

        visual = QGroupBox("Визуальный метроном")
        form = QFormLayout(visual)

        self.metro_size = QSlider(Qt.Horizontal)
        self.metro_size.setRange(60, 180)
        self.metro_size.setValue(100)
        self.metro_size.setToolTip("Размер визуального метронома")
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

        self.metro_lamps = QCheckBox("Показывать 4 индикатора долей")
        self.metro_lamps.setChecked(True)
        form.addRow("", self.metro_lamps)
        root.addWidget(visual, 1)

        hint = QGroupBox("Подсказка")
        hint_layout = QVBoxLayout(hint)
        text = QLabel(
            "Игла синхронизирована с sample-clock аудиодвижка. "
            "Мигалка — только визуальный слой и не участвует в тайминге звука."
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

    def current_pattern(self) -> BarPattern:
        return BarPattern([editor.pattern() for editor in self.editors])

    def _pattern_changed(self) -> None:
        pattern = self.current_pattern()
        self.engine.set_pattern(pattern)
        self._refresh_span_visuals(pattern)

    def _refresh_span_visuals(self, pattern: BarPattern | None = None) -> None:
        pattern = pattern or self.current_pattern()
        owners = pattern.coverage()
        for i, editor in enumerate(self.editors):
            editor.set_span_covered(owners[i] is not None and owners[i] != i)

    def _config_changed(self, *_args) -> None:
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

    def toggle(self) -> None:
        try:
            if self.engine.is_running:
                self.engine.stop()
                self.play.setText("▶ Старт")
                self.clear_playhead()
                self._set_ramp_visual(4)
                self.visual.set_state(phase=0.0, beat=0, active_beats=4, count_in=False, running=False)
            else:
                self._sync()
                self.engine.start()
                self.play.setText("■ Стоп")
        except Exception as exc:
            self.engine.stop()
            self.play.setText("▶ Старт")
            QMessageBox.critical(self, "Ошибка аудио", str(exc))

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

    def randomize_four(self) -> None:
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

        active_beats = 4 if st["count_in"] else int(st["active_beats"])
        self.visual.set_state(
            phase=float(st["beat_phase"]),
            beat=int(st["beat"]),
            active_beats=active_beats,
            count_in=bool(st["count_in"]),
            running=True,
        )

        if st["count_in"]:
            self.status.setText(f"COUNT-IN · {bpm} BPM")
            self._set_ramp_visual(4)
            self.highlight(int(st["beat"]), None)
            return

        self._set_ramp_visual(active_beats)
        stage = "4/4" if self.mode.currentData() == "loop" else f"{active_beats}/4"
        self.status.setText(f"Такт {st['bar']} · этап {stage} · доля {int(st['beat']) + 1} · {bpm} BPM")
        self.highlight(int(st["beat"]), int(st["sub"]))

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

    def session(self) -> dict:
        return {
            "version": 2,
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
        for editor, pattern in zip(self.editors, bar.beats):
            editor.set_pattern(pattern)

        practice = data.get("practice", {})
        self.mode.setCurrentIndex(max(0, self.mode.findData(practice.get("mode", "loop"))))
        self.bars.setValue(int(practice.get("bars", 8)))
        self.count.setValue(int(practice.get("count", 1)))
        self.inactive.setChecked(bool(practice.get("inactive", True)))
        self.tempo_train.setChecked(bool(practice.get("trainer", False)))
        self.tempo_step.setValue(int(practice.get("step", 2)))
        self.tempo_every.setValue(int(practice.get("every", 4)))
        self.tempo_target.setValue(int(practice.get("target", 140)))

        sound = data.get("sound", {})
        self.ti_on.setChecked(bool(sound.get("ti_on", True)))
        self._combo(self.ti_sound, sound.get("ti_sound", "Clap"))
        self.ti_vol.setValue(int(sound.get("ti_vol", 100)))
        self.ta_on.setChecked(bool(sound.get("ta_on", False)))
        self._combo(self.ta_sound, sound.get("ta_sound", "Muted click"))
        self.ta_vol.setValue(int(sound.get("ta_vol", 70)))
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
        for editor in self.editors:
            editor.set_pattern(BeatPattern("sixteenth", [TI, TA, TA, TA], False))
        self.mode.setCurrentIndex(0)
        self.bars.setValue(8)
        self.count.setValue(1)
        self.inactive.setChecked(True)
        self.tempo_train.setChecked(False)
        self.ti_on.setChecked(True)
        self.ti_vol.setValue(100)
        self.ta_on.setChecked(False)
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

        self._set_ramp_visual(4)
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
