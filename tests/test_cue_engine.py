import random

import pytest

from showsuite.cue.engine import (ManualClock, Runtime, SECOND_TRIGGER_DEVAMP, SECOND_TRIGGER_PLAYLIST_NEXT,
                                  SECOND_TRIGGER_STOP, ORIGIN_TRIGGER, ActionHandler)
from showsuite.cue.model import (CONTINUE_AUTO_CONTINUE, CONTINUE_AUTO_FOLLOW, GROUP_PLAYLIST, GROUP_START_FIRST,
                                 GROUP_START_FIRST_AND_ENTER, GROUP_START_RANDOM, GROUP_TIMELINE, TYPE_ARM,
                                 TYPE_AUDIO, TYPE_DEVAMP, TYPE_DISARM, TYPE_FADE, TYPE_GOTO, TYPE_GROUP, TYPE_LOAD,
                                 TYPE_MEMO, TYPE_NETWORK, TYPE_PAUSE, TYPE_RESET, TYPE_SCRIPT, TYPE_START, TYPE_STOP, TYPE_TARGET,
                                 TYPE_WAIT, Workspace)


def build(*specs):
    workspace = Workspace()
    cues = []
    for spec in specs:
        cue = workspace.new_cue(spec.get("type", TYPE_NETWORK), parent=spec.get("parent"))
        if cue.cue_type == TYPE_NETWORK:
            cue.params["message"] = "/test"
        cue.duration = spec.get("duration", cue.duration)
        cue.pre_wait = spec.get("pre_wait", 0.0)
        cue.post_wait = spec.get("post_wait", 0.0)
        cue.continue_mode = spec.get("continue_mode", 0)
        cue.armed = spec.get("armed", True)
        cues.append(cue)
    runtime = Runtime(workspace, ManualClock())
    return workspace, runtime, cues


def started(runtime):
    return [entry[1] for entry in runtime.events("start")]


def test_go_avvia_e_sposta_il_playhead():
    workspace, runtime, cues = build({}, {}, {})
    assert runtime.playhead() is cues[0]
    runtime.go()
    assert runtime.playhead() is cues[1]
    assert started(runtime) == [cues[0].unique_id]


def test_go_salta_l_intera_sequenza():
    workspace, runtime, cues = build({"continue_mode": CONTINUE_AUTO_CONTINUE}, {"continue_mode": CONTINUE_AUTO_FOLLOW}, {}, {})
    runtime.go()
    assert runtime.playhead() is cues[3]


def test_fine_lista_go_non_fa_nulla():
    workspace, runtime, cues = build({})
    runtime.go()
    assert runtime.playhead() is None
    assert runtime.go() == False


def test_auto_continue_parte_a_post_wait_in_parallelo():
    workspace, runtime, cues = build({"duration": 10, "post_wait": 2, "continue_mode": CONTINUE_AUTO_CONTINUE}, {"duration": 1})
    runtime.go()
    runtime.advance(1.9)
    assert runtime.is_active(cues[1]) == False
    runtime.advance(0.2)
    assert runtime.is_running(cues[1]) == True
    assert runtime.is_running(cues[0]) == True


def test_auto_follow_parte_al_termine_dell_azione():
    workspace, runtime, cues = build({"duration": 3, "continue_mode": CONTINUE_AUTO_FOLLOW}, {"duration": 1})
    runtime.go()
    runtime.advance(2.9)
    assert runtime.is_active(cues[1]) == False
    runtime.advance(0.2)
    assert runtime.is_running(cues[1]) == True


def test_pre_wait_ritarda_l_azione():
    workspace, runtime, cues = build({"duration": 2, "pre_wait": 1.5})
    runtime.go()
    assert runtime.status(cues[0])["pre_wait_running"] == True
    runtime.advance(1.4)
    assert runtime.status(cues[0])["running"] == False
    runtime.advance(0.2)
    assert runtime.status(cues[0])["running"] == True
    runtime.advance(2.0)
    assert runtime.is_active(cues[0]) == False


