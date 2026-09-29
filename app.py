from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider,
    QSpinBox, QVBoxLayout, QWidget,
)

from audio_engine import AudioEngine
from model import BarPattern, BeatPattern
from presets import ALL_PRESETS, OFF, TA, TI, CellPreset, presets_for_subdivision

APP_NAME = "TittyTatter"
VERSION_FILE = Path(__file__).with_name("VERSION")
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.1"
STATE_TEXT = {TI: "ТИ", TA: "ТА", OFF: "·"}
STATE_STYLE = {
    TI: "background:#3169c6;color:white;font-weight:700;border:2px solid #5f95f2;border-radius:8px;padding:10px;",
    TA: "background:#42464f;color:white;font-weight:700;border:2px solid #666b75;border-radius:8px;padding:10px;",
    OFF: "background:#22252a;color:#8e949e;border:2px solid #343941;border-radius:8px;padding:10px;",
}


class StepButton(QPushButton):
    changed = Signal()
    def __init__(self) -> None:
        super().__init__(); self.state = OFF; self.playing = False; self.setMinimumWidth(54); self.clicked.connect(self.cycle); self.refresh()
    def cycle(self) -> None:
        order = (TI, TA, OFF); self.set_state(order[(order.index(self.state) + 1) % 3]); self.changed.emit()
    def set_state(self, state: str) -> None:
        self.state = state if state in (TI, TA, OFF) else OFF; self.refresh()
    def set_playing(self, value: bool) -> None:
        self.playing = value; self.refresh()
    def refresh(self) -> None:
        extra = "border:3px solid #f3c969;" if self.playing else ""; self.setText(STATE_TEXT[self.state]); self.setStyleSheet(f"QPushButton{{{STATE_STYLE[self.state]}{extra}}}")


