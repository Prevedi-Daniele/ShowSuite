"""Azioni di controllo esterno (OSC, MIDI). Valori continui 0.0-1.0."""
from __future__ import annotations

ACTIONS = {
    "cue": "Avvia/ferma un cue (args: cue)",
    "master": "Grand Master (continuo)",
    "bpm": "BPM (continuo 20-300)",
    "tap": "Tap tempo",
    "blackout": "Blackout (on/off)",
    "freeze": "Freeze (on/off)",
    "blind": "Blind (on/off)",
    "shift": "Tasto Shift del controller (le altre mappature con Shift valgono solo mentre è premuto)",
    "fixture": "Canale di un fixture (args: fixture, channel; continuo)",
}


class ControlError(ValueError):
    pass


class ActionRunner:
    def __init__(self, engine):
        self.engine = engine
        self.on_select_page = None        # callback(nome pagina) impostato dalla UI
        self.on_select_fixtures = None    # callback(nomi, selezionare: bool)

    def run(self, action: str, args: dict | None = None, value: float = 1.0) -> None:
        """`value`: 0.0-1.0. Per i pulsanti >0 = premuto; le azioni on/off seguono il valore."""
        a, e = args or {}, self.engine
        value = max(0.0, min(1.0, float(value)))
        if action == "cue":
            cue = self._cue(a.get("cue"))
            on = value > 0
            if cue.toggle:
                if on:               # i pulsanti toggle reagiscono solo alla pressione
                    e.live.trigger(cue)
            else:
                e.live.trigger(cue) if on else e.live.release(cue)
        elif action == "shift":
            pass                       # gestito da MidiController (stato del tasto)
        elif action == "master":
            e.grand_master = value
        elif action == "bpm":
            e.beat.set_bpm(20 + value * 280)
        elif action == "tap":
            if value > 0:
                e.beat.tap()
        elif action in ("blackout", "freeze", "blind"):
            on = value > 0
            if action == "freeze":
                e.set_freeze(on)
            else:
                setattr(e, action, on)
        elif action == "fixture":
            fx = e.project.patch.find(a.get("fixture", ""))   # KeyError se non esiste
            ch = next((c for c in fx.profile.channels if c.name == a.get("channel")), None)
            if ch is None:
                raise ControlError(f"canale sconosciuto: {a.get('channel')}")
            e.set_value(fx.name, ch.name, round(value * (65535 if ch.fine else 255)))
        else:
            raise ControlError(f"azione sconosciuta: {action}")

    def _cue(self, ref):
        cues = self.engine.project.cues
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            i = int(ref) - 1       # numerazione da 1
            if 0 <= i < len(cues):
                return cues[i]
        for c in cues:
            if c.name == ref:
                return c
        raise ControlError(f"cue non trovato: {ref}")