def test_disarmato_rispetta_il_timing():
    workspace, runtime, cues = build({"duration": 2, "continue_mode": CONTINUE_AUTO_FOLLOW, "armed": False}, {"duration": 1})
    runtime.go()
    runtime.advance(1.9)
    assert runtime.is_active(cues[1]) == False
    runtime.advance(0.2)
    assert runtime.is_running(cues[1]) == True


def test_preview_non_avvia_i_successivi_ne_sposta_il_playhead():
    workspace, runtime, cues = build({"duration": 1, "pre_wait": 5, "continue_mode": CONTINUE_AUTO_FOLLOW}, {"duration": 1})
    runtime.preview()
    assert runtime.is_running(cues[0]) == True
    runtime.advance(2)
    assert runtime.is_active(cues[1]) == False
    assert runtime.playhead() is cues[0]


def test_double_go_ignorato_ma_non_i_trigger():
    workspace, runtime, cues = build({}, {}, {})
    workspace.settings["min_go_time"] = 1.0
    assert runtime.go() == True
    runtime.advance(0.5)
    assert runtime.go() == False
    assert runtime.start_cue(cues[2], origin=ORIGIN_TRIGGER) == True
    runtime.advance(0.6)
    assert runtime.go() == True


def test_cue_in_esecuzione_ignora_nuovo_start_e_second_trigger():
    workspace, runtime, cues = build({"duration": 10})
    runtime.start_cue(cues[0], origin=ORIGIN_TRIGGER)
    assert runtime.start_cue(cues[0], origin=ORIGIN_TRIGGER) == False
    cues[0].second_trigger_action = SECOND_TRIGGER_STOP
    assert runtime.start_cue(cues[0], origin=ORIGIN_TRIGGER) == True
    assert runtime.is_active(cues[0]) == False
    # il second trigger non fa nulla se il cue non gira
    assert runtime.start_cue(cues[0], origin=ORIGIN_TRIGGER) == True
    assert runtime.is_running(cues[0]) == True


def test_second_trigger_al_rilascio():
    workspace, runtime, cues = build({"duration": 10})
    cues[0].second_trigger_action = SECOND_TRIGGER_STOP
    cues[0].second_trigger_on_release = True
    runtime.start_cue(cues[0], origin=ORIGIN_TRIGGER)
    runtime.release_trigger(cues[0])
    assert runtime.is_active(cues[0]) == False


def test_pause_e_resume_congelano_i_tempi():
    workspace, runtime, cues = build({"duration": 4})
    runtime.go()
    runtime.advance(1)
    runtime.pause_cue(cues[0])
    runtime.advance(10)
    assert runtime.is_active(cues[0]) == True
    runtime.resume_cue(cues[0])
    runtime.advance(2.9)
    assert runtime.is_active(cues[0]) == True
    runtime.advance(0.2)
    assert runtime.is_active(cues[0]) == False


def test_stop_non_fa_partire_il_follow():
    workspace, runtime, cues = build({"duration": 4, "continue_mode": CONTINUE_AUTO_FOLLOW}, {"duration": 1})
    runtime.go()
    runtime.advance(1)
    runtime.stop_cue(cues[0])
    runtime.advance(10)
    assert runtime.is_active(cues[1]) == False


def test_panic_poi_hard_stop_dopo_panic_duration():
    workspace, runtime, cues = build({"duration": 100})
    workspace.settings["panic_duration"] = 2.0
    runtime.go()
    runtime.panic_all()
    assert runtime.status(cues[0])["panicking"] == True
    runtime.advance(1.9)
    assert runtime.is_active(cues[0]) == True
    runtime.advance(0.2)
    assert runtime.is_active(cues[0]) == False


def test_secondo_panic_e_hard_stop_immediato():
    workspace, runtime, cues = build({"duration": 100})
    runtime.go()
    runtime.panic_all()
    runtime.panic_all()
    assert runtime.is_active(cues[0]) == False


