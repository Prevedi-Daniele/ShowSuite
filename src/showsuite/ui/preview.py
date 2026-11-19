"""Preview 2D: fixture, raggi, selezione (click, Ctrl, rettangolo, prefisso nome, Tab)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from ..light.engine import LightEngine
from .theme import ACCENT

BEAM_LEN = 130.0
HIT_R = 22


class PreviewWidget(QWidget):
    selection_changed = Signal(list)

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        self.selection: list[str] = []
        self._drag_from: QPointF | None = None
        self._drag_start_pos: dict[str, tuple[float, float]] = {}
        self._rubber: QRectF | None = None
        self._rubber_add = False
        self._typed = ""
        self._type_timer = QTimer(self, singleShot=True, interval=1200)
        self._type_timer.timeout.connect(lambda: setattr(self, "_typed", ""))
        self.setMinimumSize(420, 300)
        self.setFocusPolicy(Qt.StrongFocus)

    # --- selezione ---
    def set_selection(self, names: list[str], emit: bool = True) -> None:
        valid = {f.name for f in self.engine.project.patch.fixtures}
        names = [n for n in names if n in valid]
        if names != self.selection:
            self.selection = names
            if emit:
                self.selection_changed.emit(list(names))
        self.update()

    @property
    def current(self) -> str | None:
        return self.selection[0] if self.selection else None

    def focusNextPrevChild(self, next_: bool) -> bool:   # Tab serve alla selezione alfabetica
        return False

    # --- geometria ---
    def _pos(self, fx) -> QPointF:
        return QPointF(fx.x * self.width(), fx.y * self.height())

    def _hit(self, pos: QPointF) -> str | None:
        for fx in reversed(self.engine.project.patch.fixtures):
            d = self._pos(fx) - pos
            if d.x() ** 2 + d.y() ** 2 <= HIT_R ** 2:
                return fx.name
        return None

    @staticmethod
    def beam_polygon(origin: QPointF, rotation: float, angle: float, length: float = BEAM_LEN) -> QPolygonF:
        """Cono dal fixture. rotation 0 = verso il basso, positivo = antiorario."""
        poly = QPolygonF([origin])
        half = math.radians(max(1.0, min(170.0, angle)) / 2)
        base = math.radians(rotation)
        for a in (-half, half):
            t = base + a
            poly.append(QPointF(origin.x() - math.sin(t) * length / math.cos(min(half, 1.2)),
                                origin.y() + math.cos(t) * length / math.cos(min(half, 1.2))))
        return poly

    # --- disegno ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(14, 15, 18))
        p.setPen(QPen(QColor(38, 40, 48), 1))
        for gx in range(0, self.width(), 40):
            for gy in range(0, self.height(), 40):
                p.drawPoint(gx, gy)
        fixtures = self.engine.project.patch.fixtures
        # raggi sotto ai simboli
        for fx in fixtures:
            r, g, b = self.engine.fixture_color(fx)
            level = max(r, g, b) / 255
            if fx.hide_beam or level <= 0.02:
                continue
            o = self._pos(fx)
            grad = QLinearGradient(o, QPointF(o.x() - math.sin(math.radians(fx.rotation)) * BEAM_LEN,
                                              o.y() + math.cos(math.radians(fx.rotation)) * BEAM_LEN))
            col = QColor(r, g, b)
            col.setAlphaF(0.55 * level)
            end = QColor(r, g, b); end.setAlphaF(0.0)
            grad.setColorAt(0, col); grad.setColorAt(1, end)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(grad))
            p.drawPolygon(self.beam_polygon(o, fx.rotation, fx.beam_angle))
        for fx in fixtures:
            r, g, b = self.engine.fixture_color(fx)
            c = self._pos(fx)
            sel = fx.name in self.selection
            p.setBrush(QBrush(QColor(r, g, b)))
            p.setPen(QPen(QColor(ACCENT) if sel else QColor(110, 114, 128), 3 if sel else 1.5))
            if fx.profile.is_mover:
                p.drawRoundedRect(QRectF(c.x() - 16, c.y() - 16, 32, 32), 8, 8)
                p.setPen(QPen(QColor(20, 20, 24), 2))
                p.drawLine(c, QPointF(c.x() - math.sin(math.radians(fx.rotation)) * 14,
                                      c.y() + math.cos(math.radians(fx.rotation)) * 14))
            else:
                p.drawEllipse(c, 16, 16)
            p.setPen(QColor(205, 208, 218) if sel else QColor(150, 154, 168))
            p.drawText(QRectF(c.x() - 50, c.y() + 20, 100, 18), Qt.AlignCenter, fx.name)
        if self._rubber:
            p.setPen(QPen(QColor(ACCENT), 1, Qt.DashLine))
            p.setBrush(QColor(58, 139, 255, 40))
            p.drawRect(self._rubber)
        if self._typed:
            p.setPen(QColor(ACCENT))
            p.drawText(12, self.height() - 12, f"Selezione: {self._typed}")

    # --- mouse ---
    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position()
        name = self._hit(pos)
        ctrl = bool(e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier))
        if e.button() == Qt.RightButton:
            if name and name not in self.selection:
                self.set_selection([name])
            self._context_menu(e.globalPosition().toPoint())
            return
        if name:
            if ctrl:
                sel = list(self.selection)
                sel.remove(name) if name in sel else sel.append(name)
                self.set_selection(sel)
            elif name not in self.selection:
                self.set_selection([name])
            self._drag_from = pos
            self._drag_start_pos = {n: (self.engine.project.patch.find(n).x, self.engine.project.patch.find(n).y)
                                    for n in self.selection}
        else:
            self._rubber_add = ctrl
            self._rubber = QRectF(pos, pos)
            self._drag_from = pos
            if not ctrl:
                self.set_selection([])
        self.update()

    def mouseMoveEvent(self, e):
        if self._drag_from is None:
            return
        pos = e.position()
        if self._rubber is not None:
            self._rubber = QRectF(self._drag_from, pos).normalized()
        elif self._drag_start_pos and self.width() and self.height():
            dx = (pos.x() - self._drag_from.x()) / self.width()
            dy = (pos.y() - self._drag_from.y()) / self.height()
            for n, (x0, y0) in self._drag_start_pos.items():
                fx = self.engine.project.patch.find(n)
                fx.x, fx.y = min(1, max(0, x0 + dx)), min(1, max(0, y0 + dy))
        self.update()

    def mouseReleaseEvent(self, _):
        if self._rubber is not None:
            inside = [f.name for f in self.engine.project.patch.fixtures
                      if self._rubber.contains(self._pos(f))]
            sel = list(self.selection) if self._rubber_add else []
            self.set_selection(sel + [n for n in inside if n not in sel])
        self._rubber = None
        self._drag_from = None
        self._drag_start_pos = {}
        self.update()

    # --- tastiera ---
    def keyPressEvent(self, e):
        names = sorted((f.name for f in self.engine.project.patch.fixtures), key=str.lower)
        if e.key() == Qt.Key_Escape:
            self.set_selection([]); self._typed = ""
        elif e.key() in (Qt.Key_Tab, Qt.Key_Backtab) and names:
            i = names.index(self.current) if self.current in names else -1
            step = -1 if e.key() == Qt.Key_Backtab else 1
            self.set_selection([names[(i + step) % len(names)]])
        elif e.key() == Qt.Key_A and e.modifiers() & Qt.ControlModifier:
            self.set_selection([f.name for f in self.engine.project.patch.fixtures])
        elif e.text() and e.text().isprintable() and not (e.modifiers() & Qt.ControlModifier):
            self._typed += e.text().lower().replace(" ", "")
            self._type_timer.start()
            self.set_selection([n for n in names if n.lower().replace(" ", "").startswith(self._typed)])
        else:
            return super().keyPressEvent(e)
        self.update()

    # --- menu fixture ---
    def _context_menu(self, global_pos):
        if not self.selection:
            return
        fxs = [self.engine.project.patch.find(n) for n in self.selection]
        m = QMenu(self)
        m.addAction("Ruota +15°", lambda: self._rotate(fxs, 15))
        m.addAction("Ruota −15°", lambda: self._rotate(fxs, -15))
        m.addAction("Angolo del raggio…", lambda: self._ask_angle(fxs))
        hide = all(f.hide_beam for f in fxs)
        m.addAction("Mostra raggio" if hide else "Nascondi raggio", lambda: self._set_hide(fxs, not hide))
        m.exec(global_pos)

    def _rotate(self, fxs, delta):
        for f in fxs:
            f.rotation = (f.rotation + delta + 180) % 360 - 180
        self.update()

    def _ask_angle(self, fxs):
        v, ok = QInputDialog.getDouble(self, "Raggio", "Apertura (gradi):", fxs[0].beam_angle, 1, 170, 0)
        if ok:
            for f in fxs:
                f.beam_angle = v
            self.update()

    def _set_hide(self, fxs, hide):
        for f in fxs:
            f.hide_beam = hide
        self.update()
