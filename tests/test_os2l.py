import socket
import time

from showsuite.light import project as pj
from showsuite.light.control.actions import ActionRunner
from showsuite.light.control.os2l import Os2lParser, Os2lServer, handle_message
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer
from showsuite.light.live import LiveCue


def mk():
    p = pj.Project("O"); p.patch.add(FixtureInstance("D", generic_dimmer(), 1, 1)); p.cues = [LiveCue("Go", ["D"])]
    e = LightEngine(p); return e, ActionRunner(e)


def test_parser_partial_and_concatenated():
    ps = Os2lParser()
    assert ps.feed(b'{"evt":"beat","bpm":128}{"evt":"b') == [{"evt": "beat", "bpm": 128}]
    assert ps.feed(b'tn","name":"Go"}\n') == [{"evt": "btn", "name": "Go"}]


def test_beat_sets_bpm_and_button_triggers():
    e, r = mk()
    handle_message(e, r, {"evt": "beat", "bpm": 128.0, "pos": 1})
    assert round(e.beat.bpm) == 128
    handle_message(e, r, {"evt": "btn", "name": "Go", "state": "on"}); assert "Go" in e.live.active
    handle_message(e, r, {"evt": "btn", "name": "Inesistente", "state": "on"})   # ignorato


def test_server_over_tcp():
    e, r = mk(); s = Os2lServer(e, r, port=0); s.start()
    try:
        c = socket.create_connection(("127.0.0.1", s.port)); c.sendall(b'{"evt":"beat","bpm":140}'); 
        for _ in range(50):
            if round(e.beat.bpm) == 140:
                break
            time.sleep(0.05)
        assert round(e.beat.bpm) == 140; c.close()
    finally:
        s.stop()
