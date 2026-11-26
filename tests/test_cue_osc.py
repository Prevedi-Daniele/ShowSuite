import json
import socket
import time

import pytest

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_AUDIO, TYPE_GROUP, TYPE_MEMO, TYPE_NETWORK, TYPE_WAIT, Workspace
from showsuite.cue.osc import (Impulse, MemoryClient, OscServer, SlipDecoder, decode_packet, encode_message,
                               parse_plain_text, pattern_matches, slip_encode)
from showsuite.cue.qlab_api import QLabApi


def test_codec_roundtrip():
    data = encode_message("/cue/1/name", ["Ciao mondo", 3, 2.5, True, None, Impulse(), b"ab"])
    address, arguments = decode_packet(data)[0]
    assert address == "/cue/1/name"
    assert arguments[0] == "Ciao mondo"
    assert arguments[1] == 3
    assert arguments[2] == pytest.approx(2.5)
    assert arguments[3] is True and arguments[4] is None
    assert isinstance(arguments[5], Impulse)
    assert arguments[6] == b"ab"


def test_bundle_e_slip():
    first = encode_message("/a", [1])
    second = encode_message("/b", ["x"])
    bundle = b"#bundle\x00" + b"\x00" * 8 + len(first).to_bytes(4, "big") + first + len(second).to_bytes(4, "big") + second
    assert [item[0] for item in decode_packet(bundle)] == ["/a", "/b"]
    framed = slip_encode(bytes([0xC0, 0xDB, 1])) + slip_encode(b"xy")
    decoder = SlipDecoder()
    assert decoder.feed(framed[:3]) == []
    assert decoder.feed(framed[3:]) == [bytes([0xC0, 0xDB, 1]), b"xy"]


def test_pattern_osc():
    assert pattern_matches("understudy-*", "understudy-12")
    assert pattern_matches("?", "5") and not pattern_matches("?", "55")
    assert pattern_matches("[1-3]", "2")
    assert pattern_matches("{a,b}", "b")


def test_testo_semplice():
    assert parse_plain_text("/cue/1/name \"Hello world\"") == ("/cue/1/name", ["Hello world"])
    assert parse_plain_text("/cue/1/preWait 2.5") == ("/cue/1/preWait", [2.5])


def make_api():
    workspace = Workspace("Show Demo")
    workspace.settings["passcodes"] = [{"passcode": "", "view": True, "edit": True, "control": True}]
    first = workspace.new_cue(TYPE_WAIT, name="Uno")
    second = workspace.new_cue(TYPE_WAIT, name="Due")
    first.duration = 5
    second.duration = 5
    runtime = Runtime(workspace, ManualClock())
    api = QLabApi([runtime])
    client = MemoryClient()
    return workspace, runtime, api, client, (first, second)


def last_reply(client):
    address, arguments = client.messages[-1]
    return address, json.loads(arguments[0])


def test_lettura_scrittura_e_risposte_json():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/cue/1/name", [], client)
    address, payload = last_reply(client)
    assert address == "/reply/cue/1/name"
    assert payload["status"] == "ok" and payload["data"] == "Uno"
    api.handle("/cue/1/name", ["Primo"], client)
    assert cues[0].name == "Primo"
    api.handle("/cue/1/preWait/+", [1.5], client)
    api.handle("/cue/1/preWait/+", [1.5], client)
    assert cues[0].pre_wait == 3.0
    api.handle("/cue/zzz/name", [], client)
    assert last_reply(client)[1]["status"] == "error"


def test_azioni_go_panic_e_trasporto():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/go", [], client)
    assert runtime.is_running(cues[0]) == True
    assert runtime.playhead() is cues[1]
    api.handle("/cue/2/start", [], client)
    assert runtime.is_running(cues[1]) == True
    api.handle("/pause", [], client)
    assert runtime.status(cues[0])["paused"] == True
    api.handle("/resume", [], client)
    api.handle("/workspace/%s/hardStop" % workspace.workspace_id, [], client)
    assert runtime.active_cues() == []
    api.handle("/playhead/1", [], client)
    assert runtime.playhead() is cues[0]


