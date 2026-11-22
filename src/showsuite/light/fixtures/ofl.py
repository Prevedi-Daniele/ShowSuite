"""Import profili da Open Fixture Library (formato JSON OFL).

Un file OFL contiene più modalità: si genera un FixtureProfile per ognuna.
Limiti: i canali pixel/matrice (template) non sono supportati.
"""
from __future__ import annotations

import json
import os
import re

from .profile import ChannelDef, FixtureProfile


class OflImportError(ValueError):
    pass


def _default(value, fine: bool) -> int:
    top = 65535 if fine else 255
    if value is None:
        return 0
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*%\s*", value)
        if not m:
            raise OflImportError(f"valore di default non valido: {value!r}")
        return max(0, min(top, round(float(m.group(1)) / 100 * top)))
    return max(0, min(top, int(value)))


_SIMPLE = {"Pan": "pan", "Tilt": "tilt", "Zoom": "zoom", "Focus": "focus", "Iris": "iris",
           "Prism": "prism", "Frost": "frost"}


def _caps_list(spec: dict) -> list[dict]:
    return spec.get("capabilities") or ([spec["capability"]] if "capability" in spec else [])


def _kind(spec: dict) -> str:
    for c in _caps_list(spec):
        t = c.get("type")
        if t == "Intensity":
            return "intensity"
        if t == "ColorIntensity":
            col = str(c.get("color", "")).lower()
            return {"uv": "uv", "ultraviolet": "uv"}.get(col, col)
        if t in _SIMPLE:
            return _SIMPLE[t]
        if t == "ShutterStrobe":
            return "shutter"
        if t == "ColorPreset":
            return "color_wheel"
        if t == "WheelSlot":
            return "gobo_wheel" if "gobo" in str(c.get("wheel", "")).lower() else "color_wheel"
    return ""


def _caps(spec: dict, kind: str) -> tuple:
    """Intervalli utili (shutter, ruote): ((da, a, tipo, etichetta), ...)."""
    if kind not in ("shutter", "color_wheel", "gobo_wheel"):
        return ()
    out = []
    for c in _caps_list(spec):
        rng = c.get("dmxRange")
        if not rng or c.get("type") in ("NoFunction", "Maintenance"):
            continue
        label = c.get("shutterEffect") or c.get("comment") or c.get("slotNumber") or c.get("type")
        out.append((int(rng[0]), int(rng[1]), c.get("type"), str(label)))
    return tuple(out)


def parse_ofl(doc: dict, manufacturer: str = "") -> list[FixtureProfile]:
    if "name" not in doc or "modes" not in doc or "availableChannels" not in doc:
        raise OflImportError("non è un file fixture OFL")
    manufacturer = manufacturer or doc.get("manufacturer") or ""
    avail = doc["availableChannels"]
    # nome canale fine -> (canale coarse, livello)
    fine_of: dict[str, str] = {}
    for coarse, spec in avail.items():
        for alias in spec.get("fineChannelAliases", []):
            fine_of[alias] = coarse

    # canali "switching": compaiono nelle modalità col nome-chiave, definiti in switchChannels
    switching: set[str] = set()
    for spec in avail.values():
        for cap in spec.get("capabilities", []) or ([spec["capability"]] if "capability" in spec else []):
            switching.update((cap.get("switchChannels") or {}).keys())

    profiles = []
    for mode in doc["modes"]:
        chans: list[ChannelDef] = []
        names = list(mode["channels"])
        i, seen = 0, set()
        while i < len(names):
            n = names[i]
            if n is None:
                chans.append(ChannelDef(f"(vuoto {i + 1})"))
            elif isinstance(n, dict):
                raise OflImportError(f"modalità «{mode['name']}»: canali matrice/pixel non supportati")
            else:
                if n not in avail and n not in fine_of and n not in switching:
                    raise OflImportError(f"canale sconosciuto: {n}")
                if n in fine_of:   # byte fine non adiacente al coarse: resta un canale a 8 bit
                    chans.append(ChannelDef(n))
                else:
                    spec = avail.get(n, {})
                    fine_names = spec.get("fineChannelAliases", [])
                    adjacent = (len(fine_names) >= 1 and i + 1 < len(names) and names[i + 1] == fine_names[0])
                    name = n if n not in seen else f"{n} ({i + 1})"
                    if adjacent:
                        chans.append(ChannelDef(name, _default(spec.get("defaultValue"), True), fine=True,
                                                kind=_kind(spec), caps=_caps(spec, _kind(spec))))
                        i += 1  # consuma il byte fine (solo 16 bit; il 24 bit resta come canale a parte)
                    else:
                        chans.append(ChannelDef(name, _default(spec.get("defaultValue"), False),
                                                kind=_kind(spec), caps=_caps(spec, _kind(spec))))
                    seen.add(n)
            i += 1
        profiles.append(FixtureProfile(manufacturer, doc["name"], mode["name"], tuple(chans)))
    return profiles


def load_ofl(path: str) -> list[FixtureProfile]:
    with open(path, encoding="utf-8") as f:
        try:
            doc = json.load(f)
        except json.JSONDecodeError as e:
            raise OflImportError(f"JSON non valido: {e}") from e
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    maker = folder.replace("-", " ").title() if folder not in ("", "fixtures", "tmp") else ""
    return parse_ofl(doc, maker)
