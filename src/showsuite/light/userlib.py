"""Libreria profili dell'utente (JSON) + testo <-> intervalli (caps) per l'editor profili."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .fixtures import ChannelDef, FixtureProfile
from .project import _profile_from_dict, _profile_to_dict

KINDS = ("", "intensity", "red", "green", "blue", "white", "amber", "uv", "pan", "tilt", "zoom", "focus", "iris",
         "prism", "frost", "shutter", "color_wheel", "gobo_wheel", "fog", "speed")


def _dir() -> Path:
    base = os.environ.get("SHOWSUITE_CONFIG") or os.path.join(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config", "showsuite")
    return Path(base) / "profiles"


def caps_to_text(caps) -> str:
    """((0, 9, 'x', 'Open'), …) -> '0-9:Open; 10-255:Strobe'."""
    return "; ".join(f"{lo}-{hi}:{label}" for lo, hi, _t, label in caps)


def text_to_caps(text: str) -> tuple:
    out = []
    for part in filter(None, (p.strip() for p in text.split(";"))):
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)\s*:\s*(.+)", part)
        if not m:
            raise ValueError(f"intervallo non valido: «{part}» (usa 0-9:Etichetta)")
        lo, hi = int(m[1]), int(m[2])
        if not (0 <= lo <= hi <= 255):
            raise ValueError(f"intervallo fuori range: «{part}»")
        out.append((lo, hi, "Custom", m[3].strip()))
    return tuple(out)


def validate(p: FixtureProfile) -> None:
    if not p.model.strip():
        raise ValueError("il modello non può essere vuoto")
    if not p.channels:
        raise ValueError("servono almeno un canale")
    if p.footprint > 512:
        raise ValueError("più di 512 canali")
    names = [c.name for c in p.channels]
    if any(not n.strip() for n in names):
        raise ValueError("canale senza nome")
    if len(set(names)) != len(names):
        raise ValueError("nomi di canale duplicati")


def _fname(p: FixtureProfile) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", f"{p.manufacturer}_{p.model}_{p.mode}") + ".json"


def save_profile(p: FixtureProfile) -> Path:
    validate(p)
    d = _dir(); d.mkdir(parents=True, exist_ok=True)
    f = d / _fname(p); f.write_text(json.dumps(_profile_to_dict(p), indent=2)); return f


def load_all() -> list[FixtureProfile]:
    out = []
    for f in sorted(_dir().glob("*.json")) if _dir().exists() else []:
        try:
            out.append(_profile_from_dict(json.loads(f.read_text())))
        except Exception:
            continue
    return out


def delete_profile(p: FixtureProfile) -> None:
    try:
        (_dir() / _fname(p)).unlink()
    except OSError:
        pass


def export_profile(p: FixtureProfile, path: str) -> None:
    Path(path).write_text(json.dumps(_profile_to_dict(p), indent=2))


def import_profile(path: str) -> FixtureProfile:
    p = _profile_from_dict(json.loads(Path(path).read_text())); validate(p); return p
