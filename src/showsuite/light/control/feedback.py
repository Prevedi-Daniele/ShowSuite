"""Feedback verso i controller: OSC (stato dei cue/master) e MIDI out (LED dei pad)."""
from __future__ import annotations

import socket

from .osc import build_osc


def _state(engine) -> dict[str, float]:
    st = {f"/cue/{n}": 1.0 for n, s in engine.live.active.items() if not s.get("releasing")}
    for c in engine.project.cues:
        st.setdefault(f"/cue/{c.name}", 0.0)
    st["/master"] = float(engine.grand_master)
    st["/blackout"] = 1.0 if engine.blackout else 0.0
    st["/freeze"] = 1.0 if engine.freeze else 0.0
    return st


class OscFeedback:
    """Invia ai client (ultimo mittente o indirizzi fissi) solo i valori cambiati."""

    def __init__(self, send=None):
        self.targets: set[tuple[str, int]] = set()
        self._last: dict[str, float] = {}
        self._send = send or self._udp
        self._sock = None

    def add_target(self, host: str, port: int) -> None:
        if (host, port) not in self.targets:
            self.targets.add((host, port)); self._last.clear()      # nuovo client: rimanda tutto

    def _udp(self, host: str, port: int, data: bytes) -> None:
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.sendto(data, (host, port))

    def poll(self, engine) -> int:
        st = _state(engine)
        changed = {k: v for k, v in st.items() if self._last.get(k) != v}
        self._last = st
        for host, port in self.targets:
            for k, v in changed.items():
                try:
                    self._send(host, port, build_osc(k, v))
                except OSError:
                    pass
        return len(changed) if self.targets else 0


class MidiFeedback:
    """Accende i pad mappati a un cue (nota con velocity 127 = attivo, 0 = spento)."""

    def __init__(self, send):
        self.send = send           # send(kind, channel, number, value)
        self._last: dict[tuple, int] = {}

    def poll(self, engine, mappings) -> int:
        n = 0
        active = {n_ for n_, s in engine.live.active.items() if not s.get("releasing")}
        for m in mappings:
            if m.action != "cue":
                continue
            val = 127 if m.args.get("cue") in active else 0
            if self._last.get(m.key()) != val:
                self._last[m.key()] = val; n += 1
                self.send("note" if m.kind == "note" else "cc", m.channel, m.number, val)
        return n
