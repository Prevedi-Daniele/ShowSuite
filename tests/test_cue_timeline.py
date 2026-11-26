import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.model import GROUP_TIMELINE, TYPE_AUDIO, TYPE_WAIT, Workspace


def make_timeline():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    workspace = Workspace("T")
    first = workspace.new_cue(TYPE_WAIT, name="Luce")
    first.duration = 4.0
    second = workspace.new_cue(TYPE_AUDIO, name="Musica")
    second.params.update({"media_duration": 10.0, "rate": 2.0})
    second.pre_wait = 2.0
    group = workspace.make_group([first, second], GROUP_TIMELINE)
    return workspace, group, first, second


def test_lunghezza_figli_e_layout():
    from showsuite.ui.cue_timeline import LABEL_WIDTH, TimelineEditor, child_length
    workspace, group, first, second = make_timeline()
    assert child_length(first) == 4.0 and child_length(second) == 5.0
    editor = TimelineEditor()
    editor.load(group)
    layout = editor.layout()
    assert len(layout) == 2
    assert layout[1][1].left() == LABEL_WIDTH + 2.0 * editor.pixels_per_second
    assert layout[1][1].width() == 5.0 * editor.pixels_per_second
    assert editor.total_length() == 9.0


def test_spostare_una_barra_cambia_il_pre_wait_con_snap():
    from showsuite.ui.cue_timeline import TimelineEditor
    workspace, group, first, second = make_timeline()
    editor = TimelineEditor()
    editor.load(group)
    seen = []
    editor.changed.connect(lambda: seen.append(1))
    editor.move_child(first, 3.04)
    assert first.pre_wait == pytest.approx(3.0)
    editor.move_child(first, -5.0)
    assert first.pre_wait == 0.0
    assert len(seen) == 2


def test_trascinamento_con_il_mouse():
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from showsuite.ui.cue_timeline import TimelineEditor
    workspace, group, first, second = make_timeline()
    editor = TimelineEditor()
    editor.load(group)
    rect = editor.child_rect(1)
    start = QPointF(rect.left() + 5, rect.center().y())
    editor.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, start, start, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    end = QPointF(start.x() + 80, start.y())
    editor.mouseMoveEvent(QMouseEvent(QEvent.MouseMove, end, end, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    editor.mouseReleaseEvent(QMouseEvent(QEvent.MouseButtonRelease, end, end, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    assert second.pre_wait == pytest.approx(4.0)
    assert editor.drag_child is None


def test_inspector_mostra_la_scheda_timeline_solo_per_gruppi_timeline():
    from showsuite.ui.cue_window import Inspector
    workspace, group, first, second = make_timeline()
    inspector = Inspector(workspace)
    inspector.load(group)
    assert inspector.tabs.tabText(inspector.tabs.count() - 1) == "Timeline"
    inspector.load(first)
    assert "Timeline" not in [inspector.tabs.tabText(index) for index in range(inspector.tabs.count())]


def test_playhead_segue_il_tempo_reale_del_gruppo():
    from showsuite.cue.engine import ManualClock, Runtime
    from showsuite.cue.model import GROUP_TIMELINE, TYPE_GROUP, TYPE_NETWORK, Workspace
    from showsuite.ui.cue_timeline import TimelineEditor
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    workspace = Workspace("S")
    group = workspace.new_cue(TYPE_GROUP)
    group.params["mode"] = GROUP_TIMELINE
    child = workspace.new_cue(TYPE_NETWORK, parent=group)
    child.duration = 5.0
    clock = ManualClock()
    runtime = Runtime(workspace, clock)
    editor = TimelineEditor()
    editor.load(group)
    editor.refresh_playhead(runtime)
    assert editor.playhead is None
    runtime.start_cue(group)
    clock.advance(2.0)
    runtime.update()
    editor.refresh_playhead(runtime)
    assert editor.playhead is not None
    assert abs(editor.playhead - 2.0) < 0.2
