"""MIDI: mappature con MIDI-learn. Funziona con qualunque controller (es. Arturia MiniLab 3).

Non assumiamo la mappa dei pad/manopole del controller: l'utente "insegna" ogni
controllo (Impara → tocca il pad o gira la manopola).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ActionRunner, ControlError


@dataclass
class MidiMapping:
    kind: str        # "note" | "cc"
    channel: int     # 0-15
    number: int      # nota o numero CC (0-127)
    action: str
    args: dict = field(default_factory=dict)

    def key(self) -> tuple:
        return (self.kind, self.channel, self.number)


class MidiController:
    def __init__(self, runner: ActionRunner, mappings: list[MidiMapping] | None = None):
        self.runner = runner
        self.mappings: list[MidiMapping] = mappings if mappings is not None else []
        self._learn: tuple[str, dict] | None = None
        self.on_learned = None   # callback(MidiMapping)
        self.errors: list[str] = []
        self._port = None
        self.clock = None   # MidiClockSync opzionale (imposta dall'esterno)

    # --- learn ---
    def learn(self, action: str, args: dict | None = None) -> None:
        self._learn = (action, args or {})

    def cancel_learn(self) -> None:
        self._learn = None

    @property
    def learning(self) -> bool:
        return self._learn is not None

    # --- messaggi ---
    def handle(self, kind: str, channel: int, number: int, value: int) -> None:
        """kind: "note_on" | "note_off" | "cc". value 0-127."""
        k = "cc" if kind == "cc" else "note"
        if kind == "note_off":
            value = 0
        if self._learn and (k == "cc" or (kind == "note_on" and value > 0)):
            action, args = self._learn
            self._learn = None
            self.mappings[:] = [m for m in self.mappings if m.key() != (k, channel, number)]  # stessa lista del progetto
            m = MidiMapping(k, channel, number, action, args)
            self.mappings.append(m)
            if self.on_learned:
                self.on_learned(m)
            return
        for m in self.mappings:
            if m.key() == (k, channel, number):
                try:
                    self.runner.run(m.action, m.args, value / 127.0)
                except (ControlError, KeyError) as e:
                    self.errors.append(str(e)); del self.errors[:-20]

    def _on_message(self, msg) -> None:
        if self.clock is not None and msg.type in ("clock", "start", "stop", "continue"):
            getattr(self.clock, "on_" + msg.type)()
            return
        if msg.type in ("note_on", "note_off"):
            self.handle(msg.type, msg.channel, msg.note, msg.velocity)
        elif msg.type == "control_change":
            self.handle("cc", msg.channel, msg.control, msg.value)

    # --- porta (mido + python-rtmidi, opzionali) ---
    @staticmethod
    def list_ports() -> list[str]:
        try:
            import mido
            return mido.get_input_names()
        except Exception:
            return []

    def open(self, name: str) -> None:
        import mido   # ImportError esplicito se manca (pip install showsuite[midi])
        self.close()
        self._port = mido.open_input(name, callback=self._on_message)

    def close(self) -> None:
        if self._port:
            self._port.close()
            self._port = None
