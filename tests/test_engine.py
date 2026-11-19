from showsuite.light.engine import LightEngine
from showsuite.light.fixtures import FixtureInstance, generic_rgb


def test_engine_values_and_color():
    e = LightEngine()
    fx = e.project.patch.add(FixtureInstance("P", generic_rgb(), 1, 10))
    e.set_value("P", "Green", 200)
    out = e.mixer.render(1)
    assert out[10] == 200 and out[9] == 0
    assert e.fixture_color(fx) == (0, 200, 0)
    e.remove_fixture("P")
    assert e.mixer.render(1)[10] == 0
