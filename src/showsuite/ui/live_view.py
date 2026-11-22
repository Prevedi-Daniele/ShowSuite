"""Live view: pagine con pulsanti cue (toggle/flash), colori, priorità."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMenu,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from ..light.engine import LightEngine
from ..light.live import LiveButton, LivePage


def _text_on(color: QColor) -> str:
    return "#111" if color.lightness() > 150 else "#fff"


class CueButton(QPushButton):
    """Pulsante grande: toggle al click, flash finché premuto."""
    removed = Signal()

    def __init__(self, view: "LiveView", page: LivePage, btn: LiveButton):
        super().__init__(btn.label or btn.cue)
        self.view, self.page, self.btn = view, page, btn
        self._active = None
        self.setMinimumHeight(34)
        self.setMinimumWidth(110)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.restyle(False)

    def cue(self):
        return next((c for c in self.view.engine.project.cues if c.name == self.btn.cue), None)

    def restyle(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        col = QColor(self.btn.color)
        if active:
            bg, fg = col.lighter(125), "#111"
        else:   # tinta scura del colore, testo colorato (come Lightkey)
            bg, fg = QColor(col.red() // 4 + 28, col.green() // 4 + 28, col.blue() // 4 + 28), col.lighter(135).name()
        self.setStyleSheet(f"QPushButton {{ background: {bg.name()}; color: {fg}; border: none; border-radius: 2px;"
                           f" text-align: left; padding: 6px 10px; font-weight: {'700' if active else '500'}; }}")

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        cue, live = self.cue(), self.view.engine.live
        if cue is None or self.view.edit_mode:
            return
        if self.btn.mode == "flash":
            live.start(cue, self.page.priority)
        else:
            live.trigger(cue, self.page.priority)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.btn.mode == "flash" and not self.view.edit_mode:
            cue = self.cue()
            if cue:
                self.view.engine.live.release(cue)

    def _menu(self, pos):
        m = QMenu(self)
        m.addAction("Modalità: " + ("Toggle" if self.btn.mode == "flash" else "Flash"),
                    lambda: setattr(self.btn, "mode", "toggle" if self.btn.mode == "flash" else "flash"))
        m.addAction("Colore…", self._color)
        m.addAction("Etichetta…", self._label)
        m.addAction("Rimuovi dalla pagina", self._remove)
        m.exec(self.mapToGlobal(pos))

    def _color(self):
        c = QColorDialog.getColor(QColor(self.btn.color), self, "Colore pulsante")
        if c.isValid():
            self.btn.color = c.name(); self._active = None; self.restyle(False)

    def _label(self):
        t, ok = QInputDialog.getText(self, "Etichetta", "Testo:", text=self.btn.label or self.btn.cue)
        if ok:
            self.btn.label = t; self.setText(t or self.btn.cue)

    def _remove(self):
        self.page.buttons.remove(self.btn)
        self.removed.emit()


class LiveView(QWidget):
    """Colonna Master/BPM a sinistra, menu pagina e Edit in alto, pulsanti dentro una cornice."""

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        self.edit_mode = False
        self.cur = 0
        # colonna sinistra
        self.master = QSlider(Qt.Vertical); self.master.setRange(0, 100); self.master.setValue(100)
        self.master.setFixedWidth(46); self.master.setMinimumHeight(110)
        self.master.setStyleSheet("QSlider::groove:vertical{background:#2a2d36;width:46px;border-radius:5px;}"
                                  "QSlider::sub-page:vertical{background:#2a2d36;border-radius:5px;}"
                                  "QSlider::add-page:vertical{background:#f3e8ff;border-radius:5px;}"
                                  "QSlider::handle:vertical{height:3px;background:#fff;}")
        self.master.valueChanged.connect(lambda v: setattr(self.engine, "grand_master", v / 100))
        self.bpm_btn = QPushButton(); self.bpm_btn.setToolTip("Clic = tap tempo")
        self.bpm_btn.clicked.connect(self.engine.beat.tap)
        left = QVBoxLayout()
        lab = QLabel("Master"); lab.setAlignment(Qt.AlignCenter); lab.setStyleSheet("color:#8b90a0;")
        left.addWidget(lab); left.addWidget(self.master, 1, Qt.AlignHCenter); left.addWidget(self.bpm_btn)
        # in alto
        self.page_btn = QPushButton(); self.page_btn.setStyleSheet("QPushButton{border-radius:11px;padding:3px 16px;min-height:16px;}")
        self.page_btn.clicked.connect(self._page_menu)
        self.edit_btn = QPushButton("Edit"); self.edit_btn.setCheckable(True)
        self.edit_btn.toggled.connect(self.set_edit)
        self.add_btn = QPushButton("+ Pagina"); self.add_btn.clicked.connect(self.add_page); self.add_btn.hide()
        top = QHBoxLayout(); top.addWidget(self.page_btn); top.addStretch(); top.addWidget(self.add_btn); top.addWidget(self.edit_btn)
        # cornice
        self.frame = QFrame(); self.frame.setObjectName("frame")
        self.frame.setStyleSheet("#frame{background:rgba(255,255,255,0.05);border-radius:6px;}")
        self.grid = QGridLayout(self.frame); self.grid.setSpacing(3); self.grid.setAlignment(Qt.AlignTop)
        self.empty = QLabel("Nessun pulsante: registra un cue dalla selezione (Ctrl+R)")
        self.empty.setStyleSheet("color:#8b90a0;"); self.empty.setAlignment(Qt.AlignCenter)
        mid = QVBoxLayout(); mid.addLayout(top); mid.addWidget(self.frame); mid.addWidget(self.empty); mid.addStretch(1)
        root = QHBoxLayout(self); root.addLayout(left); root.addLayout(mid, 1)
        self.widgets: list[CueButton] = []
        self.rebuild()

    def set_edit(self, on: bool) -> None:
        self.edit_mode = on
        self.add_btn.setVisible(on)
        self.frame.setStyleSheet("#frame{background:rgba(255,255,255,0.05);border-radius:6px;"
                                 + ("border:1px dashed #3a8bff;}" if on else "}"))

    def _page_menu(self) -> None:
        m = QMenu(self)
        for i, pg in enumerate(self.pages):
            m.addAction(("✓ " if i == self.cur else "   ") + pg.name, lambda i=i: self.select_page(i))
        if self.edit_mode and self.page:
            m.addSeparator()
            m.addAction("Rinomina…", lambda: self._rename(self.cur))
            m.addAction("Priorità…", lambda: self._prio(self.page))
            m.addAction("Elimina pagina", lambda: self._delete(self.cur))
        m.exec(self.page_btn.mapToGlobal(self.page_btn.rect().bottomLeft()))

    def select_page(self, i: int) -> None:
        self.cur = max(0, min(i, len(self.pages) - 1)); self._fill_grid()

    # --- pagine ---
    @property
    def pages(self) -> list[LivePage]:
        return self.engine.project.pages

    @property
    def page(self) -> LivePage | None:
        return self.pages[self.cur] if 0 <= self.cur < len(self.pages) else None

    def rebuild(self) -> None:
        self.cur = min(self.cur, max(0, len(self.pages) - 1))
        self._fill_grid()

    def _fill_grid(self) -> None:
        for w in self.widgets:
            w.setParent(None); w.deleteLater()
        self.widgets.clear()
        p = self.page
        self.page_btn.setText((p.name if p else "Nessuna pagina") + " ⌄")
        self.empty.setVisible(not (p and p.buttons)); self.frame.setVisible(bool(p and p.buttons))
        if not p:
            return
        for i, b in enumerate(p.buttons):
            w = CueButton(self, p, b)
            w.removed.connect(self._fill_grid)
            self.grid.addWidget(w, i // p.columns, i % p.columns)
            self.widgets.append(w)

    def add_page(self) -> None:
        name, ok = QInputDialog.getText(self, "Nuova pagina", "Nome:", text=f"Pagina {len(self.pages) + 1}")
        if ok and name:
            self.pages.append(LivePage(name))
            self.cur = len(self.pages) - 1; self.rebuild()

    def add_cue_button(self, cue_name: str) -> None:
        if not self.pages:
            self.pages.append(LivePage("Pagina 1"))
            self.rebuild()
        self.page.buttons.append(LiveButton(cue_name))
        self._fill_grid()

    def _rename(self, i):
        t, ok = QInputDialog.getText(self, "Rinomina", "Nome:", text=self.pages[i].name)
        if ok and t:
            self.pages[i].name = t; self._fill_grid()

    def _prio(self, page):
        v, ok = QInputDialog.getInt(self, "Priorità pagina", "0-99 (più alta vince):", page.priority, 0, 99)
        if ok:
            page.priority = v

    def _delete(self, i):
        del self.pages[i]
        self.rebuild()

    def sync(self) -> None:
        self.bpm_btn.setText(f"{self.engine.beat.bpm:.0f} bpm")
        v = round(self.engine.grand_master * 100)
        if v != self.master.value() and not self.master.isSliderDown():
            self.master.blockSignals(True); self.master.setValue(v); self.master.blockSignals(False)
        for w in self.widgets:
            st = self.engine.live.active.get(w.btn.cue)
            w.restyle(bool(st and not st["releasing"]))
