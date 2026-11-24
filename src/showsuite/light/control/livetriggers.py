"""Live Triggers: Ableton Live pilota i cue via MIDI (canale 16, riservato), come nel manuale Lightkey.

Il manuale dice solo che i cue usano Note On (max 128 per pagina) sul canale 16; lo schema esatto non è
documentato, quindi lo definiamo noi:
  * Note On, nota = posizione del cue nella pagina (0-127), velocity = numero pagina (1-127, 1 = prima pagina);
    Note Off (o velocity 0) rilascia i cue "flash".
  * CC 0 = Select Page (valore = numero pagina, 1-based).
  * Azioni generiche: CC 1 Blackout, CC 2 Freeze, CC 3 Blind (valore > 0 = attivo).
I clip MIDI (.mid) da trascinare in Ableton si esportano con `export_clips`.
"""
from __future__ import annotations

import os

TRIGGER_CHANNEL = 15      # canale 16 (0-based)
MAX_CUES = 128
ACTIONS = {1: "blackout", 2: "freeze", 3: "blind"}


def bindings(project) -> list[dict]:
    """Elenco binding: [{page, page_index, note, cue, label}], saltando i cue esclusi e i testi."""
    out = []
    cues = {c.name: c for c in project.cues}
    for pi, page in enumerate(project.pages):
        n = 0
        for b in page.buttons:
            c = cues.get(b.cue)
            if b.kind == "text" or c is None or c.no_trigger:
                continue
            if n >= MAX_CUES:
                break
            out.append({"page": page.name, "page_index": pi, "note": n, "cue": c.name, "label": b.label or c.name})
            n += 1
    return out


def handle(runner, kind: str, number: int, value: int) -> str:
    """Esegue un messaggio del canale 16. Ritorna la descrizione dell'azione (stringa vuota se ignorato)."""
    e = runner.engine
    pages = e.project.pages
    if kind == "cc":
        if number == 0:
            i = value - 1
            if 0 <= i < len(pages) and runner.on_select_page:
                runner.on_select_page(pages[i].name); return f"Select Page {pages[i].name}"
        elif number in ACTIONS:
            runner.run(ACTIONS[number], {}, 1.0 if value else 0.0); return ACTIONS[number]
        return ""
    pi = max(0, value - 1) if kind == "note_on" and value else None
    if kind == "note_on" and value:
        for b in bindings(e.project):
            if b["page_index"] == pi and b["note"] == number:
                cue = runner._cue(b["cue"])
                if runner.on_select_page:
                    runner.on_select_page(b["page"])
                runner.run("cue", {"cue": b["cue"]}, 1.0)
                return f"Cue {b['cue']}"
    else:
        # Note Off: non porta la pagina, rilascia il cue con quella nota che sia flash e attivo
        for b in bindings(e.project):
            if b["note"] == number:
                cue = runner._cue(b["cue"])
                btn = next((x for p in pages for x in p.buttons if x.cue == cue.name), None)
                if btn and btn.mode == "flash" and cue.name in e.live.active:
                    e.live.release(cue); return f"Release {cue.name}"
    return ""


def export_clips(project, folder: str) -> list[str]:
    """Scrive un clip .mid (una nota, canale 16) per ogni binding + Select Page + azioni. Richiede mido."""
    import mido
    os.makedirs(folder, exist_ok=True)
    made = []

    def write(name: str, msgs: list) -> None:
        mid = mido.MidiFile(ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.extend(msgs)
        safe = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in name)
        path = os.path.join(folder, safe + ".mid"); mid.save(path); made.append(path)

    for b in bindings(project):
        v = b["page_index"] + 1
        write(f"{b['page']} - {b['label']}", [
            mido.Message("note_on", channel=TRIGGER_CHANNEL, note=b["note"], velocity=min(127, v), time=0),
            mido.Message("note_off", channel=TRIGGER_CHANNEL, note=b["note"], velocity=0, time=480)])
    for pi, p in enumerate(project.pages):
        write(f"{p.name} - Select Page", [mido.Message("control_change", channel=TRIGGER_CHANNEL, control=0, value=min(127, pi + 1), time=0)])
    for num, name in ACTIONS.items():
        write(f"Actions - {name.title()} On", [mido.Message("control_change", channel=TRIGGER_CHANNEL, control=num, value=127, time=0)])
        write(f"Actions - {name.title()} Off", [mido.Message("control_change", channel=TRIGGER_CHANNEL, control=num, value=0, time=0)])
    return made
