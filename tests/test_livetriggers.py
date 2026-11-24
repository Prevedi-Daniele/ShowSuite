import os
from showsuite.light.control import livetriggers as lt
from showsuite.light.control.actions import ActionRunner
from showsuite.light.control.midi import MidiController
from showsuite.light.engine import LightEngine
from showsuite.light.live import LiveButton, LiveCue, LivePage, interp_curve
from showsuite.light.fixtures.profile import FixtureInstance, generic_rgb
from showsuite.light import project as pj


def make():
    e = LightEngine()
    e.project.patch.add(FixtureInstance("L1", generic_rgb(), 1, 1))
    e.project.cues = [LiveCue("A", ["L1"]), LiveCue("B", ["L1"]), LiveCue("C", ["L1"])]
    e.project.cues[2].no_trigger = True
    e.project.pages = [LivePage("P1", [LiveButton("A"), LiveButton("B")]), LivePage("P2", [LiveButton("C"), LiveButton("A")])]
    return e


def test_bindings_skip_excluded():
    e = make(); b = lt.bindings(e.project)
    assert [(x["page_index"], x["note"], x["cue"]) for x in b] == [(0, 0, "A"), (0, 1, "B"), (1, 0, "A")]


def test_midi_channel16_triggers_cue_and_page():
    e = make(); r = ActionRunner(e); pages = []; r.on_select_page = pages.append
    m = MidiController(r)
    m.handle("note_on", 15, 1, 1)          # pagina 1, nota 1 = B
    assert "B" in e.live.active and pages == ["P1"]
    m.handle("note_on", 15, 0, 2)          # pagina 2, nota 0 = A (C escluso)
    assert pages[-1] == "P2"
    m.handle("cc", 15, 0, 2); assert pages[-1] == "P2"
    m.handle("cc", 15, 1, 127); assert e.blackout is True


def test_disabled_live_triggers_ignored():
    e = make(); m = MidiController(ActionRunner(e)); m.live_triggers = False
    m.handle("note_on", 15, 0, 1); assert not e.live.active


def test_export_clips(tmp_path):
    import pytest; pytest.importorskip("mido")
    e = make(); files = lt.export_clips(e.project, str(tmp_path))
    assert len(files) == 3 + 2 + 6 and all(os.path.exists(f) for f in files)


def test_custom_curve_and_roundtrip():
    assert interp_curve([(0.5, 0.1)], 0.5) == 0.1 and interp_curve([], 0.3) == 0.3
    e = make(); c = e.project.cues[0]
    c.curve = "custom"; c.curve_points = [(0.5, 0.1)]; c.mods = {"pan": 30.0, "fade_time": 2.0}; c.no_trigger = True
    p2 = pj.loads(pj.dumps(e.project)); c2 = p2.cues[0]
    assert c2.curve_points == [(0.5, 0.1)] and c2.mods == c.mods and c2.no_trigger


def test_modifiers_apply():
    e = make(); c = e.project.cues[0]
    c.preset = None
    from showsuite.light.preset import Preset
    c.preset = Preset("x", {("L1", "Red"): 200, ("L1", "Green"): 100, ("L1", "Blue"): 50}) if False else None
    out = e.live._apply_mods([("L1", "Red", 100), ("L1", "Green", 100), ("L1", "Blue", 100)], {"color_temp": 5000})
    d = {(f, ch): v for f, ch, v in out}
    assert d[("L1", "Red")] > d[("L1", "Blue")]


def test_popover_modifiers_and_curve_editor(qapp=None):
    from showsuite.ui.button_popover import ButtonPopover
    from showsuite.ui.curve_editor import CurveWidget
    e = make(); c = e.project.cues[0]
    class V:  # vista minima
        pass
    from PySide6.QtWidgets import QWidget
    pop = ButtonPopover(QWidget(), e.project.pages[0].buttons[0], c)
    pop.mod_widgets["pan"].setValue(40); pop.mod_widgets["zoom"].setValue(50); pop.excl.setChecked(True)
    assert c.mods == {"pan": 40.0, "zoom": 0.5} and c.no_trigger
    pop.mod_widgets["pan"].setValue(0); assert "pan" not in c.mods
    w = CurveWidget([(0.5, 0.2)]); assert w.points == [[0.5, 0.2]]