class BeatEditor(QGroupBox):
    changed = Signal()
    def __init__(self, number: int) -> None:
        super().__init__(f"Доля {number}"); box = QVBoxLayout(self)
        row = QHBoxLayout(); row.addWidget(QLabel("Сетка:")); self.grid = QComboBox(); self.grid.addItem("16-е ×4", 4); self.grid.addItem("Триоль ×3", 3); row.addWidget(self.grid, 1); box.addLayout(row)
        row = QHBoxLayout(); self.preset = QComboBox(); self.apply_btn = QPushButton("Применить"); row.addWidget(self.preset, 1); row.addWidget(self.apply_btn); box.addLayout(row)
        row = QHBoxLayout(); self.steps = [StepButton() for _ in range(4)]
        for b in self.steps: b.changed.connect(self.changed.emit); row.addWidget(b)
        box.addLayout(row)
        row = QHBoxLayout(); inv = QPushButton("ТИ↔ТА"); clear = QPushButton("Паузы"); row.addWidget(inv); row.addWidget(clear); box.addLayout(row)
        self.grid.currentIndexChanged.connect(self._grid_changed); self.apply_btn.clicked.connect(self.apply_preset); inv.clicked.connect(self.invert); clear.clicked.connect(self.clear)
        self.set_pattern(BeatPattern(4, [TI, TA, TA, TA]))
    def _reload(self) -> None:
        self.preset.clear()
        for p in presets_for_subdivision(int(self.grid.currentData())): self.preset.addItem(p.human, p)
    def _grid_changed(self) -> None:
        sub = int(self.grid.currentData()); self._reload()
        for i, b in enumerate(self.steps):
            b.setVisible(i < sub)
            if i >= sub: b.set_state(OFF)
        self.changed.emit()
    def apply_preset(self) -> None:
        p = self.preset.currentData()
        if isinstance(p, CellPreset): self.set_pattern(BeatPattern(p.subdivision, list(p.steps))); self.changed.emit()
    def invert(self) -> None:
        for b in self.steps[:int(self.grid.currentData())]:
            if b.state == TI: b.set_state(TA)
            elif b.state == TA: b.set_state(TI)
        self.changed.emit()
    def clear(self) -> None:
        for b in self.steps[:int(self.grid.currentData())]: b.set_state(OFF)
        self.changed.emit()
    def pattern(self) -> BeatPattern:
        sub = int(self.grid.currentData()); return BeatPattern(sub, [b.state for b in self.steps[:sub]])
    def set_pattern(self, p: BeatPattern) -> None:
        p.normalize(); self.grid.blockSignals(True); self.grid.setCurrentIndex(self.grid.findData(p.subdivision)); self.grid.blockSignals(False); self._reload()
        for i, b in enumerate(self.steps): b.setVisible(i < p.subdivision); b.set_state(p.steps[i] if i < p.subdivision else OFF)
        for i in range(self.preset.count()):
            q = self.preset.itemData(i)
            if isinstance(q, CellPreset) and q.steps == tuple(p.steps): self.preset.setCurrentIndex(i); break
    def playhead(self, sub: int | None) -> None:
        n = int(self.grid.currentData())
        for i, b in enumerate(self.steps): b.set_playing(sub is not None and i == sub and i < n)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__(); self.setWindowTitle(f"{APP_NAME} {APP_VERSION}"); self.resize(1180, 780); self.settings = QSettings(APP_NAME, APP_NAME); self.engine = AudioEngine(); self.tap_times: list[float] = []
        self._ui(); self._shortcuts(); self._restore(); self._sync(); self.timer = QTimer(self); self.timer.timeout.connect(self._poll); self.timer.start(30)
    def _ui(self) -> None:
        root = QWidget(); out = QVBoxLayout(root)
        row = QHBoxLayout(); self.play = QPushButton("▶ Старт"); self.play.clicked.connect(self.toggle); row.addWidget(self.play); row.addWidget(QLabel("BPM")); self.bpm = QSpinBox(); self.bpm.setRange(20, 320); self.bpm.setValue(80); row.addWidget(self.bpm)
        self.bpm_slider = QSlider(Qt.Horizontal); self.bpm_slider.setRange(20, 320); self.bpm_slider.setValue(80); row.addWidget(self.bpm_slider, 1)
        for delta in (-5, -1, 1, 5):
            b = QPushButton(f"{delta:+d}"); b.clicked.connect(lambda _=False, d=delta: self.bpm.setValue(self.bpm.value()+d)); row.addWidget(b)
        self.tap = QPushButton("TAP [T]"); self.tap.clicked.connect(self.tap_tempo); row.addWidget(self.tap); out.addLayout(row)
        self.status = QLabel("Готов"); self.status.setAlignment(Qt.AlignCenter); self.status.setStyleSheet("font-size:17px;font-weight:700;padding:6px"); out.addWidget(self.status)
        group = QGroupBox("Такт 4/4 — сетка выбирается отдельно для каждой доли"); row = QHBoxLayout(group); self.editors = [BeatEditor(i+1) for i in range(4)]
        for e in self.editors: e.changed.connect(self._pattern_changed); row.addWidget(e, 1)
        out.addWidget(group)
        ab = QGroupBox("Конструктор A / B"); g = QGridLayout(ab); self.a = QComboBox(); self.b = QComboBox()
        for p in ALL_PRESETS: self.a.addItem(p.display_name, p); self.b.addItem(p.display_name, p)
        g.addWidget(QLabel("A:"),0,0); g.addWidget(self.a,0,1); g.addWidget(QLabel("B:"),1,0); g.addWidget(self.b,1,1)
        for col, shape in enumerate(("ABAB","ABBA","AABB")):
            btn=QPushButton(shape); btn.clicked.connect(lambda _=False,s=shape:self.apply_ab(s)); g.addWidget(btn,2,col)
        ramp=QPushButton("ABAB + разгон 2/4→4/4"); ramp.clicked.connect(self.apply_ab_ramp); g.addWidget(ramp,2,3)
        random_btn=QPushButton("Случайный такт"); random_btn.clicked.connect(self.randomize); g.addWidget(random_btn,3,0,1,2)
        invert_btn=QPushButton("Инвертировать весь такт"); invert_btn.clicked.connect(lambda:[e.invert() for e in self.editors]); g.addWidget(invert_btn,3,2,1,2); out.addWidget(ab)
        settings = QGroupBox("Тренировка / звук"); g = QGridLayout(settings)
        self.mode=QComboBox(); self.mode.addItem("Петля 4/4","loop"); self.mode.addItem("Разгон 1/4→2/4→3/4→4/4","ramp_1_4"); self.mode.addItem("Разгон 2/4→4/4","ramp_2_4")
        self.bars=QSpinBox(); self.bars.setRange(1,64); self.bars.setValue(8); self.count=QSpinBox(); self.count.setRange(0,8); self.count.setValue(1); self.inactive=QCheckBox("ТА-пульс на незаполненных долях"); self.inactive.setChecked(True)
        g.addWidget(QLabel("Режим"),0,0); g.addWidget(self.mode,0,1); g.addWidget(QLabel("Тактов/этап"),0,2); g.addWidget(self.bars,0,3); g.addWidget(QLabel("Count-in"),0,4); g.addWidget(self.count,0,5); g.addWidget(self.inactive,1,0,1,3)
        self.tempo_train=QCheckBox("Tempo trainer"); self.tempo_step=QSpinBox(); self.tempo_step.setRange(1,20); self.tempo_step.setValue(2); self.tempo_every=QSpinBox(); self.tempo_every.setRange(1,64); self.tempo_every.setValue(4); self.tempo_target=QSpinBox(); self.tempo_target.setRange(20,320); self.tempo_target.setValue(140)
        g.addWidget(self.tempo_train,1,3); g.addWidget(QLabel("± BPM"),1,4); g.addWidget(self.tempo_step,1,5); g.addWidget(QLabel("каждые такты"),2,3); g.addWidget(self.tempo_every,2,4); g.addWidget(QLabel("цель"),2,5); g.addWidget(self.tempo_target,2,6)
        self.ti_on=QCheckBox("ТИ"); self.ti_on.setChecked(True); self.ti_sound=QComboBox(); self.ti_sound.addItems(["Clap","Wood","Click","Beep"]); self.ti_vol=QSlider(Qt.Horizontal); self.ti_vol.setRange(0,100); self.ti_vol.setValue(95)
        self.ta_on=QCheckBox("ТА"); self.ta_sound=QComboBox(); self.ta_sound.addItems(["Muted click","Rim","Low tick"]); self.ta_vol=QSlider(Qt.Horizontal); self.ta_vol.setRange(0,100); self.ta_vol.setValue(58)
        self.metro_on=QCheckBox("Метроном"); self.metro_on.setChecked(True); self.accent=QCheckBox("Акцент 1"); self.accent.setChecked(True); self.metro_vol=QSlider(Qt.Horizontal); self.metro_vol.setRange(0,100); self.metro_vol.setValue(38); self.master=QSlider(Qt.Horizontal); self.master.setRange(0,100); self.master.setValue(85)
        g.addWidget(self.ti_on,3,0); g.addWidget(self.ti_sound,3,1); g.addWidget(self.ti_vol,3,2); g.addWidget(self.ta_on,3,3); g.addWidget(self.ta_sound,3,4); g.addWidget(self.ta_vol,3,5); g.addWidget(self.metro_on,4,0); g.addWidget(self.accent,4,1); g.addWidget(self.metro_vol,4,2); g.addWidget(QLabel("Master"),4,3); g.addWidget(self.master,4,4,1,2); out.addWidget(settings)
        row=QHBoxLayout(); save=QPushButton("Сохранить сессию"); load=QPushButton("Загрузить сессию"); reset=QPushButton("Сброс"); save.clicked.connect(self.save_session); load.clicked.connect(self.load_session); reset.clicked.connect(self.reset); row.addWidget(save); row.addWidget(load); row.addWidget(reset); row.addStretch(); out.addLayout(row); self.setCentralWidget(root)
        self.bpm.valueChanged.connect(self._bpm_from_spin); self.bpm_slider.valueChanged.connect(self._bpm_from_slider)
        for w in (self.mode,self.bars,self.count,self.inactive,self.tempo_train,self.tempo_step,self.tempo_every,self.tempo_target,self.ti_on,self.ti_sound,self.ti_vol,self.ta_on,self.ta_sound,self.ta_vol,self.metro_on,self.accent,self.metro_vol,self.master):
            sig = getattr(w,"valueChanged",None) or getattr(w,"toggled",None) or getattr(w,"currentIndexChanged",None)
            if sig: sig.connect(self._config_changed)
    def _shortcuts(self) -> None:
        QShortcut(QKeySequence("Space"),self,activated=self.toggle); QShortcut(QKeySequence("T"),self,activated=self.tap_tempo); QShortcut(QKeySequence("Up"),self,activated=lambda:self.bpm.setValue(self.bpm.value()+1)); QShortcut(QKeySequence("Down"),self,activated=lambda:self.bpm.setValue(self.bpm.value()-1)); QShortcut(QKeySequence("Shift+Up"),self,activated=lambda:self.bpm.setValue(self.bpm.value()+5)); QShortcut(QKeySequence("Shift+Down"),self,activated=lambda:self.bpm.setValue(self.bpm.value()-5))
    def current_pattern(self) -> BarPattern: return BarPattern([e.pattern() for e in self.editors])
    def _pattern_changed(self) -> None: self.engine.set_pattern(self.current_pattern())
    def _config_changed(self,*_) -> None:
        self.engine.set_config(bpm=self.bpm.value(),practice_mode=self.mode.currentData(),bars_per_stage=self.bars.value(),count_in_bars=self.count.value(),inactive_pulse=self.inactive.isChecked(),tempo_trainer_enabled=self.tempo_train.isChecked(),tempo_step=self.tempo_step.value(),tempo_every_bars=self.tempo_every.value(),tempo_target=self.tempo_target.value(),ti_enabled=self.ti_on.isChecked(),ti_sound=self.ti_sound.currentText(),ti_volume=self.ti_vol.value()/100,ta_enabled=self.ta_on.isChecked(),ta_sound=self.ta_sound.currentText(),ta_volume=self.ta_vol.value()/100,metronome_enabled=self.metro_on.isChecked(),accent_first_beat=self.accent.isChecked(),metronome_volume=self.metro_vol.value()/100,master_volume=self.master.value()/100)
    def _sync(self) -> None: self._pattern_changed(); self._config_changed()
    def _bpm_from_spin(self,v:int) -> None: self.bpm_slider.blockSignals(True); self.bpm_slider.setValue(v); self.bpm_slider.blockSignals(False); self.engine.set_config(bpm=v)
    def _bpm_from_slider(self,v:int) -> None: self.bpm.blockSignals(True); self.bpm.setValue(v); self.bpm.blockSignals(False); self.engine.set_config(bpm=v)
    def toggle(self) -> None:
        try:
            if self.engine.is_running: self.engine.stop(); self.play.setText("▶ Старт"); self.clear_playhead()
            else: self._sync(); self.engine.start(); self.play.setText("■ Стоп")
        except Exception as exc:
            self.engine.stop(); self.play.setText("▶ Старт"); QMessageBox.critical(self,"Ошибка аудио",str(exc))
    def tap_tempo(self) -> None:
        now=time.perf_counter()
        if self.tap_times and now-self.tap_times[-1]>2.5:self.tap_times=[]
        self.tap_times.append(now); self.tap_times=self.tap_times[-7:]
        if len(self.tap_times)>1:
            ints=[b-a for a,b in zip(self.tap_times,self.tap_times[1:])]
            if len(ints)>=4: ints=sorted(ints)[1:-1]
            self.bpm.setValue(round(60/(sum(ints)/len(ints))))
    def apply_ab(self,shape:str) -> None:
        a,b=self.a.currentData(),self.b.currentData()
        if not isinstance(a,CellPreset) or not isinstance(b,CellPreset): return
        for e,t in zip(self.editors,shape):
            p=a if t=="A" else b; e.set_pattern(BeatPattern(p.subdivision,list(p.steps)))
        self._pattern_changed()
    def apply_ab_ramp(self) -> None: self.apply_ab("ABAB"); self.mode.setCurrentIndex(self.mode.findData("ramp_2_4")); self._config_changed()
    def randomize(self) -> None:
        for e in self.editors:
            p=random.choice(ALL_PRESETS); e.set_pattern(BeatPattern(p.subdivision,list(p.steps)))
        self._pattern_changed()
    def _poll(self) -> None:
        st=self.engine.status()
        if not st["running"]: return
        bpm=round(st["bpm"])
        if bpm!=self.bpm.value(): self.bpm.setValue(bpm)
        if st["count_in"]: self.status.setText(f"COUNT-IN · {bpm} BPM"); self.highlight(st["beat"],None); return
        stage="4/4" if self.mode.currentData()=="loop" else f"{st['active_beats']}/4"; self.status.setText(f"Такт {st['bar']} · этап {stage} · доля {st['beat']+1} · {bpm} BPM"); self.highlight(st["beat"],st["sub"])
    def highlight(self,beat:int,sub:int|None) -> None:
        for i,e in enumerate(self.editors): e.playhead(sub if i==beat else None)
    def clear_playhead(self) -> None:
        for e in self.editors:e.playhead(None)
    def session(self) -> dict:
        return {"version":1,"bpm":self.bpm.value(),"pattern":self.current_pattern().to_dict(),"practice":{"mode":self.mode.currentData(),"bars":self.bars.value(),"count":self.count.value(),"inactive":self.inactive.isChecked(),"trainer":self.tempo_train.isChecked(),"step":self.tempo_step.value(),"every":self.tempo_every.value(),"target":self.tempo_target.value()},"sound":{"ti_on":self.ti_on.isChecked(),"ti_sound":self.ti_sound.currentText(),"ti_vol":self.ti_vol.value(),"ta_on":self.ta_on.isChecked(),"ta_sound":self.ta_sound.currentText(),"ta_vol":self.ta_vol.value(),"metro_on":self.metro_on.isChecked(),"accent":self.accent.isChecked(),"metro_vol":self.metro_vol.value(),"master":self.master.value()}}
    def save_session(self) -> None:
        path,_=QFileDialog.getSaveFileName(self,"Сохранить","tittytatter_session.json","JSON (*.json)")
        if path: Path(path).write_text(json.dumps(self.session(),ensure_ascii=False,indent=2),encoding="utf-8")
    def load_session(self) -> None:
        path,_=QFileDialog.getOpenFileName(self,"Загрузить","","JSON (*.json)")
        if not path:return
        try:self.apply_session(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception as exc: QMessageBox.warning(self,"Ошибка",str(exc))
    def apply_session(self,d:dict) -> None:
        self.bpm.setValue(int(d.get("bpm",80))); bar=BarPattern.from_dict(d.get("pattern",{}))
        for e,p in zip(self.editors,bar.beats):e.set_pattern(p)
        p=d.get("practice",{}); self.mode.setCurrentIndex(max(0,self.mode.findData(p.get("mode","loop")))); self.bars.setValue(int(p.get("bars",8))); self.count.setValue(int(p.get("count",1))); self.inactive.setChecked(bool(p.get("inactive",True))); self.tempo_train.setChecked(bool(p.get("trainer",False))); self.tempo_step.setValue(int(p.get("step",2))); self.tempo_every.setValue(int(p.get("every",4))); self.tempo_target.setValue(int(p.get("target",140)))
        s=d.get("sound",{}); self.ti_on.setChecked(bool(s.get("ti_on",True))); self._combo(self.ti_sound,s.get("ti_sound","Clap")); self.ti_vol.setValue(int(s.get("ti_vol",95))); self.ta_on.setChecked(bool(s.get("ta_on",False))); self._combo(self.ta_sound,s.get("ta_sound","Muted click")); self.ta_vol.setValue(int(s.get("ta_vol",58))); self.metro_on.setChecked(bool(s.get("metro_on",True))); self.accent.setChecked(bool(s.get("accent",True))); self.metro_vol.setValue(int(s.get("metro_vol",38))); self.master.setValue(int(s.get("master",85))); self._sync()
    @staticmethod
    def _combo(c:QComboBox,text:str) -> None:
        i=c.findText(str(text))
        if i>=0:c.setCurrentIndex(i)
    def reset(self) -> None:
        self.engine.stop(); self.bpm.setValue(80)
        for e in self.editors:e.set_pattern(BeatPattern(4,[TI,TA,TA,TA]))
        self.mode.setCurrentIndex(0); self.bars.setValue(8); self.count.setValue(1); self.inactive.setChecked(True); self.tempo_train.setChecked(False); self.ti_on.setChecked(True); self.ta_on.setChecked(False); self.metro_on.setChecked(True); self._sync()
    def _restore(self) -> None:
        g=self.settings.value("geometry")
        if g:self.restoreGeometry(g)
        self.bpm.setValue(int(self.settings.value("bpm",80)))
    def closeEvent(self,event:QCloseEvent) -> None:
        self.settings.setValue("geometry",self.saveGeometry()); self.settings.setValue("bpm",self.bpm.value()); self.engine.close(); event.accept()


def main() -> int:
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setStyle("Fusion"); w=MainWindow(); w.show(); return app.exec()


if __name__=="__main__": raise SystemExit(main())
