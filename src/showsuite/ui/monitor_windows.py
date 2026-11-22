"""External Control Log e DMX Monitor (come in Lightkey)."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QPushButton, QTabBar, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QHeaderView)

from ..light import properties as P
from ..light.control.log import ControlLog
from ..light.engine import LightEngine

COLORS = {"ok": "#34c759", "learn": "#3a8bff", "invalid": "#ff9f0a", "info": "#8b90a0"}
SOURCES = ("dmx", "midi", "osc")


class ControlLogWindow(QDialog):
    def __init__(self, log: ControlLog, parent=None):
        super().__init__(parent)
        self.log = log
        self.setWindowTitle("External Control Log"); self.resize(760, 360)
        self.tabs = QTabBar()
        for t in ("DMX-In", "MIDI", "OSC"):
            self.tabs.addTab(t)
        self.tabs.setCurrentIndex(1)
        self.tabs.currentChanged.connect(self.refresh)
        self.pause = QPushButton("Pausa"); self.pause.setCheckable(True)
        self.pause.toggled.connect(lambda on: setattr(log, "paused", on))
        clear = QPushButton("Svuota"); clear.clicked.connect(lambda: (log.clear(), self.refresh()))
        top = QHBoxLayout(); top.addStretch(); top.addWidget(self.tabs); top.addStretch()
        top.addWidget(self.pause); top.addWidget(clear)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time", "Endpoint", "Direction", "Message", "Comment"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().hide(); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.table)
        self._n = -1
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(300)
        self.refresh()

    def refresh(self, *_):
        rows = self.log.snapshot(SOURCES[self.tabs.currentIndex()])[-200:]
        key = (len(rows), rows[-1].time if rows else 0, self.tabs.currentIndex())
        if key == self._n:
            return
        self._n = key
        self.table.setRowCount(len(rows))
        for r, e in enumerate(reversed(rows)):
            t = time.strftime("%H:%M:%S", time.localtime(e.time)) + f".{int(e.time * 1000) % 1000:03d}"
            vals = [t, e.endpoint, "→ In" if e.direction == "in" else "← Out", e.message, e.comment]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 4:
                    it.setForeground(QColor(COLORS.get(e.status, "#d6d9e0")))
                self.table.setItem(r, c, it)


class DmxMonitor(QDialog):
    """Per i fixture indicati: canale, proprietà, valore in uscita (dopo master/blackout)."""

    def __init__(self, engine: LightEngine, names: list[str], parent=None):
        super().__init__(parent)
        self.engine, self.names = engine, names
        self.setWindowTitle("DMX Monitor"); self.resize(420, 480)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Channel", "Property", "Name", "Output"])
        self.table.verticalHeader().hide(); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        QVBoxLayout(self).addWidget(self.table)
        self.rows = self.layout_rows()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(100)
        self.refresh()

    def layout_rows(self) -> list[tuple[int, int, str, str]]:
        """[(universo, indirizzo DMX, proprietà, nome canale)]"""
        out = []
        for n in self.names:
            fx = self.engine.project.patch.find(n)
            kinds = {c.name: c.kind for c in fx.profile.channels}
            pos = 0
            for c in fx.profile.channels:
                prop = c.kind or "—"
                title = {"intensity": "Dimmer", "red": "Color", "green": "Color", "blue": "Color", "white": "Color",
                         "amber": "Color", "uv": "Color", "pan": "Position", "tilt": "Position"}.get(
                    c.kind, P.PROPERTY_TITLES.get(c.kind, "Other"))
                for k in range(c.width):
                    out.append((fx.universe, fx.address + pos, title, c.name + (" Fine" if k else "")))
                    pos += 1
        return out

    def refresh(self):
        self.table.setRowCount(len(self.rows))
        cache: dict[int, bytes] = {}
        for r, (u, a, prop, name) in enumerate(self.rows):
            data = cache.setdefault(u, self.engine.process(u, self.engine.render_output(u)) if not self.engine.freeze else self.engine.render_output(u))
            for c, v in enumerate([str(a), prop, name, str(data[a - 1])]):
                it = self.table.item(r, c) or QTableWidgetItem()
                it.setText(v); self.table.setItem(r, c, it)
