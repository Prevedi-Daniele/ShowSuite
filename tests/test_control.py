import socket
import time

import pytest

from showsuite.light.control.actions import ActionRunner, ControlError
from showsuite.light.control.midi import MidiController, MidiMapping
from showsuite.light.control.osc import OscServer, build_osc, dispatch, parse_osc
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_rgb
from showsuite.light.live import LiveCue
from showsuite.light.preset import Preset


def setup():
    e = LightEngine()
    e.project.patch.add(FixtureInstance("Par 1", generic_rgb(), 1, 1))
    e.project.cues.append(LiveCue("Rosso", ["Par 1"], Preset("r", {"Red": 200})))
    return e, ActionRunner(e)


def test_osc_roundtrip_and_bundle():
    pkt = build_osc("/fixture/Par%201/Red", 0.5)
    assert parse_osc(pkt) == [("/fixture/Par%201/Red", [pytest.approx(0.5)])]
    assert parse_osc(build_osc("/tap")) == [("/tap", [])]
    inner = build_osc("/blackout", True)
    bundle = b"#bundle\x00" + b"\x00" * 8 + len(inner).to_bytes(4, "big") + inner
    assert parse_osc(bundle) == [("/blackout", [True])]
    for bad in (b"", b"garbage", b"/x\x00\x00,i\x00\x00\x00"):
        with pytest.raises(ValueError):
            parse_osc(bad)


def test_dispatch_actions():
    e, r = setup()
    dispatch(r, "/fixture/Par%201/Red", [0.5]); e.live.update()
    assert e.mixer.render(1)[0] == 128   # round(0.5*255)
    dispatch(r, "/cue/Rosso", [1.0]); e.live.update()
    assert "Rosso" in e.live.active
    dispatch(r, "/cue/1", []);  # toggle: spegne
    assert e.live.active["Rosso"]["releasing"]
    dispatch(r, "/master", [0.25]); assert e.grand_master == 0.25
    dispatch(r, "/bpm", [128]); assert e.beat.bpm == pytest.approx(128, abs=0.01)
    dispatch(r, "/blackout", [True]); assert e.blackout
    dispatch(r, "/blind", [0]); assert not e.blind
    for bad in ("/nope", "/cue/Inesistente", "/fixture/X/Red", "/fixture/Par%201/Boh"):
        with pytest.raises((ControlError, KeyError)):
            dispatch(r, bad, [1])


def test_osc_server_udp_and_bad_packets():
    e, r = setup()
    s = OscServer(r, port=0, host="127.0.0.1"); s.start()
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        c.sendto(b"\xff\xfe", ("127.0.0.1", s.port))               # spazzatura: il server resta vivo
        c.sendto(build_osc("/master", 0.5), ("127.0.0.1", s.port))
        for _ in range(50):
            if e.grand_master == pytest.approx(0.5):
                break
            time.sleep(0.02)
        assert e.grand_master == pytest.approx(0.5) and s.errors
    finally:
        s.stop()


def test_midi_learn_and_run():
    e, r = setup()
    m = MidiController(r)
    got = []
    m.on_learned = got.append
    m.learn("cue", {"cue": "Rosso"})
    m.handle("note_on", 9, 36, 100)            # pad: impara
    assert got and got[0].key() == ("note", 9, 36) and not m.learning
    m.handle("note_on", 9, 36, 100)            # ora esegue: toggle on
    assert "Rosso" in e.live.active
    m.learn("master"); m.handle("cc", 0, 74, 64)
    m.handle("cc", 0, 74, 127); assert e.grand_master == 1.0
    m.handle("cc", 0, 74, 0); assert e.grand_master == 0.0
    # rilearn sullo stesso controllo sostituisce la mappatura
    m.learn("blackout"); m.handle("cc", 0, 74, 5)
    assert sum(1 for x in m.mappings if x.key() == ("cc", 0, 74)) == 1


def test_midi_unknown_cue_does_not_crash():
    e, r = setup()
    m = MidiController(r, [MidiMapping("note", 0, 1, "cue", {"cue": "Boh"})])
    m.handle("note_on", 0, 1, 100)
    assert m.errors


def test_midi_mappings_saved_in_project(tmp_path):
    from showsuite.light import project as pj
    p = pj.Project("M"); p.osc_port = 9000
    p.midi_mappings.append(MidiMapping("cc", 0, 74, "master"))
    f = tmp_path / "m.showsuite-light"; pj.save(p, str(f))
    q = pj.load(str(f))
    assert q.osc_port == 9000 and q.midi_mappings[0].action == "master"


