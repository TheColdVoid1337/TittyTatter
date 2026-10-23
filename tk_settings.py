"""Tkinter settings Notebook mirroring the existing TittyTatter tabs.

GUI only: the host TkApp is responsible for the canonical AudioEngine,
persistence and musical calculations. No PySide6 imports or Qt adapters.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, colorchooser

from audio_engine import (
    GAME_MISS_SOUNDS, GAME_TA_HIT_SOUNDS, GAME_TI_HIT_SOUNDS, SOUND_NAMES,
)
from training_modes import (
    DISPLACED_CLICK_OPTIONS, SPARSE_CLICK_OPTIONS, TEMPO_MODES, TRAINING_MODES,
)

EXTRA_MODES = (
    ("ladder_bars", "Тактов / деление:", 1, 32, 2, ("subdivision_ladder",)),
    ("burst_base_bars", "База, тактов:", 1, 32, 4, ("burst",)),
    ("burst_fast_bars", "Рывок, тактов:", 1, 16, 1, ("burst",)),
    ("burst_fast_bpm", "Рывок, BPM:", 20, 320, 120, ("burst",)),
    ("accent_bars", "Тактов / акцент:", 1, 32, 1, ("accent_shift",)),
    ("tempo_min_bpm", "Мин. BPM:", 20, 320, 80, ("tempo_wave", "random_tempo")),
    ("tempo_max_bpm", "Макс. BPM:", 20, 320, 120, ("tempo_wave", "random_tempo")),
    ("tempo_block_bars", "Тактов / блок:", 1, 32, 2, ("tempo_wave", "random_tempo")),
    ("random_seed", "Seed:", 0, 999999, 7, ("random_tempo",)),
    ("endurance_work_bars", "Работа, тактов:", 1, 64, 4, ("endurance",)),
    ("endurance_rest_bars", "Отдых, тактов:", 1, 32, 1, ("endurance",)),
    ("blind_learn_bars", "Подсказки, тактов:", 1, 64, 4, ("blind_pattern",)),
    ("blind_memory_bars", "Память, тактов:", 1, 32, 2, ("blind_pattern",)),
)
DEFAULTS = {
    "mode": "loop", "bars_per_stage": 8, "count_in_bars": 1,
    "inactive_pulse": True, "ramp_warning": True,
    "gap_play_bars": 4, "gap_silent_bars": 2, "progressive_gap_max_silent_bars": 4,
    "sparse_click_pattern": "beat_1", "displaced_click": "eighth_and",
    "tempo_trainer_enabled": False, "tempo_step": 2, "tempo_every_bars": 4,
    "tempo_target": 140, "practice_timer": False, "timer_minutes": 10, "timer_seconds": 0,
    "ti_enabled": True, "ti_sound": "Wood", "ti_volume": 100,
    "ta_enabled": True, "ta_sound": "Low tick", "ta_volume": 70,
    "metronome_enabled": True, "accent_first_beat": True,
    "metronome_volume": 70, "master_volume": 100,
    "metro_size": 100, "needle_color": "#e8ebf0", "flash_color": "#ffd56a",
    "metro_flash": True, "metro_flash_whole": False, "metro_flash_brightness": 100,
    "needle_width": 4, "needle_angle": 42, "metro_lamps": True,
    "picking_enabled": False, "picking_strategy": "economy",
    "picking_start_stroke": "auto", "picking_escape_profile": "auto",
    "picking_crossing_preference": "auto", "picking_show_sweeps": True,
    "picking_show_next": True, "picking_next_count": 1,
    "picking_highlight_current": True, "picking_cue_size": 52,
    "game_hit_sound": True, "game_split_hit_sound": True,
    "game_hit_choice": "game_hit", "game_hit_ta_choice": "game_ta_hit",
    "game_hit_volume": 70, "game_miss_sound": True,
    "game_miss_choice": "game_miss", "game_miss_volume": 68,
    "game_ti_key": "F", "game_ta_key": "J",
    "audio_rate": 0, "audio_block": 0, "audio_latency": "low", "audio_exclusive": False,
}
DEFAULTS.update({key: default for key, _label, _lo, _hi, default, _modes in EXTRA_MODES})


class SettingsTabsMixin:
    """Mixin methods called on TkApp (tk.Tk)."""

    def make_var(self, key: str, default=None):
        if key not in self.v:
            raw = DEFAULTS.get(key, default)
            typ = tk.BooleanVar if isinstance(raw, bool) else tk.IntVar if isinstance(raw, int) else tk.StringVar
            self.v[key] = typ(master=self, value=raw)
        return self.v[key]

    def get(self, key: str):
        current = self.make_var(key).get()
        return self._option_maps.get(key, {}).get(current, current)

    def set_option(self, key: str, value):
        backwards = {v: k for k, v in self._option_maps.get(key, {}).items()}
        self.make_var(key).set(backwards.get(value, value))

    def _notify(self, *_args) -> None:
        if not self._loading:
            self.on_setting_changed()

    def _setting_row(self, parent, label: str):
        line = ttk.Frame(parent)
        line.pack(fill="x", padx=7, pady=3)
        ttk.Label(line, text=label, width=22, anchor="w").pack(side="left", padx=(0, 8))
        return line

    def _spin(self, parent, key, label, lo, hi, default):
        line = self._setting_row(parent, label)
        widget = tk.Spinbox(line, from_=lo, to=hi, width=8, justify="center",
                            textvariable=self.make_var(key, default),
                            command=self._notify, bg="#2b303a", fg="white",
                            buttonbackground="#3c4654", insertbackground="white", relief="flat")
        widget.pack(side="left")
        widget.bind("<FocusOut>", self._notify)
        widget.bind("<Return>", self._notify)
        self.setting_widgets[key] = widget
        return line

    def _check(self, parent, key, label, default=False):
        line = ttk.Frame(parent)
        line.pack(fill="x", padx=7, pady=4)
        widget = ttk.Checkbutton(line, text=label, variable=self.make_var(key, default), command=self._notify)
        widget.pack(anchor="w")
        self.setting_widgets[key] = widget
        return line

    def _choices(self, parent, key, label, options, default):
        line = self._setting_row(parent, label)
        names = []
        display = {}
        for text, value in options:
            names.append(text)
            display[text] = value
        self._option_maps[key] = display
        selected = next((text for text, value in options if value == self.get(key)), names[0])
        self.make_var(key, default).set(selected)
        box = ttk.Combobox(line, values=names, state="readonly", width=29,
                           textvariable=self.make_var(key))
        box.pack(side="left", fill="x", expand=True)
        box.bind("<<ComboboxSelected>>", self._notify)
        self.setting_widgets[key] = box
        return line

    def _slider(self, parent, key, label, minimum, maximum, default):
        line = self._setting_row(parent, label)
        ttk.Scale(line, from_=minimum, to=maximum, variable=self.make_var(key, default),
                  orient="horizontal", command=lambda _v: self._notify()).pack(side="left", fill="x", expand=True)
        ttk.Label(line, textvariable=self.make_var(key), width=4).pack(side="left")
        return line

    def _page(self, name: str) -> ttk.Frame:
        page = ttk.Frame(self.tabs)
        self.tabs.add(page, text=name)
        canvas = tk.Canvas(page, background="#20232b", highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        horizontal = ttk.Scrollbar(page, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        horizontal.pack(side="bottom", fill="x")
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=body, anchor="nw")
        def resized(event, c=canvas, w=win, content=body):
            c.itemconfigure(w, width=max(event.width, content.winfo_reqwidth()))
            c.configure(scrollregion=c.bbox("all"))
        body.bind("<Configure>", lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", resized)
        self._page_canvases.append(canvas)
        return body

    def _group(self, parent, title):
        group = ttk.LabelFrame(parent, text=title, padding=(5, 6))
        group.pack(side="left", fill="both", expand=True, padx=7, pady=7)
        return group

    def build_tabs(self) -> None:
        self.setting_widgets = {}
        self._option_maps = {}
        self._page_canvases = []
        self._mode_rows = {}
        self.tabs = ttk.Notebook(self)
        self._build_training_tab()
        self._build_sound_tab()
        self._build_metronome_tab()
        self._build_game_tab()
        self._build_picking_tab()
        self._build_audio_tab()
        self._build_export_tab()
        self._build_about_tab()
        self._refresh_mode_options()

    def _build_training_tab(self):
        body = self._page("Тренировка")
        columns = ttk.Frame(body)
        columns.pack(fill="both", expand=True)
        left = self._group(columns, "Режим тренировки")
        self._choices(left, "mode", "Режим:", tuple((label, key) for key, label in TRAINING_MODES), "loop")
        self._mode_rows["ramp"] = [
            self._spin(left, "bars_per_stage", "Тактов / этап:", 1, 64, 8),
            self._check(left, "inactive_pulse", "ТА-пульс на неактивных долях", True),
            self._check(left, "ramp_warning", "Предупреждать о следующем этапе", True),
        ]
        self._mode_rows["gap"] = [self._spin(left, "gap_play_bars", "Со звуком, тактов:", 1, 32, 4)]
        self._mode_rows["gap_only"] = [self._spin(left, "gap_silent_bars", "Без звука, тактов:", 1, 32, 2)]
        self._mode_rows["progressive_gap"] = [
            self._spin(left, "progressive_gap_max_silent_bars", "Макс. тишина:", 1, 16, 4),
        ]
        self._mode_rows["sparse_click"] = [
            self._choices(left, "sparse_click_pattern", "Клик:",
                          tuple((label, key) for key, label in SPARSE_CLICK_OPTIONS), "beat_1"),
        ]
        self._mode_rows["displaced_click"] = [
            self._choices(left, "displaced_click", "Позиция клика:",
                          tuple((label, key) for key, label in DISPLACED_CLICK_OPTIONS), "eighth_and"),
        ]
        for key, label, lo, hi, default, modes in EXTRA_MODES:
            row = self._spin(left, key, label, lo, hi, default)
            self._mode_rows[key] = [row]
        ttk.Button(left, text="🎲 Случайный такт", command=self.randomize).pack(fill="x", padx=7, pady=7)

        middle = self._group(columns, "Опции")
        self._spin(middle, "count_in_bars", "Count-in:", 0, 8, 1)
        self._check(middle, "tempo_trainer_enabled", "Разгон темпа (Tempo Trainer)")
        self._spin(middle, "tempo_step", "Шаг BPM:", 1, 20, 2)
        self._spin(middle, "tempo_every_bars", "Каждые такты:", 1, 64, 4)
        self._spin(middle, "tempo_target", "Цель BPM:", 20, 320, 140)
        self._check(middle, "practice_timer", "Таймер")
        self._spin(middle, "timer_minutes", "Минуты:", 0, 180, 10)
        self._spin(middle, "timer_seconds", "Секунды:", 0, 59, 0)

        right = self._group(columns, "Как пользоваться")
        self.mode_help = ttk.Label(
            right, text="Pattern — что играть. Training Mode — как тренироваться.\n"
                        "Режимы используют общий таймлайн и аудиодвижок.",
            wraplength=270, justify="left",
        )
        self.mode_help.pack(fill="x", padx=7, pady=9)

    def _refresh_mode_options(self) -> None:
        mode = self.get("mode")
        visible = {
            "ramp": mode in ("ramp_1_4", "ramp_2_4"),
            "gap": mode in ("gap", "progressive_gap"),
            "gap_only": mode == "gap",
            "progressive_gap": mode == "progressive_gap",
            "sparse_click": mode == "sparse_click",
            "displaced_click": mode == "displaced_click",
        }
        for key, _label, _lo, _hi, _default, modes in EXTRA_MODES:
            visible[key] = mode in modes
        for key, rows in self._mode_rows.items():
            for row in rows:
                if visible.get(key, False):
                    row.pack(fill="x", padx=7, pady=3)
                else:
                    row.pack_forget()
        msg = {
            "loop": "Повторение выбранного рисунка.",
            "ramp_1_4": "Постепенно добавляются активные доли, BPM не удваивается.",
            "ramp_2_4": "Разгон с двух активных долей до полного такта.",
            "gap": "Чередование тактов со звуком и без звука.",
            "progressive_gap": "Тихий интервал последовательно увеличивается.",
            "burst": "Чередование базового темпа и кратковременного ускорения.",
            "subdivision_ladder": "Четверти → восьмые → триоли → шестнадцатые.",
            "accent_shift": "Акцент переходит на следующую долю.",
        }.get(mode, "Упражнение использует тот же исходный Pattern.")
        self.mode_help.configure(text=msg)
        for key in ("tempo_step", "tempo_every_bars", "tempo_target"):
            widget = self.setting_widgets.get(key)
            if widget is not None:
                widget.configure(state="normal" if self.get("tempo_trainer_enabled") and mode not in TEMPO_MODES else "disabled")
        for key in ("timer_minutes", "timer_seconds"):
            self.setting_widgets[key].configure(state="normal" if self.get("practice_timer") else "disabled")

    def _build_sound_tab(self):
        body = self._page("Звук")
        row = ttk.Frame(body)
        row.pack(fill="x")
        a = self._group(row, "(ТИ) · Пятая струна")
        self._check(a, "ti_enabled", "Включить ТИ", True)
        self._choices(a, "ti_sound", "Тембр:", tuple((x, x) for x in SOUND_NAMES), "Wood")
        self._slider(a, "ti_volume", "Громкость:", 0, 100, 100)
        b = self._group(row, "ТА · Шестая струна")
        self._check(b, "ta_enabled", "Включить ТА", True)
        self._choices(b, "ta_sound", "Тембр:", tuple((x, x) for x in SOUND_NAMES), "Low tick")
        self._slider(b, "ta_volume", "Громкость:", 0, 100, 70)
        c = self._group(row, "Метроном и микшер")
        self._check(c, "metronome_enabled", "Звук метронома", True)
        self._check(c, "accent_first_beat", "Акцент первой доли", True)
        self._slider(c, "metronome_volume", "Метроном:", 0, 100, 70)
        self._slider(c, "master_volume", "Общая громкость:", 0, 100, 100)

    def _build_metronome_tab(self):
        body = self._page("Метроном")
        a = self._group(body, "Визуализация")
        self._slider(a, "metro_size", "Размер:", 60, 180, 100)
        for key, label in (("needle_color", "Цвет иглы"), ("flash_color", "Цвет мигалки")):
            row = self._setting_row(a, label)
            ttk.Button(row, text="Выбрать", command=lambda k=key: self.pick_color(k)).pack(side="left")
        self._check(a, "metro_flash", "Кружок", True)
        self._check(a, "metro_flash_whole", "Мигать всем полем", False)
        self._slider(a, "metro_flash_brightness", "Яркость:", 0, 200, 100)
        self._spin(a, "needle_width", "Толщина иглы:", 1, 12, 4)
        self._spin(a, "needle_angle", "Размах:", 15, 70, 42)
        self._check(a, "metro_lamps", "Индикаторы долей", True)

    def pick_color(self, key: str):
        chosen = colorchooser.askcolor(initialcolor=self.get(key), parent=self)[1]
        if chosen:
            self.make_var(key).set(chosen)
            self._notify()

    def _build_game_tab(self):
        body = self._page("Игра")
        row = ttk.Frame(body)
        row.pack(fill="x")
        a = self._group(row, "Опции игры")
        self._check(a, "game_hit_sound", "HIT", True)
        self._check(a, "game_split_hit_sound", "Разные ТИ/ТА", True)
        self._choices(a, "game_hit_choice", "ТИ HIT:", GAME_TI_HIT_SOUNDS, "game_hit")
        self._choices(a, "game_hit_ta_choice", "ТА HIT:", GAME_TA_HIT_SOUNDS, "game_ta_hit")
        self._slider(a, "game_hit_volume", "HIT громкость:", 0, 100, 70)
        self._check(a, "game_miss_sound", "MISS", True)
        self._choices(a, "game_miss_choice", "MISS:", GAME_MISS_SOUNDS, "game_miss")
        self._slider(a, "game_miss_volume", "MISS громкость:", 0, 100, 68)
        ttk.Button(a, text="▶ Запустить игру", command=self.toggle_game).pack(fill="x", padx=7, pady=9)
        b = self._group(row, "Управление")
        for key, default, caption in (
            ("game_ti_key", "F", "(ТИ):"), ("game_ta_key", "J", "ТА:"),
        ):
            line = self._setting_row(b, caption)
            ttk.Entry(line, textvariable=self.make_var(key, default), width=10).pack(side="left")
        self.game_stats = ttk.Label(b, text="Score: 0\nПопадания: 0\nПромахи: 0", justify="left")
        self.game_stats.pack(anchor="w", padx=9, pady=9)

    def _build_picking_tab(self):
        body = self._page("Штрих")
        a = self._group(body, "Picking Guide")
        self._check(a, "picking_enabled", "Показывать подсказку штриха в метрономе")
        self._choices(a, "picking_strategy", "Тактика:", (
            ("Экономный", "economy"), ("Строго переменный ↓↑", "alternate"),
        ), "economy")
        self._choices(a, "picking_start_stroke", "Первый штрих:", (
            ("Авто", "auto"), ("Вниз ↓", "down"), ("Вверх ↑", "up"),
        ), "auto")
        self._choices(a, "picking_escape_profile", "Механика Economy:", (
            ("Авто", "auto"), ("USX", "usx"), ("DSX", "dsx"), ("DBX", "dbx"),
        ), "auto")
        self._choices(a, "picking_crossing_preference", "Пересечения:", (
            ("Авто", "auto"), ("Внутри", "inside"), ("Снаружи", "outside"),
        ), "auto")
        self._check(a, "picking_show_sweeps", "Показывать связи sweep", True)
        self._check(a, "picking_show_next", "Следующие штрихи", True)
        self._spin(a, "picking_next_count", "Следующих:", 1, 8, 1)
        self._check(a, "picking_highlight_current", "Подсвечивать текущую долю", True)
        self._spin(a, "picking_cue_size", "Размер стрелки:", 32, 80, 52)

    def _build_audio_tab(self):
        body = self._page("Аудио")
        a = self._group(body, "Аудиоустройство")
        device_line = self._setting_row(a, "Выход:")
        self.audio_device = ttk.Combobox(device_line, state="readonly", width=46)
        self.audio_device.pack(side="left", padx=4)
        ttk.Button(device_line, text="↻", command=self.refresh_devices).pack(side="left")
        self._choices(a, "audio_rate", "Sample rate:", (
            ("Default", 0), ("44.1 kHz", 44100), ("48 kHz", 48000),
            ("88.2 kHz", 88200), ("96 kHz", 96000),
        ), 0)
        self._choices(a, "audio_block", "Block size:", (
            ("Auto", 0), ("128", 128), ("256", 256), ("512", 512), ("1024", 1024),
        ), 0)
        self._choices(a, "audio_latency", "Latency:", (("Low", "low"), ("High", "high")), "low")
        self._check(a, "audio_exclusive", "WASAPI exclusive", False)
        ttk.Button(a, text="Применить аудио", command=self.apply_audio).pack(fill="x", padx=7, pady=8)
        self.audio_status = ttk.Label(a, text="", wraplength=600)
        self.audio_status.pack(anchor="w", padx=8, pady=8)

    def _build_export_tab(self):
        body = self._page("Экспорт")
        a = self._group(body, "Экспорт текущего рисунка")
        for name, ext in (("MIDI (.mid)", "mid"), ("Guitar Pro 5 (.gp5)", "gp5"), ("Audio (.wav)", "wav")):
            ttk.Button(a, text=name, command=lambda e=ext: self.export_pattern(e)).pack(fill="x", padx=8, pady=6)

    def _build_about_tab(self):
        body = self._page("About")
        ttk.Label(body, text="TittyTatter · Tkinter experiment",
                  font=("Segoe UI", 18, "bold")).pack(pady=(25, 12))
        ttk.Label(body,
                  text="Общий ритмический движок и Pattern с оригинальным TittyTatter.\n"
                       "Экспериментальный интерфейс, не отдельный релиз.",
                  justify="center").pack(pady=5)
        ttk.Label(body, text="https://github.com/TheColdVoid1337/TittyTatter").pack(pady=10)
