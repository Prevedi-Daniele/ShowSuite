"""Editor Timeline per i gruppi in modalità Timeline: una traccia per figlio, trascinando la barra si cambia il pre-wait.

Come in QLab, in una Timeline tutti i figli partono insieme alla partenza del gruppo e la loro posizione sull'asse del tempo
è il loro pre-wait. Approssimazioni: nessuna traccia multipla per figlio, nessuna selezione multipla né snap magnetico
(passo fisso di 0,1 s), niente scorrimento di anteprima audio."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..cue.model import Cue

TRACK_HEIGHT = 26
RULER_HEIGHT = 22
LABEL_WIDTH = 130
MINIMUM_VISIBLE_LENGTH = 0.5
SNAP_STEP = 0.1


def child_length(child: Cue) -> float:
    """Durata mostrata di un figlio: durata del cue, altrimenti durata del file / velocità, altrimenti un minimo visibile."""
    if child.duration is not None and float(child.duration) > 0:
        return float(child.duration)
    media = child.params.get("media_duration")
    if media:
        end = child.params.get("end_time")
        start = float(child.params.get("start_time", 0.0))
        length = (float(end) if end is not None else float(media)) - start
        rate = max(0.03, float(child.params.get("rate", 1.0)))
        return max(MINIMUM_VISIBLE_LENGTH, length / rate)
    return MINIMUM_VISIBLE_LENGTH


class TimelineEditor(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.group: Cue | None = None
        self.pixels_per_second = 40.0
        self.playhead: float | None = None
        self.drag_child: Cue | None = None
        self.drag_offset = 0.0
        self.setMinimumHeight(RULER_HEIGHT + TRACK_HEIGHT * 3)
        self.setMouseTracking(True)

    def load(self, group: Cue | None) -> None:
        self.group = group
        height = RULER_HEIGHT + TRACK_HEIGHT * max(3, len(group.children) if group is not None else 3) + 4
        self.setMinimumHeight(height)
        self.update()

    # --- geometria ---
    def total_length(self) -> float:
        if self.group is None or len(self.group.children) == 0:
            return 10.0
        return max(child.pre_wait + child_length(child) for child in self.group.children) + 2.0

    def child_rect(self, index: int) -> QRectF:
        child = self.group.children[index]
        return QRectF(LABEL_WIDTH + child.pre_wait * self.pixels_per_second, RULER_HEIGHT + index * TRACK_HEIGHT + 3,
                      child_length(child) * self.pixels_per_second, TRACK_HEIGHT - 6)

    def layout(self) -> list:
        if self.group is None:
            return []
        return [(child, self.child_rect(index)) for index, child in enumerate(self.group.children)]

    def child_at(self, x: float, y: float):
        for child, rect in self.layout():
            if rect.contains(x, y):
                return child, rect
        return None, None

    def move_child(self, child: Cue, new_pre_wait: float) -> None:
        snapped = round(max(0.0, new_pre_wait) / SNAP_STEP) * SNAP_STEP
        child.pre_wait = round(snapped, 3)
        self.changed.emit()
        self.update()

    # --- mouse ---
    def mousePressEvent(self, event) -> None:
        child, rect = self.child_at(event.position().x(), event.position().y())
        if child is not None and event.button() == Qt.LeftButton:
            self.drag_child = child
            self.drag_offset = event.position().x() - rect.left()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_child is not None:
            left = event.position().x() - self.drag_offset
            self.move_child(self.drag_child, (left - LABEL_WIDTH) / self.pixels_per_second)

    def mouseReleaseEvent(self, event) -> None:
        self.drag_child = None

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.pixels_per_second = max(5.0, min(400.0, self.pixels_per_second * factor))
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)

    # --- disegno ---
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#888")))
        step = 1.0 if self.pixels_per_second >= 30 else 5.0
        seconds = 0.0
        while LABEL_WIDTH + seconds * self.pixels_per_second < self.width():
            x = LABEL_WIDTH + seconds * self.pixels_per_second
            painter.drawLine(int(x), RULER_HEIGHT - 6, int(x), self.height())
            painter.drawText(int(x) + 3, RULER_HEIGHT - 8, "%g" % seconds)
            seconds = seconds + step
        if self.group is None:
            return
        metrics = QFontMetrics(painter.font())
        for index, (child, rect) in enumerate(self.layout()):
            top = RULER_HEIGHT + index * TRACK_HEIGHT
            painter.setPen(QPen(QColor("#333")))
            painter.drawLine(0, top + TRACK_HEIGHT, self.width(), top + TRACK_HEIGHT)
            painter.setPen(QPen(QColor("#ddd")))
            label = "%s %s" % (child.number, child.display_name())
            painter.drawText(4, top + 17, metrics.elidedText(label, Qt.ElideRight, LABEL_WIDTH - 8))
            painter.fillRect(rect, QColor("#2e7d9a") if child.armed else QColor("#555"))
            painter.setPen(QPen(QColor("#9fd8ee")))
            painter.drawRect(rect)
        if self.playhead is not None:
            x = LABEL_WIDTH + self.playhead * self.pixels_per_second
            painter.setPen(QPen(QColor("#ff5252"), 2))
            painter.drawLine(int(x), 0, int(x), self.height())
