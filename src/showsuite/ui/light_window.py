"""Finestra principale Light (PySide6): patch, Preview 2D, fader, uscite."""
from __future__ import annotations

import sys

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QStackedWidget, QToolBar, QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
                               QCheckBox, QDockWidget, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMainWindow, QMessageBox, QPushButton, QScrollArea, QSlider,
                               QSpinBox, QSplitter, QVBoxLayout, QWidget)

from ..light import project as pj
from ..light.control.actions import ACTIONS, ActionRunner
from ..light.control.clocksync import MidiClockSync
from ..light.control.dmxin import DmxInput, DmxMapping
from ..light.control.midi import MidiController
from ..light.control.osc import OscServer
from . import theme
from .design_view import DesignView
from .live_view import LiveView
from .preview import PreviewWidget
from ..light.effects import WAVES, Effect
from ..light.live import CURVES, LiveCue
from ..light.preset import Preset
from ..light.engine import LightEngine
from ..light.fixtures import FixtureInstance, PatchError
from ..light.fixtures.ofl import OflImportError

SHORTCUT_TEXT = "D Dimmer   C Color   G Gobo\nP Position   S Shutter   M Prism\nF Focus   Z Zoom   I Iris   R Frost\nO Overrides"


class FaderPanel(QWidget):
    """Proprietà del primo fixture selezionato; i valori vanno a tutta la selezione."""

    def __init__(self, engine: LightEngine):
        super().__init__()
        self.engine = engine
        self.lay = QVBoxLayout(self)
        self.title = QLabel("Nessun fixture selezionato")
        self.lay.addWidget(self.title)
        self.sliders: list[QWidget] = []
        self.lay.addStretch()

    def show_fixture(self, name: str | None) -> None:
        self.show_fixtures([name] if name else [])

    def show_fixtures(self, names: list[str]) -> None:
        for w in self.sliders:
            w.setParent(None)
        self.sliders.clear()
        if not names:
            self.title.setText("Nessun fixture selezionato")
            return
        first = self.engine.project.patch.find(names[0])
        if len(names) == 1:
            self.title.setText(f"{first.name}: U{first.universe} @{first.address}")
        else:
            self.title.setText(f"{len(names)} fixture selezionati (valori applicati a tutti)")
        for ch in first.profile.channels:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(ch.name)
            lab.setMinimumWidth(90)
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 65535 if ch.fine else 255)
            s.setValue(self.engine.get_value(first.name, ch.name))
            val = QLabel(str(s.value()))
            val.setMinimumWidth(40)

            def changed(v, n=ch.name, lbl=val):
                lbl.setText(str(v))
                for fx_name in names:
                    fx = self.engine.project.patch.find(fx_name)
                    if any(c.name == n for c in fx.profile.channels):
                        self.engine.set_value(fx_name, n, v)
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
        self.clock_chk = QCheckBox("Sincronizza il BPM con il MIDI clock esterno")
        self.clock_chk.setChecked(win.midi.clock.enabled)
        self.clock_chk.toggled.connect(lambda on: setattr(win.midi.clock, "enabled", on))
        v.addWidget(self.clock_chk)
        drow = QHBoxLayout()
        self.dmx_btn = QPushButton("Ferma DMX-In" if win.dmxin else "Avvia DMX-In (Art-Net/sACN)")
        self.dmx_btn.clicked.connect(self._toggle_dmxin)
        self.dmx_uni = QSpinBox(); self.dmx_uni.setRange(0, 32767); self.dmx_uni.setValue(1)
        self.dmx_ch = QSpinBox(); self.dmx_ch.setRange(1, 512)
        add_dmx = QPushButton("Mappa canale DMX → azione"); add_dmx.clicked.connect(self._add_dmx)
        for w_ in (self.dmx_btn, QLabel("U"), self.dmx_uni, QLabel("Ch"), self.dmx_ch, add_dmx):
            drow.addWidget(w_)
        v.addLayout(drow)
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

    def _toggle_dmxin(self):
        w = self.win
        if w.dmxin:
            w.dmxin.stop(); w.dmxin = None
        else:
            try:
                w.dmxin = DmxInput(w.runner, w.engine.project.dmx_mappings); w.dmxin.start()
            except OSError as e:
                w.dmxin = None
                QMessageBox.warning(self, "DMX-In", f"Impossibile aprire le porte: {e}")
        self.dmx_btn.setText("Ferma DMX-In" if w.dmxin else "Avvia DMX-In (Art-Net/sACN)")

    def _action_args(self):
        a = self.action.currentText()
        args = {}
        if a == "cue":
            args = {"cue": self.arg1.currentText()}
        elif a == "fixture":
            args = {"fixture": self.arg1.currentText(), "channel": self.arg2.currentText()}
        return a, args

    def _add_dmx(self):
        a, args = self._action_args()
        if a in ("cue", "fixture") and not all(args.values()):
            QMessageBox.information(self, "DMX-In", "Scegli cue o fixture/canale."); return
        m = self.win.engine.project.dmx_mappings
        m[:] = [x for x in m if (x.universe, x.channel) != (self.dmx_uni.value(), self.dmx_ch.value())]
        m.append(DmxMapping(self.dmx_uni.value(), self.dmx_ch.value(), a, args))
        self._reload()

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
            self.list.addItem(f"MIDI {m.kind} ch{m.channel + 1} #{m.number} → {m.action} {m.args or ''}")
        for m in self.win.engine.project.dmx_mappings:
            self.list.addItem(f"DMX U{m.universe} ch{m.channel} → {m.action} {m.args or ''}")

    def _remove(self):
        i = self.list.currentRow()
        mm, dm = self.win.midi.mappings, self.win.engine.project.dmx_mappings
        if 0 <= i < len(mm):
            del mm[i]
        elif len(mm) <= i < len(mm) + len(dm):
            del dm[i - len(mm)]
        else:
            return
        self._reload()

    def done(self, r):
        self.t.stop(); self.win.midi.cancel_learn(); super().done(r)


