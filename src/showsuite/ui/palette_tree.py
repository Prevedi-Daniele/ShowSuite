"""Preset Palette ad albero: cartelle (gruppi) > palette > preset, più gli effetti (cue). Trascinamento fra cartelle."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QInputDialog, QMenu, QMessageBox, QTreeWidget, QTreeWidgetItem

from ..light.preset import Palette, Preset

KIND, OBJ = Qt.UserRole + 1, Qt.UserRole
ALL = "Tutti i fixture"


def _dot(preset: Preset) -> QIcon | None:
    v = {k.lower(): x for k, x in preset.values.items()}
    r, g, b = (next((x for k, x in v.items() if k.startswith(c)), None) for c in ("red", "green", "blue"))
    if r is None and g is None and b is None:
        return None
    pm = QPixmap(12, 12); pm.fill(QColor(r or 0, g or 0, b or 0))
    return QIcon(pm)


class PaletteTree(QTreeWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.filter = ""
        self.itemDoubleClicked.connect(self.activate)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    # --- contenuto
    def refresh(self) -> None:
        pr = self.win.engine.project
        self.clear()
        q = self.filter.lower()
        folders: dict[str, QTreeWidgetItem] = {}

        def folder(name: str) -> QTreeWidgetItem:
            if name not in folders:
                it = QTreeWidgetItem([name]); it.setData(0, KIND, "folder"); it.setData(0, OBJ, name)
                it.setFlags(it.flags() & ~Qt.ItemIsDragEnabled)
                folders[name] = it; self.addTopLevelItem(it)
            return folders[name]
        for g in pr.groups:
            folder(g.name)
        for pal in pr.palettes:
            top = folder(pal.group or ALL)
            pit = QTreeWidgetItem([pal.name]); pit.setData(0, KIND, "palette"); pit.setData(0, OBJ, pal)
            pit.setFlags(pit.flags() & ~Qt.ItemIsDropEnabled)
            for p in pal.presets:
                if q and q not in p.name.lower() and q not in pal.name.lower():
                    continue
                it = QTreeWidgetItem([p.name]); it.setData(0, KIND, "preset"); it.setData(0, OBJ, p)
                it.setFlags(it.flags() & ~(Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled))
                ic = _dot(p)
                if ic:
                    it.setIcon(0, ic)
                pit.addChild(it)
            if pit.childCount() or not q:
                top.addChild(pit)
        if pr.cues:
            fx = folder("Effetti")
            for c in pr.cues:
                if q and q not in c.name.lower():
                    continue
                it = QTreeWidgetItem(["▶ " + c.name]); it.setData(0, KIND, "cue"); it.setData(0, OBJ, c)
                it.setFlags(it.flags() & ~(Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)); fx.addChild(it)
        self.expandAll()

    def set_filter(self, text: str) -> None:
        self.filter = text.strip(); self.refresh()

    # --- azioni
    def targets(self, palette: Palette | None) -> list[str]:
        if palette is not None and palette.group:
            g = next((g for g in self.win.engine.project.groups if g.name == palette.group), None)
            if g:
                return list(g.fixtures)
        return self.win.selected_names()

    def activate(self, item, _col=0) -> None:
        kind, obj = item.data(0, KIND), item.data(0, OBJ)
        if kind == "cue":
            self.win.engine.live.trigger(obj)
        elif kind == "preset":
            pal = item.parent().data(0, OBJ)
            names = self.targets(pal)
            for n in names:
                for ch, v in obj.values.items():
                    try:
                        self.win.engine.set_value(n, ch, v)
                    except KeyError:
                        pass
            self.win.design.refresh_dots()

    def add_from_programmer(self) -> None:
        eng = self.win.engine; names = self.win.selected_names()
        vals: dict[str, int] = {}
        for n in names:
            for ch, v in eng.values.get(n, {}).items():
                vals.setdefault(ch, v)
        if not vals:
            QMessageBox.information(self, "Preset", "Imposta dei valori sui fixture selezionati (Design view) prima di salvare un preset.")
            return
        pals = [p.name for p in eng.project.palettes]
        pname, ok = QInputDialog.getItem(self, "Preset", "Palette:", pals + ["Nuova palette…"], 0, True)
        if not ok or not pname.strip():
            return
        if pname == "Nuova palette…":
            pname, ok = QInputDialog.getText(self, "Palette", "Nome della palette:")
            if not ok or not pname.strip():
                return
        name, ok = QInputDialog.getText(self, "Preset", "Nome del preset:")
        if not ok or not name.strip():
            return
        pal = next((p for p in eng.project.palettes if p.name == pname), None)
        if pal is None:
            pal = Palette(pname.strip()); eng.project.palettes.append(pal)
        pal.presets = [p for p in pal.presets if p.name != name.strip()] + [Preset(name.strip(), vals)]
        self.refresh()

    def _menu(self, pos) -> None:
        it = self.itemAt(pos)
        if not it:
            return
        kind, obj = it.data(0, KIND), it.data(0, OBJ)
        m = QMenu(self)
        if kind == "preset":
            pal = it.parent().data(0, OBJ)
            m.addAction("Elimina preset", lambda: (pal.presets.remove(obj), self.refresh()))
        elif kind == "palette":
            m.addAction("Elimina palette", lambda: (self.win.engine.project.palettes.remove(obj), self.refresh()))
        if not m.isEmpty():
            m.exec(self.mapToGlobal(pos))

    # --- trascinamento: una palette può essere spostata su un'altra cartella (gruppo)
    def dropEvent(self, e) -> None:
        src = self.currentItem()
        dst = self.itemAt(e.position().toPoint())
        if src is None or dst is None or src.data(0, KIND) != "palette":
            return e.ignore()
        while dst is not None and dst.data(0, KIND) != "folder":
            dst = dst.parent()
        if dst is None or dst.data(0, OBJ) == "Effetti":
            return e.ignore()
        name = dst.data(0, OBJ)
        src.data(0, OBJ).group = "" if name == ALL else name
        e.accept(); self.refresh()
