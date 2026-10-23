"""Tkinter presentation widgets for the separate TittyTatter GUI experiment.

This module imports NO Qt. Music representation is the canonical model/presets
used by app.py; audio events are supplied from the existing PortAudio engine.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Callable

from model import BeatPattern
from presets import OFF, TA, TI, grid_label, grid_spec, grid_specs_for_meter, presets_for_grid

BG = "#20232b"
PANEL = "#2b303a"
CANVAS = "#191f29"
FG = "#ebedf3"
MUTED = "#aab6c6"
TI_BG = "#1d679b"
TA_BG = "#555d6f"
OFF_BG = "#353b45"
ACCENT = "#ffd56a"


def configure_theme(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(background=BG)
    style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", padding=(8, 5), background=PANEL, foreground=FG)
    style.map("TButton", background=[("active", "#404957")])
    style.configure("TCheckbutton", background=BG, foreground=FG)
    style.map("TCheckbutton", background=[("active", BG)], foreground=[("disabled", MUTED)])
    style.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG)
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=FG, padding=(11, 5))
    style.map("TNotebook.Tab", background=[("selected", "#3d536d")], foreground=[("selected", "#ffffff")])
    style.configure("TLabelframe", background=BG, foreground=FG)
    style.configure("TLabelframe.Label", background=BG, foreground=FG)
    style.configure("TEntry", fieldbackground=PANEL, foreground=FG)
    style.configure("Vertical.TScrollbar", background=PANEL)
    return style


class MetronomeCanvas(tk.Canvas):
    """Metronome visual driven by engine.status(), never its own timing clock."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=CANVAS, highlightthickness=0, height=142)
        self.configure(background=CANVAS)
        self.state = {
            "beat": 0, "sub": 0, "beat_phase": 0.0, "numerator": 4,
            "denominator": 4, "running": False, "count_in": False,
            "active_beats": 4, "bar": 1, "bpm": 60,
            "training_silent": False, "blind_hidden": False, "mode_rest": False,
        }
        self.needle_color = "#e8ebf0"
        self.flash_color = ACCENT
        self.flash = True
        self.flash_whole = False
        self.flash_brightness = 100
        self.needle_width = 4
        self.swing_angle = 42
        self.scale_percent = 100
        self.show_lamps = True
        self.focus = False
        self.picking_tokens: list[list[str]] = []
        self.picking_show_next = True
        self.picking_next_count = 1
        self.rhythm_states: list[list[str]] = []
        self.timer_text = ""
        self.game_text = ""
        self.stage_text = ""
        self.bind("<Configure>", lambda _e: self.draw())

    def set_settings(self, *, needle_color: str, flash_color: str, flash: bool,
                     flash_whole: bool, flash_brightness: int, needle_width: int,
                     swing_angle: int, scale_percent: int, lamps: bool) -> None:
        self.needle_color = needle_color
        self.flash_color = flash_color
        self.flash = flash
        self.flash_whole = flash_whole
        self.flash_brightness = flash_brightness
        self.needle_width = needle_width
        self.swing_angle = swing_angle
        self.scale_percent = scale_percent
        self.show_lamps = lamps
        self.draw()

    def update_status(self, state: dict) -> None:
        self.state = dict(state)
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        st = self.state
        running = bool(st.get("running"))
        beat = int(st.get("beat", 0))
        beats = max(1, int(st.get("numerator", 4)))
        phase = float(st.get("beat_phase", 0.0))
        visible = not bool(st.get("blind_hidden") or st.get("mode_rest"))
        silent = bool(st.get("training_silent", False))
        cx, pivot = w / 2.0, max(46.0, min(h * 0.60, h - 35.0))
        swing = math.sin(math.pi * 2 * phase) * math.radians(self.swing_angle) if running else 0.0
        needle_length = min(h * 0.38, 150) * (self.scale_percent / 100)
        nx = cx + math.sin(swing) * needle_length
        ny = pivot - math.cos(swing) * needle_length
        if running and phase < 0.13 and not silent and self.flash and visible:
            color = self.flash_color
            if self.flash_whole:
                self.create_rectangle(0, 0, w, h, fill=color, stipple="gray75", outline="")
            else:
                self.create_oval(17, 18, 39, 40, fill=color, outline="")
        self.create_line(cx, pivot, nx, ny, fill=self.needle_color, width=self.needle_width)
        self.create_oval(cx - 5, pivot - 5, cx + 5, pivot + 5, fill=MUTED, outline="")
        self.create_text(18, h - 17, text=f'{st.get("bpm", 60):g} BPM', fill=MUTED,
                         anchor="w", font=("Segoe UI", 10, "bold"))
        self.create_text(w - 16, h - 17, text=f'{beats}/{st.get("denominator", 4)}  ·  такт {st.get("bar", 1)}',
                         fill=MUTED, anchor="e", font=("Segoe UI", 10))
        if self.show_lamps and beats <= 16:
            gap = min(34.0, (w - 100) / (beats + 1))
            start = cx - ((beats - 1) * gap / 2)
            yy = min(h - 34, pivot + 26)
            for i in range(beats):
                col = ACCENT if running and i == beat and visible and not silent else (
                    TI_BG if i < int(st.get("active_beats", beats)) else OFF_BG)
                self.create_oval(start + gap * i - 5, yy - 5, start + gap * i + 5, yy + 5, fill=col, outline="")
        if self.stage_text:
            self.create_text(16, 16, anchor="nw", text=self.stage_text,
                             fill=FG, font=("Segoe UI", 10))
        if self.timer_text:
            self.create_text(w - 16, 16, anchor="ne", text=self.timer_text,
                             fill=ACCENT, font=("Segoe UI", 12, "bold"))
        if self.game_text:
            self.create_text(cx, h * 0.72, text=self.game_text, fill=ACCENT, font=("Segoe UI", 13, "bold"))
        elif self.focus and self.rhythm_states and visible and not silent:
            self._draw_focus_strip(w, h, beat)
        if self.picking_tokens and visible and not silent and not self.game_text:
            row = self.picking_tokens[beat] if beat < len(self.picking_tokens) else []
            current = row[min(len(row) - 1, int(st.get("sub", 0)))] if row else ""
            if current:
                self.create_text(
                    cx + min(135, w * 0.18), max(50, pivot - 35),
                    text=current, fill=ACCENT, font=("Segoe UI", 31, "bold"),
                )
            if self.picking_show_next:
                flat = [x for x in row if x]
                if flat:
                    self.create_text(
                        cx + min(135, w * 0.18), pivot + 4,
                        text=" ".join(flat[:self.picking_next_count]),
                        fill=MUTED, font=("Segoe UI", 10),
                    )

    def _draw_focus_strip(self, w: int, h: int, beat: int) -> None:
        if h < 240:
            return
        active = [x for x in self.rhythm_states if x]
        if not active:
            return
        beats = len(self.rhythm_states)
        dx = min(175.0, (w - 45) / beats)
        left = (w - dx * beats) / 2
        yy = max(h * 0.73, h - 112)
        for i, states in enumerate(self.rhythm_states):
            if not states:
                continue
            cellw = min(29.0, (dx - 8) / len(states))
            x = left + i * dx + 4
            for j, state in enumerate(states):
                fill = TI_BG if state == TI else TA_BG if state == TA else OFF_BG
                self.create_rectangle(x + j * cellw, yy, x + (j + 1) * cellw - 2, yy + 27,
                                      fill=fill, outline=ACCENT if beat == i and j == int(self.state.get("sub", 0)) else "")
                self.create_text(x + (j + 0.5) * cellw - 1, yy + 13, text="Т" if state == TI else "а" if state == TA else "·",
                                 font=("Segoe UI", 9, "bold"), fill="white")


