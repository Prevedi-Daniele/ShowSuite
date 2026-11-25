"""Codec OSC 1.0/1.1, framing SLIP, pattern matching OSC e trasporti (UDP, TCP/SLIP, testo semplice).

Nessuna dipendenza esterna. I trasporti non conoscono il significato dei messaggi: consegnano (indirizzo, argomenti)
a un callback e inviano le risposte che il callback restituisce."""
from __future__ import annotations

import re
import socket
import struct
import threading

SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD


class Impulse:
    def __eq__(self, other):
        return isinstance(other, Impulse)

    def __repr__(self):
        return "Impulse()"


def _pad(data: bytes) -> bytes:
    return data + b"\x00" * (4 - len(data) % 4)


def _read_string(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(b"\x00", offset)
    text = data[offset:end].decode("utf-8", errors="replace")
    return text, (end + 4) & ~3


def encode_message(address: str, arguments: list | tuple = ()) -> bytes:
    tags = ","
    body = b""
    for value in arguments:
        if isinstance(value, bool):
            tags = tags + ("T" if value else "F")
        elif isinstance(value, Impulse):
            tags = tags + "I"
        elif value is None:
            tags = tags + "N"
        elif isinstance(value, int):
            if -2147483648 <= value <= 2147483647:
                tags = tags + "i"
                body = body + struct.pack(">i", value)
            else:
                tags = tags + "h"
                body = body + struct.pack(">q", value)
        elif isinstance(value, float):
            tags = tags + "f"
            body = body + struct.pack(">f", value)
        elif isinstance(value, (bytes, bytearray)):
            tags = tags + "b"
            body = body + struct.pack(">i", len(value)) + _pad_blob(bytes(value))
        else:
            tags = tags + "s"
            body = body + _pad(str(value).encode("utf-8"))
    return _pad(address.encode("utf-8")) + _pad(tags.encode("ascii")) + body


def _pad_blob(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


def decode_packet(data: bytes) -> list[tuple[str, list]]:
    """Decodifica un messaggio o un bundle (ricorsivo) in una lista di (indirizzo, argomenti)."""
    if data.startswith(b"#bundle"):
        messages = []
        offset = 16
        while offset + 4 <= len(data):
            size = struct.unpack(">i", data[offset:offset + 4])[0]
            offset = offset + 4
            messages.extend(decode_packet(data[offset:offset + size]))
            offset = offset + size
        return messages
    address, offset = _read_string(data, 0)
    if offset >= len(data):
        return [(address, [])]
    tags, offset = _read_string(data, offset)
    arguments: list = []
    for tag in tags[1:]:
        if tag == "i":
            arguments.append(struct.unpack(">i", data[offset:offset + 4])[0])
            offset = offset + 4
        elif tag == "f":
            arguments.append(struct.unpack(">f", data[offset:offset + 4])[0])
            offset = offset + 4
        elif tag == "h":
            arguments.append(struct.unpack(">q", data[offset:offset + 8])[0])
            offset = offset + 8
        elif tag == "d":
            arguments.append(struct.unpack(">d", data[offset:offset + 8])[0])
            offset = offset + 8
        elif tag == "t":
            offset = offset + 8
        elif tag in ("s", "S"):
            text, offset = _read_string(data, offset)
            arguments.append(text)
        elif tag == "b":
            size = struct.unpack(">i", data[offset:offset + 4])[0]
            offset = offset + 4
            arguments.append(data[offset:offset + size])
            offset = (offset + size + 3) & ~3
        elif tag == "T":
            arguments.append(True)
        elif tag == "F":
            arguments.append(False)
        elif tag == "N":
            arguments.append(None)
        elif tag == "I":
            arguments.append(Impulse())
        elif tag == "c":
            arguments.append(chr(struct.unpack(">i", data[offset:offset + 4])[0]))
            offset = offset + 4
        else:
            break
    return [(address, arguments)]


def slip_encode(packet: bytes) -> bytes:
    out = bytearray([SLIP_END])
    for byte in packet:
        if byte == SLIP_END:
            out.extend([SLIP_ESC, SLIP_ESC_END])
        elif byte == SLIP_ESC:
            out.extend([SLIP_ESC, SLIP_ESC_ESC])
        else:
            out.append(byte)
    out.append(SLIP_END)
    return bytes(out)


class SlipDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.escaped = False

    def feed(self, data: bytes) -> list[bytes]:
        packets = []
        for byte in data:
            if byte == SLIP_END:
                if len(self.buffer) > 0:
                    packets.append(bytes(self.buffer))
                self.buffer = bytearray()
                self.escaped = False
            elif self.escaped == True:
                self.buffer.append(SLIP_END if byte == SLIP_ESC_END else SLIP_ESC if byte == SLIP_ESC_ESC else byte)
                self.escaped = False
            elif byte == SLIP_ESC:
                self.escaped = True
            else:
                self.buffer.append(byte)
        return packets


def pattern_to_regex(pattern: str) -> re.Pattern:
    """Pattern OSC (`*`, `?`, `[abc]`, `[a-z]`, `[!abc]`, `{a,b}`) in espressione regolare."""
    result = ""
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            result = result + ".*"
        elif character == "?":
            result = result + "."
        elif character == "[":
            end = pattern.find("]", index)
            if end == -1:
                result = result + re.escape(character)
            else:
                content = pattern[index + 1:end]
                negate = content.startswith("!")
                if negate == True:
                    content = content[1:]
                result = result + "[" + ("^" if negate else "") + content.replace("\\", "\\\\") + "]"
                index = end
        elif character == "{":
            end = pattern.find("}", index)
            if end == -1:
                result = result + re.escape(character)
            else:
                options = pattern[index + 1:end].split(",")
                result = result + "(?:" + "|".join(re.escape(option) for option in options) + ")"
                index = end
        else:
            result = result + re.escape(character)
        index = index + 1
    return re.compile("^" + result + "$")


def has_wildcard(text: str) -> bool:
    return any(character in text for character in "*?[{")


def pattern_matches(pattern: str, text: str) -> bool:
    if has_wildcard(pattern) == False:
        return pattern == text
    return pattern_to_regex(pattern).match(text) is not None


def parse_plain_text(line: str) -> tuple[str, list]:
    """`/cue/1/name Hello world` -> ('/cue/1/name', ['Hello', 'world']); numeri diventano int/float."""
    tokens = []
    current = ""
    quoted = False
    for character in line.strip():
        if character == '"':
            quoted = quoted == False
        elif character == " " and quoted == False:
            if current != "":
                tokens.append(current)
                current = ""
        else:
            current = current + character
    if current != "":
        tokens.append(current)
    if len(tokens) == 0:
        return "", []
    arguments: list = []
    for token in tokens[1:]:
        arguments.append(parse_argument(token))
    return tokens[0], arguments


def parse_argument(token: str):
    if token == "\\T":
        return True
    if token == "\\F":
        return False
    if token == "\\I":
        return Impulse()
    if token == "\\N":
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token.replace(",", "."))
    except ValueError:
        return token


class OscServer:
    """Server UDP (+ risposte), TCP/SLIP e testo semplice. `callback(address, args, client)` -> None.

    `client` è un oggetto `ClientHandle` con metodo `send(address, args)`."""

    def __init__(self, callback, host: str = "0.0.0.0", port: int = 53000, reply_port: int = 53001,
                 plain_port: int = 53535):
        self.callback = callback
        self.host = host
        self.port = port
        self.reply_port = reply_port
        self.plain_port = plain_port
        self.running = False
        self.threads: list[threading.Thread] = []
        self.udp_socket: socket.socket | None = None
        self.tcp_socket: socket.socket | None = None
        self.plain_socket: socket.socket | None = None
        self.connections: list = []
        self.clients: dict = {}

    def start(self) -> None:
        self.running = True
        self.udp_socket = self._bind(socket.SOCK_DGRAM, self.port)
        self.tcp_socket = self._bind(socket.SOCK_STREAM, self.port)
        self.tcp_socket.listen(8)
        self.plain_socket = self._bind(socket.SOCK_DGRAM, self.plain_port)
        for target in (self._udp_loop, self._tcp_accept_loop, self._plain_loop):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self.threads.append(thread)

    def _bind(self, kind: int, port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, kind)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, port))
        sock.settimeout(0.2)
        return sock

    def bound_ports(self) -> tuple[int, int, int]:
        return (self.udp_socket.getsockname()[1], self.tcp_socket.getsockname()[1],
                self.plain_socket.getsockname()[1])

    def stop(self) -> None:
        self.running = False
        for sock in (self.udp_socket, self.tcp_socket, self.plain_socket):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        for connection in list(self.connections):
            try:
                connection.close()
            except OSError:
                pass

    def _udp_loop(self) -> None:
        while self.running == True:
            try:
                data, address = self.udp_socket.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            key = ("udp", address[0])
            client = self.clients.get(key)
            if client is None:
                client = UdpClient(self.udp_socket, address[0], self.reply_port)
                self.clients[key] = client
            for packet_address, arguments in _safe_decode(data):
                self.callback(packet_address, arguments, client)

    def _plain_loop(self) -> None:
        while self.running == True:
            try:
                data, address = self.plain_socket.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            client = UdpClient(self.plain_socket, address[0], 0, silent=True)
            for line in data.decode("utf-8", errors="replace").splitlines():
                packet_address, arguments = parse_plain_text(line)
                if packet_address.startswith("/"):
                    self.callback(packet_address, arguments, client)

    def _tcp_accept_loop(self) -> None:
        while self.running == True:
            try:
                connection, address = self.tcp_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            connection.settimeout(0.2)
            self.connections.append(connection)
            thread = threading.Thread(target=self._tcp_client_loop, args=(connection, address), daemon=True)
            thread.start()
            self.threads.append(thread)

    def _tcp_client_loop(self, connection: socket.socket, address) -> None:
        client = TcpClient(connection)
        decoder = SlipDecoder()
        while self.running == True:
            try:
                data = connection.recv(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if data == b"":
                break
            for packet in decoder.feed(data):
                for packet_address, arguments in _safe_decode(packet):
                    self.callback(packet_address, arguments, client)
        client.closed = True
        if connection in self.connections:
            self.connections.remove(connection)
        try:
            connection.close()
        except OSError:
            pass


def _safe_decode(data: bytes) -> list:
    try:
        return decode_packet(data)
    except (ValueError, struct.error, IndexError):
        return []


class ClientHandle:
    transport = ""

    def __init__(self):
        self.closed = False
        self.state = None

    def send(self, address: str, arguments: list) -> None:
        raise NotImplementedError

    def identity(self) -> str:
        return ""


class UdpClient(ClientHandle):
    transport = "udp"

    def __init__(self, sock: socket.socket, host: str, reply_port: int, silent: bool = False):
        super().__init__()
        self.sock = sock
        self.host = host
        self.reply_port = reply_port
        self.silent = silent

    def send(self, address: str, arguments: list) -> None:
        if self.silent == True or self.reply_port == 0:
            return
        try:
            self.sock.sendto(encode_message(address, arguments), (self.host, self.reply_port))
        except OSError:
            pass

    def identity(self) -> str:
        return "udp:" + self.host


class TcpClient(ClientHandle):
    transport = "tcp"

    def __init__(self, connection: socket.socket):
        super().__init__()
        self.connection = connection
        self.lock = threading.Lock()

    def send(self, address: str, arguments: list) -> None:
        try:
            with self.lock:
                self.connection.sendall(slip_encode(encode_message(address, arguments)))
        except OSError:
            self.closed = True

    def identity(self) -> str:
        return "tcp:%d" % id(self)


class MemoryClient(ClientHandle):
    """Client in memoria per i test e per l'uso locale: raccoglie le risposte."""
    transport = "memory"

    def __init__(self, name: str = "memory"):
        super().__init__()
        self.name = name
        self.messages: list = []

    def send(self, address: str, arguments: list) -> None:
        self.messages.append((address, list(arguments)))

    def identity(self) -> str:
        return "memory:" + self.name
