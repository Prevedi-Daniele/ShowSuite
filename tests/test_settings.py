from showsuite.light import settings as S


def test_settings_and_password(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    c = S.load(); assert c["on_quit"] == "ask" and S.check_pw(c, "qualsiasi")
    c["lock_password"] = S.hash_pw("segreto"); S.save(c)
    c = S.load(); assert S.check_pw(c, "segreto") and not S.check_pw(c, "no")


def test_favorites_and_palette_io(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    for c in ("#ff0000", "#00ff00", "#FF0000"):
        S.add_favorite(c)
    assert S.load()["color_favorites"] == ["#ff0000", "#00ff00"]
    S.remove_favorite("#00FF00"); assert S.load()["color_favorites"] == ["#ff0000"]
    from showsuite.light.preset import Palette, Preset, export_palettes, import_palettes
    src = [Palette("Colori", [Preset("Rosso", {"A": {"Red": 255}})], "Gruppo")]
    f = tmp_path / "p.json"; assert export_palettes(src, str(f)) == 1
    dst = [Palette("Colori", [Preset("Rosso", {})])]
    assert import_palettes(dst, str(f)) == 1 and [x.name for x in dst[0].presets] == ["Rosso", "Rosso 2"]
    empty = []; import_palettes(empty, str(f)); assert empty[0].group == "Gruppo"