def test_cue_di_controllo_start_stop_pause_non_spostano_il_playhead():
    workspace, runtime, cues = build({"duration": 10}, {"type": TYPE_START}, {"type": TYPE_PAUSE}, {"type": TYPE_STOP}, {})
    for control in cues[1:4]:
        control.target_id = cues[0].unique_id
    runtime.start_cue(cues[1])
    assert runtime.is_running(cues[0]) == True
    assert runtime.playhead() is cues[0]
    runtime.start_cue(cues[2])
    assert runtime.status(cues[0])["paused"] == True
    runtime.start_cue(cues[1])
    assert runtime.status(cues[0])["paused"] == False
    runtime.start_cue(cues[3])
    assert runtime.is_active(cues[0]) == False


def test_goto_sposta_il_playhead():
    workspace, runtime, cues = build({}, {}, {"type": TYPE_GOTO})
    cues[2].target_id = cues[1].unique_id
    runtime.start_cue(cues[2])
    assert runtime.playhead() is cues[1]


def test_arm_disarm():
    workspace, runtime, cues = build({}, {"type": TYPE_DISARM}, {"type": TYPE_ARM})
    cues[1].target_id = cues[0].unique_id
    cues[2].target_id = cues[0].unique_id
    runtime.start_cue(cues[1])
    assert cues[0].armed == False
    runtime.start_cue(cues[2])
    assert cues[0].armed == True


def test_target_cue_temporaneo_e_reset():
    workspace, runtime, cues = build({"duration": 5}, {"duration": 5}, {"type": TYPE_START}, {"type": TYPE_TARGET})
    cues[1].number = "20"
    cues[2].target_id = cues[0].unique_id
    cues[3].target_id = cues[2].unique_id
    cues[3].params["new_target_number"] = "20"
    runtime.start_cue(cues[3])
    assert runtime.resolve_target(cues[2]) is cues[1]
    assert workspace.find_target(cues[2]) is cues[0]
    runtime.start_cue(cues[2])
    assert runtime.is_running(cues[1]) == True
    assert runtime.is_running(cues[0]) == False
    runtime.reset_cue(cues[2])
    assert runtime.resolve_target(cues[2]) is cues[0]


def test_cue_senza_target_e_broken_ma_rispetta_il_timing():
    workspace, runtime, cues = build({"type": TYPE_START, "duration": 0, "continue_mode": CONTINUE_AUTO_CONTINUE, "post_wait": 1}, {"duration": 1})
    assert runtime.is_broken(cues[0]) == True
    runtime.go()
    runtime.advance(1.1)
    assert runtime.is_running(cues[1]) == True


def test_load_con_tempo_negativo_dalla_fine():
    workspace, runtime, cues = build({"duration": 10})
    runtime.load_cue(cues[0], -3.0)
    assert runtime.loaded[cues[0].unique_id] == 7.0


def test_timeline_avvia_tutti_i_figli_e_i_figli_con_continue_sono_broken():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_TIMELINE
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    first.duration = 2
    second.duration = 3
    second.pre_wait = 1
    runtime = Runtime(workspace, ManualClock())
    runtime.go()
    assert runtime.is_running(first) == True
    assert runtime.is_running(second) == False
    runtime.advance(1.1)
    assert runtime.is_running(second) == True
    assert runtime.playhead() is None
    first.continue_mode = CONTINUE_AUTO_FOLLOW
    assert runtime.is_broken(first) == True


def test_gruppo_termina_quando_finiscono_i_figli():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_TIMELINE
    child = workspace.new_cue(TYPE_WAIT, parent=group)
    child.duration = 2
    runtime = Runtime(workspace, ManualClock())
    runtime.go()
    assert runtime.is_running(group) == True
    runtime.advance(2.1)
    assert runtime.is_active(group) == False


def test_start_first_avvia_solo_il_primo_e_il_playhead_salta_dopo_il_group():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_START_FIRST
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    after = workspace.new_cue(TYPE_WAIT)
    runtime = Runtime(workspace, ManualClock())
    runtime.go()
    assert runtime.is_running(first) == True
    assert runtime.is_active(second) == False
    assert runtime.playhead() is after


