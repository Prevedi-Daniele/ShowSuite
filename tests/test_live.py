import pytest

from showsuite.light.beat import BeatClock
from showsuite.light.effects import Effect
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_dimmer, generic_rgb
from showsuite.light.live import LiveCue
from showsuite.light.preset import Preset


class Clock:
    t = 0.0
    def __call__(self): return self.t


def test_tap_tempo():
    c = Clock(); b = BeatClock(100, c)
    for _ in range(5):
        b.tap(); c.t += 0.5
    assert b.bpm == pytest.approx(120, abs=0.5)
    with pytest.raises(ValueError):
        b.set_bpm(5)


def test_effect_waves_and_fan():
    e = Effect("Dimmer", "square", beats_per_cycle=1)
    assert e.value(0.0) == 255 and e.value(0.6) == 0
    e = Effect("Dimmer", "saw", fan=1.0)
    v = e.evaluate(["a", "b", "c", "d"], 0.0)
    assert [v[k] for k in "abcd"] == [0, 64, 128, 191]
    with pytest.raises(ValueError):
        Effect("Dimmer", "boh").value(0)


def make():
    c = Clock()
    e = LightEngine(now=c)
    for i in range(2):
        e.project.patch.add(FixtureInstance(f"P{i}", generic_rgb(), 1, 1 + 3 * i))
    return e, c


def test_cue_fade_and_release():
    e, c = make()
    cue = LiveCue("Rosso", ["P0", "P1"], Preset("r", {"Red": 200}), fade_in=2.0, fade_out=1.0)
    e.live.trigger(cue)
    e.live.update(); assert e.mixer.render(1)[0] == 0
    c.t = 1.0; e.live.update(); assert e.mixer.render(1)[0] == 100
    c.t = 2.0; e.live.update(); assert e.mixer.render(1)[0] == 200 and e.mixer.render(1)[3] == 200
    e.live.trigger(cue)  # toggle: release
    c.t = 2.5; e.live.update(); assert e.mixer.render(1)[0] == 100
    c.t = 4.0; e.live.update(); assert e.mixer.render(1)[0] == 0 and not e.live.active


def test_priority_and_skip_missing_channel():
    e, c = make()
    e.project.patch.add(FixtureInstance("D", generic_dimmer(), 1, 10))
    low = LiveCue("low", ["P0"], Preset("a", {"Red": 50}), priority=5)
    high = LiveCue("high", ["P0", "D"], Preset("b", {"Red": 250}), priority=20)  # D non ha Red
    e.live.trigger(low); e.live.trigger(high); e.live.update()
    assert e.mixer.render(1)[0] == 250 and e.mixer.render(1)[9] == 0
    e.live.trigger(high); e.live.update()
    assert e.mixer.render(1)[0] == 50


def test_effect_cue_follows_beat():
    e, c = make()
    e.beat.set_bpm(60)  # 1 battuta al secondo
    cue = LiveCue("chase", ["P0", "P1"], effects=[Effect("Red", "saw", fan=0.5)])
    e.live.trigger(cue)
    c.t = 0.5; e.live.update()
    out = e.mixer.render(1)
    assert out[0] == 128 and out[3] == round(255 * 0.75)


def test_sequence_steps_crossfade_and_loop():
    from showsuite.light.preset import Preset as P
    e, c = make()
    e.beat.set_bpm(60)
    seq = LiveCue("Seq", ["P0"], steps=[P("a", {"Red": 100}), P("b", {"Red": 200})],
                  beats_per_step=2.0, crossfade=0.5)
    e.live.trigger(seq)
    c.t = 0.5; e.live.update(); assert e.mixer.render(1)[0] == 100    # step 1
    c.t = 1.5; e.live.update(); assert e.mixer.render(1)[0] == 150    # a metà del crossfade
    c.t = 2.5; e.live.update(); assert e.mixer.render(1)[0] == 200    # step 2
    c.t = 4.5; e.live.update(); assert e.mixer.render(1)[0] == 100    # loop
    seq2 = LiveCue("Once", ["P1"], steps=[P("a", {"Red": 10}), P("b", {"Red": 20})],
                   beats_per_step=1.0, loop=False)
    e.live.trigger(seq2)
    c.t = 20; e.live.update(); assert e.mixer.render(1)[3] == 20      # resta sull'ultimo