def test_wildcard_e_selected():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/cue/*/armed", [0], client)
    assert cues[0].armed == False and cues[1].armed == False
    api.handle("/select/2", [], client)
    api.handle("/cue/selected/colorName", ["green"], client)
    assert cues[1].color == "green" and cues[0].color == "none"
    api.handle("/cue/[*]/flagged", [1], client)
    assert cues[0].flagged == True


def test_live_non_modifica_il_documento():
    workspace, runtime, api, client, cues = make_api()
    audio = workspace.new_cue(TYPE_AUDIO)
    api.handle("/cue/%s/rate/live" % audio.number, [2.0], client)
    assert audio.params["rate"] == 1.0
    assert runtime.get_param(audio, "rate") == 2.0
    api.handle("/cue/%s/rate" % audio.number, [], client)
    assert last_reply(client)[1]["data"] == 2.0 or last_reply(client)[1]["data"] == 1.0


def test_permessi_passcode_e_connect():
    workspace, runtime, api, client, cues = make_api()
    workspace.settings["passcodes"] = [{"passcode": "", "view": False, "edit": False, "control": False},
                                       {"passcode": "1234", "view": True, "edit": False, "control": True}]
    api.handle("/cue/1/name", [], client)
    assert last_reply(client)[1]["status"] == "denied"
    api.handle("/workspace/%s/connect" % workspace.workspace_id, ["0000"], client)
    assert last_reply(client)[1]["data"] == "badpass"
    api.handle("/workspace/%s/connect" % workspace.workspace_id, ["1234"], client)
    assert last_reply(client)[1]["data"] == "ok"
    api.handle("/cue/1/name", [], client)
    assert last_reply(client)[1]["data"] == "Uno"
    api.handle("/cue/1/name", ["X"], client)
    assert last_reply(client)[1]["status"] == "denied"
    api.handle("/go", [], client)
    assert runtime.is_running(cues[0]) == True


def test_always_reply_e_reply_format():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/go", [], client)
    count = len(client.messages)
    api.handle("/alwaysReply", [1], client)
    api.handle("/cue/2/start", [], client)
    assert len(client.messages) > count
    api.handle("/replyFormat", ["#data# #address#"], client)
    api.handle("/cue/1/colorName", [], client)
    assert client.messages[-1][1][0] == "none /cue/1/colorName"


def test_new_delete_renumber_e_liste_di_cue():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/new", ["memo"], client)
    identifier = last_reply(client)[1]["data"]
    assert workspace.find_by_id(identifier).cue_type == TYPE_MEMO
    api.handle("/cue_id/%s/number" % identifier, ["77"], client)
    assert workspace.find_by_id(identifier).number == "77"
    api.handle("/cue/77/number", ["1"], client)
    assert last_reply(client)[1]["status"] == "error"
    api.handle("/cueLists", [], client)
    data = last_reply(client)[1]["data"]
    assert data[0]["type"] == "Cue List" and len(data[0]["cues"]) == 3
    api.handle("/delete/77", [], client)
    assert workspace.find_by_number("77") is None


def test_push_updates_playhead():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/updates", [1], client)
    api.handle("/go", [], client)
    pushed = [message for message in client.messages if message[0].startswith("/update/")]
    assert pushed[-1][0].endswith("/playbackPosition")
    assert pushed[-1][1] == [cues[1].unique_id]


def test_sessione_udp_scade_dopo_61_secondi():
    workspace, runtime, api, client, cues = make_api()
    now = [0.0]
    api.monotonic = lambda: now[0]
    client.transport = "udp"
    api.handle("/alwaysReply", [1], client)
    assert len(api.sessions) == 1
    now[0] = 62.0
    other = MemoryClient("altro")
    other.transport = "udp"
    api.handle("/version", [], other)
    assert client.identity() not in api.sessions


def test_query_per_network_cue():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/select/2", [], client)
    assert api.query("/cue/selected/number") == ["2"] or api.query("/cue/selected/number") == "2"


def test_livello_e_geometria():
    workspace, runtime, api, client, cues = make_api()
    audio = workspace.new_cue(TYPE_AUDIO)
    api.handle("/cue/%s/level/0/0" % audio.number, [-3.0], client)
    assert audio.params["levels"]["main"] == -3.0
    api.handle("/cue/%s/translation/x" % audio.number, [40], client)
    assert audio.params["translation"][0] == 40.0
    api.handle("/cue/%s/scale" % audio.number, [2, 3], client)
    assert audio.params["scale"] == [2.0, 3.0]
    api.handle("/cue/%s/addSliceMarker" % audio.number, [2.5, -1], client)
    assert audio.params["slices"][0] == {"time": 2.5, "play_count": "inf"}


def test_trasporto_reale_udp_tcp_e_testo():
    workspace, runtime, api, client, cues = make_api()
    server = OscServer(api.handle, host="127.0.0.1", port=0, reply_port=0, plain_port=0)
    server.start()
    try:
        udp_port, tcp_port, plain_port = server.bound_ports()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(encode_message("/go", []), ("127.0.0.1", udp_port))
        for _ in range(50):
            if runtime.is_running(cues[0]):
                break
            time.sleep(0.02)
        assert runtime.is_running(cues[0]) == True
        sock.sendto(b"/cue/2/start", ("127.0.0.1", plain_port))
        for _ in range(50):
            if runtime.is_running(cues[1]):
                break
            time.sleep(0.02)
        assert runtime.is_running(cues[1]) == True
        tcp = socket.create_connection(("127.0.0.1", tcp_port))
        tcp.sendall(slip_encode(encode_message("/cue/1/name", [])))
        tcp.settimeout(2.0)
        data = tcp.recv(4096)
        address, arguments = decode_packet(SlipDecoder().feed(data)[0])[0]
        assert address == "/reply/cue/1/name"
        assert json.loads(arguments[0])["data"] == "Uno"
        tcp.close()
    finally:
        server.stop()


def broadcast_messages(client):
    return [(address, arguments) for address, arguments in client.messages if address.startswith("/qlab/event")]


def test_show_control_broadcast_listen_e_forme():
    workspace, runtime, api, client, cues = make_api()
    cues[0].number = "24"
    cues[0].name = "intro music"
    api.handle("/listen/go/number", [], client)
    api.handle("/listen/panicAll", [], client)
    api.handle("/go", [], client)
    messages = broadcast_messages(client)
    assert messages == [("/qlab/event/workspace/go/number", ["24"])]
    api.handle("/panic", [], client)
    assert ("/qlab/event/workspace/panicAll", []) in broadcast_messages(client)


def test_show_control_broadcast_tutte_le_forme_start_e_stop():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/listen", [], client)
    api.handle("/cue/2/start", [], client)
    addresses = [address for address, arguments in broadcast_messages(client)]
    assert "/qlab/event/workspace/cue/start" in addresses
    assert "/qlab/event/workspace/cue/start/uniqueID" in addresses
    assert "/qlab/event/workspace/go" not in addresses
    start = [m for m in broadcast_messages(client) if m[0] == "/qlab/event/workspace/cue/start"][0]
    assert start[1] == ["2", "Due", cues[1].unique_id, "Wait"]
    api.handle("/stop", [], client)
    assert "/qlab/event/workspace/cue/stop" in [a for a, x in broadcast_messages(client)]
    assert "/qlab/event/workspace/stopAll" in [a for a, x in broadcast_messages(client)]


def test_ignore_e_event_format():
    workspace, runtime, api, client, cues = make_api()
    api.handle("/listen/go/number", [], client)
    api.handle("/eventFormat", ["/cue/#data#/start"], client)
    api.handle("/go", [], client)
    sent = [(address, arguments) for address, arguments in client.messages if address.startswith("/cue/")]
    assert sent == [("/cue/1/start", [])]
    client.messages.clear()
    api.handle("/ignore", [], client)
    api.handle("/go", [], client)
    assert broadcast_messages(client) == []
    api.handle("/eventFormat", [], client)
    assert last_reply(client)[1]["data"] == "/cue/#data#/start"


def test_settings_audio_patch_per_nome_e_id():
    import json as json_module
    workspace, runtime, api, client, cues = make_api()
    workspace.patches["audio"] = [{"name": "Sala", "device": "", "first_channel": 3, "channels": 2}]
    api.handle("/settings/audio/patch/Sala", [], client)
    info = json_module.loads(last_reply(client)[1]["data"])
    assert info["name"] == "Sala" and info["routing"] == [3, 4]
    identifier = info["uniqueID"]
    api.handle("/settings/audio/patchID/%s/cueOutputChannels" % identifier, [4], client)
    api.handle("/settings/audio/patch/Sala/routing", [], client)
    assert last_reply(client)[1]["data"] == [3, 4, 5, 6]
    api.handle("/settings/audio/patch/Sala/mute/2", [True], client)
    api.handle("/settings/audio/patch/Sala/mute/2", [], client)
    assert last_reply(client)[1]["data"] == True
    api.handle("/settings/audio/patch/Sala/muteChannels", [], client)
    assert last_reply(client)[1]["data"] == [2]
    api.handle("/settings/audio/patch/Sala/mute/clear", [], client)
    assert workspace.patches["audio"][0]["mute"] == []
    api.handle("/settings/audio/patch/Sala/level/1/2", ["off"], client)
    api.handle("/settings/audio/patch/Sala/level/1/2", [], client)
    assert last_reply(client)[1]["data"] == -200.0
    api.handle("/settings/audio/patch/Sala/name", ["Platea"], client)
    assert workspace.patches["audio"][0]["name"] == "Platea"
    api.handle("/settings/audio/patch/Nessuna", [], client)
    assert last_reply(client)[1]["status"] == "error"


def test_settings_video_stage_regioni_e_route():
    import json as json_module
    workspace, runtime, api, client, cues = make_api()
    workspace.patches["video_stage"] = [{"name": "Main", "width": 400, "height": 200,
                                         "regions": [{"name": "Sx", "bounds": [0, 0, 200, 100]}]}]
    workspace.patches["video_route"] = [{"name": "Proiettore", "stage": 1, "region": "Sx"}]
    api.handle("/settings/video/stage/Main/size/width", [], client)
    assert last_reply(client)[1]["data"] == 400
    api.handle("/settings/video/stage/Main/region/Sx/bounds", [], client)
    bounds = json_module.loads(last_reply(client)[1]["data"])
    assert bounds == {"x": 0, "y": 100, "width": 200, "height": 100}
    api.handle("/settings/video/stage/Main/region/Sx/bounds", [10, 20, 100, 50], client)
    assert workspace.patches["video_stage"][0]["regions"][0]["bounds"] == [10, 130, 100, 50]
    api.handle("/settings/video/stage/Main/regionIndex/0/bounds", ["{{5,5}{50,40}}"], client)
    assert workspace.patches["video_stage"][0]["regions"][0]["bounds"] == [5, 155, 50, 40]
    api.handle("/settings/video/stage/Main/region/Sx/bounds/size/width", [500], client)
    assert last_reply(client)[1]["status"] == "error"
    api.handle("/settings/video/stage/Main/name", ["Palco"], client)
    api.handle("/settings/video/stage/Palco/uniqueID", [], client)
    stage_id = last_reply(client)[1]["data"]
    api.handle("/settings/video/stageID/%s/regions" % stage_id, [], client)
    assert json_module.loads(last_reply(client)[1]["data"])[0]["name"] == "Sx"
    api.handle("/settings/video/routeIndex/0/enableGuides", [True], client)
    api.handle("/settings/video/route/Proiettore/enableGuides", [], client)
    assert last_reply(client)[1]["data"] == True
    api.handle("/settings/video/route/Nessuna", [], client)
    assert last_reply(client)[1]["status"] == "error"


def test_settings_audio_map_marks_filtri_oggetti():
    import json as json_module
    from showsuite.cue import audiomap
    workspace, runtime, api, client, cues = make_api()
    audio_map = audiomap.new_map("Sala", 1000, 800)
    audiomap.add_mark(audio_map, "L", 0, 400, {1: 0.0})
    audiomap.add_filter(audio_map, "Muro", 500, 0)
    audiomap.add_object(audio_map)
    workspace.patches["audio_map"] = [audio_map]
    api.handle("/settings/audio/map/Sala/size/height", [], client)
    assert last_reply(client)[1]["data"] == 800
    api.handle("/settings/audio/map/Sala/mark/L/gravity", [3], client)
    assert audio_map["marks"][0]["gravity"] == 3.0
    api.handle("/settings/audio/map/Sala/mark/L/gravity", [9], client)
    assert last_reply(client)[1]["status"] == "error"
    api.handle("/settings/audio/map/Sala/mark/L/level/2", [-6], client)
    api.handle("/settings/audio/map/Sala/mark/*/levels", [], client)
    assert last_reply(client)[1]["data"][2] == -6
    api.handle("/settings/audio/map/Sala/filter/Muro/passthrough/3", [True], client)
    api.handle("/settings/audio/map/Sala/filter/Muro/passthroughs", [], client)
    assert last_reply(client)[1]["data"][2] == True
    api.handle("/settings/audio/map/Sala/object/A/position/live", [10, 20], client)
    assert (audio_map["objects"][0]["x"], audio_map["objects"][0]["y"]) == (10.0, 20.0)
    api.handle("/settings/audio/map/Sala/object/A/colorName", ["blue"], client)
    api.handle("/settings/audio/map/Sala/object/A/colorName", ["inesistente"], client)
    assert last_reply(client)[1]["status"] == "error"
    api.handle("/settings/audio/map/Sala/uniqueID", [], client)
    identifier = last_reply(client)[1]["data"]
    api.handle("/settings/audio/mapID/%s/objects" % identifier, [], client)
    assert json_module.loads(last_reply(client)[1]["data"])[0]["colorName"] == "blue"
    api.handle("/settings/audio/map/Sala/testObject/start", [], client)
    api.handle("/settings/audio/map/Sala/testObject/running", [], client)
    assert last_reply(client)[1]["data"] == True


