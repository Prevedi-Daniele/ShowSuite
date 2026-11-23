import pytest

from showsuite.light import userlib as U
from showsuite.light.fixtures import ChannelDef, FixtureProfile


def prof(**kw):
    ch = (ChannelDef("Dimmer", kind="intensity"), ChannelDef("Shutter", kind="shutter",
          caps=U.text_to_caps("0-9:Closed; 10-19:Open; 20-255:Strobe")))
    return FixtureProfile("Acme", "Par X", "2ch", kw.get("channels", ch))


def test_caps_roundtrip_and_errors():
    c = U.text_to_caps("0-9:Closed; 10-255:Open")
    assert c[0][:2] == (0, 9) and U.caps_to_text(c) == "0-9:Closed; 10-255:Open"
    for bad in ("0-300:x", "boh", "9-1:x"):
        with pytest.raises(ValueError):
            U.text_to_caps(bad)


def test_save_load_export(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    p = prof(); U.save_profile(p)
    assert U.load_all() == [p]
    f = tmp_path / "x.json"; U.export_profile(p, str(f)); assert U.import_profile(str(f)) == p
    U.delete_profile(p); assert U.load_all() == []
    with pytest.raises(ValueError):
        U.save_profile(prof(channels=(ChannelDef("A"), ChannelDef("A"))))


def test_editor_build_and_engine_library(tmp_path, monkeypatch):
    import os; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from showsuite.ui.profile_editor import ProfileEditor
    ed = ProfileEditor(prof()); ed.model.setText("Par Y")
    assert ed.build().footprint == 2 and ed.build().channels[1].caps[0][3] == "Closed"
    ed.add_row(); ed.table.setCurrentCell(2, 0); ed.move(-1); assert ed.table.item(1, 0).text() == "Canale 3"
    ed.save(); assert ed.result_profile and ed.result_profile.model == "Par Y"
    from showsuite.light import project as pj
    from showsuite.light.engine import LightEngine
    assert any("Par Y" in k for k in LightEngine(pj.Project("L")).library)
