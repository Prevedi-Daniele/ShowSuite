"""DMX-In via rete (Art-Net e sACN): i canali ricevuti pilotano le azioni di controllo."""
from __future__ import annotations

import socket
import struct
import threading
from dataclasses import dataclass, field

from .actions import ActionRunner, ControlError

ARTNET_PORT = 6454
SACN_PORT = 5568
BUTTON_ACTIONS = ("cue", "tap", "blackout", "freeze", "blind")   # reagiscono a soglia, non in continuo
THRESHOLD = 128


@dataclass
class DmxMapping:
    universe: int       # come usato dal sorgente (Art-Net: port-address; sACN: universo)
    channel: int        # 1-512
    action: str
    args: dict = field(default_factory=dict)


def parse_artdmx(data: bytes) -> tuple[int, bytes] | None:
    """ArtDmx -> (universo, dati) oppure None se non è un pacchetto ArtDmx valido."""
    if len(data) < 18 or not data.startswith(b"Art-Net\x00") or data[8:10] != b"\x00\x50":
        return None
    universe = data[14] | ((data[15] & 0x7F) << 8)
    length = (data[16] << 8) | data[17]
    if length > 512 or len(data) < 18 + length:
        return None
    return universe, data[18:18 + length]


def parse_sacn(data: bytes) -> tuple[int, bytes] | None:
    """Pacchetto E1.31 dati -> (universo, dati) oppure None."""
    if len(data) < 126 or data[4:16] != b"ASC-E1.17\x00\x00\x00":
        return None
    if data[18:22] != b"\x00\x00\x00\x04" or data[40:44] != b"\x00\x00\x00\x02":
        return None
    if data[117] != 0x02 or data[125] != 0:     # vettore DMP e start code 0
        return None
    universe = struct.unpack_from(">H", data, 113)[0]
    count = struct.unpack_from(">H", data, 123)[0] - 1
    if not 0 <= count <= 512 or len(data) < 126 + count:
        return None
    return universe, data[126:126 + count]


class DmxInput:
    def __init__(self, runner: ActionRunner, mappings: list[DmxMapping] | None = None,
                 artnet_port: int | None = ARTNET_PORT, sacn_port: int | None = SACN_PORT,
                 host: str = "0.0.0.0"):
        self.runner = runner
        self.mappings = mappings if mappings is not None else []
        self.ports = {"artnet": artnet_port, "sacn": sacn_port}
        self.host = host
        self.errors: list[str] = []
        self._last: dict[tuple[int, int], int] = {}
        self._socks: list[socket.socket] = []
        self._threads: list[threading.Thread] = []
        self._running = False
        self.bound: dict[str, int] = {}

    # --- elaborazione frame (testabile senza rete) ---
    def handle_frame(self, universe: int, data: bytes) -> None:
        for m in self.mappings:
            if m.universe != universe or not 1 <= m.channel <= len(data):
                continue
            v = data[m.channel - 1]
            key = (universe, m.channel)
            prev = self._last.get(key)
            if prev == v:
                continue
            self._last[key] = v
            try:
                if m.action in BUTTON_ACTIONS:
                    was_on = prev is not None and prev >= THRESHOLD
                    is_on = v >= THRESHOLD
                    if is_on != was_on and not (prev is None and not is_on):
                        self.runner.run(m.action, m.args, 1.0 if is_on else 0.0)
                else:
                    self.runner.run(m.action, m.args, v / 255.0)
            except (ControlError, KeyError) as e:
                self.errors.append(str(e)); del self.errors[:-20]

    # --- rete ---
    def start(self) -> None:
        self._running = True
        for kind, parser in (("artnet", parse_artdmx), ("sacn", parse_sacn)):
            port = self.ports.get(kind)
            if port is None:
                continue
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, port))
            sock.settimeout(0.2)
            self.bound[kind] = sock.getsockname()[1]
            self._socks.append(sock)
            t = threading.Thread(target=self._loop, args=(sock, parser), name=f"dmx-in-{kind}", daemon=True)
            t.start(); self._threads.append(t)

    def _loop(self, sock, parser) -> None:
        while self._running:
            try:
                data, _ = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                return
            frame = parser(data)
            if frame:
                self.handle_frame(*frame)

    def stop(self) -> None:
        self._running = False
        for s in self._socks:
            s.close()
        for t in self._threads:
            t.join(timeout=1)
        self._socks.clear(); self._threads.clear(); self.bound.clear()