def test_cue_audio_map_e_oggetti_propri():
    import json as json_module
    from showsuite.cue import audiomap
    from showsuite.cue.model import TYPE_AUDIO
    workspace, runtime, api, client, cues = make_api()
    audio_cue = workspace.new_cue(TYPE_AUDIO)
    audio_cue.number = "9"
    audio_map = audiomap.new_map("Sala", 1000, 1000)
    audiomap.add_mark(audio_map, "L", 0, 0, {1: 0.0})
    workspace.patches["audio_map"] = [audio_map]
    api.handle("/cue/9/audioMapName", ["Sala"], client)
    api.handle("/cue/9/audioMapNumber", [], client)
    assert last_reply(client)[1]["data"] == 1
    api.handle("/cue/9/audioMap/mark/L/gravity", [2], client)
    assert audio_map["marks"][0]["gravity"] == 2.0
    api.handle("/cue/9/audioMap/size/width", [], client)
    assert last_reply(client)[1]["data"] == 1000.0
    audio_cue.params["objects"] = [{"channel": 1}]
    api.handle("/cue/9/objects", [], client)
    listed = json_module.loads(last_reply(client)[1]["data"])
    assert listed[0]["name"] == "A"
    api.handle("/cue/9/object/A/position", [5, 6], client)
    api.handle("/cue/9/object/A/position/x", [], client)
    assert last_reply(client)[1]["data"] == 5.0
    api.handle("/cue/9/audioMapID", ["none"], client)
    assert audio_cue.params["audio_map"] == ""
    api.handle("/cue/9/audioMap", [], client)
    assert last_reply(client)[1]["status"] == "error"


