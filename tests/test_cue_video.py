import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_FADE, TYPE_TEXT, TYPE_VIDEO, Workspace
from showsuite.cue.video import MemorySink, VideoCompositor, euler_to_quaternion, quaternion_to_matrix


def setup(tmp_path, color=(255, 0, 0), size=(100, 200)):
    path = str(tmp_path / "img.png")
    image = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    image[:] = (color[2], color[1], color[0])
    cv2.imwrite(path, image)
    workspace = Workspace("V")
    workspace.patches["video_stage"] = [{"name": "Main", "width": 400, "height": 200, "regions": [
        {"name": "Sinistra", "bounds": [0, 0, 200, 200]}, {"name": "Destra", "bounds": [200, 0, 200, 200],
                                                           "edge_blend": {"left": 50, "gamma": 1.0}}]}]
    workspace.patches["video_route"] = [{"name": "Proiettore1", "stage": 1, "region": "Sinistra"},
                                        {"name": "Proiettore2", "stage": 1, "region": "Destra"}]
    runtime = Runtime(workspace, ManualClock())
    sink = MemorySink()
    compositor = VideoCompositor(runtime, sink)
    compositor.install()
    cue = workspace.new_cue(TYPE_VIDEO)
    cue.params["file_target"] = path
    return workspace, runtime, compositor, sink, cue


def test_fill_stage_con_aspect_e_regioni(tmp_path):
    workspace, runtime, compositor, sink, cue = setup(tmp_path)
    runtime.start_cue(cue)
    frames = compositor.render_routes()
    left = frames["Proiettore1"]
    assert left.shape == (200, 200, 4)
    # immagine 200x100 -> fit in stage 400x200 => 400x200 scalata 2x: piena. Rosso ovunque
    assert tuple(left[100, 100, :3]) == (255, 0, 0)
    right = frames["Proiettore2"]
    assert right[100, 5, 0] < 40 and right[100, 150, 0] == 255
    assert "Proiettore2" in sink.frames


def test_traslazione_scala_opacita_e_layer(tmp_path):
    workspace, runtime, compositor, sink, cue = setup(tmp_path)
    cue.params.update({"fill_stage": False, "scale": [0.5, 0.5], "translation": [100.0, 0.0], "opacity": 0.5})
    runtime.start_cue(cue)
    stage = compositor.render_stage()
    assert stage[100, 100, 0] == 0
    assert 120 <= stage[100, 300, 0] <= 135
    top = workspace.new_cue(TYPE_VIDEO)
    top.params.update(cue.params)
    top.params.update({"layer": 5, "opacity": 1.0, "translation": [100.0, 0.0]})
    runtime.start_cue(top)
    stage = compositor.render_stage()
    assert stage[100, 300, 0] == 255


def test_rotazione_z_e_quaternione():
    quaternion = euler_to_quaternion(0, 0, 90)
    matrix = quaternion_to_matrix(quaternion)
    assert matrix @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-6)


def test_fade_opacita_dal_fade_cue(tmp_path):
    workspace, runtime, compositor, sink, cue = setup(tmp_path)
    fade = workspace.new_cue(TYPE_FADE)
    fade.target_id = cue.unique_id
    fade.params.update({"do_opacity": True, "opacity": 0.0, "curve": {"type": "linear", "intensity": 0.5, "rising": [], "falling": []}})
    fade.duration = 2.0
    runtime.start_cue(cue)
    runtime.start_cue(fade)
    runtime.advance(1.0)
    assert 100 <= compositor.render_stage()[100, 100, 0] <= 155
    runtime.advance(1.5)
    assert compositor.render_stage()[100, 100, 0] == 0


def test_maschera_e_testo(tmp_path):
    workspace, runtime, compositor, sink, cue = setup(tmp_path)
    workspace.patches["video_stage"][0]["regions"][0]["mask"] = np.zeros((10, 10), dtype=np.uint8)
    runtime.start_cue(cue)
    assert compositor.render_routes()["Proiettore1"][100, 100, 0] == 0
    text = workspace.new_cue(TYPE_TEXT)
    text.params["text"] = "CIAO"
    runtime.start_cue(text)
    stage = compositor.render_stage()
    assert stage[..., 1].max() > 0


def test_warp_prospettico_della_regione(tmp_path):
    workspace, runtime, compositor, sink, cue = setup(tmp_path)
    workspace.patches["video_stage"][0]["regions"][0]["warp"] = {"corners": [[50, 0], [150, 0], [200, 200], [0, 200]]}
    runtime.start_cue(cue)
    frame = compositor.render_routes()["Proiettore1"]
    assert frame[5, 10, 0] == 0 and frame[190, 10, 0] == 255
