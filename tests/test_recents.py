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


def test_project_browser_choices(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    f = tmp_path / "a.showsuite-light"; f.write_bytes(b"x"); recents.add(str(f)); recents.add("/non/esiste")
    from showsuite.ui.project_browser import ProjectBrowser
    b = ProjectBrowser(); assert b.list.count() == 1
    b._open_item(b.list.item(0)); assert b.choice == ("path", str(f))
    b2 = ProjectBrowser(); b2._done(("new", None)); assert b2.choice == ("new", None)
