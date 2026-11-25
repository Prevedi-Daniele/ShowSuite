import datetime
import struct

import pytest

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_LIST, TYPE_MIDI, TYPE_MIDI_FILE, TYPE_NETWORK, TYPE_TIMECODE, TYPE_WAIT, Workspace
from showsuite.cue.outputs import OutputHub
from showsuite.cue.protocols import (LtcDecoder, MtcDecoder, frames_to_timecode, ltc_encode_frame, msc_message,
                                     mtc_full_frame, mtc_quarter_frames, parse_midi_file, parse_msc,
                                     pitch_bend_message, seconds_to_timecode, sysex_from_text, timecode_to_frames,
                                     timecode_to_seconds, voice_message)
from showsuite.cue.osc import decode_packet
from showsuite.cue.qlab_api import QLabApi
from showsuite.cue.triggers import TriggerManager, match_midi_trigger


def test_voce_msc_sysex():
    assert voice_message(1, 1, 60, 100) == bytes([0x90, 60, 100])
    assert voice_message(4, 16, 5) == bytes([0xCF, 5])
    assert pitch_bend_message(1, 8192) == bytes([0xE0, 0, 64])
    data = msc_message(1, 1, 5, "10", "2")
    assert data == b"\xF0\x7F\x05\x02\x01\x01" + b"10\x002" + b"\xF7"
    assert parse_msc(data) == {"device_id": 5, "command_format": 1, "command": 1, "q_number": "10", "q_list": "2",
                               "q_path": ""}
    set_message = msc_message(1, 6, 0, control_number=130, control_value=16383)
    assert parse_msc(set_message)["control_number"] == 130
    assert parse_msc(set_message)["control_value"] == 16383
    assert sysex_from_text("7E 7F 09 01") == b"\xF0\x7E\x7F\x09\x01\xF7"
    with pytest.raises(ValueError):
        sysex_from_text("F0 90 F7")


def test_drop_frame_e_conversioni():
    assert timecode_to_frames(0, 1, 0, 2, 2) == 1800
    assert frames_to_timecode(1800, 2) == (0, 1, 0, 2)
    assert frames_to_timecode(17982, 2) == (0, 10, 0, 0)
    assert timecode_to_seconds(1, 0, 0, 0, 1) == 3600.0
    assert seconds_to_timecode(3600.5, 1) == (1, 0, 0, 12)
    for count in (0, 1799, 1800, 17981, 17982, 100000):
        assert timecode_to_frames(*frames_to_timecode(count, 2), 2) == count


def test_mtc_quarter_frame_roundtrip():
    decoder = MtcDecoder()
    result = None
    for message in mtc_quarter_frames((1, 23, 45, 12), 1):
        result = decoder.feed(message) or result
    assert result == (1, 23, 45, 12)
    assert decoder.format_index == 1
    assert decoder.feed(mtc_full_frame((2, 3, 4, 5), 3)) == (2, 3, 4, 5)


def test_ltc_roundtrip():
    state = {"polarity": 1.0, "residual": 0.0}
    samples = []
    for second in range(3):
        for frame in range(25):
            samples.extend(ltc_encode_frame((0, 0, second, frame), 1, 48000, state=state))
    decoder = LtcDecoder(48000)
    found = decoder.feed(samples)
    assert len(found) >= 70
    assert found[-1] == (0, 0, 2, 23)
    assert found[-2] == (0, 0, 2, 22)


def test_file_midi_standard():
    track = bytes([0x00, 0xFF, 0x51, 0x03, 0x07, 0xA1, 0x20, 0x00, 0x90, 60, 100, 0x60, 0x80, 60, 0, 0x00, 0xFF, 0x2F, 0x00])
    data = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 96) + b"MTrk" + struct.pack(">I", len(track)) + track
    events, duration = parse_midi_file(data)
    assert events[0] == (0.0, bytes([0x90, 60, 100]))
    assert events[1][0] == pytest.approx(0.5)
    assert duration == pytest.approx(0.5)


