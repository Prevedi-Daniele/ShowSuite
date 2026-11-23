"""Scheda Effetti: libreria + editor colore/posizione, anteprima sul Preview e creazione di un pulsante Live."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QInputDialog, QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..light import effectlib
from ..light.live import LiveCue
from ..light.posfx import PositionEffect
from .color_effect_editor import ColorEffectEditor
from .effect_editor import PositionEffectEditor


class EffectView(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.color_btn = QPushButton("Color Effect"); self.pos_btn = QPushButton("Position Effect")
        for b in (self.color_btn, self.pos_btn):
            b.setCheckable(True)
        self.color_btn.clicked.connect(lambda: self.set_mode("color")); self.pos_btn.clicked.connect(lambda: self.set_mode("position"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Cerca effetto…"); self.search.textChanged.connect(self.fill)
        self.lib = QListWidget(); self.lib.setMaximumWidth(200); self.lib.itemClicked.connect(self._load)
        self.color_ed = ColorEffectEditor(effectlib.get("Fire")); self.pos_ed = PositionEffectEditor()
        self.stack = QStackedWidget(); self.stack.addWidget(self.color_ed); self.stack.addWidget(self.pos_ed)
        self.try_btn = QPushButton("Prova sulla selezione"); self.try_btn.setCheckable(True)
        self.try_btn.toggled.connect(self._try)
        self.make_btn = QPushButton("Crea pulsante Live…"); self.make_btn.clicked.connect(self.make_button)
        top = QHBoxLayout(); top.addWidget(self.color_btn); top.addWidget(self.pos_btn); top.addStretch()
        top.addWidget(self.try_btn); top.addWidget(self.make_btn)
        left = QVBoxLayout(); left.addWidget(self.search); left.addWidget(self.lib)
        body = QHBoxLayout(); body.addLayout(left); body.addWidget(self.stack, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addLayout(body)
        self.mode = "color"; self.t = 0.0
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.setInterval(40)
        self.set_mode("color")

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.color_btn.setChecked(mode == "color"); self.pos_btn.setChecked(mode == "position")
        self.stack.setCurrentIndex(0 if mode == "color" else 1)
        self.search.setVisible(mode == "color"); self.lib.setVisible(mode == "color")
        self.fill()

    def fill(self, *_) -> None:
        self.lib.clear()
        if self.mode == "color":
            self.lib.addItems(effectlib.search(self.search.text()))

    def _load(self, item) -> None:
        self.color_ed.effect.__dict__.update(effectlib.get(item.text()).__dict__)
        self.color_ed.mode_btn.setChecked(self.color_ed.effect.mode == "swatches")
        self.color_ed.dur.setValue(self.color_ed.effect.duration)
        self.color_ed.rebuild_swatches(); self.color_ed.curve.update()
        self.color_ed.changed.emit(self.color_ed.effect)

    def effect(self):
        return self.color_ed.effect if self.mode == "color" else self.pos_ed.effect

    # --- anteprima
    def _try(self, on: bool) -> None:
        if on and not self.win.selected_names():
            self.try_btn.blockSignals(True); self.try_btn.setChecked(False); self.try_btn.blockSignals(False)
            QMessageBox.information(self, "Effetti", "Seleziona dei fixture nel Preview."); return
        self.t = 0.0
        if on:
            self._names = self.win.selected_names(); self.timer.start()
        else:
            self.timer.stop()
            for n in getattr(self, "_names", []):
                self.win.engine.release_programmer(n)

    def _tick(self) -> None:
        self.t += 0.04
        self.effect().apply(self.win.engine, self._names, self.t)

    # --- pulsante Live
    def make_button(self) -> None:
        names = self.win.selected_names()
        if not names:
            QMessageBox.information(self, "Effetti", "Seleziona dei fixture nel Preview."); return
        name, ok = QInputDialog.getText(self, "Nuovo pulsante", "Nome del cue:")
        name = name.strip()
        if not ok or not name:
            return
        if any(c.name == name for c in self.win.engine.project.cues):
            QMessageBox.warning(self, "Effetti", "Esiste già un cue con questo nome."); return
        from copy import deepcopy
        fx = deepcopy(self.effect())
        cue = LiveCue(name, names, color_fx=fx if self.mode == "color" else None,
                      position_fx=fx if self.mode == "position" else None)
        self.win.engine.project.cues.append(cue)
        self.win.live_view.add_cue_button(name)
