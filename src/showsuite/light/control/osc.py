"""OSC: parser minimale (UDP), server e mappa indirizzi -> azioni.

Indirizzi:
  /cue/<n|nome>            [valore]   avvia/ferma (toggle) o on/off per cue non-toggle
  /master  /bpm            f 0-1
  /tap  /blackout  /freeze  /blind   [valore]
  /fixture/<nome>/<canale> f 0-1
Il valore è il primo argomento (int/float/True/False); se manca vale 1.
"""
from __future__ import annotations

import socket
import struct
import threading
from urllib.parse import unquote

from .actions import ActionRunner, ControlError

DEFAULT_PORT = 21600   # come Lightkey


def _pad4(n: int) -> int:
    return (n + 4) & ~3


def _read_str(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", "replace"), _pad4(end) if end >= pos else pos


def parse_osc(data: bytes) -> list[tuple[str, list]]:
    """Messaggio o bundle -> lista di (indirizzo, argomenti). Solleva ValueError se malformato."""
    try:
        if data.startswith(b"#bundle\x00"):
            out, pos = [], 16
            while pos < len(data):
                (size,) = struct.unpack_from(">i", data, pos)
                pos += 4
                out += parse_osc(data[pos:pos + size])
                pos += size
            return out
        addr, pos = _read_str(data, 0)
        if not addr.startswith("/"):
            raise ValueError("indirizzo OSC non valido")
        tags, pos = _read_str(data, pos) if pos < len(data) else (",", pos)
        args: list = []
        for t in tags[1:]:
            if t == "i":
                args.append(struct.unpack_from(">i", data, pos)[0]); pos += 4
            elif t == "f":
                args.append(struct.unpack_from(">f", data, pos)[0]); pos += 4
            elif t == "d":
                args.append(struct.unpack_from(">d", data, pos)[0]); pos += 8
            elif t == "s":
                s, pos = _read_str(data, pos); args.append(s)
            elif t == "T":
                args.append(True)
            elif t == "F":
                args.append(False)
            elif t in "NI":
                args.append(None)
            else:
                raise ValueError(f"tipo OSC non supportato: {t}")
        return [(addr, args)]
    except (struct.error, ValueError, IndexError) as e:
        raise ValueError(f"pacchetto OSC non valido: {e}") from e


def build_osc(addr: str, *args) -> bytes:
    """Costruisce un messaggio OSC (utile per i test e per inviare feedback)."""
    def s(x: str) -> bytes:
        b = x.encode() + b"\x00"
        return b + b"\x00" * (-len(b) % 4)
    tags, body = ",", b""
    for a in args:
        if isinstance(a, bool):
            tags += "T" if a else "F"
        elif isinstance(a, int):
            tags += "i"; body += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"; body += struct.pack(">f", a)
        else:
            tags += "s"; body += s(str(a))
    return s(addr) + s(tags) + body


def _value(args: list) -> float:
    if not args or args[0] is None:
        return 1.0
    v = args[0]
    if isinstance(v, str):
        raise ControlError("valore stringa non valido")
    return 1.0 if v is True else 0.0 if v is False else float(v)


def dispatch(runner: ActionRunner, addr: str, args: list) -> None:
    parts = [unquote(p) for p in addr.strip("/").split("/")]
    head = parts[0]
    if head == "cue" and len(parts) == 2:
        runner.run("cue", {"cue": parts[1]}, _value(args))
    elif head == "fixture" and len(parts) == 3:
        runner.run("fixture", {"fixture": parts[1], "channel": parts[2]}, _value(args))
    elif head in ("master", "bpm", "tap", "blackout", "freeze", "blind") and len(parts) == 1:
        v = _value(args)
        if head == "bpm" and args and not isinstance(args[0], bool) and float(args[0]) > 1:
            v = (float(args[0]) - 20) / 280    # accetta anche BPM reali (es. 128)
        runner.run(head, {}, v)
    else:
        raise ControlError(f"indirizzo OSC sconosciuto: {addr}")


class OscServer:
    def __init__(self, runner: ActionRunner, port: int = DEFAULT_PORT, host: str = "0.0.0.0"):
        self.runner, self.port, self.host = runner, port, host
        self.errors: list[str] = []
        self.log = None     # ControlLog opzionale
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self.port = self._sock.getsockname()[1]   # utile con porta 0 nei test
        self._sock.settimeout(0.2)
        self._thread = threading.Thread(target=self._loop, name="osc-in", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        sock = self._sock
        while sock is self._sock:
            try:
                data, src = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                for addr, args in parse_osc(data):
                    msg = addr + (" " + " ".join(str(a) for a in args) if args else "")
                    try:
                        dispatch(self.runner, addr, args)
                        if self.log:
                            self.log.add("osc", src[0], msg, "Azione eseguita", "ok")
                    except (ValueError, KeyError) as e:
                        if self.log:
                            self.log.add("osc", src[0], msg, f"Azione non valida: {e}", "invalid")
                        raise
            except (ValueError, KeyError) as e:   # input esterno: mai crashare il thread
                self.errors.append(str(e))
                del self.errors[:-20]

    def stop(self) -> None:
        sock, self._sock = self._sock, None
        if sock:
            sock.close()
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
