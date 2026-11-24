"""Enttec DMX USB Pro / Pro Mk2 e compatibili (DMXking ultraDMX, Jese DMX-TRI, Robe Universal Interface).

L'interfaccia ha un microcontrollore: il PC invia pacchetti "Output Only Send DMX" (label 6) e il
chip genera break e timing DMX da solo (nessun jitter come con le interfacce Open DMX).
"""
from __future__ import annotations

from .base import OutputDriver

START, END = 0x7E, 0xE7
LABEL_SEND_DMX = 6


def build_packet(data: bytes, label: int = LABEL_SEND_DMX) -> bytes:
    """Pacchetto: 7E, label, lunghezza LSB, lunghezza MSB, start code DMX (0) + dati, E7."""
    payload = b"\x00" + bytes(data[:512])
    n = len(payload)
    return bytes([START, label, n & 0xFF, n >> 8]) + payload + bytes([END])


class EnttecProDriver(OutputDriver):
    def __init__(self, port: str, universe: int = 1, port_index: int = 1):
        self.port, self.universe, self.port_index = port, universe, port_index   # port_index 2: seconda porta (Mk2)
        self._ser = None

    def open(self) -> None:
        import serial
        self._ser = serial.Serial(self.port, baudrate=57600, timeout=0.1, write_timeout=0.5)

    def send(self, universe: int, data: bytes) -> None:
        if universe != self.universe:
            return
        label = LABEL_SEND_DMX if self.port_index == 1 else 0xA9      # 0xA9 = porta 2 del Pro Mk2
        self._ser.write(build_packet(data, label))

    def close(self) -> None:
        if self._ser:
            self._ser.close(); self._ser = None
