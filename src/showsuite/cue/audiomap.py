"""Audio map (object audio, manuale 5.2 e 5.6): mappe con marks, filtri e oggetti.

Una mappa è uno spazio senza unità. I marks associano una posizione a un insieme di livelli per le uscite cue
(0 = riga main, 1..128 = uscite); i filtri limitano l'influenza dei marks; gli oggetti si muovono e il loro
instradamento deriva dalla distanza dai marks.

APPROSSIMAZIONE DICHIARATA: il manuale descrive l'effetto di gravity, shadow e filtri solo a parole e non pubblica
l'algoritmo di QLab. Qui l'influenza di un mark è gravity / distanza², attenuata linearmente dall'angolo se un altro mark
con shadow lo nasconde; un filtro azzera l'influenza dei marks sul lato opposto per le uscite non in passthrough
(marks e oggetti dentro la larghezza del filtro non sono toccati). Un oggetto esattamente su un mark prende i suoi livelli.
I valori intermedi NON coincidono con quelli di QLab."""
from __future__ import annotations

import math
import uuid

MINUS_INFINITY = -200.0
OUTPUT_COUNT = 128
COLORS = ["berry", "blue", "crimson", "cyan", "forest", "gray", "green", "hot pink", "indigo", "lavender", "magenta",
          "midnight", "olive", "orange", "peach", "plum", "purple", "red", "sky blue", "yellow", "none"]


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def double_letter_name(index: int) -> str:
    """Nomi di default degli oggetti: A, B, ... Z, AA, BB, ..."""
    letter = chr(ord("A") + index % 26)
    return letter * (index // 26 + 1)


def new_map(name: str = "Map", width: float = 1000.0, height: float = 1000.0) -> dict:
    return {"unique_id": new_id(), "name": name, "width": width, "height": height, "marks": [], "filters": [],
            "objects": [], "background": "", "test_object": {"running": False, "level": MINUS_INFINITY, "x": width / 2,
                                                              "y": height / 2}}


def add_mark(audio_map: dict, name: str, x: float, y: float, levels: dict | None = None, gravity: float = 1.0,
             shadow: float = 0.0) -> dict:
    mark = {"unique_id": new_id(), "name": name, "x": float(x), "y": float(y),
            "levels": {int(key): float(value) for key, value in (levels or {}).items()},
            "gravity": min(5.0, max(0.1, float(gravity))), "shadow": min(90.0, max(0.0, float(shadow)))}
    audio_map["marks"].append(mark)
    return mark


def add_filter(audio_map: dict, name: str, x: float, y: float, angle: float = 90.0, width: float = 0.0,
               passthroughs: list | None = None) -> dict:
    item = {"unique_id": new_id(), "name": name, "x": float(x), "y": float(y), "angle": float(angle),
            "width": float(width), "passthroughs": sorted(int(value) for value in (passthroughs or []))}
    audio_map["filters"].append(item)
    return item


def add_object(audio_map: dict, name: str | None = None, x: float = 0.0, y: float = 0.0, spread: float = 0.0,
               color: str = "none") -> dict:
    item = {"unique_id": new_id(), "name": name if name is not None else double_letter_name(len(audio_map["objects"])),
            "x": float(x), "y": float(y), "home_x": float(x), "home_y": float(y), "spread": float(spread),
            "color": color}
    audio_map["objects"].append(item)
    return item


def _gain(decibel: float) -> float:
    return 0.0 if decibel <= -100.0 else 10.0 ** (decibel / 20.0)


def _to_decibel(gain: float) -> float:
    return MINUS_INFINITY if gain <= 1e-10 else 20.0 * math.log10(gain)


def _side(item: dict, x: float, y: float) -> int:
    """Lato del punto rispetto a un filtro: -1, +1 oppure 0 se dentro la larghezza."""
    angle = math.radians(item["angle"])
    distance = (x - item["x"]) * -math.sin(angle) + (y - item["y"]) * math.cos(angle)
    if abs(distance) <= item["width"] / 2.0:
        return 0
    return 1 if distance > 0 else -1


def _angle_between(first: tuple, second: tuple) -> float:
    dot = first[0] * second[0] + first[1] * second[1]
    norm = math.hypot(*first) * math.hypot(*second)
    if norm == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / norm))))


def _point_gains(audio_map: dict, x: float, y: float, outputs: list) -> dict:
    marks = audio_map["marks"]
    result = {output: 0.0 for output in outputs}
    if len(marks) == 0:
        return result
    distances = [math.hypot(mark["x"] - x, mark["y"] - y) for mark in marks]
    for index, mark in enumerate(marks):
        if distances[index] < 1e-6:
            return {output: _gain(mark["levels"].get(output, MINUS_INFINITY)) for output in outputs}
    weights = []
    for index, mark in enumerate(marks):
        weight = mark["gravity"] / (distances[index] ** 2)
        for other_index, other in enumerate(marks):
            if other_index == index or other["shadow"] <= 0 or distances[other_index] >= distances[index]:
                continue
            angle = _angle_between((other["x"] - x, other["y"] - y), (mark["x"] - x, mark["y"] - y))
            if angle < other["shadow"]:
                weight = weight * (angle / other["shadow"])
        weights.append(weight)
    for output in outputs:
        total = 0.0
        accumulated = 0.0
        for index, mark in enumerate(marks):
            blocked = False
            for item in audio_map["filters"]:
                if output in item["passthroughs"]:
                    continue
                object_side = _side(item, x, y)
                mark_side = _side(item, mark["x"], mark["y"])
                if object_side != 0 and mark_side != 0 and object_side != mark_side:
                    blocked = True
                    break
            if blocked == True:
                continue
            total = total + weights[index]
            accumulated = accumulated + weights[index] * _gain(mark["levels"].get(output, MINUS_INFINITY))
        result[output] = accumulated / total if total > 0 else 0.0
    return result


def object_levels(audio_map: dict, x: float, y: float, spread: float = 0.0, outputs: list | None = None) -> dict:
    """Livelli (dB) di un oggetto in {uscita: dB}. Con spread > 0 vale il punto più forte entro il raggio."""
    if outputs is None:
        used = {0}
        for mark in audio_map["marks"]:
            used.update(mark["levels"].keys())
        outputs = sorted(used)
    points = [(x, y)]
    if spread > 0:
        for radius in (spread, spread / 2.0):
            for step in range(8):
                angle = math.pi * 2.0 * step / 8.0
                points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    best = {output: 0.0 for output in outputs}
    for point_x, point_y in points:
        gains = _point_gains(audio_map, point_x, point_y, outputs)
        for output in outputs:
            best[output] = max(best[output], gains[output])
    return {output: _to_decibel(gain) for output, gain in best.items()}


def find_map(maps: list, reference: str) -> dict | None:
    for audio_map in maps:
        if audio_map["unique_id"] == reference or audio_map["name"] == reference:
            return audio_map
    return None
