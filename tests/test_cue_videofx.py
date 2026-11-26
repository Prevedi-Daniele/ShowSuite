import json

import numpy as np
import pytest

from showsuite.cue import videofx
from showsuite.cue.model import TYPE_VIDEO
from tests.test_cue_osc import last_reply, make_api


def solid(red, green, blue, size=8):
    frame = np.zeros((size, size, 4), dtype=np.uint8)
    frame[..., 0], frame[..., 1], frame[..., 2], frame[..., 3] = red, green, blue, 255
    return frame


def run(name, frame, **parameters):
    effect = videofx.new_effect(name)
    for key, value in parameters.items():
        videofx.set_parameter(effect, key, value)
    return videofx.apply_effects(frame, [effect])


def test_effetto_sconosciuto_e_parametro_sconosciuto():
    with pytest.raises(ValueError):
        videofx.new_effect("Kaleidoscope")
    with pytest.raises(ValueError):
        videofx.set_parameter(videofx.new_effect("Gamma"), "nope", 1)


def test_valori_predefiniti_non_cambiano_il_frame():
    frame = solid(100, 150, 200)
    for name in ("ColorControls", "Exposure", "Gamma", "Vibrance", "ColorClamp", "ColorMatrix", "Shutter", "Window"):
        assert np.array_equal(run(name, frame), frame), name


def test_colori():
    frame = solid(100, 150, 200)
    assert run("MinMaxInvert", frame)[0, 0, 0] == 155
    assert run("MinMaxInvert", frame, Choose_Effect=0)[0, 0, 0] == 100
    assert run("MinMaxInvert", frame, Choose_Effect=1)[0, 0, 0] == 200
    assert run("Exposure", frame, inputEV=1.0)[0, 0, 0] == 200
    assert run("ColorControls", frame, inputSaturation=0.0)[0, 0, 0] == run("ColorControls", frame, inputSaturation=0.0)[0, 0, 2]
    assert run("ColorControls", frame, inputBrightness=1.0)[0, 0, 0] == 255
    assert run("ColorThreshold", frame, inputThreshold=0.9)[0, 0, 0] == 0
    assert run("ColorThreshold", frame, inputThreshold=0.1)[0, 0, 0] == 255
    assert run("ColorClamp", frame, Max_R=0.2)[0, 0, 0] == 51
    swapped = run("ColorMatrix", frame, R_R=0.0, R_B=1.0, B_B=0.0, B_R=1.0)
    assert swapped[0, 0, 0] == 200 and swapped[0, 0, 2] == 100
    assert run("ColorPosterize", frame, inputLevels=2.0)[0, 0, 0] in (0, 255)


def test_sepia_e_monochrome():
    frame = solid(100, 150, 200)
    sepia = run("SepiaMonochrome", frame)
    assert sepia[0, 0, 0] > sepia[0, 0, 2]
    mono = run("SepiaMonochrome", frame, Choose_Effect=1, inputColor=[1, 1, 1, 1])
    assert mono[0, 0, 0] == mono[0, 0, 1] == mono[0, 0, 2]


def test_blur_pixellate_e_sharpen():
    frame = solid(0, 0, 0, 16)
    frame[8, 8, :3] = 255
    blurred = run("BoxDiscGaussianBlur", frame, inputRadius=3.0)
    assert blurred[8, 8, 0] < 255 and blurred[8, 9, 0] > 0
    for mode in (0, 1):
        assert run("BoxDiscGaussianBlur", frame, Choose_Blur=mode, inputRadius=2.0)[8, 9, 0] > 0
    assert run("BoxDiscGaussianBlur", frame, inputRadius=0.0).tolist() == frame.tolist()
    assert run("MotionBlur", frame, inputRadius=3.0)[8, 10, 0] > 0
    pixel = run("Pixellation", frame, inputScale=4.0)
    assert pixel[8, 8, 0] == pixel[9, 9, 0]
    assert run("SharpenLuminance", blurred, inputSharpness=1.0)[8, 8, 0] >= blurred[8, 8, 0]
    assert run("UnsharpMask", blurred)[8, 8, 0] >= blurred[8, 8, 0]


