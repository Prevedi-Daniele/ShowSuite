"""OS2L (Open Sound to Light, usato da VirtualDJ e altri): server TCP che riceve beat e pulsanti in JSON."""
from __future__ import annotations

import json
import socket
import threading

from .actions import ControlError

DEFAULT_PORT = 8000


class Os2lParser:
    """Estrae oggetti JSON da un flusso TCP (messaggi concatenati o separati da newline)."""

    def __init__(self):
        self.buf = ""
        self._dec = json.JSONDecoder()

    def feed(self, data: bytes) -> list[dict]:
        self.buf += data.decode("utf-8", "replace")
        out = []
        while True:
            self.buf = self.buf.lstrip()
            if not self.buf:
                return out
            try:
                obj, end = self._dec.raw_decode(self.buf)
            except ValueError:
                if len(self.buf) > 65536:
                    self.buf = ""
                return out            # messaggio incompleto: aspetta altri byte
            self.buf = self.buf[end:]
            if isinstance(obj, dict):
                out.append(obj)


def handle_message(engine, runner, msg: dict) -> None:
    evt = msg.get("evt")
    if evt == "beat":
        bpm = msg.get("bpm")
        if isinstance(bpm, (int, float)) and 20 <= bpm <= 400 and abs(bpm - engine.beat.bpm) > 0.05:
            engine.beat.set_bpm(float(bpm))
        engine.beat.align(round(engine.beat.beats()))      # il beat cade su un numero intero
    elif evt == "btn":
        name = msg.get("name")
        state = msg.get("state", "on")
        on = state in ("on", True, 1, "1", "true")
        try:
            runner.run("cue", {"cue": name}, 1.0 if on else 0.0)
        except (ControlError, KeyError):
            pass                                              # pulsante senza cue corrispondente: ignora
    elif evt == "cmd":
        pass                                                  # comandi non mappati


class Os2lServer:
    def __init__(self, engine, runner, port: int = DEFAULT_PORT, host: str = "0.0.0.0"):
        self.engine, self.runner, self.port, self.host = engine, runner, port, host
        self._srv: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self.errors: list[str] = []

    def start(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port)); s.listen(4); s.settimeout(0.2)
        self.port = s.getsockname()[1]; self._srv = s
        self._thread = threading.Thread(target=self._accept, name="os2l", daemon=True); self._thread.start()

    def _accept(self) -> None:
        srv = self._srv
        while srv is self._srv:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._client, args=(conn, srv), daemon=True).start()

    def _client(self, conn, srv) -> None:
        parser = Os2lParser(); conn.settimeout(0.5)
        with conn:
            while srv is self._srv:
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    return
                if not data:
                    return
                for m in parser.feed(data):
                    try:
                        handle_message(self.engine, self.runner, m)
                    except Exception as e:           # input esterno: mai crashare
                        self.errors.append(str(e)); del self.errors[:-20]

    def stop(self) -> None:
        srv, self._srv = self._srv, None
        if srv:
            srv.close()
        if self._thread:
            self._thread.join(timeout=1); self._thread = None
