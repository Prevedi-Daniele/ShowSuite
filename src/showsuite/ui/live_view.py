"""Live view: pagine con pulsanti cue (toggle/flash), colori, priorità."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QGridLayout, QHBoxLayout, QInputDialog, QMenu,
                               QPushButton, QTabBar, QVBoxLayout, QWidget)

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
        self.setMinimumHeight(64)
        self.setMinimumWidth(90)
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
        shown = col if active else col.darker(220)
        border = "3px solid #ffffff" if active else "1px solid #33363f"
        self.setStyleSheet(f"QPushButton {{ background: {shown.name()}; color: {_text_on(shown)};"
                           f" border: {border}; font-weight: {'700' if active else '500'}; }}")

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        cue, live = self.cue(), self.view.engine.live
        if cue is None:
            return
        if self.btn.mode == "flash":
            live.start(cue, self.page.priority)
        else:
            live.trigger(cue, self.page.priority)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.btn.mode == "flash":
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
    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        v = QVBoxLayout(self)
        row = QHBoxLayout()
        self.tabs = QTabBar(); self.tabs.setExpanding(False); self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(lambda _: self._fill_grid())
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._tab_menu)
        add = QPushButton("+ Pagina"); add.clicked.connect(self.add_page)
        row.addWidget(self.tabs); row.addWidget(add); row.addStretch()
        v.addLayout(row)
        self.grid_w = QWidget(); self.grid = QGridLayout(self.grid_w)
        self.grid.setSpacing(8)
        self.grid.setAlignment(Qt.AlignTop)
        v.addWidget(self.grid_w)
        v.addStretch(1)
        self.widgets: list[CueButton] = []
        self.rebuild()

    # --- pagine ---
    @property
    def pages(self) -> list[LivePage]:
        return self.engine.project.pages

    @property
    def page(self) -> LivePage | None:
        i = self.tabs.currentIndex()
        return self.pages[i] if 0 <= i < len(self.pages) else None

    def rebuild(self) -> None:
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for p in self.pages:
            self.tabs.addTab(p.name)
        self.tabs.blockSignals(False)
        self._fill_grid()

    def _fill_grid(self) -> None:
        for w in self.widgets:
            w.setParent(None); w.deleteLater()
        self.widgets.clear()
        p = self.page
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
            self.rebuild(); self.tabs.setCurrentIndex(len(self.pages) - 1)

    def add_cue_button(self, cue_name: str) -> None:
        if not self.pages:
            self.pages.append(LivePage("Pagina 1"))
            self.rebuild()
        self.page.buttons.append(LiveButton(cue_name))
        self._fill_grid()

    def _tab_menu(self, pos):
        i = self.tabs.tabAt(pos)
        if i < 0:
            return
        page = self.pages[i]
        m = QMenu(self)
        m.addAction("Rinomina…", lambda: self._rename(i))
        m.addAction("Priorità…", lambda: self._prio(page))
        m.addAction("Elimina pagina", lambda: self._delete(i))
        m.exec(self.tabs.mapToGlobal(pos))

    def _rename(self, i):
        t, ok = QInputDialog.getText(self, "Rinomina", "Nome:", text=self.pages[i].name)
        if ok and t:
            self.pages[i].name = t; self.tabs.setTabText(i, t)

    def _prio(self, page):
        v, ok = QInputDialog.getInt(self, "Priorità pagina", "0-99 (più alta vince):", page.priority, 0, 99)
        if ok:
            page.priority = v

    def _delete(self, i):
        del self.pages[i]
        self.rebuild()

    def sync(self) -> None:
        for w in self.widgets:
            st = self.engine.live.active.get(w.btn.cue)
            w.restyle(bool(st and not st["releasing"]))
