"""Open DMX / interfacce FTDI FT232R economiche (nessun microcontrollore).

Il PC genera break + MAB + dati. Su Windows/Linux il timing del break è
impreciso (jitter ~1 ms): in pratica funziona con quasi tutti i fixture.
"""
from __future__ import annotations

import time

from .base import OutputDriver


class OpenDmxDriver(OutputDriver):
    def __init__(self, port: str, universe: int = 1, break_us: int = 150, mab_us: int = 20):
        self.port = port
        self.universe = universe  # universo da trasmettere su questa interfaccia
        self.break_s = break_us / 1e6
        self.mab_s = mab_us / 1e6
        self._ser = None

    def open(self) -> None:
        import serial  # importato qui: non serve per Art-Net/sACN
        self._ser = serial.Serial(self.port, baudrate=250000, bytesize=serial.EIGHTBITS,
                                  parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)

    def send(self, universe: int, data: bytes) -> None:
        if universe != self.universe:
            return
        ser = self._ser
        ser.break_condition = True
        time.sleep(self.break_s)
        ser.break_condition = False
        time.sleep(self.mab_s)
        ser.write(b"\x00" + data.ljust(512, b"\x00")[:512])
        ser.flush()

    def close(self) -> None:
        if self._ser:
            self._ser.close()
            self._ser = None
