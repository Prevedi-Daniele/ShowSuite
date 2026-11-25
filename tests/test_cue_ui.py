import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_GROUP, TYPE_NETWORK, TYPE_WAIT, Workspace


def make_window():
    from PySide6.QtWidgets import QApplication
    from showsuite.ui.cue_window import CueWindow
    QApplication.instance() or QApplication([])
    workspace = Workspace("Demo")
    runtime = Runtime(workspace, ManualClock())
    return CueWindow(workspace, runtime)


def test_aggiunta_cue_selezione_e_inspector():
    window = make_window()
    window.add_cue(TYPE_WAIT)
    window.add_cue(TYPE_NETWORK)
    assert len(window.workspace.active_list().children) == 2
    cue = window.workspace.active_list().children[1]
    assert window.selected_cues() == [cue]
    window.inspector.number.setText("5")
    window.inspector.number.editingFinished.emit()
    assert cue.number == "5"
    window.inspector.number.setText("1")
    window.inspector.number.editingFinished.emit()
    assert cue.number == "5"
    assert window.inspector.number_error.text() != ""
    window.inspector.pre_wait.setText("1:30")
    window.inspector.pre_wait.editingFinished.emit()
    assert cue.pre_wait == 90.0
    window.close()


def test_go_nella_ui_e_stato_riga():
    window = make_window()
    window.add_cue(TYPE_WAIT)
    window.add_cue(TYPE_WAIT)
    first, second = window.workspace.active_list().children
    first.duration = 5
    window.runtime.set_playhead(first)
    window.go_action.trigger()
    assert window.runtime.is_running(first) == True
    window.runtime.advance(1.0)
    window.paint_states()
    assert "0:01" in window.tree.topLevelItem(0).text(5)
    assert window.runtime.playhead() is second
    window.close()


def test_raggruppa_elimina_undo_show_mode():
    window = make_window()
    for _ in range(3):
        window.add_cue(TYPE_WAIT)
    cues = list(window.workspace.active_list().children)
    window.tree.clearSelection()
    window._items[cues[0].unique_id].setSelected(True)
    window._items[cues[1].unique_id].setSelected(True)
    window.group_selected()
    top = window.workspace.active_list().children
    assert top[0].cue_type == TYPE_GROUP and len(top[0].children) == 2
    window.undo()
    assert len(window.workspace.active_list().children) == 3
    window.set_show_mode(True)
    window.add_cue(TYPE_WAIT)
    assert len(window.workspace.active_list().children) == 3
    window.close()


def test_cart_e_screenshot(tmp_path):
    window = make_window()
    for kind in (TYPE_WAIT, TYPE_NETWORK, TYPE_GROUP):
        window.add_cue(kind)
    cues = list(window.workspace.active_list().children)
    cues[0].name = "Intro"
    cues[0].duration = 8
    cues[0].color = "green"
    cues[1].continue_mode = 1
    cues[1].pre_wait = 2.5
    cues[1].flagged = True
    cues[2].params["group_mode"] = 3
    window.workspace.new_cue(TYPE_WAIT, parent=cues[2], name="Sipario")
    window.refresh_tree()
    window.runtime.go()
    window.runtime.advance(2.0)
    window.paint_states()
    window.show()
    window.grab().save(str(tmp_path / "cue.png"))
    cart = window.workspace.new_list("Cart", cart=True)
    window.workspace.new_cue(TYPE_WAIT, parent=cart, name="Applauso")
    window.refresh_tabs()
    window.workspace.active_list_id = cart.unique_id
    window.refresh_tree()
    assert "Applauso" in window.cart_view.buttons[cart.children[0].unique_id].text()
    window.grab().save(str(tmp_path / "cart.png"))
    assert (tmp_path / "cue.png").stat().st_size > 1000
    import shutil
    shutil.copy(tmp_path / "cue.png", "/tmp/cue_shot.png")
    shutil.copy(tmp_path / "cart.png", "/tmp/cart_shot.png")
    window.close()
