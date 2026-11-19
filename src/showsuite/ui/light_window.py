"""Finestra principale Light (PySide6): patch, Preview 2D, fader, uscite."""
from __future__ import annotations

import sys

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
                               QCheckBox, QDockWidget, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMainWindow, QMessageBox, QPushButton, QScrollArea, QSlider,
                               QSpinBox, QSplitter, QVBoxLayout, QWidget)

from ..light import project as pj
from ..light.control.actions import ACTIONS, ActionRunner
from ..light.control.midi import MidiController
from ..light.control.osc import OscServer
from ..light.effects import WAVES, Effect
from ..light.live import CURVES, LiveCue
from ..light.preset import Preset
from ..light.engine import LightEngine
from ..light.fixtures import FixtureInstance, PatchError
from ..light.fixtures.ofl import OflImportError

class PreviewWidget(QWidget):
    selected = Signal(str)

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        self.current: str | None = None
        self._drag: str | None = None
        self.setMinimumSize(400, 300)

    def _pos(self, fx) -> QPointF:
        return QPointF(fx.x * self.width(), fx.y * self.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(20, 20, 24))
        for fx in self.engine.project.patch.fixtures:
            r, g, b = self.engine.fixture_color(fx)
            c = self._pos(fx)
            p.setBrush(QBrush(QColor(r, g, b)))
            sel = fx.name == self.current
            p.setPen(QPen(QColor(255, 255, 255) if sel else QColor(90, 90, 100), 2 if sel else 1))
            p.drawEllipse(c, 18, 18)
            p.setPen(QColor(200, 200, 210))
            p.drawText(int(c.x()) - 40, int(c.y()) + 36, 80, 16, Qt.AlignCenter, fx.name)

    def _hit(self, pos) -> str | None:
        for fx in reversed(self.engine.project.patch.fixtures):
            d = self._pos(fx) - pos
            if d.x() ** 2 + d.y() ** 2 <= 20 ** 2:
                return fx.name
        return None

    def mousePressEvent(self, e):
        name = self._hit(e.position())
        self._drag = name
        if name:
            self.current = name
            self.selected.emit(name)
        self.update()

    def mouseMoveEvent(self, e):
        if self._drag:
            fx = self.engine.project.patch.find(self._drag)
            fx.x = min(1, max(0, e.position().x() / self.width()))
            fx.y = min(1, max(0, e.position().y() / self.height()))
            self.update()

    def mouseReleaseEvent(self, _):
        self._drag = None


class FaderPanel(QWidget):
    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        self.lay = QVBoxLayout(self)
        self.title = QLabel("Nessun fixture selezionato")
        self.lay.addWidget(self.title)
        self.sliders: list[QWidget] = []
        self.lay.addStretch()

    def show_fixture(self, name: str | None):
        for w in self.sliders:
            w.setParent(None)
        self.sliders.clear()
        if not name:
            self.title.setText("Nessun fixture selezionato")
            return
        fx = self.engine.project.patch.find(name)
        self.title.setText(f"{fx.name}: U{fx.universe} @{fx.address}")
        for ch in fx.profile.channels:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(ch.name)
            lab.setMinimumWidth(60)
            s = QSlider(Qt.Horizontal)
            top = 65535 if ch.fine else 255
            s.setRange(0, top)
            s.setValue(self.engine.get_value(name, ch.name))
            val = QLabel(str(s.value()))
            val.setMinimumWidth(40)

            def changed(v, n=ch.name, lbl=val):
                lbl.setText(str(v))
                self.engine.set_value(name, n, v)
            s.valueChanged.connect(changed)
            h.addWidget(lab); h.addWidget(s); h.addWidget(val)
            self.lay.insertWidget(self.lay.count() - 1, row)
            self.sliders.append(row)


