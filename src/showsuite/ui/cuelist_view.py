"""Cuelist in stile Lightkey: tabella Nome/Hold/Fade con casella skip e pulsanti Go / Stop / Indietro."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QLineEdit, QDoubleSpinBox, QHBoxLayout, QHeaderView, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..light.engine import LightEngine
from ..light.live import CueList, CueListStep, LivePage

MANUAL = -1.0   # valore dello spinbox che significa "manuale" (hold None)


def fmt(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:04.1f}"


class CueListView(QWidget):
    changed = Signal()

    def __init__(self, engine: LightEngine, page: LivePage):
        super().__init__()
        self.engine, self.page = engine, page
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "Name", "Hold Time", "Fade Time"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch); h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().hide(); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemChanged.connect(self._toggle_skip)
        self.table.cellDoubleClicked.connect(self._edit_cell)
        self.go_btn = QPushButton("▶ Go"); self.go_btn.clicked.connect(self.go)
        self.back_btn = QPushButton("« Indietro"); self.back_btn.clicked.connect(self.back)
        self.stop_btn = QPushButton("■ Stop"); self.stop_btn.clicked.connect(self.stop)
        self.add_btn = QPushButton("+ Step"); self.add_btn.clicked.connect(self.add_step)
        self.rm_btn = QPushButton("− Step"); self.rm_btn.clicked.connect(self.remove_step)
        self.loop_btn = QPushButton("Loop"); self.loop_btn.setCheckable(True)
        self.loop_btn.toggled.connect(lambda on: setattr(self.cl, "loop", on))
        self.up_btn = QPushButton("↑"); self.up_btn.clicked.connect(lambda: self.move(-1))
        self.down_btn = QPushButton("↓"); self.down_btn.clicked.connect(lambda: self.move(1))
        self.dup_btn = QPushButton("Duplica"); self.dup_btn.clicked.connect(self.duplicate_step)
        self.grp_btn = QPushButton("Gruppo…"); self.grp_btn.setToolTip("Cue group: avvia più cue insieme in questo step")
        self.grp_btn.clicked.connect(self.edit_group)
        self.filter = QLineEdit(); self.filter.setPlaceholderText("Filtra…"); self.filter.textChanged.connect(self.apply_filter)
        side = QVBoxLayout()
        for b in (self.go_btn, self.back_btn, self.stop_btn, self.loop_btn, self.add_btn, self.rm_btn,
                  self.up_btn, self.down_btn, self.dup_btn, self.grp_btn):
            side.addWidget(b)
        side.addStretch()
        left = QVBoxLayout(); left.addWidget(self.filter); left.addWidget(self.table, 1)
        lay = QHBoxLayout(self); lay.addLayout(left, 1); lay.addLayout(side)
        self.refresh()

    @property
    def cl(self) -> CueList:
        return self.page.cuelist

    def refresh(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.cl.steps))
        for i, st in enumerate(self.cl.steps):
            chk = QTableWidgetItem(); chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked if st.skip else Qt.Checked)
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(f"{i + 1:03d} {st.cue}" + (f" + {', '.join(st.also)}" if st.also else "")))
            self.table.setItem(i, 2, QTableWidgetItem("—" if st.hold is None else fmt(st.hold)))
            self.table.setItem(i, 3, QTableWidgetItem(fmt(st.fade)))
        self.table.blockSignals(False)
        self.loop_btn.blockSignals(True); self.loop_btn.setChecked(self.cl.loop); self.loop_btn.blockSignals(False)
        self.sync()

    def apply_filter(self, text: str = "") -> None:
        q = text.strip().lower()
        for r, st in enumerate(self.cl.steps):
            self.table.setRowHidden(r, bool(q) and q not in " ".join([st.cue, *st.also]).lower())

    def move(self, d: int) -> None:
        r = self.table.currentRow(); n = r + d
        if 0 <= r < len(self.cl.steps) and 0 <= n < len(self.cl.steps):
            steps = self.cl.steps; steps[r], steps[n] = steps[n], steps[r]
            self.refresh(); self.table.selectRow(n); self.changed.emit()

    def duplicate_step(self) -> None:
        import copy
        r = self.table.currentRow()
        if 0 <= r < len(self.cl.steps):
            self.cl.steps.insert(r + 1, copy.deepcopy(self.cl.steps[r])); self.refresh(); self.changed.emit()

    def edit_group(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem
        r = self.table.currentRow()
        if not 0 <= r < len(self.cl.steps):
            return
        st = self.cl.steps[r]
        d = QDialog(self); d.setWindowTitle(f"Cue group — step {r + 1}"); v = QVBoxLayout(d)
        lst = QListWidget(); v.addWidget(lst)
        for c in self.engine.project.cues:
            if c.name == st.cue:
                continue
            it = QListWidgetItem(c.name); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if c.name in st.also else Qt.Unchecked); lst.addItem(it)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); v.addWidget(bb)
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        if d.exec():
            st.also = [lst.item(i).text() for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]
            self.refresh(); self.changed.emit()

    def sync(self) -> None:
        cur = self.engine.live.current_step(self.cl)
        for r in range(self.table.rowCount()):
            for c in range(1, 4):
                it = self.table.item(r, c)
                if it:
                    it.setBackground(Qt.darkBlue if cur == r + 1 else Qt.transparent)

    # --- azioni
    def go(self) -> None:
        self.engine.live.go(self.cl, self.page.priority); self.sync()

    def back(self) -> None:
        cur = self.engine.live.current_step(self.cl) or 1
        n = len(self.cl.steps)
        if n:
            self.engine.live.goto(self.cl, ((cur - 2) % n) + 1, self.page.priority)
        self.sync()

    def stop(self) -> None:
        self.engine.live.stop_cuelist(self.cl); self.sync()

    def add_step(self, cue: str | None = None) -> None:
        name = cue if isinstance(cue, str) else None
        if name is None:
            sel = [c.name for c in self.engine.project.cues]
            if not sel:
                return
            name = sel[len(self.cl.steps) % len(sel)]
        self.cl.steps.append(CueListStep(name)); self.refresh(); self.changed.emit()

    def remove_step(self) -> None:
        r = self.table.currentRow()
        if 0 <= r < len(self.cl.steps):
            del self.cl.steps[r]; self.refresh(); self.changed.emit()

    def _toggle_skip(self, item) -> None:
        if item.column() == 0 and item.row() < len(self.cl.steps):
            self.cl.steps[item.row()].skip = item.checkState() != Qt.Checked
            self.changed.emit()

    def _edit_cell(self, row: int, col: int) -> None:
        from PySide6.QtWidgets import QInputDialog
        st = self.cl.steps[row]
        if col == 1:
            names = [c.name for c in self.engine.project.cues]
            n, ok = QInputDialog.getItem(self, "Cue", "Cue dello step:", names, max(0, names.index(st.cue)) if st.cue in names else 0, False)
            if ok:
                st.cue = n
        elif col in (2, 3):
            cur = st.fade if col == 3 else (st.hold if st.hold is not None else MANUAL)
            v, ok = QInputDialog.getDouble(self, "Tempo", "Secondi" + (" (-1 = manuale)" if col == 2 else ""),
                                           cur, MANUAL if col == 2 else 0, 3600, 1)
            if ok:
                if col == 3:
                    st.fade = v
                else:
                    st.hold = None if v < 0 else v
        self.refresh(); self.changed.emit()
