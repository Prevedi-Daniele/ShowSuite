"""Art-Net (ArtDmx, UDP 6454)."""
from __future__ import annotations

import socket

from .base import OutputDriver

ARTNET_PORT = 6454


def build_artdmx(universe: int, data: bytes, sequence: int = 0) -> bytes:
    """Universo = Port-Address a 15 bit (0-32767)."""
    if len(data) > 512:
        raise ValueError("max 512 byte")
    if len(data) % 2:
        data += b"\x00"  # la lunghezza deve essere pari
    n = len(data)
    return (b"Art-Net\x00" + b"\x00\x50"           # OpCode ArtDmx (little endian)
            + b"\x00\x0e"                          # ProtVer 14
            + bytes([sequence & 0xFF, 0])          # sequence, physical
            + bytes([universe & 0xFF, (universe >> 8) & 0x7F])  # SubUni, Net
            + bytes([n >> 8, n & 0xFF]) + data)


class ArtNetDriver(OutputDriver):
    def __init__(self, host: str = "255.255.255.255", port: int = ARTNET_PORT):
        self.host, self.port = host, port
        self._sock: socket.socket | None = None
        self._seq = 0

    def open(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def send(self, universe: int, data: bytes) -> None:
        self._seq = (self._seq % 255) + 1  # 0 = sequenza disattivata
        self._sock.sendto(build_artdmx(universe, data, self._seq), (self.host, self.port))

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
