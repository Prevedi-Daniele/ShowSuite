"""Annulla/Ripristina a istantanee del progetto (byte del file .showsuite-light)."""
from __future__ import annotations


class UndoStack:
    def __init__(self, initial: bytes, limit: int = 100):
        self.states = [initial]
        self.pos = 0
        self.limit = limit

    def record(self, data: bytes) -> bool:
        """Registra un nuovo stato se diverso dall'attuale; scarta il ramo "redo". True se registrato."""
        if data == self.states[self.pos]:
            return False
        del self.states[self.pos + 1:]
        self.states.append(data)
        if len(self.states) > self.limit:
            del self.states[0]
        self.pos = len(self.states) - 1
        return True

    @property
    def can_undo(self) -> bool:
        return self.pos > 0

    @property
    def can_redo(self) -> bool:
        return self.pos < len(self.states) - 1

    def undo(self) -> bytes | None:
        if not self.can_undo:
            return None
        self.pos -= 1
        return self.states[self.pos]

    def redo(self) -> bytes | None:
        if not self.can_redo:
            return None
        self.pos += 1
        return self.states[self.pos]