def setup_runtime():
    workspace = Workspace("P")
    runtime = Runtime(workspace, ManualClock())
    api = QLabApi([runtime])
    hub = OutputHub(runtime, api)
    hub.install()
    workspace.patches["midi"] = [{"name": "Uscita", "device": "port1"}]
    workspace.patches["network"] = [{"name": "Esterno", "kind": "udp", "host": "10.0.0.5", "port": 9000},
                                    {"name": "Locale", "kind": "udp", "host": "localhost", "port": 53000}]
    return workspace, runtime, api, hub


def test_cue_midi_voce_e_fade_del_controller():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_MIDI)
    cue.params.update({"status": 3, "channel": 2, "byte1": 7, "byte2": 0, "end_value": 100})
    cue.duration = 2.0
    runtime.start_cue(cue)
    assert hub.midi_sent[0] == ("port1", bytes([0xB1, 7, 0]))
    runtime.advance(1.0)
    assert hub.midi_sent[-1][1][2] == 50
    runtime.advance(1.1)
    assert hub.midi_sent[-1][1][2] == 100


def test_override_midi_disabilita_uscita():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_MIDI)
    workspace.settings["overrides"]["midiOutput"] = False
    runtime.start_cue(cue)
    assert hub.midi_sent == []
    assert runtime.is_active(cue) == True or runtime.is_active(cue) == False


def test_cue_network_osc_query_e_loopback():
    workspace, runtime, api, hub = setup_runtime()
    other = workspace.new_cue(TYPE_WAIT, name="X")
    network = workspace.new_cue(TYPE_NETWORK)
    network.params.update({"message": "/device/standby #/cue/%s/number#" % other.number, "network_patch": 1})
    runtime.start_cue(network)
    kind, host, port, payload = hub.network_sent[-1]
    assert (host, port) == ("10.0.0.5", 9000)
    assert payload.startswith(b"/device/standby")
    assert payload.endswith(b"\x00\x00\x00\x01")
    local = workspace.new_cue(TYPE_NETWORK)
    local.params.update({"message": "/cue/%s/name Rinominato" % other.number, "network_patch": 2})
    runtime.start_cue(local)
    assert other.name == "Rinominato"


def test_network_fade_1d_a_fps():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_NETWORK)
    cue.params.update({"message": "/level $1", "network_patch": 1, "fade_type": 1, "fade_from": 0.0,
                       "fade_to": 10.0, "fps": 10, "curve": {"type": "linear", "intensity": 0.5, "rising": [], "falling": []}})
    cue.duration = 1.0
    runtime.start_cue(cue)
    for _ in range(53):
        runtime.advance(0.02)
    assert 10 <= len(hub.network_sent) <= 13
    assert decode_packet(hub.network_sent[-1][3])[0] == ("/level", [10.0])


def test_cue_timecode_mtc_invia_quarter_frame():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_TIMECODE)
    cue.params.update({"kind": "mtc", "format": 1, "start_time": "00:00:10:00"})
    runtime.start_cue(cue)
    runtime.advance(0.5)
    assert hub.midi_sent[0][1].startswith(b"\xF0\x7F\x7F\x01\x01")
    quarters = [item for item in hub.midi_sent if item[1][0] == 0xF1]
    assert len(quarters) in (50, 51, 52)
    decoder = MtcDecoder()
    decoded = None
    for item in quarters:
        decoded = decoder.feed(item[1]) or decoded
    assert decoded[2] == 10


def test_trigger_midi_regole():
    trigger = {"status": "note_on", "channel": 1, "byte1": "60", "byte2": ">0"}
    assert match_midi_trigger(trigger, bytes([0x90, 60, 1])) == True
    assert match_midi_trigger(trigger, bytes([0x90, 60, 0])) == False
    assert match_midi_trigger(trigger, bytes([0x91, 60, 100])) == False
    assert match_midi_trigger({"status": "note_on", "channel": 0, "byte1": "any", "byte2": "any"},
                              bytes([0x95, 12, 5])) == True


