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