class TransportBar(QToolBar):
    """Master, beat, blackout/freeze/blind, output."""

    def __init__(self, win: "MainWindow"):
        super().__init__("Controlli")
        self.setMovable(False)
        e = win.engine
        self.bpm = QDoubleSpinBox(); self.bpm.setRange(20, 400); self.bpm.setValue(e.beat.bpm)
        self.bpm.setDecimals(1); self.bpm.valueChanged.connect(lambda x: e.beat.set_bpm(x))
        tap = QPushButton("Tap"); tap.clicked.connect(self._tap)
        self.master = QSlider(Qt.Horizontal); self.master.setRange(0, 100); self.master.setValue(100)
        self.master.setMinimumWidth(180)
        self.master.valueChanged.connect(lambda x: setattr(e, "grand_master", x / 100))
        self.bo = QPushButton("Blackout"); self.bo.setCheckable(True); self.bo.setObjectName("danger")
        self.bo.toggled.connect(lambda on: setattr(e, "blackout", on))
        self.fr = QPushButton("Freeze"); self.fr.setCheckable(True)
        self.fr.toggled.connect(e.set_freeze)
        self.bl = QPushButton("Blind"); self.bl.setCheckable(True)
        self.bl.setToolTip("Le modifiche del programmer non vanno in uscita")
        self.bl.toggled.connect(lambda on: setattr(e, "blind", on))
        self.hl = QPushButton("Evidenzia"); self.hl.setCheckable(True)
        self.hl.setToolTip("Accende i fixture selezionati per riconoscerli sul palco")
        self.hl.toggled.connect(win.set_highlight)
        self.out = QPushButton("Output OFF"); self.out.setCheckable(True)
        self.out.toggled.connect(win._toggle_output)
        self.design = QPushButton("Design"); self.design.setCheckable(True)
        self.live = QPushButton("Live"); self.live.setCheckable(True)
        self.addWidget(QLabel("BPM")); self.addWidget(self.bpm); self.addWidget(tap)
        self.addSeparator()
        self.addWidget(QLabel("Master")); self.addWidget(self.master)
        for w in (self.bo, self.fr, self.bl, self.hl):
            self.addWidget(w)
        spacer = QWidget(); spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                                                 spacer.sizePolicy().verticalPolicy().Preferred)
        spacer.setStyleSheet("background: transparent;")
        self.addWidget(spacer)
        self.addWidget(self.out)

    def _tap(self):
        self.parent().engine.beat.tap()
        self.bpm.blockSignals(True); self.bpm.setValue(self.parent().engine.beat.bpm); self.bpm.blockSignals(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = LightEngine()
        self.path: str | None = None
        self.runner = ActionRunner(self.engine)
        self.midi = MidiController(self.runner, self.engine.project.midi_mappings)
        self.osc: OscServer | None = None
        self.dmxin: DmxInput | None = None
        self.midi.clock = MidiClockSync(self.engine.beat)
        self._seq_steps: list[Preset] = []
        self._seq_fixtures: list[str] = []
        self.preview = PreviewWidget(self.engine)
        self.faders = FaderPanel(self.engine)
        self.live_view = LiveView(self.engine)
        self.fixlist = QListWidget()
        self.fixlist.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.preview.selection_changed.connect(self._on_preview_selection)
        self.fixlist.itemSelectionChanged.connect(self._on_list_selection)
        # layout: patch | preview ; sotto Design/Live
        left = QWidget(); lv = QVBoxLayout(left); lv.addWidget(QLabel("Patch")); lv.addWidget(self.fixlist)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.faders)
        scroll.setMinimumWidth(320)
        self.design = DesignView(self.engine, scroll)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.design); self.stack.addWidget(self.live_view)
        self.palette_tree = QTreeWidget(); self.palette_tree.setHeaderHidden(True)
        self.palette_tree.itemDoubleClicked.connect(self._apply_preset_item)
        self.shortcuts = QLabel(SHORTCUT_TEXT); self.shortcuts.setStyleSheet("color:#8b90a0;padding:6px;")
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(QLabel("<b>Preset Palette</b>")); rv.addWidget(self.palette_tree, 1)
        rv.addWidget(QLabel("<b>Shortcuts</b>")); rv.addWidget(self.shortcuts)
        top = QSplitter(); top.addWidget(left); top.addWidget(self.preview); top.addWidget(right)
        top.setSizes([180, 760, 220])
        self.bar = TransportBar(self)
        tabs = QWidget(); th = QHBoxLayout(tabs); th.setContentsMargins(8, 4, 8, 0); th.addStretch()
        for b in (self.bar.design, self.bar.live):
            b.setStyleSheet("QPushButton{border-radius:13px;padding:4px 22px;min-height:18px;}"); th.addWidget(b)
        th.addStretch()
        bottom = QWidget(); bv = QVBoxLayout(bottom); bv.setContentsMargins(0, 0, 0, 0); bv.setSpacing(0)
        bv.addWidget(tabs); bv.addWidget(self.stack)
        main = QSplitter(Qt.Vertical); main.addWidget(top); main.addWidget(bottom); main.setSizes([420, 280])
        self.setCentralWidget(main)
        self.addToolBar(self.bar)
        self.bar.design.clicked.connect(lambda: self.show_view(0))
        self.bar.live.clicked.connect(lambda: self.show_view(1))
        self.show_view(1)
        self._menus()
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(40)
        self._retitle(); self._refresh_list(); self._refresh_palette()

    def _apply_preset_item(self, item, _col=0):
        pr = item.data(0, Qt.UserRole)
        names = self.selected_names()
        if pr is None or not names:
            return
        for n in names:
            for ch, v in pr.values.items():
                try:
                    self.engine.set_value(n, ch, v)
                except KeyError:
                    pass
        self.design.refresh_dots()

    def _refresh_palette(self):
        self.palette_tree.clear()
        for pal in self.engine.project.palettes:
            top = QTreeWidgetItem([pal.name]); self.palette_tree.addTopLevelItem(top)
            for pr in pal.presets:
                it = QTreeWidgetItem([pr.name]); it.setData(0, Qt.UserRole, pr); top.addChild(it)
        self.palette_tree.expandAll()

    def _update_tint(self):
        fx = self.engine.project.patch.fixtures
        r = g = b = 0
        for f in fx:
            c = self.engine.fixture_color(f); r += c[0]; g += c[1]; b += c[2]
        n = max(1, len(fx)); base = (14, 15, 18)
        a = 0.22   # intensità del riflesso
        self.preview.tint = tuple(int(base[i] + (c / n - base[i]) * a) for i, c in enumerate((r, g, b)))

    def show_view(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.bar.design.setChecked(i == 0); self.bar.live.setChecked(i == 1)

    @property
    def out_btn(self):
        return self.bar.out

    @property
    def livedock(self):   # compatibilità: ora è la Live view
        return self.live_view

    def _menus(self):
        def act(menu, text, fn, key=None):
            a = QAction(text, self); a.triggered.connect(fn)
            if key: a.setShortcut(key)
            menu.addAction(a)
        m = self.menuBar().addMenu("File")
        act(m, "Nuovo", self.new, "Ctrl+N"); act(m, "Apri…", self.open, "Ctrl+O")
        act(m, "Salva", self.save, "Ctrl+S"); act(m, "Salva con nome…", self.save_as)
        v = self.menuBar().addMenu("Vista")
        act(v, "Design", lambda: self.show_view(0), "Ctrl+D"); act(v, "Live", lambda: self.show_view(1), "Ctrl+L")
        p = self.menuBar().addMenu("Patch")
        act(p, "Aggiungi fixture…", self.add_fixture); act(p, "Rimuovi selezionati", self.remove_fixture)
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
        self.preview.set_selection([n for n in self.preview.selection], emit=False)
        self._sync_list()
        self.preview.update()

    def _sync_list(self):
        self.fixlist.blockSignals(True)
        for i in range(self.fixlist.count()):
            it = self.fixlist.item(i)
            it.setSelected(it.text() in self.preview.selection)
        self.fixlist.blockSignals(False)

    def _on_preview_selection(self, names):
        self._sync_list()
        self.faders.show_fixtures(names); self.design.set_selection(names)
        if self.bar.hl.isChecked():
            self.engine.set_highlight(names)

    def _on_list_selection(self):
        names = [i.text() for i in self.fixlist.selectedItems()]
        self.preview.set_selection(names)

    def selected_names(self) -> list[str]:
        return list(self.preview.selection)

    def _select(self, name):   # compatibilità con i test/azioni
        self.preview.set_selection([name] if name else [])

    def set_highlight(self, on: bool):
        self.engine.set_highlight(self.preview.selection if on else [])

    def add_fixture(self):
        d = AddFixtureDialog(self.engine, self)
        if d.exec() == QDialog.Accepted and d.create() == 0:
            QMessageBox.warning(self, "Patch", "Nessun indirizzo libero in questo universo.")
        self._refresh_list()

    def remove_fixture(self):
        names = self.selected_names()
        if not names:
            return
        for n in names:
            self.engine.remove_fixture(n)
        self.preview.set_selection([])
        self._refresh_list()

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
        self.engine.clear_programmer(); self.faders.show_fixtures(self.selected_names())

    def record_cue(self):
        names = self.selected_names()
        if not names:
            QMessageBox.information(self, "Cue", "Seleziona uno o più fixture nell'elenco Patch.")
            return
        d = RecordCueDialog(self.engine, names, self)
        if d.exec() == QDialog.Accepted:
            self.engine.project.cues.append(d.build())
            for n in names:   # i valori sono ora nel cue: svuota il programmer per questi fixture
                self.engine.release_programmer(n)
            self.live_view.add_cue_button(self.engine.project.cues[-1].name)
            self.faders.show_fixtures(self.selected_names())

    def add_step(self):
        names = self.selected_names() or self._seq_fixtures
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
        self.faders.show_fixtures(self.selected_names())
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
            self.live_view.add_cue_button(self.engine.project.cues[-1].name)

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
        self._tint_n = getattr(self, '_tint_n', 0) + 1
        if self._tint_n % 5 == 0:
            self._update_tint()
        self.preview.update()
        errs = self.engine.output_errors()
        self.statusBar().showMessage(errs[-1] if errs else "")

    # --- file ---
    def _load_into_engine(self, proj):
        self.engine.stop_output(); self.out_btn.setChecked(False)
        self.engine.project = proj
        self.midi.mappings = proj.midi_mappings
        if self.dmxin:
            self.dmxin.mappings = proj.dmx_mappings
        self.engine.clear_programmer()
        self.preview.set_selection([], emit=False); self.faders.show_fixtures([])
        self._retitle(); self._refresh_list(); self._refresh_palette()
        self.engine.live.active.clear(); self.live_view.rebuild()

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
        if self.dmxin:
            self.dmxin.stop()
        super().closeEvent(e)


def main() -> int:
    app = QApplication(sys.argv)
    theme.apply(app)
    w = MainWindow(); w.resize(1100, 640); w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
