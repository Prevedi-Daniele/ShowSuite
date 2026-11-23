import os

import pytest

from showsuite.light import project as pj
from showsuite.light.undo import UndoStack


def test_stack_basic():
    u = UndoStack(b"a")
    assert not u.record(b"a") and u.record(b"b") and u.record(b"c")
    assert u.undo() == b"b" and u.undo() == b"a" and u.undo() is None
    assert u.redo() == b"b" and u.record(b"x") and not u.can_redo and u.states == [b"a", b"b", b"x"]
    s = UndoStack(b"0", limit=3)
    for i in range(1, 6):
        s.record(bytes([48 + i]))
    assert len(s.states) == 3 and s.undo() == b"4"


def test_dumps_loads_roundtrip():
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    p = pj.Project("Z"); p.patch.add(FixtureInstance("A", generic_rgb(), 1, 1)); p.background = b"img"
    q = pj.loads(pj.dumps(p)); assert q.name == "Z" and q.patch.find("A").address == 1 and q.background == b"img"
    assert pj.dumps(p) == pj.dumps(p)           # deterministico: serve al confronto fra istantanee


def test_window_undo_redo():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); w.snapshot()
    d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(3); d.create(); w._refresh_list()
    w.snapshot(); assert len(w.engine.project.patch.fixtures) == 3
    w.engine.project.shapes.append(__import__("showsuite.light.stage", fromlist=["StageShape"]).StageShape("text", .5, .5, text="A"))
    w.snapshot()
    w.undo(); assert w.engine.project.shapes == [] and len(w.engine.project.patch.fixtures) == 3
    w.undo(); assert w.engine.project.patch.fixtures == [] and w.fixlist.count() == 0
    w.undo(); assert w.engine.project.patch.fixtures == []                  # niente da annullare
    w.redo(); w.redo(); assert len(w.engine.project.shapes) == 1 and w.fixlist.count() == 3
    w.new(); assert not w.undo_stack.can_undo
    w.close()



def test_dumps_uses_fixed_timestamps():
    import io, zipfile
    z = zipfile.ZipFile(io.BytesIO(pj.dumps(pj.Project("T"))))
    assert {i.date_time for i in z.infolist()} == {(2020, 1, 1, 0, 0, 0)}
