import pytest

from showsuite.cue.model import (CONTINUE_AUTO_FOLLOW, DuplicateNumberError, InvalidNumberError, TYPE_AUDIO,
                                 TYPE_CART, TYPE_FADE, TYPE_GROUP, TYPE_MEMO, TYPE_START, TYPE_WAIT, Workspace, Cue)
from showsuite.cue.timeutil import format_db, format_time, parse_db, parse_time


def test_numeri_unici_e_caratteri_vietati():
    workspace = Workspace()
    first = workspace.new_cue(TYPE_MEMO)
    second = workspace.new_cue(TYPE_MEMO)
    assert first.number == "1"
    assert second.number == "2"
    with pytest.raises(DuplicateNumberError):
        workspace.set_number(second, "1")
    with pytest.raises(InvalidNumberError):
        workspace.set_number(second, "a b")
    workspace.set_number(second, "1.0")
    assert second.number == "1.0"


def test_auto_numero_tra_vicini():
    workspace = Workspace()
    parent = workspace.active_list()
    for number in ("2", "4", "6"):
        workspace.new_cue(TYPE_MEMO, number=number)
    assert workspace.new_cue(TYPE_MEMO).number == "7"
    inserted = workspace.new_cue(TYPE_MEMO, index=1)
    assert inserted.number == "3"
    between = workspace.new_cue(TYPE_MEMO, index=2)
    assert between.number == "3.5"
    assert len(parent.children) == 6


def test_renumber_salta_esistenti_e_delete_numbers():
    workspace = Workspace()
    cues = [workspace.new_cue(TYPE_MEMO, number=str(value * 10)) for value in range(1, 4)]
    workspace.renumber(cues, 1, 1, prefix="Q")
    assert [cue.number for cue in cues] == ["Q1", "Q2", "Q3"]
    workspace.delete_numbers(cues)
    assert [cue.number for cue in cues] == ["", "", ""]


def test_cart_non_contiene_group_e_dimensione():
    workspace = Workspace()
    cart = workspace.new_list("Cart", cart=True)
    assert cart.cue_type == TYPE_CART
    with pytest.raises(ValueError):
        workspace.new_cue(TYPE_GROUP, parent=cart)
    cue = workspace.new_cue(TYPE_MEMO, parent=cart)
    assert (cue.cart_row, cue.cart_column) == (1, 1)
    cue.cart_row = 4
    with pytest.raises(ValueError):
        workspace.set_cart_size(cart, 2, 2)


def test_make_group_e_spostamento():
    workspace = Workspace()
    first = workspace.new_cue(TYPE_MEMO)
    second = workspace.new_cue(TYPE_MEMO)
    group = workspace.make_group([first, second])
    assert group.children == [first, second]
    assert first.parent is group
    with pytest.raises(ValueError):
        workspace.move_cue(group, first)


def test_salvataggio_e_caricamento(tmp_path):
    workspace = Workspace("Prova")
    group = workspace.new_cue(TYPE_GROUP)
    workspace.new_cue(TYPE_WAIT, parent=group)
    fade = workspace.new_cue(TYPE_FADE)
    fade.target_id = group.unique_id
    path = str(tmp_path / "prova.showcue")
    workspace.save(path)
    loaded = Workspace.load(path)
    assert loaded.name == "Prova"
    assert loaded.workspace_id == workspace.workspace_id
    assert len(loaded.active_list().children) == 2
    assert loaded.find_by_id(fade.unique_id).target_id == group.unique_id
    assert loaded.modified == False


def test_undo_redo():
    workspace = Workspace()
    workspace.push_undo()
    workspace.new_cue(TYPE_MEMO)
    assert len(workspace.active_list().children) == 1
    assert workspace.undo() == True
    assert len(workspace.active_list().children) == 0
    assert workspace.redo() == True
    assert len(workspace.active_list().children) == 1


def test_nome_predefinito_segue_il_target():
    workspace = Workspace()
    target = workspace.new_cue(TYPE_WAIT, name="Buio")
    start = workspace.new_cue(TYPE_START)
    start.target_id = target.unique_id
    assert start.display_name(workspace) == "start Buio"
    start.name = "Mio"
    assert start.display_name(workspace) == "Mio"
    start.name = ""
    assert start.display_name(workspace) == "start Buio"


def test_duplicato_ha_nuovi_id():
    workspace = Workspace()
    cue = workspace.new_cue(TYPE_WAIT)
    copy_cue = workspace.duplicate_cue(cue)
    assert copy_cue.unique_id != cue.unique_id
    assert copy_cue.number == ""


def test_tempi_e_db():
    assert parse_time("1:30") == 90.0
    assert parse_time("1:01:01.5") == 3661.5
    assert parse_time("2,5") == 2.5
    assert format_time(65.5) == "1:05.50"
    assert parse_db("6") == -6.0
    assert parse_db("+6") == 6.0
    assert parse_db("") == float("-inf")
    assert format_db(float("-inf")) == "-INF"
