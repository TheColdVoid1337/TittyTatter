"""TittyTatter Tkinter UI experiment — independent of PySide6.

The original Qt app.py is untouched. The experiment reuses the *real* audio
engine, Pattern, presets, Training Mode timeline, Picking v2, and exports.
Audio timing comes solely from AudioEngine's PortAudio callback; Tk.after()
only redraws the screen and polls game input status.
"""
from __future__ import annotations

import json
import random
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk, simpledialog

from audio_engine import AudioEngine
from exports import export_gp5, export_midi, export_wav
from game_logic import LATE_HIT_WINDOW_MS, choose_target_index, grade_timing
from model import BarPattern, BeatPattern
from picking_logic import (
    DOWN, UP, alternate_pick_beats_v2, economy_pick_beats_v2,
    economy_pick_ramp_stages_v2,
)
from presets import CORE_PRACTICE_PRESETS, OFF, TA, TI, VALID_DENOMINATORS
from tk_settings import DEFAULTS, EXTRA_MODES, SettingsTabsMixin
from tk_widgets import BG, FG, HorizontalCards, MetronomeCanvas, BeatCard, configure_theme
from training_modes import RAMP_MODES, TEMPO_MODES, TRAINING_MODES, ladder_effective_pattern, ramp_stages

SETTINGS = Path(__file__).resolve().with_name("tittytatter.tk.settings.json")
MODES = {label: key for key, label in TRAINING_MODES}


def existing_gui_session(data: dict) -> dict:
    """Sanitize compatible Qt session data without invoking Qt or audio."""
    if not isinstance(data, dict):
        raise ValueError("Invalid session format")
    pat = BarPattern.from_dict(data.get("pattern", {}))
    return {**data, "pattern": pat.to_dict()}