def test_blind_hides_programmer_from_output():
    e, c = make()
    e.set_value("P0", "Red", 200)
    e.blind = True
    assert e.render_output(1)[0] == 0 and e.mixer.render(1)[0] == 200  # preview sì, uscita no
    e.blind = False
    assert e.render_output(1)[0] == 200


def test_page_priority_and_flash_start():
    e, c = make()
    lo = LiveCue("lo", ["P0"], Preset("a", {"Red": 50}), priority=90)
    hi = LiveCue("hi", ["P0"], Preset("b", {"Red": 250}), priority=1)
    e.live.trigger(lo, page_priority=0); e.live.trigger(hi, page_priority=1); e.live.update()
    assert e.mixer.render(1)[0] == 250          # pagina 1 batte pagina 0 anche con priorità cue più bassa
    e.live.release(hi); c.t = 1; e.live.update()
    assert e.mixer.render(1)[0] == 50
    f = LiveCue("f", ["P1"], Preset("c", {"Red": 90}), fade_out=0.0)
    e.live.start(f); e.live.start(f)            # start non fa toggle
    e.live.update(); assert e.mixer.render(1)[3] == 90 and not e.live.active["f"]["releasing"]
    e.set_value("P0", "Red", 7)
    assert e.mixer.render(1)[0] == 7            # il programmer vince su tutto


def _cl_engine():
    from showsuite.light.fixtures import ChannelDef, FixtureProfile
    from showsuite.light.live import CueList, CueListStep, LivePage
    e, c = make()
    mover = FixtureProfile("X", "M", "m", (ChannelDef("Dimmer", kind="intensity"), ChannelDef("Pan")))
    e.project.patch.add(FixtureInstance("M", mover, 1, 20))
    e.project.cues += [LiveCue("A", ["P0"], Preset("a", {"Red": 100})),
                       LiveCue("B", ["P0"], Preset("b", {"Red": 200})),
                       LiveCue("C", ["P0"], Preset("c", {"Green": 50}))]
    cl = CueList("L", [CueListStep("A", hold=None, fade=0.0),
                       CueListStep("B", hold=1.0, fade=2.0),
                       CueListStep("C", skip=True),
                       CueListStep("A", hold=None)])
    e.project.pages.append(LivePage("p", cuelist=cl))
    return e, c, cl


def test_cuelist_go_crossfade_auto_follow_skip_loop():
    e, c, cl = _cl_engine()
    assert e.live.go(cl) and e.live.current_step(cl) == 1
    e.live.update(); assert e.mixer.render(1)[0] == 100
    e.live.go(cl)                                   # step 2: crossfade A->B in 2s
    c.t = 1.0; e.live.update()
    assert e.mixer.render(1)[0] == 100   # a metà: B (200*0.5) ha la precedenza su A (100*0.5)
    c.t = 2.0; e.live.update()
    assert e.mixer.render(1)[0] == 200 and "A" not in e.live.active
    # auto-follow: hold 1s dopo il fade (t=2+1) -> salta lo step skip e va al 4
    c.t = 3.1; e.live.update()
    assert e.live.current_step(cl) == 4
    c.t = 10; e.live.update()                        # step 4 ha hold manuale: resta
    assert e.live.current_step(cl) == 4
    assert e.live.go(cl) is False and e.live.current_step(cl) is None   # fine lista, senza loop
    e.live.update(); c.t = 11; e.live.update()
    assert e.mixer.render(1)[0] == 0
    cl.loop = True
    e.live.go(cl); assert e.live.current_step(cl) == 1
    e.live.goto(cl, 3)                               # goto entra anche negli step skip
    assert e.live.current_step(cl) == 3
    import pytest as _p
    with _p.raises(IndexError):
        e.live.goto(cl, 9)


