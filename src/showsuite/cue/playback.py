"""Piano di riproduzione di Audio/Video: start/end, play count, slice con loop, rate, devamp.

Il piano è puro calcolo sul tempo trascorso: non apre file e non produce suono. I backend audio/video lo usano per
sapere dove si trova la riproduzione e quando finisce."""
from __future__ import annotations

import math

MINIMUM_SLICE_LENGTH = 0.05
INFINITE = math.inf


class Segment:
    def __init__(self, start: float, end: float, count: float):
        self.start = start
        self.end = end
        self.count = count

    def length(self, rate: float) -> float:
        return (self.end - self.start) / rate


class PlaybackPlan:
    def __init__(self, params: dict, media_duration: float | None):
        self.rate = max(0.03, min(33.0, float(params.get("rate", 1.0))))
        start = float(params.get("start_time", 0.0))
        end_value = params.get("end_time", None)
        if end_value is None:
            end_value = media_duration if media_duration is not None else start
        end = float(end_value)
        self.start = start
        self.end = max(end, start)
        if params.get("infinite_loop", False) == True:
            self.cycles = INFINITE
        else:
            self.cycles = float(max(1, int(params.get("play_count", 1))))
        self.segments = self._build_segments(params.get("slices", []))

    def _build_segments(self, slices: list) -> list[Segment]:
        if len(slices) == 0:
            return [Segment(self.start, self.end, 1.0)]
        ordered = sorted(slices, key=lambda item: float(item["time"]))
        markers = []
        for item in ordered:
            time_value = float(item["time"])
            if self.start <= time_value < self.end:
                markers.append((time_value, item.get("play_count", 1)))
        segments: list[Segment] = []
        if len(markers) == 0 or markers[0][0] > self.start:
            first_end = markers[0][0] if len(markers) > 0 else self.end
            segments.append(Segment(self.start, first_end, 1.0))
        for index, (time_value, count_value) in enumerate(markers):
            if index + 1 < len(markers):
                slice_end = markers[index + 1][0]
            else:
                slice_end = self.end
            if slice_end - time_value < MINIMUM_SLICE_LENGTH:
                continue
            segments.append(Segment(time_value, slice_end, _parse_count(count_value)))
        return segments

    def is_playable(self) -> bool:
        """Falso se tutte le slice hanno play count 0 (cue broken) o se l'intervallo è vuoto."""
        for segment in self.segments:
            if segment.count > 0 and segment.end > segment.start:
                return True
        return False

    def cycle_duration(self) -> float:
        total = 0.0
        for segment in self.segments:
            if segment.count > 0:
                total = total + segment.length(self.rate) * segment.count
        return total

    def total_duration(self) -> float:
        cycle = self.cycle_duration()
        if cycle == INFINITE or self.cycles == INFINITE:
            return INFINITE
        return cycle * self.cycles

    def locate(self, elapsed: float) -> dict | None:
        """Posizione al tempo trascorso: ciclo, indice slice, iterazione, tempo nel file. None se finito."""
        cycle = self.cycle_duration()
        if cycle <= 0.0:
            return None
        if cycle == INFINITE:
            cycle_index = 0
            local = elapsed
        else:
            cycle_index = int(elapsed // cycle)
            if self.cycles != INFINITE and cycle_index >= self.cycles:
                return None
            local = elapsed - cycle_index * cycle
        for index, segment in enumerate(self.segments):
            if segment.count <= 0:
                continue
            segment_length = segment.length(self.rate)
            span = segment_length * segment.count
            if local < span or segment.count == INFINITE:
                iteration = int(local // segment_length) if segment_length > 0 else 0
                inside = local - iteration * segment_length
                return {"cycle": cycle_index, "slice": index, "iteration": iteration,
                        "media_time": segment.start + inside * self.rate}
            local = local - span
        return None

    def is_looping(self, elapsed: float) -> bool:
        """Vero se la riproduzione è dentro un loop infinito (slice infinita o cue in loop)."""
        position = self.locate(elapsed)
        if position is None:
            return False
        segment = self.segments[position["slice"]]
        if segment.count == INFINITE:
            return True
        return self.cycles == INFINITE

    def devamp(self, elapsed: float, whole_cue: bool) -> bool:
        """Esce dal loop alla fine dell'iterazione in corso. Restituisce True se ha cambiato qualcosa."""
        position = self.locate(elapsed)
        if position is None:
            return False
        if whole_cue == True:
            if self.cycles == INFINITE or self.cycles > position["cycle"] + 1:
                self.cycles = float(position["cycle"] + 1)
                for segment in self.segments:
                    if segment.count == INFINITE:
                        segment.count = 1.0
                return True
            return False
        segment = self.segments[position["slice"]]
        wanted = float(position["iteration"] + 1)
        if segment.count == INFINITE or segment.count > wanted:
            segment.count = wanted
            return True
        return False

    def end_of_current_iteration(self, elapsed: float) -> float | None:
        position = self.locate(elapsed)
        if position is None:
            return None
        segment = self.segments[position["slice"]]
        segment_length = segment.length(self.rate)
        offset = 0.0
        cycle = self.cycle_duration()
        if cycle != INFINITE:
            offset = position["cycle"] * cycle
        for index in range(position["slice"]):
            earlier = self.segments[index]
            if earlier.count > 0:
                offset = offset + earlier.length(self.rate) * earlier.count
        return offset + (position["iteration"] + 1) * segment_length


def _parse_count(value) -> float:
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("inf", "infinite", "loop", "∞") or (len(text) == 1 and text.isalpha()):
            return INFINITE
        return float(int(text))
    if value is None:
        return 1.0
    return float(int(value))
