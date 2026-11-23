"""Preview 2D: fixture, raggi, selezione (click, Ctrl, rettangolo, prefisso nome, Tab)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QBrush, QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from ..light.engine import LightEngine
from ..light.stage import ALIGN_MODES, StageShape, align, distribute, make_group, select_by_profile
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
        self.edit_mode = False
        self.tool: str | None = None          # "truss" | "line" | "text" in modifica
        self.sel_shape: StageShape | None = None
        self._shape_new: StageShape | None = None
        self._handle: int | None = None
        self._bg_cache: tuple[bytes, QPixmap] | None = None
        self.setMinimumSize(420, 300)
        self.setFocusPolicy(Qt.StrongFocus)

    # --- selezione ---
    tint = (14, 15, 18)   # sfondo adattivo: segue il colore predominante delle luci

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

    # --- sfondo e scena ---
    def _paint_background(self, p: QPainter) -> None:
        data = self.engine.project.background
        if not data:
            return
        if self._bg_cache is None or self._bg_cache[0] is not data:
            pm = QPixmap(); pm.loadFromData(data); self._bg_cache = (data, pm)
        pm = self._bg_cache[1]
        if pm.isNull():
            return
        sc = pm.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.setOpacity(0.55)
        p.drawPixmap((self.width() - sc.width()) // 2, (self.height() - sc.height()) // 2, sc)
        p.setOpacity(1.0)

    def _paint_shapes(self, p: QPainter) -> None:
        W, H = self.width(), self.height()
        shapes = list(self.engine.project.shapes) + ([self._shape_new] if self._shape_new else [])
        for sh in shapes:
            col = QColor(sh.color)
            if sh is self.sel_shape and self.edit_mode:
                col = QColor(ACCENT)
            if sh.kind == "text":
                p.setPen(col); f = p.font(); f.setPointSize(14); f.setBold(True); p.setFont(f)
                p.drawText(QPointF(sh.x1 * W, sh.y1 * H), sh.text or "Testo")
                f.setPointSize(10); f.setBold(False); p.setFont(f)
                continue
            pts = [QPointF(x * W, y * H) for x, y in sh.points()]
            if sh.kind == "line":
                p.setPen(QPen(col, 3))
                for u, v in zip(pts, pts[1:]):
                    p.drawLine(u, v)
            else:   # traliccio: due correnti paralleli con diagonali
                offs = []
                for i, q in enumerate(pts):
                    u, v = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
                    d = v - u; L = math.hypot(d.x(), d.y()) or 1.0
                    offs.append(QPointF(-d.y() / L, d.x() / L) * 6)
                p.setPen(QPen(col, 2))
                for sign in (1, -1):
                    for i in range(len(pts) - 1):
                        p.drawLine(pts[i] + offs[i] * sign, pts[i + 1] + offs[i + 1] * sign)
                p.setPen(QPen(col, 1))
                n = len(pts) - 1; step = max(1, n // max(1, int(sum(math.hypot((v - u).x(), (v - u).y()) for u, v in zip(pts, pts[1:])) // 14)))
                k = 0
                for i in range(0, n, step):
                    j = min(n, i + step); sg = 1 if k % 2 == 0 else -1
                    p.drawLine(pts[i] + offs[i] * sg, pts[j] - offs[j] * sg); k += 1
            if sh is self.sel_shape and self.edit_mode:
                p.setPen(QPen(QColor(ACCENT), 2)); p.setBrush(QColor("#fff"))
                for hx, hy in self._handles(sh):
                    p.drawEllipse(QPointF(hx * W, hy * H), 5, 5)
                p.setBrush(Qt.NoBrush)

    def _handles(self, sh: StageShape) -> list[tuple[float, float]]:
        mid = sh.points(2)[1] if sh.bulge else ((sh.x1 + sh.x2) / 2, (sh.y1 + sh.y2) / 2)
        return [(sh.x1, sh.y1), (sh.x2, sh.y2), mid]       # inizio, fine, curvatura

    def _handle_at(self, sh: StageShape, pos: QPointF) -> int | None:
        for i, (hx, hy) in enumerate(self._handles(sh)):
            if abs(hx * self.width() - pos.x()) < 9 and abs(hy * self.height() - pos.y()) < 9:
                return i
        return None

    def _shape_at(self, pos: QPointF) -> StageShape | None:
        if not self.width() or not self.height():
            return None
        x, y = pos.x() / self.width(), pos.y() / self.height()
        best = min(self.engine.project.shapes, key=lambda s: s.distance(x, y), default=None)
        return best if best and best.distance(x, y) < 0.02 else None

    def set_tool(self, tool: str | None) -> None:
        self.tool = tool; self.edit_mode = self.edit_mode or tool is not None

    def set_edit_mode(self, on: bool) -> None:
        self.edit_mode = on
        if not on:
            self.tool = None; self.sel_shape = None
        self.update()

    # --- disegno ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(*self.tint))
        p.setPen(QPen(QColor(38, 40, 48), 1))
        for gx in range(0, self.width(), 40):
            for gy in range(0, self.height(), 40):
                p.drawPoint(gx, gy)
        self._paint_background(p)
        self._paint_shapes(p)
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
        if self.edit_mode and not name:
            if self.tool and self.width() and self.height():
                x, y = pos.x() / self.width(), pos.y() / self.height()
                if self.tool == "text":
                    t, ok = QInputDialog.getText(self, "Testo", "Testo:")
                    if ok and t:
                        self.engine.project.shapes.append(StageShape("text", x, y, text=t))
                    self.update(); return
                self._shape_new = StageShape(self.tool, x, y, x, y)
                self._drag_from = pos; return
            if self.sel_shape and self.sel_shape.kind != "text":
                h = self._handle_at(self.sel_shape, pos)
                if h is not None:
                    self._handle = h; self._drag_from = pos; return
            hit = self._shape_at(pos)
            self.sel_shape = hit
            if hit:
                self._drag_from = pos; self._shape_drag = (pos, ) ; self.update(); return
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
        if self._shape_new is not None:
            self._shape_new.x2, self._shape_new.y2 = pos.x() / self.width(), pos.y() / self.height()
        elif getattr(self, "_handle", None) is not None and self.sel_shape:
            x, y = pos.x() / self.width(), pos.y() / self.height(); sh = self.sel_shape
            if self._handle == 0:
                sh.x1, sh.y1 = x, y
            elif self._handle == 1:
                sh.x2, sh.y2 = x, y
            else:   # il punto di mezzo della curva segue il mouse (mid = m + 0.5*n*bulge)
                mx, my = (sh.x1 + sh.x2) / 2, (sh.y1 + sh.y2) / 2
                dx, dy = sh.x2 - sh.x1, sh.y2 - sh.y1; l2 = dx * dx + dy * dy
                if l2 > 0:
                    sh.bulge = max(-3.0, min(3.0, 2 * (-(x - mx) * dy + (y - my) * dx) / l2))
        elif getattr(self, "_shape_drag", None) and self.sel_shape:
            last = self._shape_drag[0]
            self.sel_shape.move((pos.x() - last.x()) / self.width(), (pos.y() - last.y()) / self.height())
            self._shape_drag = (pos,)
        elif self._rubber is not None:
            self._rubber = QRectF(self._drag_from, pos).normalized()
        elif self._drag_start_pos and self.width() and self.height():
            dx = (pos.x() - self._drag_from.x()) / self.width()
            dy = (pos.y() - self._drag_from.y()) / self.height()
            for n, (x0, y0) in self._drag_start_pos.items():
                fx = self.engine.project.patch.find(n)
                fx.x, fx.y = min(1, max(0, x0 + dx)), min(1, max(0, y0 + dy))
        self.update()

    def mouseReleaseEvent(self, _):
        if self._shape_new is not None:
            sh = self._shape_new; self._shape_new = None
            if abs(sh.x2 - sh.x1) + abs(sh.y2 - sh.y1) > 0.01:
                self.engine.project.shapes.append(sh); self.sel_shape = sh
        self._shape_drag = None; self._handle = None
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
        elif e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.edit_mode and self.sel_shape:
            self.engine.project.shapes.remove(self.sel_shape); self.sel_shape = None
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
        if len(fxs) >= 2:
            al = m.addMenu("Allinea")
            for mode, lab in zip(ALIGN_MODES, ("A sinistra", "A destra", "In alto", "In basso", "Centro orizz.", "Centro vert.")):
                al.addAction(lab, lambda mode=mode: (align(fxs, mode), self.update()))
            m.addAction("Distribuisci orizzontalmente", lambda: (distribute(fxs, "h"), self.update()))
            m.addAction("Distribuisci verticalmente", lambda: (distribute(fxs, "v"), self.update()))
            m.addSeparator()
        m.addAction("Crea gruppo dalla selezione…", self.create_group_dialog)
        m.addAction("Seleziona stesso tipo", lambda: self.set_selection(select_by_profile(self.engine.project.patch, fxs[0].name)))
        m.addSeparator()
        m.addAction("Ruota +15°", lambda: self._rotate(fxs, 15))
        m.addAction("Ruota −15°", lambda: self._rotate(fxs, -15))
        m.addAction("Angolo del raggio…", lambda: self._ask_angle(fxs))
        hide = all(f.hide_beam for f in fxs)
        m.addAction("Mostra raggio" if hide else "Nascondi raggio", lambda: self._set_hide(fxs, not hide))
        m.exec(global_pos)

    groups_changed = Signal()

    def create_group_dialog(self):
        t, ok = QInputDialog.getText(self, "Nuovo gruppo", "Nome del gruppo:")
        if ok and t.strip() and self.selection:
            make_group(self.engine.project.groups, t, self.selection); self.groups_changed.emit()

    def select_group(self, name: str):
        g = next((g for g in self.engine.project.groups if g.name == name), None)
        if g:
            self.set_selection(list(g.fixtures))

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