def test_cuelist_same_cue_continuity_and_stop():
    from showsuite.light.live import CueList, CueListStep
    e, c, cl = _cl_engine()
    same = CueList("S", [CueListStep("A"), CueListStep("A")])
    e.project.pages[0].cuelist = same
    e.live.go(same); t0 = e.live.active["A"]["t0"]
    c.t = 5.0; e.live.go(same)
    assert e.live.active["A"]["t0"] == t0           # nessun riavvio tra step con lo stesso cue
    e.live.stop_cuelist(same); e.live.update(); c.t = 6; e.live.update()
    assert not e.live.active


def test_fade_only_scales_intensity_not_position():
    e, c, cl = _cl_engine()
    cue = LiveCue("Mv", ["M"], Preset("m", {"Dimmer": 200, "Pan": 180}), fade_in=2.0)
    e.live.trigger(cue); c.t = 1.0; e.live.update()
    out = e.mixer.render(1)
    assert out[19] == 100 and out[20] == 180        # dimmer a metà fade, pan già in posizione


def test_modifiers_speed_and_dimmer():
    e, c, cl = _cl_engine()
    e.beat.set_bpm(60)
    cue = LiveCue("W", ["P0"], effects=[Effect("Red", "saw")], speed=2.0, dimmer=0.5)
    e.live.trigger(cue)
    c.t = 0.25; e.live.update()
    # saw a velocità doppia: fase 0.5 -> 128, poi dimmer 0.5 sul colore (fixture RGB senza dimmer)
    assert e.mixer.render(1)[0] == round(128 * 0.5)
    cue.speed = 1.0                                   # cambio velocità senza salti di fase
    c.t = 0.5; e.live.update()
    assert e.mixer.render(1)[0] == round(round(255 * 0.75) * 0.5)


def test_cuelist_roundtrip(tmp_path):
    from showsuite.light import project as pj
    e, c, cl = _cl_engine()
    e.project.cues[0].speed = 1.5
    f = tmp_path / "cl.showsuite-light"; pj.save(e.project, str(f)); q = pj.load(str(f))
    got = q.pages[0].cuelist
    assert [s.cue for s in got.steps] == ["A", "B", "C", "A"] and got.steps[2].skip and got.steps[1].hold == 1.0
    assert q.cues[0].speed == 1.5


def test_live_cue_position_and_color_effects(tmp_path):
    from showsuite.light import project as pj
    from showsuite.light.colorfx import ColorEffect
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance
    from showsuite.light.fixtures.ofl import parse_ofl
    from showsuite.light.live import LiveCue
    from showsuite.light.posfx import PositionEffect
    (prof,) = parse_ofl({"name": "M", "availableChannels": {
        "Pan": {"capability": {"type": "Pan"}}, "Tilt": {"capability": {"type": "Tilt"}},
        "R": {"capability": {"type": "ColorIntensity", "color": "Red"}},
        "G": {"capability": {"type": "ColorIntensity", "color": "Green"}},
        "B": {"capability": {"type": "ColorIntensity", "color": "Blue"}}},
        "modes": [{"name": "m", "channels": ["Pan", "Tilt", "R", "G", "B"]}]}, "X")
    t = [0.0]
    e = LightEngine(now=lambda: t[0]); e.project.patch.add(FixtureInstance("M1", prof, 1, 1))
    cue = LiveCue("fx", ["M1"], color_fx=ColorEffect(swatches=[(255, 0, 0), (0, 0, 255)], duration=4.0, time_offset=0.0),
                  position_fx=PositionEffect("Pan Track", 4.0, time_offset=0.0), fade_in=0.0)
    e.project.cues.append(cue); e.live.trigger(cue)
    e.live.update(); d = e.mixer.render(1)
    assert d[0] == 128 and d[2] == 255 and d[4] == 0          # pan al centro, rosso
    t[0] = 1.0; e.live.update()                               # 120 BPM: 2 battute = 1 s... un quarto di ciclo
    d = e.mixer.render(1)
    assert d[0] > 230 and d[2] < 255                           # pan al massimo, colore in dissolvenza
    f = tmp_path / "p.showsuite-light"; pj.save(e.project, str(f)); q = pj.load(str(f))
    c2 = q.cues[0]
    assert c2.position_fx.pattern == "Pan Track" and c2.color_fx.swatches == [(255, 0, 0), (0, 0, 255)]


