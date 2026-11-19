"""sACN / E1.31 (UDP 5568, multicast 239.255.x.y o unicast)."""
from __future__ import annotations

import socket
import uuid

from .base import OutputDriver

SACN_PORT = 5568


def multicast_address(universe: int) -> str:
    return f"239.255.{universe >> 8}.{universe & 0xFF}"


def build_sacn(universe: int, data: bytes, cid: bytes, source: str = "ShowSuite",
               priority: int = 100, sequence: int = 0) -> bytes:
    if not 1 <= universe <= 63999:
        raise ValueError("universo sACN 1-63999")
    if len(data) > 512:
        raise ValueError("max 512 byte")
    n = len(data)
    dmp = (b"\x02\xa1\x00\x00\x00\x01" + (n + 1).to_bytes(2, "big") + b"\x00" + data)
    dmp = (0x7000 | (len(dmp) + 2)).to_bytes(2, "big") + dmp
    framing = (b"\x00\x00\x00\x02"
               + source.encode()[:63].ljust(64, b"\x00")
               + bytes([priority]) + b"\x00\x00"
               + bytes([sequence & 0xFF, 0])
               + universe.to_bytes(2, "big") + dmp)
    framing = (0x7000 | (len(framing) + 2)).to_bytes(2, "big") + framing
    root = b"\x00\x00\x00\x04" + cid + framing
    root = (0x7000 | (len(root) + 2)).to_bytes(2, "big") + root
    return (b"\x00\x10\x00\x00" + b"ASC-E1.17\x00\x00\x00" + root)


class SacnDriver(OutputDriver):
    def __init__(self, unicast: str | None = None, source: str = "ShowSuite", priority: int = 100):
        self.unicast, self.source, self.priority = unicast, source, priority
        self.cid = uuid.uuid4().bytes
        self._sock: socket.socket | None = None
        self._seq: dict[int, int] = {}

    def open(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    def send(self, universe: int, data: bytes) -> None:
        seq = self._seq.get(universe, 0)
        self._seq[universe] = (seq + 1) & 0xFF
        pkt = build_sacn(universe, data, self.cid, self.source, self.priority, seq)
        self._sock.sendto(pkt, (self.unicast or multicast_address(universe), SACN_PORT))

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
