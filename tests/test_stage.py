import os

import pytest

from showsuite.light import project as pj
from showsuite.light.fixtures import FixtureInstance, generic_rgb
from showsuite.light.stage import StageShape, align, distribute


def fxs(*pts):
    return [FixtureInstance(f"F{i}", generic_rgb(), 1, 1 + i * 3, x, y) for i, (x, y) in enumerate(pts)]


def test_align_and_distribute():
    f = fxs((0.1, 0.2), (0.4, 0.5), (0.9, 0.8))
    align(f, "left"); assert {x.x for x in f} == {0.1}
    align(f, "bottom"); assert {x.y for x in f} == {0.8}
    f = fxs((0.1, 0.2), (0.2, 0.5), (0.9, 0.8))
    distribute(f, "h"); assert [round(x.x, 3) for x in f] == [0.1, 0.5, 0.9]
    align(f, "hcenter"); assert {x.x for x in f} == {0.5}
    with pytest.raises(ValueError):
        align(f, "boh")


def test_shape_distance_and_save(tmp_path):
    t = StageShape("truss", 0.1, 0.1, 0.9, 0.1)
    assert t.distance(0.5, 0.1) == 0 and t.distance(0.5, 0.2) == pytest.approx(0.1) and t.distance(1.0, 0.1) == pytest.approx(0.1)
    p = pj.Project("S"); p.shapes = [t, StageShape("text", 0.5, 0.9, text="LED")]; p.background = b"\x89PNGfake"
    f = tmp_path / "s.showsuite-light"; pj.save(p, str(f)); q = pj.load(str(f))
    assert [s.kind for s in q.shapes] == ["truss", "text"] and q.shapes[1].text == "LED" and q.background == b"\x89PNGfake"
    p2 = pj.Project("N"); pj.save(p2, str(f)); assert pj.load(str(f)).background is None


def test_preview_draw_truss_and_delete():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from showsuite.light.engine import LightEngine
    from showsuite.ui.preview import PreviewWidget
    app = QApplication.instance() or QApplication([])
    e = LightEngine(); w = PreviewWidget(e); w.resize(800, 400); w.show()
    w.set_tool("truss")
    QTest.mousePress(w, Qt.LeftButton, pos=QPointF(100, 100).toPoint())
    QTest.mouseMove(w, QPointF(600, 100).toPoint()); QTest.mouseRelease(w, Qt.LeftButton, pos=QPointF(600, 100).toPoint())
    assert len(e.project.shapes) == 1 and e.project.shapes[0].kind == "truss"
    w.set_tool(None)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPointF(300, 100).toPoint())
    assert w.sel_shape is e.project.shapes[0]
    QTest.keyClick(w, Qt.Key_Delete); assert e.project.shapes == []
    w.grab()
