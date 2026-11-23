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


def test_groups_select_by_type_save_and_prune(tmp_path):
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import generic_dimmer
    from showsuite.light.stage import make_group, select_by_profile
    e = LightEngine()
    for i in range(3):
        e.project.patch.add(FixtureInstance(f"P{i + 1}", generic_rgb(), 1, 1 + i * 3))
    e.project.patch.add(FixtureInstance("D1", generic_dimmer(), 1, 20))
    assert select_by_profile(e.project.patch, "P2") == ["P1", "P2", "P3"]
    g = make_group(e.project.groups, "Fronte", ["P2", "P1", "P2"]); assert g.fixtures == ["P2", "P1"]
    make_group(e.project.groups, "Fronte", ["P3"]); assert len(e.project.groups) == 1 and e.project.groups[0].fixtures == ["P3"]
    import pytest as _p
    with _p.raises(ValueError):
        make_group(e.project.groups, " ", ["P1"])
    f = tmp_path / "g.showsuite-light"; pj.save(e.project, str(f)); assert pj.load(str(f)).groups[0].name == "Fronte"
    e.remove_fixture("P3"); assert e.project.groups == []


def test_group_ui_flow():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.light_window import AddFixtureDialog, MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow(); d = AddFixtureDialog(w.engine, w); d.prof.setCurrentIndex(1); d.count.setValue(3); d.create()
    w._refresh_list(); w.preview.set_selection(["Fixture 1", "Fixture 3"])
    from showsuite.light.stage import make_group
    make_group(w.engine.project.groups, "Lati", w.preview.selection); w._refresh_groups()
    assert w.grouplist.count() == 1
    w.preview.set_selection([]); w.preview.select_group("Lati")
    assert w.preview.selection == ["Fixture 1", "Fixture 3"]


def test_curved_shape_and_handles():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from showsuite.light.engine import LightEngine
    from showsuite.ui.preview import PreviewWidget
    arc = StageShape("truss", 0.1, 0.8, 0.9, 0.8, bulge=-0.5)   # bulge negativo = arco verso l alto
    pts = arc.points(); assert pts[0] == (0.1, 0.8) and pts[-1] == pytest.approx((0.9, 0.8))
    mid = arc.points(2)[1]; assert mid[0] == pytest.approx(0.5) and mid[1] == pytest.approx(0.6)
    assert arc.distance(*mid) < 1e-9 and arc.distance(0.5, 0.8) == pytest.approx(0.2, abs=0.01)
    app = QApplication.instance() or QApplication([])
    e = LightEngine(); e.project.shapes.append(arc)
    w = PreviewWidget(e); w.resize(1000, 500); w.show(); w.set_edit_mode(True); w.sel_shape = arc
    # trascina la maniglia centrale verso il basso: la curva si appiattisce e poi si inverte
    m = w._handles(arc)[2]
    start = QPointF(m[0] * 1000, m[1] * 500).toPoint()
    QTest.mousePress(w, Qt.LeftButton, pos=start); QTest.mouseMove(w, QPointF(500, 400).toPoint())
    QTest.mouseRelease(w, Qt.LeftButton, pos=QPointF(500, 400).toPoint())
    assert abs(arc.bulge) < 0.01
    e1 = w._handles(arc)[0]; QTest.mousePress(w, Qt.LeftButton, pos=QPointF(e1[0] * 1000, e1[1] * 500).toPoint())
    QTest.mouseMove(w, QPointF(50, 300).toPoint()); QTest.mouseRelease(w, Qt.LeftButton, pos=QPointF(50, 300).toPoint())
    assert arc.x1 == pytest.approx(0.05) and arc.y1 == pytest.approx(0.6)
    w.grab()