class AddFixtureDialog(QDialog):
    def __init__(self, engine: LightEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Aggiungi fixture")
        f = QFormLayout(self)
        self.prof = QComboBox(); self.prof.addItems(engine.library)
        self.name = QLineEdit("Fixture")
        self.count = QSpinBox(); self.count.setRange(1, 128); self.count.setValue(1)
        self.uni = QSpinBox(); self.uni.setRange(1, pj.MAX_UNIVERSES); self.uni.setValue(1)
        f.addRow("Profilo", self.prof); f.addRow("Nome", self.name)
        f.addRow("Quantità", self.count); f.addRow("Universo", self.uni)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def create(self) -> int:
        """Crea i fixture agli indirizzi liberi; restituisce quanti ne ha aggiunti."""
        profile = self.engine.library[self.prof.currentText()]
        added = 0
        patch = self.engine.project.patch
        existing = len(patch.fixtures)
        for i in range(self.count.value()):
            addr = patch.next_free(self.uni.value(), profile.footprint)
            if addr is None:
                break
            n = self.name.text() if self.count.value() == 1 else f"{self.name.text()} {i + 1}"
            idx = existing + added
            fx = FixtureInstance(n, profile, self.uni.value(), addr,
                                 0.1 + 0.8 * ((idx % 8) / 7), 0.2 + 0.2 * (idx // 8 % 4))
            try:
                patch.add(fx)
            except PatchError:
                break
            added += 1
        return added


class OutputsDialog(QDialog):
    def __init__(self, engine: LightEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Uscite DMX")
        v = QVBoxLayout(self)
        self.list = QListWidget(); v.addWidget(self.list)
        f = QFormLayout()
        self.type = QComboBox(); self.type.addItems(["opendmx", "artnet", "sacn"])
        self.uni = QSpinBox(); self.uni.setRange(1, pj.MAX_UNIVERSES)
        self.target = QComboBox(); self.target.setEditable(True)
        self.type.currentTextChanged.connect(self._refill)
        f.addRow("Tipo", self.type); f.addRow("Universo", self.uni)
        f.addRow("Porta / IP", self.target)
        v.addLayout(f)
        row = QHBoxLayout()
        add = QPushButton("Aggiungi"); rem = QPushButton("Rimuovi"); ok = QPushButton("Chiudi")
        add.clicked.connect(self._add); rem.clicked.connect(self._remove); ok.clicked.connect(self.accept)
        for b in (add, rem, ok):
            row.addWidget(b)
        v.addLayout(row)
        self._refill("opendmx"); self._reload()

    def _refill(self, kind):
        self.target.clear()
        if kind == "opendmx":
            try:
                from serial.tools import list_ports
                self.target.addItems([p.device for p in list_ports.comports()])
            except Exception:
                pass
        elif kind == "artnet":
            self.target.addItem("255.255.255.255")

    def _reload(self):
        self.list.clear()
        for o in self.engine.project.outputs:
            self.list.addItem(f"{o.type}  U{o.universe}  {o.params}")

    def _add(self):
        k, t = self.type.currentText(), self.target.currentText().strip()
        params = {"port": t} if k == "opendmx" else ({"host": t} if k == "artnet" else
                                                      ({"unicast": t} if t else {}))
        if k == "opendmx" and not t:
            QMessageBox.warning(self, "Uscite", "Scegli la porta seriale dell'interfaccia.")
            return
        self.engine.project.outputs.append(pj.OutputConfig(k, self.uni.value(), params))
        self._reload()

    def _remove(self):
        i = self.list.currentRow()
        if i >= 0:
            del self.engine.project.outputs[i]
            self._reload()


class RecordCueDialog(QDialog):
    """Registra un cue dai fixture selezionati e dai valori nel programmer."""

    def __init__(self, engine: LightEngine, fixtures: list[str], parent=None):
        super().__init__(parent)
        self.engine, self.fixtures = engine, fixtures
        self.setWindowTitle(f"Nuovo cue ({len(fixtures)} fixture)")
        f = QFormLayout(self)
        self.name = QLineEdit(f"Cue {len(engine.project.cues) + 1}")
        chans = sorted({c.name for n in fixtures for c in engine.project.patch.find(n).profile.channels})
        self.eff = QComboBox(); self.eff.addItems(["nessuno", *WAVES, "random"])
        self.chan = QComboBox(); self.chan.addItems(chans)
        self.cycle = QDoubleSpinBox(); self.cycle.setRange(0.125, 64); self.cycle.setValue(1.0)
        self.fan = QDoubleSpinBox(); self.fan.setRange(0, 1); self.fan.setSingleStep(0.1)
        self.fin = QDoubleSpinBox(); self.fin.setRange(0, 60)
        self.fout = QDoubleSpinBox(); self.fout.setRange(0, 60)
        self.curve = QComboBox(); self.curve.addItems(list(CURVES))
        self.prio = QSpinBox(); self.prio.setRange(1, 99); self.prio.setValue(10)
        for lab, w in (("Nome", self.name), ("Effetto", self.eff), ("Canale effetto", self.chan),
                       ("Battute per ciclo", self.cycle), ("Fanning (0-1)", self.fan),
                       ("Fade in (s)", self.fin), ("Fade out (s)", self.fout),
                       ("Curva", self.curve), ("Priorità", self.prio)):
            f.addRow(lab, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def build(self) -> LiveCue:
        values: dict[str, int] = {}
        for n in self.fixtures:
            for ch, v in self.engine.values.get(n, {}).items():
                values.setdefault(ch, v)
        effects = []
        if self.eff.currentText() != "nessuno":
            effects.append(Effect(self.chan.currentText(), self.eff.currentText(),
                                  self.cycle.value(), fan=self.fan.value()))
        return LiveCue(self.name.text() or "Cue", list(self.fixtures),
                       Preset(self.name.text(), values) if values else None, effects,
                       self.fin.value(), self.fout.value(), self.curve.currentText(), self.prio.value())


class SequenceDialog(QDialog):
    def __init__(self, n_steps: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Nuova sequenza ({n_steps} step)")
        f = QFormLayout(self)
        self.name = QLineEdit("Sequenza")
        self.bps = QDoubleSpinBox(); self.bps.setRange(0.125, 64); self.bps.setValue(1.0)
        self.xf = QDoubleSpinBox(); self.xf.setRange(0, 1); self.xf.setSingleStep(0.1)
        self.loop = QCheckBox("Ripeti"); self.loop.setChecked(True)
        self.prio = QSpinBox(); self.prio.setRange(1, 99); self.prio.setValue(10)
        for lab, w in (("Nome", self.name), ("Battute per step", self.bps),
                       ("Crossfade (0-1)", self.xf), ("", self.loop), ("Priorità", self.prio)):
            f.addRow(lab, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)


class LiveDock(QWidget):
    """Pulsanti cue, BPM e tap tempo."""

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.bpm = QDoubleSpinBox(); self.bpm.setRange(20, 400); self.bpm.setValue(engine.beat.bpm)
        self.bpm.valueChanged.connect(lambda x: engine.beat.set_bpm(x))
        tap = QPushButton("Tap"); tap.clicked.connect(self._tap)
        top.addWidget(QLabel("BPM")); top.addWidget(self.bpm); top.addWidget(tap)
        top.addSpacing(20); top.addWidget(QLabel("Master"))
        self.master = QSlider(Qt.Horizontal); self.master.setRange(0, 100); self.master.setValue(100)
        self.master.setMinimumWidth(160)
        self.master.valueChanged.connect(lambda x: setattr(engine, "grand_master", x / 100))
        top.addWidget(self.master)
        self.bo = QPushButton("Blackout"); self.bo.setCheckable(True)
        self.bo.toggled.connect(lambda on: setattr(engine, "blackout", on))
        self.fr = QPushButton("Freeze"); self.fr.setCheckable(True)
        self.fr.toggled.connect(engine.set_freeze)
        self.bl = QPushButton("Blind"); self.bl.setCheckable(True)
        self.bl.setToolTip("Le modifiche del programmer non vanno in uscita")
        self.bl.toggled.connect(lambda on: setattr(engine, "blind", on))
        top.addWidget(self.bo); top.addWidget(self.fr); top.addWidget(self.bl); top.addStretch()
        v.addLayout(top)
        self.grid_w = QWidget(); self.grid = QGridLayout(self.grid_w)
        v.addWidget(self.grid_w); v.addStretch()
        self.buttons: dict[str, QPushButton] = {}

    def _tap(self):
        self.engine.beat.tap()
        self.bpm.blockSignals(True); self.bpm.setValue(self.engine.beat.bpm); self.bpm.blockSignals(False)

    def rebuild(self):
        for b in self.buttons.values():
            b.setParent(None)
        self.buttons.clear()
        for i, cue in enumerate(self.engine.project.cues):
            b = QPushButton(cue.name); b.setMinimumHeight(48); b.setCheckable(True)
            b.clicked.connect(lambda _=False, c=cue: self.engine.live.trigger(c))
            self.grid.addWidget(b, i // 6, i % 6)
            self.buttons[cue.name] = b

    def sync(self):
        for name, b in self.buttons.items():
            st = self.engine.live.active.get(name)
            b.setChecked(bool(st and not st["releasing"]))


class ControlDialog(QDialog):
    """OSC (porta) e MIDI (porta, mappature, MIDI-learn)."""

    def __init__(self, win: "MainWindow"):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Controllo esterno")
        self.resize(520, 520)
        v = QVBoxLayout(self)
        # OSC
        orow = QHBoxLayout()
        self.osc_port = QSpinBox(); self.osc_port.setRange(1024, 65535); self.osc_port.setValue(win.engine.project.osc_port)
        self.osc_btn = QPushButton("Ferma OSC" if win.osc else "Avvia OSC"); self.osc_btn.clicked.connect(self._toggle_osc)
        orow.addWidget(QLabel("OSC porta")); orow.addWidget(self.osc_port); orow.addWidget(self.osc_btn); orow.addStretch()
        v.addLayout(orow)
        # MIDI
        mrow = QHBoxLayout()
        self.ports = QComboBox(); self.ports.addItems(MidiController.list_ports())
        self.m_btn = QPushButton("Apri MIDI"); self.m_btn.clicked.connect(self._open_midi)
        mrow.addWidget(QLabel("MIDI")); mrow.addWidget(self.ports, 1); mrow.addWidget(self.m_btn)
        v.addLayout(mrow)
        if not self.ports.count():
            v.addWidget(QLabel("Nessuna porta MIDI (serve: pip install showsuite[midi] e il controller collegato)."))
        # learn
        f = QFormLayout()
        self.action = QComboBox(); self.action.addItems(ACTIONS)
        self.arg1 = QComboBox(); self.arg1.setEditable(True)
        self.arg2 = QComboBox(); self.arg2.setEditable(True)
        self.action.currentTextChanged.connect(self._fill_args)
        f.addRow("Azione", self.action); f.addRow("Cue / fixture", self.arg1); f.addRow("Canale", self.arg2)
        v.addLayout(f)
        self.learn_btn = QPushButton("Impara (poi tocca un pad o gira una manopola)")
        self.learn_btn.clicked.connect(self._learn)
        v.addWidget(self.learn_btn)
        self.list = QListWidget(); v.addWidget(self.list)
        rem = QPushButton("Rimuovi mappatura"); rem.clicked.connect(self._remove); v.addWidget(rem)
        self.status = QLabel(""); v.addWidget(self.status)
        self._fill_args(self.action.currentText()); self._reload()
        self.t = QTimer(self); self.t.timeout.connect(self._poll); self.t.start(200)

    def _fill_args(self, action):
        e = self.win.engine
        self.arg1.clear(); self.arg2.clear()
        self.arg1.setEnabled(action in ("cue", "fixture")); self.arg2.setEnabled(action == "fixture")
        if action == "cue":
            self.arg1.addItems([c.name for c in e.project.cues])
        elif action == "fixture":
            self.arg1.addItems([f.name for f in e.project.patch.fixtures])
            self.arg1.currentTextChanged.connect(self._fill_channels)
            self._fill_channels(self.arg1.currentText())

    def _fill_channels(self, name):
        self.arg2.clear()
        try:
            self.arg2.addItems([c.name for c in self.win.engine.project.patch.find(name).profile.channels])
        except KeyError:
            pass

    def _toggle_osc(self):
        w = self.win
        if w.osc:
            w.osc.stop(); w.osc = None
        else:
            try:
                w.engine.project.osc_port = self.osc_port.value()
                w.osc = OscServer(w.runner, self.osc_port.value()); w.osc.start()
            except OSError as e:
                w.osc = None
                QMessageBox.warning(self, "OSC", f"Impossibile aprire la porta: {e}")
        self.osc_btn.setText("Ferma OSC" if w.osc else "Avvia OSC")

    def _open_midi(self):
        try:
            self.win.midi.open(self.ports.currentText())
            self.status.setText(f"MIDI aperto: {self.ports.currentText()}")
        except Exception as e:
            QMessageBox.warning(self, "MIDI", str(e))

    def _learn(self):
        a = self.action.currentText()
        args = {}
        if a == "cue":
            args = {"cue": self.arg1.currentText()}
        elif a == "fixture":
            args = {"fixture": self.arg1.currentText(), "channel": self.arg2.currentText()}
        if a in ("cue", "fixture") and not all(args.values()):
            QMessageBox.information(self, "MIDI", "Scegli cue o fixture/canale."); return
        self.win.midi.learn(a, args)
        self.learn_btn.setText("In attesa di un messaggio MIDI…")

    def _poll(self):
        if not self.win.midi.learning and self.learn_btn.text().startswith("In attesa"):
            self.learn_btn.setText("Impara (poi tocca un pad o gira una manopola)")
            self._reload()

    def _reload(self):
        self.list.clear()
        for m in self.win.midi.mappings:
            self.list.addItem(f"{m.kind} ch{m.channel + 1} #{m.number} → {m.action} {m.args or ''}")

    def _remove(self):
        i = self.list.currentRow()
        if i >= 0:
            del self.win.midi.mappings[i]; self._reload()

    def done(self, r):
        self.t.stop(); self.win.midi.cancel_learn(); super().done(r)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = LightEngine()
        self.path: str | None = None
        self.runner = ActionRunner(self.engine)
        self.midi = MidiController(self.runner, self.engine.project.midi_mappings)
        self.osc: OscServer | None = None
        self._seq_steps: list[Preset] = []
        self._seq_fixtures: list[str] = []
        self.preview = PreviewWidget(self.engine)
        self.faders = FaderPanel(self.engine)
        self.fixlist = QListWidget()
        self.fixlist.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.livedock = LiveDock(self.engine)
        dock = QDockWidget("Live", self); dock.setWidget(self.livedock)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.preview.selected.connect(self._select)
        self.fixlist.currentTextChanged.connect(self._select_from_list)
        split = QSplitter()
        left = QWidget(); lv = QVBoxLayout(left); lv.addWidget(QLabel("Patch")); lv.addWidget(self.fixlist)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.faders)
        for w in (left, self.preview, scroll):
            split.addWidget(w)
        split.setSizes([220, 560, 320])
        self.setCentralWidget(split)
        self._menus()
        self.out_btn = QPushButton("Output OFF")
        self.out_btn.setCheckable(True)
        self.out_btn.toggled.connect(self._toggle_output)
        self.statusBar().addPermanentWidget(self.out_btn)
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(40)
        self._retitle(); self._refresh_list()

    def _menus(self):
        def act(menu, text, fn, key=None):
            a = QAction(text, self); a.triggered.connect(fn)
            if key: a.setShortcut(key)
            menu.addAction(a)
        m = self.menuBar().addMenu("File")
        act(m, "Nuovo", self.new, "Ctrl+N"); act(m, "Apri…", self.open, "Ctrl+O")
        act(m, "Salva", self.save, "Ctrl+S"); act(m, "Salva con nome…", self.save_as)
        p = self.menuBar().addMenu("Patch")
        act(p, "Aggiungi fixture…", self.add_fixture); act(p, "Rimuovi selezionato", self.remove_fixture)
        act(p, "Importa profilo OFL…", self.import_ofl)
        act(p, "Azzera valori", self.clear_values)
        act(p, "Registra cue dalla selezione…", self.record_cue, "Ctrl+R")
        act(p, "Sequenza: aggiungi step dai valori", self.add_step, "Ctrl+Shift+R")
        act(p, "Sequenza: termina e crea cue…", self.finish_sequence)
        o = self.menuBar().addMenu("Uscite"); act(o, "Configura uscite…", self.outputs)
        c = self.menuBar().addMenu("Controllo"); act(c, "MIDI / OSC…", self.control)

    def _retitle(self):
        self.setWindowTitle(f"ShowSuite Light — {self.engine.project.name}")

    def _refresh_list(self):
        self.fixlist.blockSignals(True)
        self.fixlist.clear()
        for f in self.engine.project.patch.fixtures:
            self.fixlist.addItem(f.name)
        self.fixlist.blockSignals(False)
        self.preview.update()

    def _select(self, name):
        self.preview.current = name
        self.faders.show_fixture(name)
        items = self.fixlist.findItems(name, Qt.MatchExactly)
        if items:
            self.fixlist.blockSignals(True); self.fixlist.setCurrentItem(items[0]); self.fixlist.blockSignals(False)

    def _select_from_list(self, name):
        if name:
            self._select(name); self.preview.update()

    def add_fixture(self):
        d = AddFixtureDialog(self.engine, self)
        if d.exec() == QDialog.Accepted and d.create() == 0:
            QMessageBox.warning(self, "Patch", "Nessun indirizzo libero in questo universo.")
        self._refresh_list()

    def remove_fixture(self):
        n = self.preview.current
        if n:
            self.engine.remove_fixture(n)
            self.preview.current = None
            self.faders.show_fixture(None); self._refresh_list()

    def import_ofl(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Importa profili OFL", "", "Fixture OFL (*.json)")
        total = 0
        for f in files:
            try:
                total += self.engine.import_ofl(f)
            except (OflImportError, OSError, KeyError) as e:
                QMessageBox.warning(self, "Importa profilo", f"{f}\n{e}")
        if files:
            self.statusBar().showMessage(f"Importate {total} modalità", 5000)

    def clear_values(self):
        self.engine.clear_programmer(); self.faders.show_fixture(self.preview.current)

    def record_cue(self):
        names = [i.text() for i in self.fixlist.selectedItems()]
        if not names:
            QMessageBox.information(self, "Cue", "Seleziona uno o più fixture nell'elenco Patch.")
            return
        d = RecordCueDialog(self.engine, names, self)
        if d.exec() == QDialog.Accepted:
            self.engine.project.cues.append(d.build())
            for n in names:   # i valori sono ora nel cue: svuota il programmer per questi fixture
                self.engine.release_programmer(n)
            self.livedock.rebuild(); self.faders.show_fixture(self.preview.current)

    def add_step(self):
        names = [i.text() for i in self.fixlist.selectedItems()] or self._seq_fixtures
        if not names:
            QMessageBox.information(self, "Sequenza", "Seleziona i fixture nell'elenco Patch.")
            return
        if self._seq_fixtures and set(names) != set(self._seq_fixtures):
            QMessageBox.warning(self, "Sequenza", "Gli step devono usare gli stessi fixture. "
                                "Termina la sequenza in corso o riseleziona gli stessi fixture.")
            return
        values: dict[str, int] = {}
        for n in names:
            for ch, v in self.engine.values.get(n, {}).items():
                values.setdefault(ch, v)
        if not values:
            QMessageBox.information(self, "Sequenza", "Imposta almeno un valore coi fader prima.")
            return
        self._seq_fixtures = names
        self._seq_steps.append(Preset(f"Step {len(self._seq_steps) + 1}", values))
        for n in names:
            self.engine.release_programmer(n)
        self.faders.show_fixture(self.preview.current)
        self.statusBar().showMessage(f"Sequenza: {len(self._seq_steps)} step registrati", 5000)

    def finish_sequence(self):
        if len(self._seq_steps) < 2:
            QMessageBox.information(self, "Sequenza", "Servono almeno 2 step (Ctrl+Shift+R).")
            return
        d = SequenceDialog(len(self._seq_steps), self)
        if d.exec() == QDialog.Accepted:
            self.engine.project.cues.append(LiveCue(
                d.name.text() or "Sequenza", self._seq_fixtures, steps=self._seq_steps,
                beats_per_step=d.bps.value(), crossfade=d.xf.value(), loop=d.loop.isChecked(),
                priority=d.prio.value()))
            self._seq_steps, self._seq_fixtures = [], []
            self.livedock.rebuild()

    def control(self):
        ControlDialog(self).exec()

    def outputs(self):
        OutputsDialog(self.engine, self).exec()
        if self.out_btn.isChecked():
            self.engine.start_output()

    def _toggle_output(self, on):
        self.out_btn.setText("Output ON" if on else "Output OFF")
        if on:
            self.engine.start_output()
        else:
            self.engine.stop_output()

    def _tick(self):
        if not self.engine.output:
            self.engine.live.update()  # senza output il Preview deve comunque muoversi
        self.livedock.sync()
        self.preview.update()
        errs = self.engine.output_errors()
        self.statusBar().showMessage(errs[-1] if errs else "")

    # --- file ---
    def _load_into_engine(self, proj):
        self.engine.stop_output(); self.out_btn.setChecked(False)
        self.engine.project = proj
        self.midi.mappings = proj.midi_mappings
        self.engine.clear_programmer()
        self.faders.show_fixture(None); self._retitle(); self._refresh_list()
        self.engine.live.active.clear(); self.livedock.rebuild()

    def new(self):
        self.path = None; self._load_into_engine(pj.Project())

    def open(self):
        f, _ = QFileDialog.getOpenFileName(self, "Apri progetto", "", "ShowSuite Light (*.showsuite-light)")
        if f:
            try:
                self._load_into_engine(pj.load(f)); self.path = f
            except Exception as e:
                QMessageBox.critical(self, "Apri", str(e))

    def save(self):
        if not self.path:
            return self.save_as()
        pj.save(self.engine.project, self.path)

    def save_as(self):
        f, _ = QFileDialog.getSaveFileName(self, "Salva progetto", "", "ShowSuite Light (*.showsuite-light)")
        if f:
            if not f.endswith(".showsuite-light"):
                f += ".showsuite-light"
            self.path = f; pj.save(self.engine.project, f)

    def closeEvent(self, e):
        self.engine.stop_output(); self.midi.close()
        if self.osc:
            self.osc.stop()
        super().closeEvent(e)


def main() -> int:
    app = QApplication(sys.argv)
    w = MainWindow(); w.resize(1100, 640); w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