def test_fader_and_exclusive_group_and_save(tmp_path):
    from showsuite.light import project as pj
    from showsuite.light.engine import LightEngine
    from showsuite.light.fixtures import FixtureInstance, generic_rgb
    from showsuite.light.live import LiveButton, LiveCue, LivePage
    from showsuite.light.preset import Preset
    t = [0.0]
    e = LightEngine(now=lambda: t[0]); e.project.patch.add(FixtureInstance("P", generic_rgb(), 1, 1))
    red = LiveCue("R", ["P"], Preset("r", {"Red": 200}), fade_in=1.0, fade_out=1.0, toggle=True)
    blue = LiveCue("B", ["P"], Preset("b", {"Blue": 200}), fade_in=1.0, fade_out=1.0, toggle=True)
    e.project.cues += [red, blue]
    e.live.trigger_exclusive(red, [red, blue]); t[0] = 1.0; e.live.update()
    assert e.mixer.render(1)[0] == 200
    e.live.trigger_exclusive(blue, [red, blue]); t[0] = 1.5; e.live.update()
    d = e.mixer.render(1); assert 90 <= d[0] <= 110 and 90 <= d[2] <= 110      # crossfade a metà
    t[0] = 3.0; e.live.update(); d = e.mixer.render(1); assert d[0] == 0 and d[2] == 200
    # fader
    green = LiveCue("G", ["P"], Preset("g", {"Green": 200}))
    e.live.set_fader(green, 0.5); e.live.update(); assert e.mixer.render(1)[1] == 100
    e.live.set_fader(green, 0.0); e.live.update(); assert e.mixer.render(1)[1] == 0
    # persistenza cornici/tipo/gruppo
    e.project.pages = [LivePage("P1", [LiveButton("R", frame=0, group="f0"), LiveButton("G", frame=1, kind="fader")],
                                frames=["Colori", "Dimmer"])]
    f = tmp_path / "x.showsuite-light"; pj.save(e.project, str(f)); q = pj.load(str(f))
    pg = q.pages[0]
    assert pg.frames == ["Colori", "Dimmer"] and pg.buttons[1].kind == "fader" and pg.buttons[0].group == "f0"


def test_duplicate_button_and_text(tmp_path):
    from showsuite.light import project as pj
    from showsuite.light.live import LiveButton, LiveCue, LivePage, duplicate_button
    p = pj.Project("D"); p.cues = [LiveCue("A", ["x"])]
    pg = LivePage("P", [LiveButton("A"), LiveButton("", label="Titolo", kind="text")]); p.pages = [pg]
    n = duplicate_button(p, pg, pg.buttons[0]); n2 = duplicate_button(p, pg, pg.buttons[0])
    assert n.cue == "A copia" and n2.cue == "A copia 2" and len(p.cues) == 3
    f = tmp_path / "d.showsuite-light"; pj.save(p, str(f)); q = pj.load(str(f))
    assert [b.kind for b in q.pages[0].buttons].count("text") == 1


def test_manual_crossfade_and_paste_between_pages():
    from showsuite.light import project as pj
    from showsuite.light.engine import LightEngine
    from showsuite.light.live import LiveButton, LiveCue, LivePage, paste_button
    p = pj.Project("X"); p.cues = [LiveCue("A", []), LiveCue("B", [])]
    e = LightEngine(p)
    e.live.crossfade(p.cues[0], p.cues[1], 0.25)
    assert e.live.active["A"]["fader"] == 0.75 and e.live.active["B"]["fader"] == 0.25
    e.live.crossfade(p.cues[0], p.cues[1], 1.0); assert "A" not in e.live.active
    p1, p2 = LivePage("1", [LiveButton("A")]), LivePage("2")
    n = paste_button(p, p1, p1.buttons[0], p2, frame=0)
    assert p2.buttons == [n] and n.cue == "A copia" and len(p1.buttons) == 1 and len(p.cues) == 3
