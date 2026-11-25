"""Codec dei protocolli: MIDI voce, MIDI Show Control, SysEx, MIDI Timecode, LTC, file MIDI standard.

Solo byte e calcoli: nessun accesso a porte o schede audio (vedi outputs.py)."""
from __future__ import annotations

import math
import struct

# indice formato timecode QLab -> (frame al secondo nominali, rate reale, drop frame)
TIMECODE_FORMATS = {0: (24, 24.0, False), 1: (25, 25.0, False), 2: (30, 30000 / 1001, True), 3: (30, 30.0, False),
                    4: (30, 30000 / 1001, False), 5: (30, 30000 / 1001, True), 6: (60, 60.0, False),
                    7: (60, 60000 / 1001, False), 8: (60, 60.0, True), 9: (60, 60000 / 1001, True),
                    10: (50, 50.0, False), 11: (24, 24000 / 1001, False)}
MTC_RATE_CODES = {24: 0, 25: 1, 30: 3}

MSC_COMMANDS = {"GO": 1, "STOP": 2, "RESUME": 3, "TIMED_GO": 4, "LOAD": 5, "SET": 6, "FIRE": 7, "ALL_OFF": 8,
                "RESTORE": 9, "RESET": 10, "GO_OFF": 11, "STANDBY_PLUS": 13, "STANDBY_MINUS": 14,
                "SEQUENCE_PLUS": 15, "SEQUENCE_MINUS": 16, "START_CLOCK": 17, "STOP_CLOCK": 18, "ZERO_CLOCK": 19,
                "SET_CLOCK": 20, "MTC_CHASE_ON": 21, "MTC_CHASE_OFF": 22, "OPEN_CUE_LIST": 23,
                "CLOSE_CUE_LIST": 24, "OPEN_CUE_PATH": 25, "CLOSE_CUE_PATH": 26}
MSC_COMMANDS_BY_NUMBER = {value: key for key, value in MSC_COMMANDS.items()}
MSC_LIGHTING = 0x01
MSC_SOUND = 0x10
MSC_VIDEO = 0x30
MSC_ALL_TYPES = 0x7F
MSC_ACCEPTED_FORMATS = (MSC_LIGHTING, MSC_SOUND, MSC_VIDEO, MSC_ALL_TYPES)


def frames_per_second(format_index: int) -> int:
    return TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])[0]