def test_control_log_midi_osc_dmx():
    from showsuite.light.control.actions import ActionRunner
    from showsuite.light.control.log import ControlLog
    from showsuite.light.control.midi import MidiController
    from showsuite.light.engine import LightEngine
    e = LightEngine(); r = ActionRunner(e); log = ControlLog()
    m = MidiController(r); m.log = log
    m.handle("cc", 0, 7, 100)                      # nessuna associazione
    m.learn("master"); m.handle("cc", 0, 7, 100)   # learn
    m.handle("cc", 0, 7, 127)                      # eseguita
    st = [x.status for x in log.snapshot("midi")]
    assert st == ["info", "learn", "ok"] and "CC 7" in log.snapshot("midi")[0].message
    assert log.snapshot("osc") == []
    log.paused = True; m.handle("cc", 0, 7, 1); assert len(log.snapshot()) == 3
    log.paused = False; log.clear(); assert log.snapshot() == []


def test_monitor_windows_smoke():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from showsuite.light.control.log import ControlLog
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    from showsuite.ui.monitor_windows import ControlLogWindow, DmxMonitor
    global _APP
    _APP = QApplication.instance() or QApplication([])      # resta viva fino a fine processo (evita crash allo spegnimento)
    e = LightEngine(); e.project.patch.add(FixtureInstance("A", generic_rgb(), 1, 5))
    e.set_value("A", "Red", 200)
    mon = DmxMonitor(e, ["A"])
    assert mon.table.rowCount() == 3 and mon.table.item(0, 0).text() == "5" and mon.table.item(0, 3).text() == "200"
    log = ControlLog(); log.add("midi", "X", "Channel 0: CC 7 (1)", "ok")
    w = ControlLogWindow(log); assert w.table.rowCount() == 1
    mon.close(); w.close(); mon.deleteLater(); w.deleteLater()


def test_midi_shift_and_inverted(tmp_path):
    from showsuite.light import project as pj
    e, r = setup()
    m = MidiController(r)
    m.learn("shift"); m.handle("note_on", 0, 10, 127)            # tasto Shift
    m.handle("note_off", 0, 10, 0)
    m.learn("master"); m.handle("cc", 0, 1, 5)                   # senza shift
    m.handle("note_on", 0, 10, 127)                              # tieni Shift
    m.learn("blackout"); m.handle("cc", 0, 1, 5)                 # stesso CC ma con shift
    assert [(x.action, x.shift) for x in m.mappings if x.key() == ("cc", 0, 1)] == [("master", False), ("blackout", True)]
    m.handle("cc", 0, 1, 127); assert e.blackout is True and e.grand_master == 1.0   # con shift: solo blackout
    m.handle("note_off", 0, 10, 0)
    m.handle("cc", 0, 1, 0); assert e.grand_master == 0.0                            # rilasciato: master
    mm = next(x for x in m.mappings if x.action == "master"); mm.inverted = True
    m.handle("cc", 0, 1, 0); assert e.grand_master == 1.0
    p = pj.Project("M"); p.midi_mappings = list(m.mappings)
    q = pj.loads(pj.dumps(p)); assert any(x.shift for x in q.midi_mappings) and any(x.inverted for x in q.midi_mappings)


def test_lightkey_style_osc_addresses():
    from showsuite.light import project as pj
    from showsuite.light.control.osc import dispatch, match_names
    from showsuite.light.live import CueList, CueListStep, LiveButton, LivePage
    e, r = setup()
    assert match_names("Par_{1,3}", ["Par 1", "Par 2", "Par 3"]) == ["Par 1", "Par 3"]
    assert match_names("P?r_*", ["Par 1", "Led 1"]) == ["Par 1"]
    cue = e.project.cues[0].name
    e.project.pages = [LivePage("Main Page", [LiveButton(cue)], cuelist=CueList("CL", [CueListStep(cue)]))]
    base = f"/live/Main_Page/cue/{cue.replace(' ', '_')}"
    dispatch(r, base + "/activate", []); assert cue in e.live.active
    dispatch(r, base + "/deactivate", []); assert e.live.active[cue]["releasing"]
    dispatch(r, base + "/toggle", []); assert not e.live.active[cue]["releasing"]
    sel = []; r.on_select_page = sel.append
    dispatch(r, "/live/Main_Page/select", []); assert sel == ["Main Page"]
    dispatch(r, "/live/Main_Page/cuelist/start", []); assert e.live.current_step(e.project.pages[0].cuelist) == 1
    dispatch(r, "/output/master", [0.25]); assert e.grand_master == 0.25
    dispatch(r, "/output/freeze", [1]); assert e.freeze
    dispatch(r, "/beat/tempo", [140.0]); assert round(e.beat.bpm) == 140
    dispatch(r, "/beat/double", []); assert round(e.beat.bpm) == 280
    fx = e.project.patch.fixtures[0].name.replace(" ", "_")
    dispatch(r, f"/fixture/{fx}/overrides/dimmer", [1.0]); assert e.values
    dispatch(r, f"/fixture/{fx}/clear", []); assert not e.values.get(e.project.patch.fixtures[0].name)
    import pytest
    from showsuite.light.control.actions import ControlError
    with pytest.raises(ControlError):
        dispatch(r, "/live/Nessuna/select", [])
