from __future__ import annotations

from abc import ABC, abstractmethod


class OutputDriver(ABC):
    """Destinazione di uscita DMX. `send` riceve 512 byte per un universo."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def send(self, universe: int, data: bytes) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
