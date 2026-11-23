from showsuite.light import recents


def test_recents(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    assert recents.load() == []
    recents.add("a"); recents.add("b"); recents.add("a")
    assert recents.load() == ["a", "b"]
    for i in range(20):
        recents.add(str(i))
    assert len(recents.load()) == recents.MAX_RECENT
    recents.clear(); assert recents.load() == []