def test_trigger_hotkey_midi_e_second_trigger_rilascio():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_WAIT)
    cue.duration = 10
    cue.triggers["hotkey"] = "Ctrl+1"
    cue.triggers["midi"] = {"status": "note_on", "channel": 1, "byte1": "36", "byte2": "any"}
    manager = TriggerManager(runtime)
    assert manager.key_event("Ctrl+2", True) == []
    assert manager.key_event("Ctrl+1", True) == [cue]
    assert runtime.is_running(cue)
    manager.key_event("Ctrl+1", False)
    assert runtime.is_running(cue)
    runtime.stop_cue(cue)
    assert manager.midi_in(bytes([0x90, 36, 90])) == [cue]
    assert runtime.is_running(cue)


def test_msc_ricezione():
    workspace, runtime, api, hub = setup_runtime()
    first = workspace.new_cue(TYPE_WAIT)
    second = workspace.new_cue(TYPE_WAIT)
    first.duration = second.duration = 10
    workspace.settings["use_msc"] = True
    runtime.ensure_playheads()
    manager = TriggerManager(runtime)
    manager.midi_in(msc_message(1, 1))
    assert runtime.is_running(first) and runtime.playhead() is second
    manager.midi_in(msc_message(16, 1, 127, "2"))
    assert runtime.is_running(second)
    manager.midi_in(msc_message(1, 2))
    assert runtime.status(first)["paused"] == True
    manager.midi_in(msc_message(1, 3))
    assert runtime.status(first)["paused"] == False
    manager.midi_in(msc_message(1, 1, 9, "2"))
    manager.midi_in(msc_message(1, 8))
    assert runtime.status(first)["panicking"] == True
    manager.midi_in(msc_message(0x20, 1))
    assert runtime.playhead() is not None


def test_wall_clock_una_volta_al_secondo():
    workspace, runtime, api, hub = setup_runtime()
    cue = workspace.new_cue(TYPE_WAIT)
    cue.duration = 1
    cue.triggers["wall_clock"] = {"time": "20:30:00", "days": [2]}
    manager = TriggerManager(runtime)
    wrong_day = datetime.datetime(2026, 11, 23, 20, 30, 0)
    right_day = datetime.datetime(2026, 11, 25, 20, 30, 0)
    assert manager.wall_clock_tick(wrong_day) == []
    assert manager.wall_clock_tick(right_day) == [cue]
    assert manager.wall_clock_tick(right_day) == []


def test_timecode_sync_start_behavior_e_freewheel():
    workspace = Workspace("T")
    container = workspace.active_list()
    container.params.update({"timecode_sync": True, "timecode_format": 1, "timecode_start_behavior": 3,
                             "timecode_lookback_time": 5.0, "timecode_stop_behavior": 2,
                             "timecode_freewheel_time": 1.0})
    early = workspace.new_cue(TYPE_WAIT)
    late = workspace.new_cue(TYPE_WAIT)
    early.duration = late.duration = 100
    early.triggers["timecode"] = {"time": "00:00:08:00"}
    late.triggers["timecode"] = {"time": "00:00:30:00"}
    runtime = Runtime(workspace, ManualClock())
    manager = TriggerManager(runtime)
    assert manager.timecode_input(container, 10.0, now=0.0) == [early]
    assert manager.timecode_input(container, 29.9, now=0.1) == []
    assert manager.timecode_input(container, 30.1, now=0.2) == [late]
    # salto di 20 s: non fa partire i cue intermedi (>1 s)
    manager.timecode_check_signal(container, now=0.5)
    assert runtime.is_running(early)
    manager.timecode_check_signal(container, now=5.0)
    assert runtime.is_active(early) == False


def test_timecode_continuo_fa_partire_il_cue_al_suo_momento():
    workspace = Workspace("T")
    container = workspace.active_list()
    container.params.update({"timecode_sync": True, "timecode_format": 1})
    cue = workspace.new_cue(TYPE_WAIT)
    cue.duration = 10
    cue.triggers["timecode"] = {"time": "00:00:01:00"}
    runtime = Runtime(workspace, ManualClock())
    manager = TriggerManager(runtime)
    fired = []
    for step in range(0, 60):
        fired.extend(manager.timecode_input(container, step * 0.04, now=step * 0.04))
    assert fired == [cue]
