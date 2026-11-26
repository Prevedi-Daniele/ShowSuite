import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from showsuite.cue.model import TYPE_AUDIO, Workspace


def make_cue():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    workspace = Workspace("E")
    cue = workspace.new_cue(TYPE_AUDIO)
    cue.params["media_channels"] = 2
    return workspace, cue


def test_matrice_default_e_modifica_materializza_la_diagonale():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    editor = LevelsEditor(workspace)
    editor.load(cue)
    assert editor.crosspoint(0, 0) == 0.0 and editor.crosspoint(0, 1) <= -100
    editor.table.item(0, 1).setText("-6")
    assert cue.params["levels"]["1/2"] == -6.0
    assert cue.params["levels"]["1/1"] == 0.0 and cue.params["levels"]["2/2"] == 0.0
    editor.table.item(1, 1).setText("-inf")
    assert cue.params["levels"]["2/2"] <= -100
    editor.reset_matrix()
    assert [key for key in cue.params["levels"] if "/" in key] == []


def test_matrice_valore_non_valido_ripristina_la_cella():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    editor = LevelsEditor(workspace)
    editor.load(cue)
    editor.table.item(0, 0).setText("abc")
    assert editor.table.item(0, 0).text() == "0"
    assert "levels" not in cue.params or "1/1" not in cue.params["levels"]


def test_main_trim_e_numero_di_uscite_dalla_patch():
    from showsuite.ui.cue_editors import LevelsEditor
    workspace, cue = make_cue()
    workspace.patches["audio"] = [{"name": "A", "first_channel": 1, "channels": 4}]
    editor = LevelsEditor(workspace)
    editor.load(cue)
    assert editor.table.columnCount() == 4
    editor.main.setValue(-3.0)
    editor.trim.setValue(2.0)
    assert cue.params["levels"]["main"] == -3.0 and cue.params["trim"] == 2.0


def test_slice_editor_aggiunge_ordina_e_infinito():
    from showsuite.ui.cue_editors import SliceEditor
    workspace, cue = make_cue()
    cue.params["media_duration"] = 10.0
    editor = SliceEditor()
    editor.load(cue)
    editor.add_slice()
    editor.table.item(0, 0).setText("7")
    editor.add_slice()
    editor.table.item(1, 0).setText("3")
    editor.table.item(1, 1).setText("0")
    assert cue.params["slices"] == [{"time": 3.0, "play_count": "inf"}, {"time": 7.0, "play_count": 1}]
    editor.table.setCurrentCell(0, 0)
    editor.remove_selected()
    assert len(cue.params["slices"]) == 1
    editor.rate.setValue(2.0)
    editor.loop.setChecked(True)
    assert cue.params["rate"] == 2.0 and cue.params["infinite_loop"] == True


def test_envelope_editor_punti_ordinati_e_abilitazione():
    from showsuite.ui.cue_editors import EnvelopeEditor
    workspace, cue = make_cue()
    editor = EnvelopeEditor()
    editor.load(cue)
    editor.add_point()
    editor.add_point()
    editor.table.item(0, 0).setText("5")
    editor.table.item(0, 1).setText("-12")
    editor.enabled.setChecked(True)
    fade = cue.params["integrated_fade"]
    assert fade["enabled"] == True
    assert fade["points"] == [[2.0, 0.0], [5.0, -12.0]] or fade["points"] == [[1.0, 0.0], [5.0, -12.0]]
    editor.table.setCurrentCell(0, 0)
    editor.remove_selected()
    assert len(cue.params["integrated_fade"]["points"]) == 1


def test_inspector_mostra_le_schede_solo_per_cue_audio():
    from showsuite.ui.cue_window import Inspector
    workspace, cue = make_cue()
    inspector = Inspector(workspace)
    inspector.load(cue)
    titles = [inspector.tabs.tabText(index) for index in range(inspector.tabs.count())]
    assert titles[-4:] == ["Livelli", "Slice", "Envelope", "Oggetti"]
    other = workspace.new_cue("wait")
    inspector.load(other)
    assert inspector.tabs.count() == 3


