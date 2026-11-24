"""Uscita verso un server OLA (Open Lighting Architecture) via HTTP: POST /set_dmx."""
from __future__ import annotations

import http.client
import urllib.parse

from .base import OutputDriver


def build_set_dmx(universe: int, data: bytes) -> str:
    return urllib.parse.urlencode({"u": universe, "d": ",".join(str(b) for b in data)})


class OlaDriver(OutputDriver):
    def __init__(self, host: str = "127.0.0.1", port: int = 9090, ola_universe_offset: int = 0):
        self.host, self.port, self.offset = host, port, ola_universe_offset
        self._conn: http.client.HTTPConnection | None = None

    def open(self) -> None:
        self._conn = http.client.HTTPConnection(self.host, self.port, timeout=0.5)

    def send(self, universe: int, data: bytes) -> None:
        body = build_set_dmx(universe + self.offset, data)
        try:
            self._conn.request("POST", "/set_dmx", body, {"Content-Type": "application/x-www-form-urlencoded"})
            self._conn.getresponse().read()
        except (OSError, http.client.HTTPException):
            self._conn.close()                      # riconnette al frame successivo
            raise

    def close(self) -> None:
        if self._conn:
            self._conn.close(); self._conn = None
