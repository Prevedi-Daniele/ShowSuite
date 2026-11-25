import numpy as np
import pytest

soundfile = pytest.importorskip("soundfile")

from showsuite.cue.audio import AudioMixer, biquad_coefficients, db_to_gain, envelope_value, render_offline
from showsuite.cue.engine import ManualClock, Runtime
from showsuite.cue.model import TYPE_AUDIO, TYPE_FADE, Workspace

RATE = 8000


def make(tmp_path, seconds=2.0, channels=2, value=0.5):
    path = str(tmp_path / "tone.wav")
    data = np.full((int(RATE * seconds), channels), value, dtype=np.float32)
    soundfile.write(path, data, RATE)
    workspace = Workspace("A")
    runtime = Runtime(workspace, ManualClock())
    mixer = AudioMixer(runtime, sample_rate=RATE, output_channels=4, block_size=400)
    mixer.install()
    cue = workspace.new_cue(TYPE_AUDIO)
    cue.params.update({"file_target": path, "media_duration": seconds, "media_channels": channels})
    return workspace, runtime, mixer, cue


def test_riproduzione_matrice_di_default_e_fine(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path)
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 2.5)
    assert audio[100, 0] == pytest.approx(0.5, abs=1e-3) and audio[100, 1] == pytest.approx(0.5, abs=1e-3)
    assert audio[100, 2] == 0.0
    assert abs(audio[int(RATE * 2.2)]).max() == 0.0
    assert runtime.is_active(cue) == False


def test_livello_main_e_crosspoint_verso_altre_uscite(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path)
    cue.params["levels"] = {"main": -6.0206, "1/3": 0.0, "2/4": -6.0206}
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 0.5)
    assert audio[800, 0] == 0.0
    assert audio[800, 2] == pytest.approx(0.5 * 0.5, abs=1e-2)
    assert audio[800, 3] == pytest.approx(0.5 * 0.25, abs=1e-2)


def test_patch_con_canale_iniziale(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path)
    workspace.patches["audio"] = [{"name": "Uscite 3-4", "first_channel": 3}]
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 0.2)
    assert audio[100, 0] == 0.0 and audio[100, 2] == pytest.approx(0.5, abs=1e-3)


def test_loop_infinito_e_rate_doppio(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path, seconds=1.0)
    cue.params["infinite_loop"] = True
    cue.params["rate"] = 2.0
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 3.0)
    assert runtime.is_running(cue)
    assert audio[-10, 0] == pytest.approx(0.5, abs=1e-3)
    runtime.stop_cue(cue)
    assert render_offline(runtime, mixer, 0.1).max() == 0.0


def test_fade_cue_abbassa_il_livello_nel_mix(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path, seconds=4.0)
    fade = workspace.new_cue(TYPE_FADE)
    fade.target_id = cue.unique_id
    fade.params["levels"] = {"main": -20.0}
    fade.params["curve"] = {"type": "linear", "intensity": 0.5, "rising": [], "falling": []}
    fade.duration = 1.0
    runtime.start_cue(cue)
    runtime.start_cue(fade)
    audio = render_offline(runtime, mixer, 1.6)
    assert audio[10, 0] == pytest.approx(0.5, abs=0.02)
    assert audio[int(RATE * 1.5), 0] == pytest.approx(0.5 * db_to_gain(-20.0), abs=0.01)


def test_envelope_integrato_e_panic(tmp_path):
    assert envelope_value([[0, 0], [2, -20]], 1.0) == pytest.approx(-10.0)
    workspace, runtime, mixer, cue = make(tmp_path, seconds=4.0)
    cue.params["integrated_fade"] = {"enabled": True, "points": [[0.0, 0.0], [1.0, -60.0]]}
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 1.2)
    assert audio[int(RATE * 1.1), 0] < 0.001
    workspace.settings["panic_duration"] = 1.0
    cue2 = workspace.new_cue(TYPE_AUDIO)
    cue2.params.update(cue.params)
    cue2.params["integrated_fade"] = {"enabled": False, "points": []}
    runtime.start_cue(cue2)
    runtime.panic_cue(cue2)
    out = render_offline(runtime, mixer, 1.2)
    assert out[100, 0] > out[int(RATE * 0.8), 0] > 0.0
    assert runtime.is_active(cue2) == False


def test_eq_passa_alto_taglia_la_continua(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path, seconds=2.0)
    cue.params["audio_fx"] = [{"type": "highpass", "frequency": 500.0, "q": 0.707}]
    runtime.start_cue(cue)
    audio = render_offline(runtime, mixer, 1.5)
    assert abs(audio[-100:, 0]).max() < 0.01
    b, a = biquad_coefficients("peak", 1000.0, 6.0, 1.0, RATE)
    assert len(b) == 3 and len(a) == 3


def test_mute_e_solo(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path)
    cue.params["mute"] = True
    runtime.start_cue(cue)
    assert render_offline(runtime, mixer, 0.2).max() == 0.0


def test_slice_con_loop_poi_devamp(tmp_path):
    workspace, runtime, mixer, cue = make(tmp_path, seconds=3.0)
    cue.params["slices"] = [{"time": 0.0, "play_count": "inf"}, {"time": 1.0, "play_count": 1}]
    runtime.start_cue(cue)
    render_offline(runtime, mixer, 5.0)
    assert runtime.is_running(cue)
    runtime.devamp_cue(cue)
    render_offline(runtime, mixer, 4.0)
    assert runtime.is_active(cue) == False


def test_mute_e_solo_delle_uscite_patch():
    import numpy as np
    from showsuite.cue.audio import AudioMixer
    from showsuite.cue.engine import ManualClock, Runtime
    from showsuite.cue.model import Workspace
    workspace = Workspace("M")
    workspace.patches["audio"] = [{"name": "A", "first_channel": 1, "channels": 2, "mute": [1], "solo": []}]
    mixer = AudioMixer(Runtime(workspace, ManualClock()))
    block = np.ones((4, 2), dtype=np.float32)
    mixer._apply_output_mute_solo(block)
    assert block[:, 0].sum() == 0 and block[:, 1].sum() == 4
    workspace.patches["audio"][0].update({"mute": [], "solo": [2]})
    block = np.ones((4, 2), dtype=np.float32)
    mixer._apply_output_mute_solo(block)
    assert block[:, 0].sum() == 0 and block[:, 1].sum() == 4