def test_network_editor_scrive_i_parametri_e_abilita_il_fade():
    from showsuite.ui.cue_message_editors import NetworkEditor
    from showsuite.cue.model import TYPE_NETWORK
    workspace, cue = make_cue()
    network = workspace.new_cue(TYPE_NETWORK)
    editor = NetworkEditor()
    editor.load(network)
    assert editor.fade_from.isEnabled() == False
    editor.message.setText("/fader $1")
    editor.message.editingFinished.emit()
    editor.kind.setCurrentIndex(editor.kind.findData("udp"))
    editor.fade_type.setCurrentIndex(1)
    editor.fade_to.setValue(0.75)
    editor.curve.kind.setCurrentText("linear")
    assert network.params["message"] == "/fader $1" and network.params["message_kind"] == "udp"
    assert network.params["fade_type"] == 1 and network.params["fade_to"] == 0.75
    assert network.params["curve"]["type"] == "linear"
    assert editor.fade_from.isEnabled() == True


def test_midi_editor_mostra_i_campi_del_tipo_e_scrive():
    from showsuite.ui.cue_message_editors import MidiEditor
    from showsuite.cue.model import TYPE_MIDI
    workspace, cue = make_cue()
    midi = workspace.new_cue(TYPE_MIDI)
    editor = MidiEditor()
    editor.show()
    editor.load(midi)
    assert editor.visible_group() == "voice" and editor.channel.isVisible() == True and editor.raw.isVisible() == False
    editor.channel.setValue(5)
    editor.end_value.setText("100")
    editor.end_value.editingFinished.emit()
    assert midi.params["channel"] == 5 and midi.params["end_value"] == 100
    editor.message_type.setCurrentIndex(1)
    assert midi.params["message_type"] == 2 and editor.q_number.isVisible() == True and editor.channel.isVisible() == False
    editor.command.setCurrentIndex(editor.command.findData(6))
    assert midi.params["command"] == 6
    editor.message_type.setCurrentIndex(2)
    editor.raw.setText("F0 7F F7")
    editor.raw.editingFinished.emit()
    assert midi.params["raw_string"] == "F0 7F F7" and midi.params["message_type"] == 3


def test_fade_editor_livelli_e_parametri():
    from showsuite.ui.cue_message_editors import FadeEditor
    from showsuite.cue.model import TYPE_FADE
    workspace, cue = make_cue()
    fade = workspace.new_cue(TYPE_FADE)
    editor = FadeEditor()
    editor.load(fade)
    editor.add_level("main", -12.0)
    editor.add_level("1/2", -200.0)
    assert fade.params["levels"] == {"main": -12.0, "1/2": -200.0}
    editor.levels_mode.setCurrentIndex(1)
    editor.do_opacity.setChecked(True)
    editor.opacity.setValue(0.25)
    editor.stop_target.setChecked(True)
    assert fade.params["levels_mode"] == "relative" and fade.params["do_opacity"] == True
    assert fade.params["opacity"] == 0.25 and fade.params["stop_target_when_done"] == True


def test_inspector_schede_per_tipo():
    from showsuite.ui.cue_window import Inspector
    from showsuite.cue.model import TYPE_FADE, TYPE_MIDI, TYPE_NETWORK
    workspace, cue = make_cue()
    inspector = Inspector(workspace)
    for cue_type, title in ((TYPE_NETWORK, "Network"), (TYPE_MIDI, "MIDI"), (TYPE_FADE, "Fade")):
        inspector.load(workspace.new_cue(cue_type))
        assert inspector.tabs.tabText(inspector.tabs.count() - 1) == title


def test_objects_editor_mappa_e_oggetti():
    from showsuite.cue import audiomap
    from showsuite.cue.model import Workspace, TYPE_AUDIO
    from showsuite.ui.cue_editors import ObjectsEditor
    workspace = Workspace("O")
    audio_map = audiomap.new_map("Sala")
    workspace.patches["audio_map"] = [audio_map]
    cue = workspace.new_cue(TYPE_AUDIO)
    editor = ObjectsEditor(workspace)
    editor.load(cue)
    assert editor.map_box.count() == 2
    editor.map_box.setCurrentIndex(1)
    assert cue.params["audio_map"] == audio_map["unique_id"]
    editor.add_object()
    editor.table.item(0, 2).setText("A")
    editor.table.item(0, 3).setText("12,5")
    entry = cue.params["objects"][0]
    assert entry["map_object"] == "A" and entry["x"] == 12.5
    editor.table.item(0, 4).setText("abc")
    assert entry["y"] == 0.0 and editor.table.item(0, 4).text() == "0.0"
    editor.table.setCurrentCell(0, 0)
    editor.remove_object()
    assert cue.params["objects"] == []
    editor.load(cue)
    assert editor.map_box.currentData() == audio_map["unique_id"]