def test_shutter_e_window_agiscono_sull_alpha():
    frame = solid(10, 10, 10, 10)
    shutter = run("Shutter", frame, Right=0.5)
    assert shutter[5, 2, 3] == 255 and shutter[5, 8, 3] == 0
    ellipse = run("Shutter", frame, Shape=1)
    assert ellipse[5, 5, 3] == 255 and ellipse[0, 0, 3] == 0
    window = run("Window", frame, Size_W=0.5, Size_H=0.5)
    assert window[9, 2, 3] == 255 and window[0, 2, 3] == 0
    feather = run("Shutter", frame, Right=0.5, Feather=6.0)
    assert 0 < feather[5, 5, 3] < 255


def test_effetti_disabilitati_e_ordine():
    frame = solid(100, 100, 100)
    invert = videofx.new_effect("MinMaxInvert")
    invert["enabled"] = False
    assert np.array_equal(videofx.apply_effects(frame, [invert]), frame)
    invert["enabled"] = True
    exposure = videofx.new_effect("Exposure")
    videofx.set_parameter(exposure, "inputEV", 1.0)
    assert videofx.apply_effects(frame, [invert, exposure])[0, 0, 0] == 255
    assert videofx.apply_effects(frame, [exposure, invert])[0, 0, 0] == 55
    assert np.array_equal(videofx.apply_effects(frame, [{"name": "Boh"}]), frame)


def test_compositor_applica_gli_effetti(tmp_path):
    from showsuite.cue.engine import ManualClock, Runtime
    from showsuite.cue.model import TYPE_TEXT, Workspace
    from showsuite.cue.video import VideoCompositor
    workspace = Workspace("V")
    cue = workspace.new_cue(TYPE_TEXT)
    cue.params["text"] = "XXXX"
    runtime = Runtime(workspace, ManualClock())
    compositor = VideoCompositor(runtime)
    compositor.install()
    runtime.start_cue(cue)
    plain = compositor.render_stage(1).copy()
    cue.params["video_fx"] = [videofx.new_effect("MinMaxInvert")]
    inverted = compositor.render_stage(1)
    assert not np.array_equal(plain, inverted)


def test_osc_effetti():
    workspace, runtime, api, client, cues = make_api()
    video_cue = workspace.new_cue(TYPE_VIDEO)
    video_cue.number = "7"
    api.handle("/cue/7/videoEffects/add", ["Gamma"], client)
    api.handle("/cue/7/videoEffects/add", ["Exposure"], client)
    api.handle("/cue/7/videoEffects/insert", ["Vibrance", 0], client)
    api.handle("/cue/7/videoEffects", [], client)
    assert json.loads(last_reply(client)[1]["data"]) == ["Vibrance", "Gamma", "Exposure"]
    api.handle("/cue/7/videoEffect/Gamma/parameter/inputPower", [2.0], client)
    api.handle("/cue/7/videoEffect/Gamma/parameter/inputPower", [], client)
    assert last_reply(client)[1]["data"] == 2.0
    api.handle("/cue/7/videoEffect/Gamma/parameter/inputPower/+", [0.5], client)
    assert video_cue.params["video_fx"][1]["parameters"]["inputPower"] == 2.5
    api.handle("/cue/7/videoEffectIndex/2/parameters", [json.dumps({"inputEV": 1.5})], client)
    api.handle("/cue/7/videoEffectIndex/2/parameters", [], client)
    assert json.loads(last_reply(client)[1]["data"])["inputEV"] == 1.5
    api.handle("/cue/7/videoEffect/Gamma/enabled", [False], client)
    api.handle("/cue/7/videoEffectIndex/1/enabled", [], client)
    assert last_reply(client)[1]["data"] == False
    api.handle("/cue/7/videoEffect/Gamma/move", [9], client)
    assert [effect["name"] for effect in video_cue.params["video_fx"]] == ["Vibrance", "Exposure", "Gamma"]
    api.handle("/cue/7/videoEffectIndex/0/delete", [], client)
    api.handle("/cue/7/videoEffect/Nessuno/delete", [], client)
    assert len(video_cue.params["video_fx"]) == 2
    api.handle("/cue/7/videoEffects/add", ["Kaleidoscope"], client)
    assert last_reply(client)[1]["status"] == "error"
    api.handle("/cue/7/videoEffect/Gamma/parameter/inventato", [1], client)
    assert last_reply(client)[1]["status"] == "error"
