"""Impostazioni dell'app (JSON nella cartella di configurazione)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

DEFAULTS = {"on_quit": "ask",            # ask | save | discard
            "open_last": False,           # all'avvio riapre l'ultimo progetto
            "adaptive_background": True,  # lo sfondo del Preview prende il colore dei fixture
            "lock_password": ""}          # hash sha256 (vuoto = nessuna password)


def _file() -> Path:
    base = os.environ.get("SHOWSUITE_CONFIG") or os.path.join(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config", "showsuite")
    return Path(base) / "settings.json"


def load() -> dict:
    try:
        d = json.loads(_file().read_text())
    except Exception:
        d = {}
    return {**DEFAULTS, **{k: v for k, v in d.items() if k in DEFAULTS}}


def save(d: dict) -> None:
    try:
        _file().parent.mkdir(parents=True, exist_ok=True); _file().write_text(json.dumps(d, indent=2))
    except OSError:
        pass


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest() if pw else ""


def check_pw(d: dict, pw: str) -> bool:
    return not d["lock_password"] or hash_pw(pw) == d["lock_password"]
