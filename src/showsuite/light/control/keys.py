"""Trigger da tastiera: combinazione di tasti -> azione (categoria 'Tastiera' del controllo esterno)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KeyMapping:
    key: str            # sequenza Qt in formato portabile, es. "Ctrl+1", "F5", "Shift+A"
    action: str
    args: dict = field(default_factory=dict)


def normalize(key: str) -> str:
    """'ctrl + 1' -> 'Ctrl+1' (forma canonica per confrontare)."""
    parts = [p.strip() for p in key.replace(" ", "").split("+") if p.strip()]
    if not parts:
        return ""
    mods = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "meta": "Meta"}
    out = [mods.get(p.lower(), p.upper() if len(p) == 1 else p[:1].upper() + p[1:]) for p in parts]
    order = {"Ctrl": 0, "Alt": 1, "Shift": 2, "Meta": 3}
    return "+".join(sorted(out[:-1], key=lambda m: order.get(m, 9)) + out[-1:])


def add_mapping(mappings: list[KeyMapping], key: str, action: str, args: dict | None = None) -> KeyMapping:
    """Sostituisce una mappatura esistente sullo stesso tasto."""
    k = normalize(key)
    if not k:
        raise ValueError("tasto vuoto")
    mappings[:] = [m for m in mappings if normalize(m.key) != k]
    m = KeyMapping(k, action, args or {}); mappings.append(m); return m


def run_key(runner, mappings: list[KeyMapping], key: str) -> bool:
    k = normalize(key)
    for m in mappings:
        if normalize(m.key) == k:
            runner.run(m.action, m.args, 1.0)
            return True
    return False
