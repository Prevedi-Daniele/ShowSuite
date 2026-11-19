import pytest

from showsuite.light import project as pj
from showsuite.light.fixtures import FixtureInstance, generic_rgb


def test_roundtrip(tmp_path):
    p = pj.Project("Prova")
    p.patch.add(FixtureInstance("Par 1", generic_rgb(), 1, 1, 0.2, 0.8))
    p.outputs.append(pj.OutputConfig("artnet", 1, {"host": "10.0.0.5"}))
    f = tmp_path / "a.showsuite-light"
    pj.save(p, str(f))
    q = pj.load(str(f))
    assert q.name == "Prova" and q.patch.find("Par 1").x == 0.2
    assert q.patch.find("Par 1").profile.footprint == 3
    assert q.outputs[0].params["host"] == "10.0.0.5"


def test_bad_version(tmp_path):
    import json, zipfile
    f = tmp_path / "b.showsuite-light"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("project.json", json.dumps({"schema_version": 99}))
    with pytest.raises(ValueError):
        pj.load(str(f))


def test_output_build_types():
    assert pj.OutputConfig("sacn", 1).build() is not None
    with pytest.raises(ValueError):
        pj.OutputConfig("boh", 1).build()


def test_roundtrip_cues_palettes_and_v1(tmp_path):
    import json, zipfile
    from showsuite.light.effects import Effect
    from showsuite.light.live import LiveCue
    from showsuite.light.preset import Palette, Preset
    p = pj.Project("C")
    p.patch.add(FixtureInstance("A", generic_rgb(), 1, 1))
    p.palettes.append(Palette("Colori", [Preset("Rosso", {"Red": 255})]))
    p.cues.append(LiveCue("Chase", ["A"], Preset("x", {"Blue": 9}), [Effect("Red", "saw", fan=0.5)],
                          fade_in=1.5, curve="s_curve", priority=20))
    f = tmp_path / "c.showsuite-light"
    pj.save(p, str(f))
    q = pj.load(str(f))
    assert q.palettes[0].get("Rosso").values == {"Red": 255}
    c = q.cues[0]
    assert c.fade_in == 1.5 and c.curve == "s_curve" and c.effects[0].fan == 0.5 and c.preset.values == {"Blue": 9}
    # file v1 (senza palette/cue) ancora leggibile
    f1 = tmp_path / "v1.showsuite-light"
    with zipfile.ZipFile(f1, "w") as z:
        z.writestr("project.json", json.dumps({"schema_version": 1, "name": "Old", "fixtures": [], "outputs": []}))
    assert pj.load(str(f1)).cues == []


def test_sequence_roundtrip(tmp_path):
    from showsuite.light.live import LiveCue
    from showsuite.light.preset import Preset
    p = pj.Project("S")
    p.cues.append(LiveCue("Seq", ["A"], steps=[Preset("a", {"Red": 1}), Preset("b", {"Red": 2})],
                          beats_per_step=0.5, crossfade=0.25, loop=False))
    f = tmp_path / "s.showsuite-light"
    pj.save(p, str(f))
    c = pj.load(str(f)).cues[0]
    assert [x.values["Red"] for x in c.steps] == [1, 2] and c.beats_per_step == 0.5 and not c.loop


def test_pages_and_fixture_beam_roundtrip(tmp_path):
    from showsuite.light.live import LiveButton, LiveCue, LivePage
    p = pj.Project("Pg")
    p.patch.add(FixtureInstance("A", generic_rgb(), 1, 1, rotation=45.0, beam_angle=12.0, hide_beam=True))
    p.cues.append(LiveCue("C", ["A"]))
    p.pages.append(LivePage("Scene", [LiveButton("C", "flash", "#ff0000", "Rosso")], priority=3, fade_time=1.5))
    f = tmp_path / "pg.showsuite-light"; pj.save(p, str(f)); q = pj.load(str(f))
    a = q.patch.find("A")
    assert (a.rotation, a.beam_angle, a.hide_beam) == (45.0, 12.0, True)
    pg = q.pages[0]
    assert pg.priority == 3 and pg.buttons[0].mode == "flash" and pg.buttons[0].label == "Rosso"


def test_old_project_gets_default_page(tmp_path):
    import json, zipfile
    from showsuite.light.live import LiveCue
    p = pj.Project("Old"); p.cues.append(LiveCue("X", []))
    f = tmp_path / "o.showsuite-light"; pj.save(p, str(f))
    with zipfile.ZipFile(f) as z:
        doc = json.loads(z.read("project.json"))
    doc.pop("pages")
    g = tmp_path / "o2.showsuite-light"
    with zipfile.ZipFile(g, "w") as z:
        z.writestr("project.json", json.dumps(doc))
    assert pj.load(str(g)).pages[0].buttons[0].cue == "X"