def timecode_to_frames(hours: int, minutes: int, seconds: int, frames: int, format_index: int) -> int:
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    total_minutes = hours * 60 + minutes
    count = ((total_minutes * 60) + seconds) * nominal + frames
    if drop == True:
        dropped = 2 if nominal == 30 else 4
        count = count - dropped * (total_minutes - total_minutes // 10)
    return count


def frames_to_timecode(count: int, format_index: int) -> tuple[int, int, int, int]:
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    if drop == True:
        dropped = 2 if nominal == 30 else 4
        per_ten_minutes = nominal * 600 - dropped * 9
        per_minute = nominal * 60 - dropped
        tens, remainder = divmod(count, per_ten_minutes)
        if remainder < dropped:
            count = count + dropped * 9 * tens
        else:
            count = count + dropped * 9 * tens + dropped * ((remainder - dropped) // per_minute)
    frames = count % nominal
    total_seconds = count // nominal
    return total_seconds // 3600, (total_seconds // 60) % 60, total_seconds % 60, frames


def timecode_to_seconds(hours: int, minutes: int, seconds: int, frames: int, format_index: int) -> float:
    """Secondi reali di un timecode (con rate frazionari 29.97/23.976 e drop frame)."""
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    return timecode_to_frames(hours, minutes, seconds, frames, format_index) / real


def seconds_to_timecode(value: float, format_index: int) -> tuple[int, int, int, int]:
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    return frames_to_timecode(int(math.floor(value * real + 1e-9)), format_index)


def parse_timecode_text(text: str) -> tuple[int, int, int, int]:
    pieces = [int(piece) for piece in text.replace(";", ":").replace(".", ":").split(":")]
    while len(pieces) < 4:
        pieces.insert(0, 0)
    return pieces[0], pieces[1], pieces[2], pieces[3]


# ---------------------------------------------------------------- MIDI voce
VOICE_STATUS_BASES = [0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xD0, 0xE0]


def voice_message(status_index: int, channel: int, byte1: int, byte2: int = 0) -> bytes:
    """status_index: 0 note off, 1 note on, 2 key pressure, 3 control change, 4 program, 5 channel pressure, 6 bend.

    channel 1..16. Per il pitch bend byte1 = LSB, byte2 = MSB."""
    status = VOICE_STATUS_BASES[status_index] | ((channel - 1) & 0x0F)
    if status_index in (4, 5):
        return bytes([status, byte1 & 0x7F])
    return bytes([status, byte1 & 0x7F, byte2 & 0x7F])


def pitch_bend_message(channel: int, value: int) -> bytes:
    value = max(0, min(16383, value))
    return voice_message(6, channel, value & 0x7F, value >> 7)


# ---------------------------------------------------------------- SysEx e MSC
def sysex_from_text(text: str) -> bytes:
    tokens = text.replace(",", " ").split()
    data = bytes(int(token, 16) for token in tokens)
    if len(data) == 0:
        raise ValueError("SysEx vuoto")
    if data[0] != 0xF0:
        data = b"\xF0" + data
    if data[-1] != 0xF7:
        data = data + b"\xF7"
    for byte in data[1:-1]:
        if byte > 0x7F:
            raise ValueError("byte SysEx > 7F")
    return data


def msc_message(command_format: int, command: int, device_id: int = 0, q_number: str = "", q_list: str = "",
                q_path: str = "", control_number: int = 0, control_value: int = 0,
                timecode: tuple | None = None, timecode_format: int = 1) -> bytes:
    body = bytearray([0xF0, 0x7F, device_id & 0x7F, 0x02, command_format & 0x7F, command & 0x7F])
    if command == MSC_COMMANDS["SET"]:
        body.extend([control_number & 0x7F, (control_number >> 7) & 0x7F, control_value & 0x7F,
                     (control_value >> 7) & 0x7F])
        if timecode is not None:
            body.extend(mtc_full_time_bytes(timecode, timecode_format))
    elif command in (1, 2, 3, 4, 5, 7, 9, 10, 11, 23, 24, 25, 26):
        if q_number != "":
            body.extend(q_number.encode("ascii"))
            if q_list != "":
                body.append(0)
                body.extend(q_list.encode("ascii"))
                if q_path != "":
                    body.append(0)
                    body.extend(q_path.encode("ascii"))
    body.append(0xF7)
    return bytes(body)


def parse_msc(data: bytes) -> dict | None:
    """Decodifica un messaggio MSC. Restituisce None se non è MSC."""
    if len(data) < 7 or data[0] != 0xF0 or data[1] != 0x7F or data[3] != 0x02 or data[-1] != 0xF7:
        return None
    result = {"device_id": data[2], "command_format": data[4], "command": data[5], "q_number": "", "q_list": "",
              "q_path": ""}
    payload = data[6:-1]
    if data[5] == MSC_COMMANDS["SET"]:
        if len(payload) >= 4:
            result["control_number"] = payload[0] | (payload[1] << 7)
            result["control_value"] = payload[2] | (payload[3] << 7)
        return result
    parts = payload.split(b"\x00")
    names = ["q_number", "q_list", "q_path"]
    for index, part in enumerate(parts[:3]):
        result[names[index]] = part.decode("ascii", errors="replace")
    return result


# ---------------------------------------------------------------- MTC
def mtc_full_time_bytes(timecode: tuple, format_index: int) -> bytes:
    hours, minutes, seconds, frames = timecode[:4]
    nominal = frames_per_second(format_index)
    code = MTC_RATE_CODES.get(nominal, 1)
    if format_index in (2, 4, 5):
        code = 2
    return bytes([(code << 5) | (hours & 0x1F), minutes & 0x3F, seconds & 0x3F, frames & 0x1F])


def mtc_full_frame(timecode: tuple, format_index: int) -> bytes:
    return b"\xF0\x7F\x7F\x01\x01" + mtc_full_time_bytes(timecode, format_index) + b"\xF7"


def mtc_quarter_frames(timecode: tuple, format_index: int) -> list[bytes]:
    hours, minutes, seconds, frames = timecode[:4]
    code_byte = mtc_full_time_bytes(timecode, format_index)[0] >> 5
    nibbles = [frames & 0x0F, frames >> 4, seconds & 0x0F, seconds >> 4, minutes & 0x0F, minutes >> 4,
               hours & 0x0F, ((hours >> 4) & 0x01) | (code_byte << 1)]
    return [bytes([0xF1, (index << 4) | nibble]) for index, nibble in enumerate(nibbles)]


class MtcDecoder:
    """Ricostruisce il timecode da quarter frame (F1) e full frame (SysEx)."""

    def __init__(self):
        self.nibbles = [0] * 8
        self.mask = 0
        self.last: tuple | None = None
        self.format_index = 1

    def feed(self, data: bytes) -> tuple | None:
        if len(data) == 10 and data[:5] == b"\xF0\x7F\x7F\x01\x01":
            return self._from_full(data[5:9])
        if len(data) == 2 and data[0] == 0xF1:
            piece = data[1] >> 4
            if piece == 0:
                self.mask = 0
            self.nibbles[piece] = data[1] & 0x0F
            self.mask = self.mask | (1 << piece)
            if piece == 7 and self.mask == 0xFF:
                frames = self.nibbles[0] | (self.nibbles[1] << 4)
                seconds = self.nibbles[2] | (self.nibbles[3] << 4)
                minutes = self.nibbles[4] | (self.nibbles[5] << 4)
                hours = self.nibbles[6] | ((self.nibbles[7] & 1) << 4)
                self._set_format((self.nibbles[7] >> 1) & 3)
                self.last = (hours, minutes, seconds, frames)
                return self.last
        return None

    def _set_format(self, code: int) -> None:
        self.format_index = {0: 0, 1: 1, 2: 2, 3: 3}[code]

    def _from_full(self, payload: bytes) -> tuple:
        self._set_format(payload[0] >> 5)
        self.last = (payload[0] & 0x1F, payload[1], payload[2], payload[3])
        return self.last


# ---------------------------------------------------------------- LTC
def ltc_frame_bits(timecode: tuple, format_index: int) -> list[int]:
    """80 bit di una frame LTC (SMPTE 12M), LSB first per ogni campo, con sync word."""
    hours, minutes, seconds, frames = timecode[:4]
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    bits = [0] * 80

    def put(start: int, count: int, value: int) -> None:
        for index in range(count):
            bits[start + index] = (value >> index) & 1

    put(0, 4, frames % 10)
    put(8, 2, frames // 10)
    bits[10] = 1 if drop else 0
    put(16, 4, seconds % 10)
    put(24, 3, seconds // 10)
    put(32, 4, minutes % 10)
    put(40, 3, minutes // 10)
    put(48, 4, hours % 10)
    put(56, 2, hours // 10)
    sync = [0, 0] + [1] * 12 + [0, 1]
    for index, value in enumerate(sync):
        bits[64 + index] = value
    ones = sum(bits[:27]) + sum(bits[28:])
    # il bit di parità (27 per 30fps, 59 per 25fps) rende pari il numero di uno
    parity_index = 59 if nominal == 25 else 27
    bits[parity_index] = 0
    if sum(bits) % 2 == 1:
        bits[parity_index] = 1
    return bits


def ltc_encode_frame(timecode: tuple, format_index: int, sample_rate: int = 48000, level: float = 0.5,
                     state: dict | None = None) -> list[float]:
    """Campioni biphase-mark di una frame. `state` mantiene la polarità tra frame consecutive."""
    nominal, real, drop = TIMECODE_FORMATS.get(format_index, TIMECODE_FORMATS[1])
    if state is None:
        state = {"polarity": 1.0, "residual": 0.0}
    bits = ltc_frame_bits(timecode, format_index)
    samples_per_bit = sample_rate / real / 80.0
    out: list[float] = []
    position = state["residual"]
    for bit in bits:
        state["polarity"] = -state["polarity"]
        halves = 2 if bit == 1 else 1
        for half in range(halves):
            position = position + samples_per_bit / halves
            count = int(position)
            position = position - count
            out.extend([state["polarity"] * level] * count)
            if halves == 2 and half == 0:
                state["polarity"] = -state["polarity"]
    state["residual"] = position
    return out


class LtcDecoder:
    """Decodifica LTC da campioni float (cerca la sync word nel flusso biphase)."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.previous = 0.0
        self.since_edge = 0
        self.bit_length = 0.0
        self.bits: list[int] = []
        self.pending_half = False
        self.last: tuple | None = None
        self.format_index = 1
        self.drop = False

    def feed(self, samples) -> list[tuple]:
        found = []
        for sample in samples:
            self.since_edge = self.since_edge + 1
            if (sample >= 0) != (self.previous >= 0) and self.previous != 0.0:
                result = self._edge(self.since_edge)
                self.since_edge = 0
                if result is not None:
                    found.append(result)
            if sample != 0.0:
                self.previous = sample
        return found

    def _edge(self, length: int) -> tuple | None:
        if self.bit_length == 0.0:
            self.bit_length = float(length) if length > 20 else 0.0
            if self.bit_length == 0.0:
                return None
        ratio = length / self.bit_length
        if ratio > 0.75:
            if ratio > 1.4:
                self.bit_length = float(length)
            self.pending_half = False
            self.bit_length = 0.9 * self.bit_length + 0.1 * length
            self.bits.append(0)
        else:
            if self.pending_half == False:
                self.pending_half = True
                return None
            self.pending_half = False
            self.bit_length = 0.9 * self.bit_length + 0.2 * length
            self.bits.append(1)
        if len(self.bits) > 160:
            self.bits = self.bits[-160:]
        return self._try_decode()

    def _try_decode(self) -> tuple | None:
        sync = [0, 0] + [1] * 12 + [0, 1]
        if len(self.bits) >= 80 and self.bits[-16:] == sync:
            frame = self.bits[-80:]

            def get(start: int, count: int) -> int:
                return sum(frame[start + index] << index for index in range(count))

            frames = get(0, 4) + 10 * get(8, 2)
            seconds = get(16, 4) + 10 * get(24, 3)
            minutes = get(32, 4) + 10 * get(40, 3)
            hours = get(48, 4) + 10 * get(56, 2)
            self.drop = frame[10] == 1
            self.last = (hours, minutes, seconds, frames)
            self.bits = []
            return self.last
        return None


# ---------------------------------------------------------------- file MIDI standard
def _read_variable(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[offset]
        offset = offset + 1
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80 == 0:
            return value, offset


def parse_midi_file(data: bytes) -> tuple[list[tuple[float, bytes]], float]:
    """SMF 0/1 -> ([(secondi, messaggio)], durata). Gestisce tempo map. Non gestisce SMPTE division."""
    if data[:4] != b"MThd":
        raise ValueError("non è un file MIDI")
    format_type, track_count, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError("division SMPTE non supportata")
    offset = 14
    raw_events: list[tuple[int, int, bytes]] = []
    order = 0
    for track in range(track_count):
        if data[offset:offset + 4] != b"MTrk":
            raise ValueError("traccia non valida")
        size = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        position = offset + 8
        end = position + size
        tick = 0
        running = 0
        while position < end:
            delta, position = _read_variable(data, position)
            tick = tick + delta
            status = data[position]
            if status == 0xFF:
                kind = data[position + 1]
                length, position2 = _read_variable(data, position + 2)
                payload = data[position2:position2 + length]
                position = position2 + length
                if kind == 0x51:
                    raw_events.append((tick, order, b"\xFF\x51" + payload))
                    order = order + 1
            elif status in (0xF0, 0xF7):
                length, position2 = _read_variable(data, position + 1)
                payload = data[position:position2 + length]
                position = position2 + length
                raw_events.append((tick, order, payload if status == 0xF0 else payload))
                order = order + 1
            else:
                if status & 0x80:
                    running = status
                    position = position + 1
                size_data = 1 if (running & 0xF0) in (0xC0, 0xD0) else 2
                payload = bytes([running]) + data[position:position + size_data]
                position = position + size_data
                raw_events.append((tick, order, payload))
                order = order + 1
        offset = end
    raw_events.sort(key=lambda item: (item[0], item[1]))
    events = []
    tempo = 500000
    seconds = 0.0
    last_tick = 0
    for tick, index, message in raw_events:
        seconds = seconds + (tick - last_tick) * tempo / 1e6 / division
        last_tick = tick
        if message[:2] == b"\xFF\x51":
            tempo = int.from_bytes(message[2:5], "big")
        else:
            events.append((seconds, message))
    return events, seconds
