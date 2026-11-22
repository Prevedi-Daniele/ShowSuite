"""Finestra Patch in stile Lightkey: libreria fixture a sinistra, griglia 512 canali per universo a destra."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QSpinBox, QTabBar, QTabWidget, QVBoxLayout, QWidget)

from ..light import project as pj
from ..light.engine import LightEngine
from ..light.fixtures import FixtureInstance, PatchError

COLS = 24


class UniverseGrid(QWidget):
    """512 celle; i fixture sono blocchi colorati (blu = dimmer/LED, viola = testa mobile)."""
    cell_clicked = Signal(int)          # indirizzo 1..512

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine, self.universe, self.selected = engine, 1, None
        self.setMinimumSize(COLS * 38, 22 * 28)
        self.setMouseTracking(True)

    def _cell(self, addr: int) -> QRectF:
        w = self.width() / COLS
        h = 28.0
        i = addr - 1
        return QRectF((i % COLS) * w, (i // COLS) * h, w, h)

    def addr_at(self, pos) -> int | None:
        w = self.width() / COLS
        a = int(pos.y() // 28) * COLS + int(pos.x() // w) + 1
        return a if 1 <= a <= 512 else None

    def fixture_at(self, addr: int):
        for f in self.engine.project.patch.fixtures:
            if f.universe == self.universe and f.address <= addr <= f.end_address:
                return f
        return None

    def mousePressEvent(self, e):
        a = self.addr_at(e.position())
        if a:
            self.cell_clicked.emit(a)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(20, 21, 25))
        f = QFont(self.font()); f.setPointSize(8); p.setFont(f)
        used = set()
        for fx in self.engine.project.patch.fixtures:
            if fx.universe != self.universe:
                continue
            col = QColor(170, 90, 220) if fx.profile.is_mover else QColor(70, 140, 255)
            fill = QColor(col); fill.setAlpha(150 if fx.name != self.selected else 235)
            for a in range(fx.address, fx.end_address + 1):
                used.add(a)
                r = self._cell(a).adjusted(1, 1, -1, -1)
                p.setPen(Qt.NoPen); p.setBrush(fill); p.drawRoundedRect(r, 3, 3)
            p.setPen(QColor(255, 255, 255))
            p.drawText(self._cell(fx.address).adjusted(5, 2, 0, 0), Qt.AlignLeft | Qt.AlignTop, f"{fx.address:03d}")
            p.drawText(self._cell(fx.address).adjusted(5, 13, 0, 0), Qt.AlignLeft | Qt.AlignTop, fx.name)
        p.setPen(QColor(120, 124, 135))
        for a in range(1, 513):
            if a not in used:
                p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(48, 50, 58)))
                p.drawRoundedRect(self._cell(a).adjusted(1, 1, -1, -1), 3, 3)
                p.setPen(QColor(120, 124, 135)); p.drawText(self._cell(a), Qt.AlignCenter, str(a))


class PatchPopover(QDialog):
    """Popover Kind / Patching: nuovo patch o modifica di un fixture esistente."""

    def __init__(self, win: "PatchWindow", addr: int, fixture: FixtureInstance | None, profile_key: str | None):
        super().__init__(win)
        self.win, self.fixture, self.addr = win, fixture, addr
        self.setWindowTitle("Patch"); self.setModal(True)
        prof = fixture.profile if fixture else win.engine.library[profile_key]
        self.profile_key = profile_key
        tabs = QTabWidget(); lay = QVBoxLayout(self); lay.addWidget(tabs)
        kind = QWidget(); kf = QFormLayout(kind)
        kf.addRow(QLabel(f"<b>{prof.manufacturer or 'Generic'}</b><br>{prof.model or prof.name if hasattr(prof, 'name') else prof.model}"))
        self.mode = QComboBox()
        self.modes = win.modes_of(prof)
        for k, pr in self.modes:
            self.mode.addItem(f"{pr.mode or 'Standard'} ({pr.footprint} ch)", k)
        cur = next((i for i, (k, pr) in enumerate(self.modes) if pr is prof or k == profile_key), 0)
        self.mode.setCurrentIndex(cur)
        kf.addRow("Mode", self.mode)
        tabs.addTab(kind, "Kind")
        pat = QWidget(); pf = QFormLayout(pat)
        self.name = QLineEdit(fixture.name if fixture else (prof.model or "Fixture"))
        self.addr_s = QSpinBox(); self.addr_s.setRange(1, 512); self.addr_s.setValue(fixture.address if fixture else addr)
        self.count = QSpinBox(); self.count.setRange(1, 128); self.count.setEnabled(fixture is None)
        pf.addRow("Short name", self.name); pf.addRow("Address", self.addr_s); pf.addRow("Count", self.count)
        tabs.addTab(pat, "Patching")
        tabs.setCurrentIndex(0 if fixture else 1)
        self.err = QLabel(""); self.err.setStyleSheet("color:#ff6b5b;"); lay.addWidget(self.err)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Patch" if fixture is None else "Done"); ok.setStyleSheet("background:#3a8bff;color:white;")
        ok.clicked.connect(self.apply)
        row.addWidget(cancel); row.addWidget(ok); lay.addLayout(row)

    def apply(self):
        try:
            self.win.commit(self)
        except PatchError as e:
            self.err.setText(str(e)); return
        self.accept()


class PatchWindow(QDialog):
    changed = Signal()

    def __init__(self, engine: LightEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle(f"Patch — {engine.project.name}"); self.resize(1250, 720)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search Fixture Library")
        self.makers = QListWidget(); self.models = QListWidget()
        left = QWidget(); lv = QVBoxLayout(left); lv.addWidget(self.search)
        row = QHBoxLayout(); row.addWidget(self.makers); row.addWidget(self.models, 1); lv.addLayout(row)
        self.tabs = QTabBar(); self.tabs.setExpanding(False)
        self.grid = UniverseGrid(engine)
        right = QWidget(); rv = QVBoxLayout(right); rv.addWidget(self.tabs); rv.addWidget(self.grid, 1)
        lay = QHBoxLayout(self); lay.addWidget(left, 2); lay.addWidget(right, 3)
        self.search.textChanged.connect(self._fill_models)
        self.makers.currentItemChanged.connect(lambda *_: self._fill_models())
        self.tabs.currentChanged.connect(self._universe)
        self.grid.cell_clicked.connect(self._clicked)
        self.reload()

    # --- libreria ---
    def _maker(self, prof) -> str:
        return prof.manufacturer or "Generic"

    def modes_of(self, prof) -> list[tuple[str, object]]:
        return [(k, p) for k, p in self.engine.library.items()
                if self._maker(p) == self._maker(prof) and p.model == prof.model] or \
               [(next((k for k, p in self.engine.library.items() if p is prof), ""), prof)]

    def reload(self):
        cur = self.makers.currentItem().text() if self.makers.currentItem() else "Generic"
        self.makers.blockSignals(True); self.makers.clear()
        for m in sorted({self._maker(p) for p in self.engine.library.values()}, key=lambda s: (s != "Generic", s.lower())):
            self.makers.addItem(m)
        for i in range(self.makers.count()):
            if self.makers.item(i).text() == cur:
                self.makers.setCurrentRow(i)
        if self.makers.currentRow() < 0:
            self.makers.setCurrentRow(0)
        self.makers.blockSignals(False)
        self._fill_models()
        used = sorted({f.universe for f in self.engine.project.patch.fixtures} | {1})
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for u in range(1, max(used) + 1):
            self.tabs.addTab(f"Universe {u}")
        self.tabs.blockSignals(False)
        self.tabs.setCurrentIndex(self.grid.universe - 1 if self.grid.universe <= self.tabs.count() else 0)
        self.grid.update()

    def _fill_models(self):
        self.models.clear()
        q = self.search.text().lower().strip()
        m = self.makers.currentItem().text() if self.makers.currentItem() else None
        seen = set()
        for k, p in self.engine.library.items():
            if (q and q not in k.lower()) or (not q and self._maker(p) != m):
                continue
            label = p.model or k
            if (self._maker(p), label) in seen:
                continue
            seen.add((self._maker(p), label))
            it = QListWidgetItem(label if not q else f"{self._maker(p)} {label}"); it.setData(Qt.UserRole, k)
            self.models.addItem(it)

    def _universe(self, i):
        self.grid.universe = i + 1; self.grid.update()

    # --- griglia ---
    def _clicked(self, addr: int):
        fx = self.grid.fixture_at(addr)
        self.grid.selected = fx.name if fx else None; self.grid.update()
        if fx:
            PatchPopover(self, addr, fx, None).exec()
        else:
            it = self.models.currentItem()
            if it:
                PatchPopover(self, addr, None, it.data(Qt.UserRole)).exec()

    def commit(self, pop: PatchPopover):
        patch = self.engine.project.patch
        key = pop.mode.currentData()
        prof = self.engine.library[key] if key in self.engine.library else (pop.fixture.profile if pop.fixture else None)
        u = self.grid.universe
        if pop.fixture is None:
            n, a = pop.count.value(), pop.addr_s.value()
            idx = len(patch.fixtures)
            for i in range(n):
                name = pop.name.text() if n == 1 else f"{pop.name.text()} {i + 1}"
                fx = FixtureInstance(name, prof, u, a, 0.1 + 0.8 * (((idx + i) % 8) / 7), 0.2 + 0.2 * ((idx + i) // 8 % 4))
                patch.add(fx); a += prof.footprint
        else:
            old = pop.fixture
            new = FixtureInstance(pop.name.text(), prof, old.universe, pop.addr_s.value(), old.x, old.y,
                                  old.rotation, old.beam_angle, old.hide_beam)
            patch.remove(old.name)
            try:
                patch.add(new)
            except PatchError:
                patch.add(old); raise
            if old.name != new.name or old.profile is not prof:
                self.engine.values.pop(old.name, None)
        self.reload(); self.changed.emit()
