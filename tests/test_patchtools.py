import pytest

from showsuite.light import patchtools as T, project as pj
from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, PatchError, generic_dimmer, generic_rgb


def mk():
    p = pj.Project("T"); p.patch.add(FixtureInstance("A", generic_rgb(), 1, 1)); p.patch.add(FixtureInstance("B", generic_dimmer(), 1, 4))
    return p


def test_duplicate_and_change_address():
    p = mk(); n = T.duplicate_fixtures(p.patch, ["A"])
    assert n[0].name == "A 2" and n[0].address == 5 and n[0].universe == 1
    T.change_address(p.patch, "B", 2, 1); assert p.patch.find("B").universe == 2
    with pytest.raises(PatchError):
        T.change_address(p.patch, "B", 1, 2)
    assert p.patch.find("B").universe == 2            # invariato dopo l'errore


def test_reassign_profile_keeps_order_and_clears_values():
    p = mk(); e = LightEngine(p); e.set_value("A", "Red", 200)
    T.reassign_profile(e, "A", generic_dimmer())
    assert [f.name for f in p.patch.fixtures] == ["A", "B"] and "A" not in e.values
    with pytest.raises(PatchError):
        T.reassign_profile(e, "A", pj.FixtureProfile("x", "y", "z", (generic_rgb().channels * 3)))  # 9 ch: tocca B


def test_html_and_export_import(tmp_path):
    p = mk(); h = T.patch_html(p); assert "<td>A</td>" in h and "Patch" in h
    f = tmp_path / "f.json"; T.export_fixtures(p.patch, ["A", "B"], str(f))
    q = pj.Project("Q"); q.patch.add(FixtureInstance("A", generic_dimmer(), 1, 1))
    got = T.import_fixtures(q.patch, str(f))
    assert [g.name for g in got] == ["A 2", "B"] and got[1].address == 5 and len(q.patch.fixtures) == 3