class BeatCard(ttk.LabelFrame):
    """Canonical BeatPattern editing with original grid/preset/mute semantics."""

    def __init__(self, master, number: int, numerator: int, denominator: int,
                 changed: Callable[[], None]) -> None:
        super().__init__(master, text=f"Доля {number}", padding=(8, 6))
        self.number = number
        self.numerator = numerator
        self.denominator = denominator
        self.changed = changed
        self._editing = False
        self._covered = False
        self._active = True
        self._mute_allowed = True
        self._steps = [TI, TA, TA, TA]
        self.muted = tk.BooleanVar(value=False)
        self.grid_key = tk.StringVar(value="quad")
        self.preset_name = tk.StringVar()
        self._grid_labels: dict[str, str] = {}
        self._grid_by_label: dict[str, str] = {}
        self._presets_by_label: dict[str, object] = {}

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 5))
        self.mute_check = ttk.Checkbutton(controls, text="Mute", variable=self.muted, command=self._notify)
        self.mute_check.pack(side="right")
        ttk.Label(self, text="Сетка:").pack(anchor="w")
        self.grid_combo = ttk.Combobox(self, state="readonly", width=24)
        self.grid_combo.pack(fill="x", pady=(2, 4))
        self.grid_combo.bind("<<ComboboxSelected>>", self._grid_changed)
        self.preset_combo = ttk.Combobox(self, state="readonly", width=24)
        self.preset_combo.pack(fill="x", pady=(0, 8))
        self.preset_combo.bind("<<ComboboxSelected>>", self._preset_changed)
        self.step_row = ttk.Frame(self)
        self.step_row.pack(fill="x")
        self.buttons: list[tk.Button] = []
        for i in range(8):
            button = tk.Button(
                self.step_row, text="·", width=3, relief="flat", bd=1,
                font=("Segoe UI", 9, "bold"), cursor="hand2",
                command=lambda j=i: self.cycle(j),
            )
            button.grid(row=0, column=i, padx=1, sticky="ew")
            self.buttons.append(button)
        self._populate_grids()
        self.set_pattern(BeatPattern())

    def _populate_grids(self, preferred: str = "quad") -> None:
        available = [
            spec for spec in grid_specs_for_meter(self.numerator, self.denominator)
            if spec.span_beats <= self.numerator - self.number + 1
        ]
        self._grid_labels = {spec.key: grid_label(spec.key, self.denominator) for spec in available}
        self._grid_by_label = {label: key for key, label in self._grid_labels.items()}
        self.grid_combo.configure(values=tuple(self._grid_by_label.keys()))
        selected = preferred if preferred in self._grid_labels else "beat"
        self.grid_combo.set(self._grid_labels[selected])
        self.grid_key.set(selected)

    def _reload_presets(self) -> None:
        choices = tuple(presets_for_grid(self.grid_key.get()))
        self._presets_by_label = {p.human: p for p in choices}
        self.preset_combo.configure(values=tuple(self._presets_by_label.keys()))
        self.preset_combo.set("Ручная сетка")
        self.preset_combo.configure(state="readonly" if choices else "disabled")

    def _grid_changed(self, _event=None) -> None:
        if self._editing:
            return
        key = self._grid_by_label.get(self.grid_combo.get(), "quad")
        self.grid_key.set(key)
        n = grid_spec(key).steps
        self._steps = (self._steps + [OFF] * n)[:n]
        self._reload_presets()
        self._refresh()
        self._notify()

    def _preset_changed(self, _event=None) -> None:
        chosen = self._presets_by_label.get(self.preset_combo.get())
        if chosen is not None:
            self._steps = list(chosen.steps)
            self._refresh()
            self._notify()

    def _refresh(self) -> None:
        count = grid_spec(self.grid_key.get()).steps
        for i, button in enumerate(self.buttons):
            if i < count:
                button.grid()
                state = self._steps[i]
                button.configure(
                    text="(ТИ)" if state == TI else "ТА" if state == TA else "·",
                    bg=TI_BG if state == TI else TA_BG if state == TA else OFF_BG,
                    fg="white", activeforeground="white",
                    state="normal" if self._active and not self._covered else "disabled",
                )
            else:
                button.grid_remove()
        self.mute_check.configure(state="normal" if self._mute_allowed and not self._covered and self._active else "disabled")
        self.grid_combo.configure(state="readonly" if self._active and not self._covered else "disabled")
        self.preset_combo.configure(state="readonly" if self._presets_by_label and self._active and not self._covered else "disabled")

    def _notify(self) -> None:
        if not self._editing:
            self.changed()

    def cycle(self, index: int) -> None:
        if self._covered or not self._active:
            return
        old = self._steps[index]
        self._steps[index] = {TI: TA, TA: OFF, OFF: TI}[old]
        self.preset_combo.set("Ручная сетка")
        self._refresh()
        self._notify()

    def pattern(self) -> BeatPattern:
        result = BeatPattern(self.grid_key.get(), list(self._steps), self.muted.get())
        result.normalize()
        return result

    def set_pattern(self, beat: BeatPattern) -> None:
        beat = beat.copy()
        beat.normalize()
        self._editing = True
        try:
            self._populate_grids(beat.grid)
            self._steps = list(beat.steps) if beat.grid == self.grid_key.get() else [OFF]
            self.muted.set(bool(beat.muted))
            self._reload_presets()
            self._refresh()
        finally:
            self._editing = False

    def set_covered(self, covered: bool) -> None:
        self._covered = covered
        self._refresh()

    def set_ramp_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def set_mute_allowed(self, allowed: bool) -> None:
        self._mute_allowed = allowed
        self._refresh()

    def highlight(self, step: int | None) -> None:
        for i, btn in enumerate(self.buttons):
            if i < grid_spec(self.grid_key.get()).steps:
                btn.configure(highlightthickness=2 if i == step else 0,
                              highlightbackground=ACCENT if i == step else PANEL)


class HorizontalCards(ttk.Frame):
    """Horizontal scrolling row; all cards are actual widgets, not painted mockups."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, height=205, bg=BG, bd=0, highlightthickness=0)
        self.scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scroll.set)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scroll.pack(side="bottom", fill="x")
        self.content = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def replace(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.canvas.xview_moveto(0)
