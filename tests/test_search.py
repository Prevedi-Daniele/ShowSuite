from showsuite.light import project as pj
from showsuite.light.fixtures import FixtureInstance, generic_rgb
from showsuite.light.search import search


def test_search():
    p = pj.Project("S"); p.patch.add(FixtureInstance("Par Sinistra", generic_rgb(), 1, 1))
    r = search(p, "sinis"); assert r and r[0][0] == "fixture"
    assert search(p, "zzz") == [] and search(p, "") == []
    assert search(p, "sinis", ["cue"]) == []
