import pytest

from showsuite.cue import audiomap


def stereo_map():
    audio_map = audiomap.new_map("Sala", 1000, 1000)
    audiomap.add_mark(audio_map, "Sinistra", 0, 500, {1: 0.0, 2: -200.0})
    audiomap.add_mark(audio_map, "Destra", 1000, 500, {1: -200.0, 2: 0.0})
    return audio_map


def test_oggetto_su_un_mark_prende_i_suoi_livelli():
    levels = audiomap.object_levels(stereo_map(), 0, 500)
    assert levels[1] == pytest.approx(0.0) and levels[2] <= -100


def test_oggetto_al_centro_bilancia_e_si_sposta():
    audio_map = stereo_map()
    centre = audiomap.object_levels(audio_map, 500, 500)
    assert centre[1] == pytest.approx(centre[2], abs=0.01)
    left = audiomap.object_levels(audio_map, 100, 500)
    right = audiomap.object_levels(audio_map, 900, 500)
    assert left[1] > left[2] and right[2] > right[1]


def test_gravity_sposta_il_bilanciamento():
    audio_map = stereo_map()
    audio_map["marks"][1]["gravity"] = 5.0
    levels = audiomap.object_levels(audio_map, 500, 500)
    assert levels[2] > levels[1]


def test_filtro_blocca_marks_oltre_la_linea_salvo_passthrough():
    audio_map = stereo_map()
    audiomap.add_filter(audio_map, "Muro", 400, 500, angle=90.0, width=0.0)
    blocked = audiomap.object_levels(audio_map, 200, 500)
    assert blocked[2] <= -100
    audio_map["filters"][0]["passthroughs"] = [2]
    passed = audiomap.object_levels(audio_map, 200, 500)
    assert passed[2] > -100


def test_shadow_nasconde_un_mark_dietro_a_un_altro():
    audio_map = audiomap.new_map("S")
    audiomap.add_mark(audio_map, "Davanti", 100, 0, {1: -200.0})
    audiomap.add_mark(audio_map, "Dietro", 300, 0, {1: 0.0})
    audiomap.add_mark(audio_map, "Lato", 0, 300, {1: -20.0})
    without = audiomap.object_levels(audio_map, 0, 0)[1]
    audio_map["marks"][0]["shadow"] = 90.0
    with_shadow = audiomap.object_levels(audio_map, 0, 0)[1]
    assert with_shadow < without


def test_spread_prende_il_punto_piu_forte_e_nomi_doppia_lettera():
    audio_map = stereo_map()
    point = audiomap.object_levels(audio_map, 300, 500, spread=0)
    spread = audiomap.object_levels(audio_map, 300, 500, spread=300)
    assert spread[1] >= point[1]
    assert [audiomap.double_letter_name(index) for index in (0, 1, 26, 27)] == ["A", "B", "AA", "BB"]
    assert audiomap.add_object(audio_map)["name"] == "A"
    assert audiomap.find_map([audio_map], "Sala") is audio_map
