"""Live view: pagine con pulsanti cue (toggle/flash), colori, priorità."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMenu,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from ..light.engine import LightEngine
from ..light.live import CueList, LiveButton, LivePage, duplicate_button
from .cuelist_view import CueListView
from .button_popover import ButtonPopover


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

    def mouseDoubleClickEvent(self, e):
        if self.view.edit_mode and e.button() == Qt.LeftButton:
            self.view.open_popover(self)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        cue, live = self.cue(), self.view.engine.live
        if cue is None or self.view.edit_mode:
            return
        if self.btn.group:
            others = [c for b in self.page.buttons if b.group == self.btn.group and b is not self.btn
                      for c in self.view.engine.project.cues if c.name == b.cue]
            live.trigger_exclusive(cue, others, self.page.priority)
        elif self.btn.mode == "flash":
            live.start(cue, self.page.priority)
        else:
            live.trigger(cue, self.page.priority)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.btn.mode == "flash" and not self.view.edit_mode:
            cue = self.cue()
            if cue:
                self.view.engine.live.release(cue)

    def _menu(self, pos):
        self.view.button_menu(self, pos)

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


class FaderButton(QWidget):
    """Fader verticale che controlla il livello di un cue (come i fader di Lightkey)."""

    def __init__(self, view: "LiveView", page: LivePage, btn: LiveButton):
        super().__init__()
        self.view, self.page, self.btn = view, page, btn
        self.slider = QSlider(Qt.Vertical); self.slider.setRange(0, 100); self.slider.setMinimumHeight(90)
        col = QColor(btn.color)
        self.slider.setStyleSheet(f"QSlider::groove:vertical{{background:#2a2d36;width:34px;border-radius:4px;}}"
                                  f"QSlider::sub-page:vertical{{background:#2a2d36;}}"
                                  f"QSlider::add-page:vertical{{background:{col.name()};border-radius:4px;}}"
                                  f"QSlider::handle:vertical{{height:3px;background:#fff;}}")
        self.label = QLabel(btn.label or btn.cue); self.label.setAlignment(Qt.AlignCenter)
        self.slider.valueChanged.connect(self._moved)
        v = QVBoxLayout(self); v.setContentsMargins(2, 2, 2, 2)
        v.addWidget(self.slider, 1, Qt.AlignHCenter); v.addWidget(self.label)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self.view.button_menu(self, pos))

    def cue(self):
        return next((c for c in self.view.engine.project.cues if c.name == self.btn.cue), None)

    def _moved(self, v: int) -> None:
        cue = self.cue()
        if cue and not self.view.edit_mode:
            self.view.engine.live.set_fader(cue, v / 100, self.page.priority)

    def restyle(self, active: bool) -> None:
        pass


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
        self.frame = QWidget(); self.frames_box = QHBoxLayout(self.frame); self.frames_box.setContentsMargins(0, 0, 0, 0)
        self.frames_box.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.frame_widgets: list[QFrame] = []
        self.empty = QLabel("Nessun pulsante: registra un cue dalla selezione (Ctrl+R)")
        self.empty.setStyleSheet("color:#8b90a0;"); self.empty.setAlignment(Qt.AlignCenter)
        self.cl_view: CueListView | None = None
        self.cl_box = QVBoxLayout()
        mid = QVBoxLayout(); mid.addLayout(top); mid.addWidget(self.frame); mid.addWidget(self.empty)
        mid.addLayout(self.cl_box); mid.addStretch(1)
        root = QHBoxLayout(self); root.addLayout(left); root.addLayout(mid, 1)
        self.widgets: list[CueButton] = []
        self.rebuild()

    def set_edit(self, on: bool) -> None:
        self.edit_mode = on
        self.add_btn.setVisible(on)
        self._fill_grid()

    def _page_menu(self) -> None:
        m = QMenu(self)
        for i, pg in enumerate(self.pages):
            m.addAction(("✓ " if i == self.cur else "   ") + pg.name, lambda i=i: self.select_page(i))
        if self.edit_mode and self.page:
            m.addSeparator()
            if not self.page.cuelist:
                m.addAction("Aggiungi cuelist", self.add_cuelist)
            else:
                m.addAction("Rimuovi cuelist", self.remove_cuelist)
            m.addAction("Rinomina…", lambda: self._rename(self.cur))
            m.addAction("Priorità…", lambda: self._prio(self.page))
            m.addAction("Elimina pagina", lambda: self._delete(self.cur))
        m.exec(self.page_btn.mapToGlobal(self.page_btn.rect().bottomLeft()))

    def add_cuelist(self) -> None:
        """Crea la cuelist della pagina con un passo per ogni pulsante."""
        from ..light.live import CueListStep
        p = self.page
        if p and not p.cuelist:
            p.cuelist = CueList(p.name, [CueListStep(b.cue) for b in p.buttons if b.kind != "text"])
            self._fill_grid()

    def remove_cuelist(self) -> None:
        p = self.page
        if p and p.cuelist:
            self.engine.live.stop_cuelist(p.cuelist); p.cuelist = None; self._fill_grid()

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
        for f in self.frame_widgets:
            f.setParent(None); f.deleteLater()
        self.frame_widgets.clear()
        p = self.page
        self.page_btn.setText((p.name if p else "Nessuna pagina") + " ⌄")
        has = bool(p and p.buttons)
        self.empty.setVisible(not has); self.frame.setVisible(has)
        if self.cl_view:
            self.cl_view.setParent(None); self.cl_view.deleteLater(); self.cl_view = None
        if p and p.cuelist:
            self.cl_view = CueListView(self.engine, p); self.cl_box.addWidget(self.cl_view)
            self.empty.setVisible(False)
        if not p:
            return
        nframes = max(len(p.frames), max((b.frame for b in p.buttons), default=0) + 1)
        while len(p.frames) < nframes:
            p.frames.append("")
        for fi in range(nframes):
            members = [b for b in p.buttons if b.frame == fi]
            if not members and not self.edit_mode:
                continue
            box = QFrame(); box.setObjectName("frame")
            box.setStyleSheet("#frame{background:rgba(255,255,255,0.05);border-radius:6px;"
                              + ("border:1px dashed #3a8bff;" if self.edit_mode else "") + "}")
            v = QVBoxLayout(box); v.setContentsMargins(6, 6, 6, 6)
            if p.frames[fi] or self.edit_mode:
                t = QLabel(p.frames[fi] or "(senza titolo)"); t.setStyleSheet("color:#8b90a0;")
                t.setContextMenuPolicy(Qt.CustomContextMenu)
                t.customContextMenuRequested.connect(lambda pos, fi=fi: self._frame_menu(fi))
                v.addWidget(t)
            grid = QGridLayout(); grid.setSpacing(3); grid.setAlignment(Qt.AlignTop); v.addLayout(grid)
            for b in members:
                if b.kind == "text":
                    t = QLabel(b.label or "Testo"); t.setStyleSheet(f"color:{b.color};font-size:15px;font-weight:600;padding:2px 4px;")
                    t.setContextMenuPolicy(Qt.CustomContextMenu)
                    t.customContextMenuRequested.connect(lambda pos, b=b, t=t: self._text_menu(b, t))
                    v.addWidget(t)
            btns = [b for b in members if b.kind == "button"]; fads = [b for b in members if b.kind == "fader"]
            cols = 2 if len(btns) > 1 else 1
            for i, b in enumerate(btns):
                w = CueButton(self, p, b); w.removed.connect(self._fill_grid)
                grid.addWidget(w, i // cols, i % cols); self.widgets.append(w)
            for j, b in enumerate(fads):
                w = FaderButton(self, p, b); grid.addWidget(w, 0, cols + j, max(1, (len(btns) + 1) // 2), 1)
                self.widgets.append(w)
            self.frames_box.addWidget(box); self.frame_widgets.append(box)

    def _text_menu(self, b, w) -> None:
        m = QMenu(w)
        m.addAction("Modifica testo…", lambda: self._pick_label(b)); m.addAction("Colore…", lambda: self._pick_color(b))
        m.addAction("Rimuovi", lambda: (self.page.buttons.remove(b), self._fill_grid()))
        m.exec(self.cursor().pos())

    def add_text(self, fi: int) -> None:
        t, ok = QInputDialog.getText(self, "Testo", "Testo:")
        if ok and t and self.page:
            self.page.buttons.append(LiveButton("", label=t, color="#e8eaf0", frame=fi, kind="text")); self._fill_grid()

    def _frame_menu(self, fi: int) -> None:
        m = QMenu(self)
        m.addAction("Aggiungi testo…", lambda: self.add_text(fi))
        m.addAction("Titolo…", lambda: self._frame_title(fi))
        m.addAction("Nuova cornice", self.add_frame)
        m.exec(self.cursor().pos())

    def _frame_title(self, fi: int) -> None:
        t, ok = QInputDialog.getText(self, "Cornice", "Titolo:", text=self.page.frames[fi])
        if ok:
            self.page.frames[fi] = t; self._fill_grid()

    def add_frame(self) -> None:
        if self.page:
            self.page.frames.append(""); self._fill_grid()

    def button_menu(self, w, pos) -> None:
        b, p = w.btn, self.page
        m = QMenu(w)
        m.addAction("Proprietà…", lambda: self.open_popover(w))
        m.addSeparator()
        if isinstance(w, CueButton):
            m.addAction("Modalità: " + ("Toggle" if b.mode == "flash" else "Flash"),
                        lambda: setattr(b, "mode", "toggle" if b.mode == "flash" else "flash"))
        m.addAction("Diventa " + ("pulsante" if b.kind == "fader" else "fader"),
                    lambda: (setattr(b, "kind", "button" if b.kind == "fader" else "fader"), self._fill_grid()))
        m.addAction("Rimuovi dal gruppo esclusivo" if b.group else "Gruppo esclusivo (attached) con la cornice",
                    lambda: (setattr(b, "group", "" if b.group else f"f{b.frame}"), None))
        sub = m.addMenu("Sposta nella cornice")
        for i in range(len(p.frames)):
            sub.addAction(f"{i + 1}" + (f" — {p.frames[i]}" if p.frames[i] else ""),
                          lambda i=i: (setattr(b, "frame", i), self._fill_grid()))
        m.addAction("Duplica", lambda: (duplicate_button(self.engine.project, p, b), self._fill_grid()))
        m.addAction("Colore…", lambda: self._pick_color(b))
        m.addAction("Etichetta…", lambda: self._pick_label(b))
        m.addAction("Rimuovi dalla pagina", lambda: (p.buttons.remove(b), self._fill_grid()))
        m.exec(w.mapToGlobal(pos))

    def open_popover(self, w) -> None:
        cue = w.cue()
        if cue is None:
            return
        ButtonPopover(self, w.btn, cue).exec()
        self._fill_grid()

    def _pick_color(self, b) -> None:
        c = QColorDialog.getColor(QColor(b.color), self, "Colore")
        if c.isValid():
            b.color = c.name(); self._fill_grid()

    def _pick_label(self, b) -> None:
        t, ok = QInputDialog.getText(self, "Etichetta", "Testo:", text=b.label or b.cue)
        if ok:
            b.label = t; self._fill_grid()

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
        if self.cl_view:
            self.cl_view.sync()
        v = round(self.engine.grand_master * 100)
        if v != self.master.value() and not self.master.isSliderDown():
            self.master.blockSignals(True); self.master.setValue(v); self.master.blockSignals(False)
        for w in self.widgets:
            st = self.engine.live.active.get(w.btn.cue)
            w.restyle(bool(st and not st["releasing"]))