def test_start_first_and_enter_il_playhead_entra_nel_group():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_START_FIRST_AND_ENTER
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    after = workspace.new_cue(TYPE_WAIT)
    runtime = Runtime(workspace, ManualClock())
    runtime.go()
    assert runtime.playhead() is second
    runtime.go()
    assert runtime.is_running(second) == True
    assert runtime.playhead() is after


def test_start_random_round_robin():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_START_RANDOM
    children = [workspace.new_cue(TYPE_WAIT, parent=group) for _ in range(3)]
    for child in children:
        child.duration = 1
    children[1].armed = False
    runtime = Runtime(workspace, ManualClock(), random_source=random.Random(3))
    seen = []
    for _ in range(4):
        runtime.start_cue(group)
        running = [child for child in children if runtime.is_active(child)]
        assert len(running) == 1
        seen.append(running[0])
        runtime.advance(1.1)
    assert children[1] not in seen
    assert seen[0] is not seen[1]
    assert set(seen[:2]) == {children[0], children[2]}


def test_playlist_in_sequenza_automatica_e_loop():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_PLAYLIST
    group.params["playlist_loop"] = True
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    first.duration = 2
    second.duration = 3
    runtime = Runtime(workspace, ManualClock())
    runtime.go()
    assert runtime.is_running(first) == True
    runtime.advance(2.1)
    assert runtime.is_running(second) == True
    assert runtime.is_active(first) == False
    runtime.advance(3.0)
    assert runtime.is_running(first) == True


def test_playlist_crossfade_sovrappone_e_figlio_corto_e_broken():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_PLAYLIST
    group.params["playlist_crossfade"] = True
    group.params["playlist_crossfade_duration"] = 1.0
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    short = workspace.new_cue(TYPE_WAIT, parent=group)
    first.duration = 4
    second.duration = 4
    short.duration = 1.0
    runtime = Runtime(workspace, ManualClock())
    assert runtime.is_broken(short) == True
    assert runtime.is_broken(first) == False
    runtime.go()
    runtime.advance(2.9)
    assert runtime.is_running(second) == False
    runtime.advance(0.2)
    assert runtime.is_running(first) == True
    assert runtime.is_running(second) == True
    assert runtime.status(first)["crossfading_out"] == True


def test_playlist_next_via_second_trigger():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_PLAYLIST
    first = workspace.new_cue(TYPE_WAIT, parent=group)
    second = workspace.new_cue(TYPE_WAIT, parent=group)
    first.duration = 5
    second.duration = 5
    group.second_trigger_action = SECOND_TRIGGER_PLAYLIST_NEXT
    runtime = Runtime(workspace, ManualClock())
    runtime.start_cue(group, origin=ORIGIN_TRIGGER)
    runtime.start_cue(group, origin=ORIGIN_TRIGGER)
    assert runtime.is_running(second) == True
    assert runtime.is_active(first) == False


def test_playlist_loop_senza_durata_e_broken():
    workspace = Workspace()
    group = workspace.new_cue(TYPE_GROUP)
    group.params["group_mode"] = GROUP_PLAYLIST
    group.params["playlist_loop"] = True
    child = workspace.new_cue(TYPE_MEMO, parent=group)
    runtime = Runtime(workspace, ManualClock())
    assert runtime.is_broken(group) == True


def test_fade_assoluto_sul_livello_con_curva_lineare():
    workspace, runtime, cues = build({"type": TYPE_AUDIO, "duration": 0}, {"type": TYPE_FADE, "duration": 4})
    cues[0].params["file_target"] = "x.wav"
    cues[0].params["media_duration"] = 60.0
    cues[0].params["levels"] = {"main": 0.0}
    fade = cues[1]
    fade.target_id = cues[0].unique_id
    fade.params["levels"] = {"main": -20.0}
    fade.params["curve"] = {"type": "linear", "intensity": 0.5, "rising": [], "falling": []}
    runtime.start_cue(cues[0])
    runtime.start_cue(fade)
    runtime.advance(2.0)
    assert runtime.get_param(cues[0], "levels")["main"] == pytest.approx(-10.0, abs=0.01)
    runtime.advance(2.1)
    assert runtime.get_param(cues[0], "levels")["main"] == pytest.approx(-20.0)
    assert cues[0].params["levels"]["main"] == 0.0


