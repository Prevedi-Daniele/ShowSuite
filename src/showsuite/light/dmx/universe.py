"""Universo DMX: 512 canali, valori 0-255."""
from __future__ import annotations

DMX_CHANNELS = 512


class Universe:
    def __init__(self, number: int):
        if not 0 <= number <= 32767:
            raise ValueError("numero universo fuori range (0-32767)")
        self.number = number
        self._data = bytearray(DMX_CHANNELS)

    def set(self, channel: int, value: int) -> None:
        """Canale 1-512, valore limitato a 0-255."""
        if not 1 <= channel <= DMX_CHANNELS:
            raise ValueError(f"canale {channel} fuori range (1-512)")
        self._data[channel - 1] = max(0, min(255, int(value)))

    def get(self, channel: int) -> int:
        if not 1 <= channel <= DMX_CHANNELS:
            raise ValueError(f"canale {channel} fuori range (1-512)")
        return self._data[channel - 1]

    def set_range(self, start: int, values) -> None:
        for i, v in enumerate(values):
            self.set(start + i, v)

    def clear(self) -> None:
        self._data[:] = bytes(DMX_CHANNELS)

    def snapshot(self) -> bytes:
        return bytes(self._data)
