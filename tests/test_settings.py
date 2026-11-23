from showsuite.light import settings as S


def test_settings_and_password(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWSUITE_CONFIG", str(tmp_path))
    c = S.load(); assert c["on_quit"] == "ask" and S.check_pw(c, "qualsiasi")
    c["lock_password"] = S.hash_pw("segreto"); S.save(c)
    c = S.load(); assert S.check_pw(c, "segreto") and not S.check_pw(c, "no")