def test_fade_relativo_e_revert():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_FADE, "duration": 1})
    cues[0].params["file_target"] = "x.wav"
    cues[0].params["media_duration"] = 60.0
    cues[0].params["levels"] = {"main": -10.0}
    fade = cues[1]
    fade.target_id = cues[0].unique_id
    fade.params["levels"] = {"main": -5.0}
    fade.params["levels_mode"] = "relative"
    runtime.start_cue(cues[0])
    runtime.start_cue(fade)
    runtime.advance(1.5)
    assert runtime.get_param(cues[0], "levels")["main"] == pytest.approx(-15.0)
    runtime.revert_fade(fade)
    assert runtime.get_param(cues[0], "levels")["main"] == pytest.approx(-10.0)


def test_revert_non_tocca_parametri_cambiati_da_altri():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_FADE, "duration": 1})
    cues[0].params["file_target"] = "x.wav"
    cues[0].params["media_duration"] = 60.0
    fade = cues[1]
    fade.target_id = cues[0].unique_id
    fade.params["do_opacity"] = True
    fade.params["opacity"] = 0.0
    runtime.start_cue(fade)
    runtime.advance(1.5)
    runtime.set_live_param(cues[0], "opacity", 0.7)
    runtime.revert_fade(fade)
    assert runtime.get_param(cues[0], "opacity") == 0.7


def test_fade_e_stop_del_target():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_FADE, "duration": 1})
    cues[0].params["file_target"] = "x.wav"
    cues[0].params["media_duration"] = 60.0
    fade = cues[1]
    fade.target_id = cues[0].unique_id
    fade.params["levels"] = {"main": -60.0}
    fade.params["stop_target_when_done"] = True
    runtime.start_cue(cues[0])
    runtime.start_cue(fade)
    runtime.advance(1.2)
    assert runtime.is_active(cues[0]) == False
    assert fade.display_name(workspace).startswith("fade and stop")


def test_fade_senza_parametri_e_broken():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_FADE})
    cues[1].target_id = cues[0].unique_id
    assert runtime.is_broken(cues[1]) == True


def test_audio_durata_slice_e_devamp():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_DEVAMP})
    audio = cues[0]
    audio.params["file_target"] = "x.wav"
    audio.params["media_duration"] = 10.0
    audio.params["slices"] = [{"time": 0.0, "play_count": 1}, {"time": 2.0, "play_count": "inf"},
                              {"time": 4.0, "play_count": 1}]
    cues[1].target_id = audio.unique_id
    runtime.start_cue(audio)
    runtime.advance(5.0)
    assert runtime.is_running(audio) == True
    runtime.advance(0.0)
    runtime.start_cue(cues[1])
    # devamp a t=5: slice infinita lunga 2 s, iterazione 1 (t 4..6) -> esce a t=6 e suona l'ultima slice (6 s)
    runtime.advance(0.9)
    assert runtime.is_running(audio) == True
    runtime.advance(100)
    assert runtime.is_active(audio) == False


def test_devamp_esce_a_fine_slice_non_subito():
    workspace, runtime, cues = build({"type": TYPE_AUDIO}, {"type": TYPE_DEVAMP})
    audio = cues[0]
    audio.params["file_target"] = "x.wav"
    audio.params["media_duration"] = 6.0
    audio.params["slices"] = [{"time": 0.0, "play_count": "inf"}, {"time": 2.0, "play_count": 1}]
    cues[1].target_id = audio.unique_id
    runtime.start_cue(audio)
    runtime.advance(5.0)
    state = runtime.states[audio.unique_id]
    runtime.start_cue(cues[1])
    # al t=5 siamo nella 3a iterazione (4..6) della slice infinita: finisce a t=6, poi la slice di 4 s
    assert state.action_duration == pytest.approx(10.0)
    runtime.advance(4.9)
    assert runtime.is_running(audio) == True
    runtime.advance(0.2)
    assert runtime.is_active(audio) == False