def test_slice_marker_playlist_rotate_mute_solo_patch_del_cue():
    import json as json_module
    from showsuite.cue.model import TYPE_AUDIO
    workspace, runtime, api, client, cues = make_api()
    audio_cue = workspace.new_cue(TYPE_AUDIO)
    audio_cue.number = "9"
    workspace.patches["audio"] = [{"name": "Sala", "first_channel": 1, "channels": 2},
                                  {"name": "Foyer", "first_channel": 3, "channels": 2}]
    api.handle("/cue/9/addSliceMarker", [4.0, 2], client)
    api.handle("/cue/9/addSliceMarker", [1.0, -1], client)
    api.handle("/cue/9/sliceMarkers", [], client)
    listed = json_module.loads(last_reply(client)[1]["data"])
    assert listed == [{"time": 1.0, "playCount": -1}, {"time": 4.0, "playCount": 2}]
    api.handle("/cue/9/sliceMarker/1/time", [], client)
    assert last_reply(client)[1]["data"] == 4.0
    api.handle("/cue/9/sliceMarker/1/playCount", [3], client)
    api.handle("/cue/9/sliceMarker/1", [], client)
    assert json_module.loads(last_reply(client)[1]["data"]) == {"time": 4.0, "playCount": 3}
    api.handle("/cue/9/sliceMarkers/+", [2.0], client)
    assert audio_cue.params["slices"][0]["time"] == 3.0
    api.handle("/cue/9/audioOutputPatchName", ["Foyer"], client)
    api.handle("/cue/9/audioOutputPatchNumber", [], client)
    assert last_reply(client)[1]["data"] == 2
    api.handle("/cue/9/audioOutputPatch/routing", [], client)
    assert last_reply(client)[1]["data"] == [3, 4]
    api.handle("/cue/9/audioOutputPatchID", ["none"], client)
    api.handle("/cue/9/audioOutputPatchName", [], client)
    assert last_reply(client)[1]["data"] == "none"
    api.handle("/cue/9/mute/2", [True], client)
    api.handle("/cue/9/solo/channel/1", [True], client)
    api.handle("/cue/9/muteChannels", [], client)
    assert last_reply(client)[1]["data"] == [2]
    api.handle("/cue/9/solo/clear", [], client)
    assert audio_cue.params["solo_outputs"]["channels"] == []
    api.handle("/cue/9/rotate/z", [90], client)
    assert audio_cue.params["quaternion"][0] == pytest.approx(0.7071, abs=1e-3)
    api.handle("/cue/9/objectLevel/1/A", [-6], client)
    api.handle("/cue/9/objectLevels", [], client)
    assert last_reply(client)[1]["data"] == {"1/A": -6.0}
    api.handle("/cue/9/sliderLevel/2", [-3], client)
    api.handle("/cue/9/sliderLevel/2", [], client)
    assert last_reply(client)[1]["data"] == -3.0


def test_playlist_via_osc():
    from showsuite.cue.model import TYPE_WAIT
    workspace, runtime, api, client, cues = make_api()
    first = workspace.new_cue(TYPE_WAIT)
    second = workspace.new_cue(TYPE_WAIT)
    first.duration = second.duration = 10.0
    from showsuite.cue.model import GROUP_PLAYLIST
    group = workspace.make_group([first, second], GROUP_PLAYLIST)
    group.number = "20"
    api.handle("/cue/20/playlist/doLoop", [True], client)
    api.handle("/cue/20/playlist/doLoop", [], client)
    assert last_reply(client)[1]["data"] == True
    api.handle("/cue/20/playlist/crossfade/duration", [1.5], client)
    assert group.params["playlist_crossfade_duration"] == 1.5
    api.handle("/cue/20/start", [], client)
    api.handle("/cue/20/playlist/next", [], client)
    api.handle("/cue/20/playlist/currentCueID", [], client)
    assert last_reply(client)[1]["data"] == second.unique_id