class TkApp(SettingsTabsMixin, tk.Tk):
    def __init__(self, *, start_poll: bool = True) -> None:
        super().__init__()
        self.title("TittyTatter · Tkinter GUI Experiment")
        self.geometry("1240x860")
        self.minsize(870, 670)
        configure_theme(self)
        self._loading = True
        self.v = {}
        self._option_maps = {}
        self.editors: list[BeatCard] = []
        self.tap_times: list[float] = []
        self.focus = tk.BooleanVar(self, False)
        self.game_selected = tk.BooleanVar(self, False)
        self.status_text = tk.StringVar(self, "Готов · экспериментальная Tkinter версия")
        self.base_bpm = tk.IntVar(self, 60)
        self.meter_num = tk.IntVar(self, 4)
        self.meter_den = tk.IntVar(self, 4)
        self.game_active = False
        self.game_hits = 0
        self.game_misses = 0
        self.game_score = 0
        self.game_targets: list[tuple[float, str]] = []
        self.game_early_inputs: list[tuple[float, str]] = []
        self._last_stage = None
        self._device_records: list[dict] = []
        self._closed = False

        # No PortAudio playback until the user presses Start.
        self.engine = AudioEngine()
        self._build_ui()
        self._rebuild_cards()
        self._loading = False
        self.restore_settings()
        self.sync_engine()
        self._update_visual()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.bind_all("<space>", self._space)
        self.bind_all("<KeyPress>", self._keyboard_game, add="+")
        self.bind_all("<Control-s>", lambda _event: self.save_session())
        self.bind_all("<Control-o>", lambda _event: self.load_session())
        self.bind("<F11>", lambda _event: self.toggle_focus())
        if start_poll:
            self.after(33, self.poll)

    def _build_ui(self) -> None:
        transport = ttk.Frame(self)
        transport.pack(side="top", fill="x", padx=10, pady=(10, 6))
        self.play_btn = ttk.Button(transport, text="▶ Старт", command=self.toggle)
        self.play_btn.pack(side="left", padx=(0, 8))
        ttk.Label(transport, text="BPM").pack(side="left")
        self.bpm_spin = tk.Spinbox(
            transport, from_=20, to=320, textvariable=self.base_bpm, width=6,
            justify="center", bg="#2b303a", fg="white",
            insertbackground="white", buttonbackground="#3d4653", relief="flat",
            command=self.sync_engine,
        )
        self.bpm_spin.pack(side="left", padx=5)
        self.bpm_spin.bind("<FocusOut>", lambda _e: self.sync_engine())
        self.bpm_spin.bind("<Return>", lambda _e: self.sync_engine())
        ttk.Button(transport, text="TAP [T]", command=self.tap).pack(side="left", padx=5)
        ttk.Button(transport, text="Фокус режим [F]", command=self.toggle_focus).pack(side="left", padx=5)
        ttk.Label(transport, text="Режим").pack(side="left", padx=(25, 4))
        ttk.Radiobutton(transport, text="Тренировка", variable=self.game_selected,
                        value=False, command=self._switch_game).pack(side="left", padx=4)
        ttk.Radiobutton(transport, text="Игра", variable=self.game_selected,
                        value=True, command=self._switch_game).pack(side="left", padx=4)
        ttk.Label(transport, text="Размер").pack(side="left", padx=(25, 4))
        self.meter_spin = tk.Spinbox(
            transport, from_=1, to=16, width=4, justify="center",
            textvariable=self.meter_num, command=self.change_meter,
            bg="#2b303a", fg="white", insertbackground="white",
            buttonbackground="#3d4653", relief="flat",
        )
        self.meter_spin.pack(side="left", padx=2)
        self.meter_spin.bind("<Return>", lambda _e: self.change_meter())
        self.meter_spin.bind("<FocusOut>", lambda _e: self.change_meter())
        ttk.Label(transport, text="/").pack(side="left", padx=2)
        self.den_combo = ttk.Combobox(transport, width=4, state="readonly",
                                      textvariable=self.meter_den, values=VALID_DENOMINATORS)
        self.den_combo.pack(side="left", padx=2)
        self.den_combo.bind("<<ComboboxSelected>>", lambda _e: self.change_meter())

        self.visual = MetronomeCanvas(self)
        self.visual.pack(side="top", fill="x", padx=10, pady=3)
        self.visual.bind("<Button-1>", lambda _e: self.toggle())
        self.status_label = ttk.Label(self, textvariable=self.status_text,
                                       anchor="center", font=("Segoe UI", 11, "bold"))
        self.status_label.pack(side="top", fill="x", padx=10, pady=4)

        self.cards = HorizontalCards(self)
        self.cards.pack(side="top", fill="x", padx=10, pady=(3, 6))

        self.build_tabs()
        self.tabs.pack(side="top", fill="both", expand=True, padx=10, pady=(2, 6))

        self.footer = ttk.Frame(self)
        self.footer.pack(side="bottom", fill="x", padx=10, pady=(1, 10))
        ttk.Button(self.footer, text="Сохранить сессию", command=self.save_session).pack(side="left", padx=3)
        ttk.Button(self.footer, text="Загрузить сессию", command=self.load_session).pack(side="left", padx=3)
        ttk.Button(self.footer, text="Сброс сессии", command=self.reset_session).pack(side="left", padx=3)

    def _safe_int(self, key: str, low: int, high: int) -> int:
        try:
            value = int(float(self.get(key)))
        except (ValueError, tk.TclError, TypeError):
            value = low
        return max(low, min(high, value))

    def _bpm(self) -> int:
        try:
            return max(20, min(320, int(self.base_bpm.get())))
        except (ValueError, tk.TclError):
            return 60

    def _meter(self) -> tuple[int, int]:
        try:
            n = max(1, min(16, int(self.meter_num.get())))
        except (ValueError, tk.TclError):
            n = 4
        try:
            d = int(self.meter_den.get())
        except (ValueError, tk.TclError):
            d = 4
        return n, d if d in VALID_DENOMINATORS else 4

    def _rebuild_cards(self, patterns: list[BeatPattern] | None = None) -> None:
        self.cards.replace()
        n, d = self._meter()
        self.editors = []
        for index in range(n):
            card = BeatCard(self.cards.content, index + 1, n, d, self.pattern_changed)
            card.pack(side="left", padx=4, pady=3, anchor="n")
            if patterns and index < len(patterns):
                card.set_pattern(patterns[index])
            self.editors.append(card)
        self.pattern_changed()

    def current_pattern(self) -> BarPattern:
        pattern = BarPattern([ed.pattern() for ed in self.editors], *self._meter())
        pattern.normalize()
        return pattern

    def pattern_changed(self) -> None:
        if self._loading or not self.editors:
            return
        pattern = self.current_pattern()
        self.engine.set_pattern(pattern)
        coverage = pattern.coverage()
        mode = self.get("mode")
        for i, ed in enumerate(self.editors):
            ed.set_covered(coverage[i] != i)
            ed.set_mute_allowed(mode not in RAMP_MODES)
        self._update_visual()

    def change_meter(self) -> None:
        if self._loading:
            return
        old = [ed.pattern() for ed in self.editors]
        if self.engine.is_running:
            self.stop()
        self._rebuild_cards(old)
        self.sync_engine()

    def _visual_pattern(self, st: dict | None = None) -> BarPattern:
        pattern = self.current_pattern()
        if st and self.engine.is_running and self.get("mode") == "subdivision_ladder" and not st.get("count_in"):
            return ladder_effective_pattern(pattern, int(st.get("mode_stage_index", 0)))
        return pattern

    def _render_pattern_hints(self, st: dict) -> None:
        pattern = self._visual_pattern(st)
        owners = pattern.coverage()
        mode = self.get("mode")
        active = int(st.get("active_beats", pattern.numerator))
        hidden = self.engine.is_running and not st.get("count_in") and (
            st.get("mode_rest") or st.get("blind_hidden") or st.get("training_silent")
        )
        matrix: list[list[str]] = []
        for i, beat in enumerate(pattern.beats):
            if hidden or owners[i] != i:
                matrix.append([])
            elif mode in RAMP_MODES and i >= active:
                matrix.append([TA] + [OFF] * (beat.subdivision - 1))
            elif beat.muted:
                matrix.append([OFF] * beat.subdivision)
            else:
                matrix.append(list(beat.steps))
        self.visual.rhythm_states = matrix

        if self.get("picking_enabled") and not self.game_selected.get() and not hidden:
            try:
                full = [
                    list(beat.steps) if owners[i] == i and not beat.muted else
                    ([OFF] * beat.subdivision if owners[i] == i else [])
                    for i, beat in enumerate(pattern.beats)
                ]
                placeholders = {i for i in range(len(matrix)) if mode in RAMP_MODES and i >= active and full[i]}
                if self.get("picking_strategy") == "alternate":
                    v = self.get("picking_start_stroke")
                    first = None if v == "auto" else DOWN if v == "down" else UP
                    dirs = alternate_pick_beats_v2(full, matrix, TI, TA, OFF,
                                                    placeholder_beats=placeholders, start_direction=first)
                elif mode in RAMP_MODES:
                    dirs = economy_pick_ramp_stages_v2(
                        full, ramp_stages(mode, pattern.numerator), TI, TA, OFF,
                        escape_profile=self.get("picking_escape_profile"),
                        crossing_preference=self.get("picking_crossing_preference"),
                    ).get(active, [])
                else:
                    dirs = economy_pick_beats_v2(
                        full, matrix, TI, TA, OFF,
                        escape_profile=self.get("picking_escape_profile"),
                        crossing_preference=self.get("picking_crossing_preference"),
                    )
                self.visual.picking_tokens = [
                    ["↓" if x == DOWN else "↑" if x == UP else "" for x in row] for row in dirs
                ]
            except Exception as exc:
                self.visual.picking_tokens = []
                self.status_text.set(f"Picking preview: {exc}")
        else:
            self.visual.picking_tokens = []
        for i, card in enumerate(self.editors):
            if mode in RAMP_MODES:
                card.set_ramp_active(not self.engine.is_running or i < active)
            else:
                card.set_ramp_active(True)
            card.highlight(int(st["sub"]) if self.engine.is_running and not hidden and i == st["beat"] else None)

    def _update_visual(self, st: dict | None = None) -> None:
        if not hasattr(self, "visual") or self._loading:
            return
        state = st or self.engine.status()
        self._render_pattern_hints(state)
        self.visual.set_settings(
            needle_color=str(self.get("needle_color")),
            flash_color=str(self.get("flash_color")),
            flash=bool(self.get("metro_flash")),
            flash_whole=bool(self.get("metro_flash_whole")),
            flash_brightness=self._safe_int("metro_flash_brightness", 0, 200),
            needle_width=self._safe_int("needle_width", 1, 12),
            swing_angle=self._safe_int("needle_angle", 15, 70),
            scale_percent=self._safe_int("metro_size", 60, 180),
            lamps=bool(self.get("metro_lamps")),
        )
        self.visual.update_status(state)

    def on_setting_changed(self) -> None:
        if self._loading:
            return
        mode = self.get("mode")
        self._refresh_mode_options()
        if self.engine.is_running and mode != self.engine.get_config().practice_mode:
            self.stop()
        if mode in TEMPO_MODES and self.get("tempo_trainer_enabled"):
            self.make_var("tempo_trainer_enabled").set(False)
        self.sync_engine()
        self.pattern_changed()

    def sync_engine(self) -> None:
        if self._loading:
            return
        try:
            bpm = self._bpm()
            # A temporary mode-owned BPM must never replace base BPM.
            self.engine.set_pattern(self.current_pattern())
            self.engine.set_config(
                bpm=bpm, practice_mode=self.get("mode"),
                bars_per_stage=self._safe_int("bars_per_stage", 1, 64),
                count_in_bars=self._safe_int("count_in_bars", 0, 8),
                inactive_pulse=bool(self.get("inactive_pulse")),
                tempo_trainer_enabled=bool(self.get("tempo_trainer_enabled")),
                tempo_step=self._safe_int("tempo_step", 1, 20),
                tempo_every_bars=self._safe_int("tempo_every_bars", 1, 64),
                tempo_target=self._safe_int("tempo_target", 20, 320),
                gap_play_bars=self._safe_int("gap_play_bars", 1, 32),
                gap_silent_bars=self._safe_int("gap_silent_bars", 1, 32),
                progressive_gap_max_silent_bars=self._safe_int("progressive_gap_max_silent_bars", 1, 16),
                sparse_click_pattern=self.get("sparse_click_pattern"),
                displaced_click=self.get("displaced_click"),
                **{key: self._safe_int(key, lo, hi) for key, _name, lo, hi, _value, _modes in EXTRA_MODES},
                ti_enabled=bool(self.get("ti_enabled")),
                ti_sound=self.get("ti_sound"),
                ti_volume=self._safe_int("ti_volume", 0, 100) / 100,
                ta_enabled=bool(self.get("ta_enabled")),
                ta_sound=self.get("ta_sound"),
                ta_volume=self._safe_int("ta_volume", 0, 100) / 100,
                metronome_enabled=bool(self.get("metronome_enabled")),
                accent_first_beat=bool(self.get("accent_first_beat")),
                metronome_volume=self._safe_int("metronome_volume", 0, 100) / 100,
                master_volume=self._safe_int("master_volume", 0, 100) / 100,
            )
        except Exception as exc:
            self.status_text.set(f"Ошибка параметров: {exc}")

    def tap(self) -> None:
        now = time.perf_counter()
        if self.tap_times and now - self.tap_times[-1] > 2.5:
            self.tap_times.clear()
        self.tap_times.append(now)
        self.tap_times = self.tap_times[-7:]
        if len(self.tap_times) >= 2:
            intervals = [b - a for a, b in zip(self.tap_times, self.tap_times[1:])]
            if len(intervals) >= 4:
                intervals = sorted(intervals)[1:-1]
            self.base_bpm.set(max(20, min(320, round(60 / (sum(intervals) / len(intervals))))))
            self.sync_engine()

    def randomize(self) -> None:
        if self.engine.is_running:
            self.stop()
        for card in self.editors:
            preset = random.choice(CORE_PRACTICE_PRESETS)
            card.set_pattern(BeatPattern(preset.grid, list(preset.steps), False))
        self.pattern_changed()

    def toggle(self) -> None:
        if self.game_selected.get():
            self.toggle_game()
            return
        if self.engine.is_running:
            self.stop()
            return
        if self.get("practice_timer") and self._timer_limit() == 0:
            messagebox.showinfo("Таймер", "Укажи ненулевую длительность.", parent=self)
            return
        try:
            self.sync_engine()
            self.engine.start()
            self.play_btn.configure(text="■ Стоп")
            self.status_text.set("Тренировка началась")
        except Exception as exc:
            self.engine.stop()
            messagebox.showerror("Ошибка аудио", str(exc), parent=self)

    def _timer_limit(self) -> int:
        return self._safe_int("timer_minutes", 0, 180) * 60 + self._safe_int("timer_seconds", 0, 59)

    def stop(self, message: str = "Готов") -> None:
        self.engine.stop_game_tracking()
        self.engine.stop()
        self.game_active = False
        self.game_targets.clear()
        self.game_early_inputs.clear()
        self.play_btn.configure(text="▶ Старт")
        self.status_text.set(message)
        self.visual.game_text = ""
        self.visual.timer_text = ""
        if self.editors:
            self._update_visual()

    def _switch_game(self) -> None:
        if self.engine.is_running:
            self.stop()
        self._update_visual()

    def toggle_game(self) -> None:
        if self.game_active:
            self.stop("Игра остановлена")
            return
        if not self.game_selected.get():
            self.game_selected.set(True)
        try:
            self.sync_engine()
            self.game_hits = self.game_misses = self.game_score = 0
            self.game_targets.clear()
            self.game_early_inputs.clear()
            self.engine.start_game_tracking()
            self.engine.start()
            self.game_active = True
            self.play_btn.configure(text="■ Стоп")
            self.status_text.set("Игра · клавиши ТИ / ТА")
        except Exception as exc:
            self.stop()
            messagebox.showerror("Ошибка игры", str(exc), parent=self)

    def _register_game_input(self, note: str) -> None:
        if not self.game_active:
            return
        now = self.engine.stream_time()
        self._drain_game_targets(now)
        matches = [(t, s) for t, s in self.game_targets]
        idx = choose_target_index(matches, note, now)
        if idx is None:
            self.game_early_inputs.append((now, note))
        else:
            self._game_hit(idx, now)

    def _game_hit(self, index: int, timestamp: float) -> None:
        event_time, kind = self.game_targets.pop(index)
        grade = grade_timing((timestamp - event_time) * 1000.0)
        if grade.accepted:
            self.game_hits += 1
            self.game_score += grade.points
        else:
            self.game_misses += 1
        self.visual.game_text = f"{grade.label}  +{grade.points}"
        if grade.accepted and self.get("game_hit_sound"):
            sound = self.get("game_hit_choice") if kind == TI or not self.get("game_split_hit_sound") else self.get("game_hit_ta_choice")
            self.engine.queue_notification(sound, self._safe_int("game_hit_volume", 0, 100) / 100)

    def _drain_game_targets(self, now: float) -> None:
        incoming = self.engine.drain_game_targets()
        for time_at, note, *_rest in incoming:
            if note in (TI, TA):
                self.game_targets.append((float(time_at), note))
        self.game_targets.sort(key=lambda p: p[0])
        # An early input may precede publication of its future DAC target.
        for input_time, state in list(self.game_early_inputs):
            index = choose_target_index(self.game_targets, state, input_time)
            if index is not None:
                self._game_hit(index, input_time)
                self.game_early_inputs.remove((input_time, state))
            elif now - input_time > 0.18:
                self.game_early_inputs.remove((input_time, state))
                self.game_misses += 1
        for target in list(self.game_targets):
            if (now - target[0]) * 1000 > LATE_HIT_WINDOW_MS:
                self.game_targets.remove(target)
                self.game_misses += 1
                self.visual.game_text = "MISS"
                if self.get("game_miss_sound"):
                    self.engine.queue_notification(
                        self.get("game_miss_choice"),
                        self._safe_int("game_miss_volume", 0, 100) / 100,
                    )
        self.game_stats.configure(
            text=f"Score: {self.game_score}\nПопадания: {self.game_hits}\nПромахи: {self.game_misses}"
        )

    def _keyboard_game(self, event) -> None:
        # Tk keysym binding is deliberately NOT claimed to be equivalent to
        # the physical scan-code + mouse binding in the original Qt app.
        if self.game_active:
            key = str(event.keysym).upper()
            if key == str(self.get("game_ti_key")).upper():
                self._register_game_input(TI)
            elif key == str(self.get("game_ta_key")).upper():
                self._register_game_input(TA)
        elif event.keysym.lower() == "f" and not isinstance(event.widget, (tk.Entry, tk.Spinbox, ttk.Entry)):
            self.toggle_focus()
        elif event.keysym.lower() == "t" and not isinstance(event.widget, (tk.Entry, tk.Spinbox, ttk.Entry)):
            self.tap()

    def _space(self, event):
        if isinstance(event.widget, (tk.Entry, tk.Spinbox, ttk.Entry, ttk.Combobox)):
            return None
        self.toggle()
        return "break"

    def toggle_focus(self) -> None:
        self.focus.set(not self.focus.get())
        self.visual.focus = self.focus.get()
        if self.focus.get():
            self.cards.pack_forget()
            self.tabs.pack_forget()
            self.visual.pack_configure(fill="both", expand=True)
        else:
            self.visual.pack_configure(fill="x", expand=False)
            self.cards.pack(side="top", fill="x", padx=10, pady=(3, 6), before=self.footer)
            self.tabs.pack(side="top", fill="both", expand=True, padx=10, pady=(2, 6), before=self.footer)
        self._update_visual()

    def poll(self) -> None:
        if self._closed:
            return
        try:
            if self.engine.is_running:
                st = self.engine.status()
                if self.game_active:
                    self._drain_game_targets(self.engine.stream_time())
                if self.get("practice_timer") and not st.get("count_in"):
                    left = self._timer_limit() - float(st.get("practice_elapsed_seconds", 0.0))
                    self.visual.timer_text = f"{max(0, int(left)) // 60:02}:{max(0, int(left)) % 60:02}"
                    if left <= 0:
                        self.stop("Тренировка завершена")
                        self.engine.play_notification("Finish horn", 0.95)
                        return
                label = st.get("mode_stage_label") or ""
                if st.get("count_in"):
                    label = "COUNT-IN"
                if st.get("training_silent"):
                    label = "ТИШИНА"
                if st.get("mode_rest"):
                    label = "ОТДЫХ"
                self.visual.stage_text = str(label)
                self._update_visual(st)
            else:
                self._update_visual()
        except tk.TclError:
            return
        except Exception as exc:
            self.status_text.set(f"Visual update: {exc}")
        finally:
            if not self._closed:
                self.after(33, self.poll)

    def refresh_devices(self) -> None:
        self._device_records = self.engine.list_output_devices()
        titles = [f'{x["name"]} · {x["host_api"]}' for x in self._device_records]
        self.audio_device.configure(values=titles)
        chosen = next((i for i, x in enumerate(self._device_records) if x["index"] == self.engine.device_index), 0)
        if titles:
            self.audio_device.current(chosen)
        self._update_audio_status()

    def _update_audio_status(self) -> None:
        info = self.engine.stream_info()
        self.audio_status.configure(
            text=f'{info.get("host_api", "")} · {info.get("sample_rate", 0):g} Hz · '
                 f'block {info.get("blocksize", 0)} · {info.get("latency_mode", "")}'
        )

    def apply_audio(self) -> None:
        if self.engine.is_running:
            messagebox.showinfo("Аудио", "Останови воспроизведение.", parent=self)
            return
        idx = self.audio_device.current()
        if idx < 0 or idx >= len(self._device_records):
            return
        record = self._device_records[idx]
        rate = int(self.get("audio_rate"))
        try:
            self.engine.configure_output(
                device_index=int(record["index"]),
                sample_rate=float(rate or record["sample_rate"]),
                blocksize=int(self.get("audio_block")),
                latency_mode=str(self.get("audio_latency")),
                exclusive=bool(self.get("audio_exclusive")),
            )
            self._update_audio_status()
            self.status_text.set("Аудионастройки применены")
        except Exception as exc:
            messagebox.showwarning("Аудио", str(exc), parent=self)

    def export_pattern(self, kind: str) -> None:
        if kind in ("mid", "gp5"):
            repeats = simpledialog.askinteger("Экспорт", "Сколько повторов?", initialvalue=4, minvalue=1, maxvalue=999, parent=self)
            if repeats is None:
                return
            filename = f"tittytatter.{kind}"
            path = filedialog.asksaveasfilename(parent=self, defaultextension=f".{kind}", initialfile=filename)
            if not path:
                return
            try:
                if kind == "mid":
                    export_midi(path, self.current_pattern(), self._bpm(), repeats, True)
                else:
                    export_gp5(path, self.current_pattern(), self._bpm(), repeats, True)
            except Exception as exc:
                messagebox.showerror("Экспорт", str(exc), parent=self)
                return
        else:
            seconds = simpledialog.askinteger("WAV", "Длительность в секундах?", initialvalue=30, minvalue=1, maxvalue=10800, parent=self)
            if seconds is None:
                return
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".wav", initialfile="tittytatter.wav")
            if not path:
                return
            try:
                self.sync_engine()
                export_wav(path, self.current_pattern(), self.engine.get_config(), seconds, 48000, 16)
            except Exception as exc:
                messagebox.showerror("Экспорт", str(exc), parent=self)
                return
        self.status_text.set(f"Экспорт: {Path(path).name}")

    def session(self) -> dict:
        return {
            "version": 5,
            "bpm": self._bpm(),
            "pattern": self.current_pattern().to_dict(),
            "practice": {
                "mode": self.get("mode"), "bars": self.get("bars_per_stage"),
                "count": self.get("count_in_bars"),
                "inactive": self.get("inactive_pulse"), "ramp_warning": self.get("ramp_warning"),
                "gap_play_bars": self.get("gap_play_bars"),
                "gap_silent_bars": self.get("gap_silent_bars"),
                "progressive_gap_max": self.get("progressive_gap_max_silent_bars"),
                "sparse_click": self.get("sparse_click_pattern"),
                "displaced_click": self.get("displaced_click"),
                **{key: self.get(key) for key, *_ in EXTRA_MODES},
                "trainer": self.get("tempo_trainer_enabled"),
                "step": self.get("tempo_step"), "every": self.get("tempo_every_bars"),
                "target": self.get("tempo_target"), "timer_enabled": self.get("practice_timer"),
                "timer_minutes": self.get("timer_minutes"),
                "timer_seconds": self.get("timer_seconds"),
            },
            "sound": {
                "ti_on": self.get("ti_enabled"), "ti_sound": self.get("ti_sound"),
                "ti_vol": self.get("ti_volume"), "ta_on": self.get("ta_enabled"),
                "ta_sound": self.get("ta_sound"), "ta_vol": self.get("ta_volume"),
                "metro_on": self.get("metronome_enabled"), "accent": self.get("accent_first_beat"),
                "metro_vol": self.get("metronome_volume"), "master": self.get("master_volume"),
            },
            "visual_metronome": {
                "size": self.get("metro_size"), "needle_color": self.get("needle_color"),
                "flash_color": self.get("flash_color"), "flash": self.get("metro_flash"),
                "flash_whole": self.get("metro_flash_whole"),
                "flash_brightness": self.get("metro_flash_brightness"),
                "width": self.get("needle_width"), "angle": self.get("needle_angle"),
                "lamps": self.get("metro_lamps"),
            },
        }

    def apply_session(self, data: dict) -> None:
        data = existing_gui_session(data)
        if self.engine.is_running:
            self.stop()
        self._loading = True
        try:
            self.base_bpm.set(int(data.get("bpm", 60)))
            pat = BarPattern.from_dict(data["pattern"])
            self.meter_num.set(pat.numerator)
            self.meter_den.set(pat.denominator)
            self._rebuild_cards(pat.beats)
            practice = data.get("practice") or {}
            pr = {
                "mode": practice.get("mode", "loop"),
                "bars_per_stage": practice.get("bars", 8),
                "count_in_bars": practice.get("count", 1),
                "inactive_pulse": practice.get("inactive", True),
                "ramp_warning": practice.get("ramp_warning", True),
                "gap_play_bars": practice.get("gap_play_bars", 4),
                "gap_silent_bars": practice.get("gap_silent_bars", 2),
                "progressive_gap_max_silent_bars": practice.get("progressive_gap_max", 4),
                "sparse_click_pattern": practice.get("sparse_click", "beat_1"),
                "displaced_click": practice.get("displaced_click", "eighth_and"),
                "tempo_trainer_enabled": practice.get("trainer", False),
                "tempo_step": practice.get("step", 2),
                "tempo_every_bars": practice.get("every", 4),
                "tempo_target": practice.get("target", 140),
                "practice_timer": practice.get("timer_enabled", False),
                "timer_minutes": practice.get("timer_minutes", 10),
                "timer_seconds": practice.get("timer_seconds", 0),
            }
            for key, *_ in EXTRA_MODES:
                pr[key] = practice.get(key, DEFAULTS[key])
            sound = data.get("sound") or {}
            sd = {
                "ti_enabled": sound.get("ti_on", True), "ti_sound": sound.get("ti_sound", "Wood"),
                "ti_volume": sound.get("ti_vol", 100), "ta_enabled": sound.get("ta_on", True),
                "ta_sound": sound.get("ta_sound", "Low tick"), "ta_volume": sound.get("ta_vol", 70),
                "metronome_enabled": sound.get("metro_on", True), "accent_first_beat": sound.get("accent", True),
                "metronome_volume": sound.get("metro_vol", 70), "master_volume": sound.get("master", 100),
            }
            vis = data.get("visual_metronome") or {}
            vd = {
                "metro_size": vis.get("size", 100), "needle_color": vis.get("needle_color", "#e8ebf0"),
                "flash_color": vis.get("flash_color", "#ffd56a"),
                "metro_flash": vis.get("flash", True), "metro_flash_whole": vis.get("flash_whole", False),
                "metro_flash_brightness": vis.get("flash_brightness", 100),
                "needle_width": vis.get("width", 4), "needle_angle": vis.get("angle", 42),
                "metro_lamps": vis.get("lamps", True),
            }
            for key, val in {**pr, **sd, **vd}.items():
                self.set_option(key, val)
        finally:
            self._loading = False
        self.sync_engine()
        self.pattern_changed()
        self._refresh_mode_options()

    def save_session(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, initialfile="tittytatter_session.json",
                                            defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self.session(), ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_text.set(f"Сохранено: {Path(path).name}")

    def load_session(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("JSON", "*.json")])
        if path:
            try:
                self.apply_session(json.loads(Path(path).read_text(encoding="utf-8")))
                self.status_text.set(f"Загружено: {Path(path).name}")
            except Exception as exc:
                messagebox.showerror("Сессия", str(exc), parent=self)

    def reset_session(self) -> None:
        if messagebox.askyesno("Сброс", "Вернуть текущий Pattern и параметры упражнения к умолчаниям?", parent=self):
            self.apply_session({"bpm": 60, "pattern": BarPattern().to_dict()})

    def restore_settings(self) -> None:
        try:
            if SETTINGS.exists():
                data = json.loads(SETTINGS.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.apply_session(data.get("session", {}))
                    extra = data.get("tk_controls", {})
                    for key, value in extra.items():
                        if key in DEFAULTS:
                            self.set_option(key, value)
                self.sync_engine()
        except Exception as exc:
            self.status_text.set(f"Tk settings: {exc}")
        self.refresh_devices()

    def close_app(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            SETTINGS.write_text(json.dumps({
                "session": self.session(),
                "tk_controls": {key: self.get(key) for key in DEFAULTS},
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        self.engine.close()
        self.destroy()


def main() -> int:
    root = TkApp()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
