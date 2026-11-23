"""Design view in stile Lightkey: una fila di pannelli proprietà con punto blu/grigio."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSlider, QVBoxLayout, QWidget)

from ..light import properties as P
from ..light.engine import LightEngine

SWATCHES = ["#ff0000", "#ff8000", "#ffd000", "#80ff00", "#00ff00", "#00ff90", "#00ffff", "#0080ff",
            "#0000ff", "#8000ff", "#ff00ff", "#ff0080", "#ffffff", "#ffd8a8", "#a8d0ff", "#000000"]
DOT = {"none": "#6b6f7b", "some": "#7fb2ff", "all": "#3a8bff"}


class Dot(QPushButton):
    """Punto di stato: blu = valore impostato (override), grigio = valore del cue. Click = rimuove."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(14, 14)
        self.state("none")

    def state(self, s: str) -> None:
        self.setStyleSheet(f"QPushButton{{background:{DOT[s]};border:none;border-radius:7px;"
                           f"min-height:0;padding:0;}}")
        self.setToolTip({"none": "Valori dal cue", "some": "Alcuni fixture sovrascritti",
                         "all": "Sovrascritto: clic per rimuovere"}[s])


class Panel(QFrame):
    def __init__(self, view: "DesignView", prop: str):
        super().__init__()
        self.view, self.prop = view, prop
        self.setObjectName("panel")
        self.setStyleSheet("#panel{background:#1f2127;border:1px solid #33363f;border-radius:8px;}")
        self.lay = QVBoxLayout(self)
        head = QHBoxLayout()
        self.dot = Dot(); self.dot.clicked.connect(self._clear)
        head.addWidget(self.dot)
        head.addWidget(QLabel(f"<b>{P.PROPERTY_TITLES[prop]}</b>"))
        head.addStretch()
        k = QLabel(P.SHORTCUTS[prop]); k.setStyleSheet("color:#8b90a0;")
        head.addWidget(k)
        self.lay.addLayout(head)
        self.body = QVBoxLayout(); self.lay.addLayout(self.body)
        self.lay.addStretch()
        self.build()

    @property
    def engine(self) -> LightEngine:
        return self.view.engine

    @property
    def names(self) -> list[str]:
        return self.view.names

    def _clear(self):
        P.clear_property(self.engine, self.names, self.prop)
        self.view.refresh_dots()

    def touched(self):
        self.dot.state(P.property_state(self.engine, self.names, self.prop))

    def build(self) -> None:
        p = self.prop
        if p == "dimmer":
            s = QSlider(Qt.Vertical); s.setRange(0, 100); s.setMinimumHeight(110)
            s.valueChanged.connect(lambda v: (P.set_dimmer(self.engine, self.names, round(v * 2.55)), self.touched()))
            full = QPushButton("Full"); full.clicked.connect(lambda: s.setValue(100))
            self.body.addWidget(s, 1, Qt.AlignHCenter); self.body.addWidget(full)
            self.slider = s
        elif p == "color":
            g = QGridLayout(); self.body.addLayout(g)
            for i, c in enumerate(SWATCHES):
                b = QPushButton(); b.setFixedSize(26, 26)
                b.setStyleSheet(f"background:{c};border:1px solid #33363f;border-radius:4px;min-height:0;padding:0;")
                b.clicked.connect(lambda _=0, c=c: self._rgb(QColor(c)))
                g.addWidget(b, i // 4, i % 4)
            more = QPushButton("Altro…"); more.clicked.connect(
                lambda: (lambda col: col.isValid() and self._rgb(col))(QColorDialog.getColor(parent=self)))
            self.body.addWidget(more)
        elif p in ("color_wheel", "gobo_wheel", "custom"):
            self.slots = QVBoxLayout(); self.body.addLayout(self.slots)
        elif p == "shutter":
            row = QHBoxLayout()
            for label, st in (("Open", "open"), ("Closed", "closed")):
                b = QPushButton(label); b.clicked.connect(lambda _=0, st=st: self._shut(st)); row.addWidget(b)
            self.body.addLayout(row)
            sp = QSlider(Qt.Horizontal); sp.setRange(0, 100); sp.setValue(50)
            sp.valueChanged.connect(lambda v: self._shut("strobe", v / 100))
            self.body.addWidget(QLabel("Strobe (velocità)")); self.body.addWidget(sp)
        elif p == "position":
            from .position_pad import PositionPad
            fx = self.engine.project.patch.find(self.names[0]) if self.names else None
            self.pad = PositionPad(lambda pan, tilt: (P.set_position(self.engine, self.names, pan, tilt), self.touched()),
                                   fx.pan_range if fx else 540.0, fx.tilt_range if fx else 270.0)
            self.body.addWidget(self.pad)
        else:   # zoom, focus, iris, prism, frost
            s = QSlider(Qt.Horizontal); s.setRange(0, 1000)
            s.valueChanged.connect(lambda v: (P.set_simple(self.engine, self.names, p, v / 1000), self.touched()))
            self.body.addWidget(s)

    def _rgb(self, c: QColor):
        P.set_color(self.engine, self.names, (c.red(), c.green(), c.blue())); self.touched()

    def _shut(self, st, speed=0.5):
        P.set_shutter(self.engine, self.names, st, speed); self.touched()

    def fill_slots(self, profile) -> None:
        if self.prop not in ("color_wheel", "gobo_wheel", "custom"):
            return
        while self.slots.count():
            w = self.slots.takeAt(0).widget()
            if w:
                w.setParent(None)
        if self.prop == "custom":
            for name in P.property_channels(profile, "custom"):
                lab = QLabel(name); sl = QSlider(Qt.Horizontal); sl.setRange(0, 1000)
                sl.valueChanged.connect(lambda v, name=name: (P.set_channel(self.engine, self.names, name, v / 1000), self.touched()))
                self.slots.addWidget(lab); self.slots.addWidget(sl)
            return
        for i, (_v, label) in enumerate(P.wheel_slots(profile, self.prop)):
            b = QPushButton(label)
            b.clicked.connect(lambda _=0, i=i: (P.set_slot(self.engine, self.names, self.prop, i), self.touched()))
            self.slots.addWidget(b)


class DesignView(QWidget):
    """Mostra solo i pannelli disponibili per la selezione (unione dei profili)."""

    def __init__(self, engine: LightEngine, extra: QWidget | None = None):
        super().__init__()
        self.engine = engine
        self.names: list[str] = []
        self.panels: dict[str, Panel] = {p: Panel(self, p) for p in P.PROPERTY_ORDER}
        self.empty = QLabel("Seleziona uno o più fixture nel Preview")
        self.empty.setAlignment(Qt.AlignCenter)
        row = QHBoxLayout(); row.setContentsMargins(8, 8, 8, 8)
        row.addWidget(self.empty)
        for p in self.panels.values():
            row.addWidget(p); p.hide()
        if extra is not None:
            row.addWidget(extra)
        row.addStretch()
        host = QWidget(); host.setLayout(row)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
        sc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(sc)

    def set_selection(self, names: list[str]) -> None:
        self.names = list(names)
        avail: set[str] = set(); profs = {}
        for n in names:
            prof = self.engine.project.patch.find(n).profile
            for a in P.available_properties(prof):
                avail.add(a); profs.setdefault(a, prof)
        self.empty.setVisible(not names)
        for k, p in self.panels.items():
            p.setVisible(k in avail)
            if k in avail:
                p.fill_slots(profs[k])
            if k == "position" and k in avail and hasattr(p, "pad"):
                fx = self.engine.project.patch.find(names[0]); p.pad.set_ranges(fx.pan_range, fx.tilt_range)
        self.refresh_dots()

    def refresh_dots(self) -> None:
        for p in self.panels.values():
            if p.isVisibleTo(self):
                p.touched()

    def key(self, letter: str) -> None:
        """Scorciatoia da tastiera: evidenzia il pannello (D C G P S M F Z I R)."""
        for k, p in self.panels.items():
            if P.SHORTCUTS[k] == letter.upper() and p.isVisibleTo(self):
                p.setFocus(); return