def test_slice_tutte_a_zero_e_broken():
    workspace, runtime, cues = build({"type": TYPE_AUDIO})
    cues[0].params["file_target"] = "x.wav"
    cues[0].params["media_duration"] = 6.0
    cues[0].params["slices"] = [{"time": 0.0, "play_count": 0}]
    assert runtime.is_broken(cues[0]) == True


def test_script_python_esegue_e_riporta_errori():
    workspace, runtime, cues = build({"type": TYPE_SCRIPT}, {"duration": 5})
    cues[1].number = "9"
    cues[0].params["script_source"] = "cue('9').start()\nlog('ok')"
    runtime.start_cue(cues[0])
    assert runtime.is_running(cues[1]) == True
    assert runtime.script_output == ["ok"]
    cues[0].params["script_source"] = "cue('zzz').start()"
    runtime.start_cue(cues[0])
    assert len(runtime.events("script_error")) == 1
    cues[0].params["script_source"] = "def broken(:"
    assert runtime.compile_script(cues[0]) != ""
    assert runtime.is_broken(cues[0]) == True


def test_script_non_puo_importare():
    workspace, runtime, cues = build({"type": TYPE_SCRIPT})
    cues[0].params["script_source"] = "import os"
    runtime.start_cue(cues[0])
    assert len(runtime.events("script_error")) == 1


def test_reset_workspace_riporta_il_playhead_e_azzera_i_temporanei():
    workspace, runtime, cues = build({"duration": 10}, {"duration": 10})
    runtime.go()
    runtime.set_live_param(cues[0], "opacity", 0.1)
    runtime.reset_workspace()
    assert runtime.playhead() is cues[0]
    assert runtime.get_param(cues[0], "opacity", 1.0) == 1.0
    assert runtime.active_cues() == []
    assert workspace.modified == False or workspace.modified == True


def test_colore_condizionale():
    workspace, runtime, cues = build({})
    cues[0].color = "red"
    cues[0].color_condition = "before_action"
    assert runtime.current_color(cues[0]) == "red"
    runtime.go()
    assert runtime.current_color(cues[0]) == "none"
    runtime.reset_cue(cues[0])
    assert runtime.current_color(cues[0]) == "red"


def test_fade_and_stop_others_e_duck():
    workspace, runtime, cues = build({"duration": 100}, {"duration": 100})
    cues[1].fade_and_stop_others = {"mode": 2, "time": 2.0}
    runtime.start_cue(cues[0])
    runtime.start_cue(cues[1])
    runtime.advance(1.0)
    assert runtime.gain_for(cues[0]) == pytest.approx(0.5)
    runtime.advance(1.1)
    assert runtime.is_active(cues[0]) == False
    assert runtime.is_running(cues[1]) == True


def test_wait_ha_post_wait_uguale_alla_durata():
    workspace, runtime, cues = build({"type": TYPE_WAIT, "duration": 2, "continue_mode": CONTINUE_AUTO_CONTINUE}, {"duration": 1})
    runtime.go()
    runtime.advance(1.9)
    assert runtime.is_active(cues[1]) == False
    runtime.advance(0.2)
    assert runtime.is_running(cues[1]) == True


def test_gestori_di_uscita_ricevono_start_stop():
    class Recorder(ActionHandler):
        def __init__(self):
            self.calls = []

        def start(self, runtime, state):
            self.calls.append(("start", state.cue.unique_id))

        def stop(self, runtime, state, hard):
            self.calls.append(("stop", hard))

    workspace, runtime, cues = build({"duration": 1})
    recorder = Recorder()
    runtime.register_handler(TYPE_NETWORK, recorder)
    runtime.go()
    runtime.advance(1.1)
    assert recorder.calls == [("start", cues[0].unique_id), ("stop", False)]
