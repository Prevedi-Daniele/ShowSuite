/**
 * QLabWorkspace.jsx — Interfaccia Principale del Workspace di QLab 5 per ShowSuite (STEP 4.2)
 * 
 * Integra:
 * - Motore centrale CueScheduler a 60 FPS con precisione temporale al millisecondo
 * - Tasto GO gigante con barra di progresso e countdown live
 * - Barra di trasporto completa: Panic (con dissolvenza), Stop, Pause, Resume, Reset, Load
 * - Standby Cue Display in evidenza ad alto contrasto
 * - Tabella gerarchica delle Cue con colonne configurabili ed espansione ad albero
 * - Modalità Cue Cart a griglia con trigger istantanei colorati
 * - Cue Inspector inferiore dockabile e comprimibile
 * - Scorciatoie da tastiera native: Barra Spaziatrice (GO), ESC (Panic), Frecce Su/Giù
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import MacButton from '../shared/components/MacButton.jsx';
import CueListTable from './CueListTable.jsx';
import CueInspector from './CueInspector.jsx';
import CueCartGrid from './CueCartGrid.jsx';
import StageGeometryEditor from './StageGeometryEditor.jsx';
import TimecodeHUD from './TimecodeHUD.jsx';
import {
  CueScheduler,
  BaseCue,
  GroupCue,
  AudioCue,
  MicCue,
  NetworkCue,
  MidiCue,
  TimecodeCue,
  CueType,
  GroupMode,
  ContinueMode,
  CueState,
  ChaserState,
} from '../core/qlab/index.js';
import {
  Play,
  Square,
  Pause,
  RotateCcw,
  Volume2,
  Video,
  FileText,
  Sliders,
  Send,
  Radio,
  FolderPlus,
  Clock,
  Mic,
  LayoutGrid,
  List,
  Columns,
  Sparkles,
  ChevronUp,
  ChevronDown,
  Download,
  AlertTriangle,
  Maximize2,
} from 'lucide-react';

export default function QLabWorkspace() {
  // Istanza immutabile dello Scheduler QLab
  const [scheduler] = useState(() => new CueScheduler());

  // Modalità Workspace: 'cuelist' | 'cart' | 'stages'
  const [workspaceMode, setWorkspaceMode] = useState('cuelist');

  // Stato sincronizzato per React
  const [cues, setCues] = useState(() => scheduler.cues);
  const [cartCues, setCartCues] = useState([]);
  const [selectedCueId, setSelectedCueId] = useState(null);
  const [standbyCue, setStandbyCue] = useState(null);
  const [runningCount, setRunningCount] = useState(0);
  const [isPanicking, setIsPanicking] = useState(false);
  const [elapsedShowTime, setElapsedShowTime] = useState(0);

  // Configurazione Colonne della Cue List
  const [isColumnsMenuOpen, setIsColumnsMenuOpen] = useState(false);
  const [columnsConfig, setColumnsConfig] = useState({
    number: true,
    status: true,
    type: true,
    name: true,
    target: true,
    preWait: true,
    duration: true,
    postWait: true,
    continueMode: true,
    notes: true,
  });

  // Stato del cassetto Inspector inferiore
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);

  // Inizializza con show demo realistico al primo montaggio
  useEffect(() => {
    initDemoShow(scheduler);
    setCues([...scheduler.cues]);
    const initStandby = scheduler.getStandbyCue();
    setStandbyCue(initStandby);
    if (initStandby) setSelectedCueId(initStandby.id);

    // Inizializza celle per la Cue Cart
    const defaultCart = [
      new BaseCue({ id: 'cart_1', name: 'Jingle Apertura', targetId: 'jingle_sigla.wav', duration: 4.0, color: 'blue' }),
      new BaseCue({ id: 'cart_2', name: 'Applausi Folla', targetId: 'applause_crowd.wav', duration: 6.0, color: 'green' }),
      new BaseCue({ id: 'cart_3', name: 'Stacco Comico', targetId: 'rimshot.wav', duration: 1.5, color: 'orange' }),
      new BaseCue({ id: 'cart_4', name: 'Tuono / Temporale', targetId: 'thunder.wav', duration: 5.0, color: 'purple' }),
      new BaseCue({ id: 'cart_5', name: 'Sirena Emergenza', targetId: 'siren.wav', duration: 4.0, color: 'red' }),
      new BaseCue({ id: 'cart_6', name: 'BGM Loop Attesa', targetId: 'ambient_loop.wav', duration: 15.0, color: 'cyan' }),
    ];
    setCartCues(defaultCart);
  }, [scheduler]);

  // Registra lo scheduler nel bridge OSC interno di ShowSuite
  useEffect(() => {
    import('../shared/ShowSuiteBridge.js').then((module) => {
      module.default.registerQLab({ cueScheduler: scheduler });
    });
  }, [scheduler]);

  // Loop animazione ad alta precisione a 60 FPS
  useEffect(() => {
    let animId;
    let lastTime = performance.now();

    const tickLoop = (now) => {
      const dt = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;

      // 1. Tick dello scheduler
      scheduler.tick(dt);

      // 2. Tick delle celle Cart in esecuzione
      cartCues.forEach((c) => {
        if (c.state === CueState.RUNNING) {
          c.tick(dt);
        }
      });

      // 3. Aggiorna tempo totale di show se c'è almeno una cue attiva
      if (scheduler.runningCues.size > 0 || isPanicking) {
        setElapsedShowTime((prev) => prev + dt);
      }

      // 4. Sincronizza stato di rendering
      setRunningCount(scheduler.runningCues.size);
      setIsPanicking(scheduler.isPanicking);
      setStandbyCue(scheduler.getStandbyCue());

      // Trigger re-render a 60fps solo se ci sono cue in esecuzione per non appesantire la CPU
      if (scheduler.runningCues.size > 0 || cartCues.some((c) => c.state === CueState.RUNNING)) {
        setCues([...scheduler.cues]);
        setCartCues([...cartCues]);
      }

      animId = requestAnimationFrame(tickLoop);
    };

    animId = requestAnimationFrame(tickLoop);
    return () => cancelAnimationFrame(animId);
  }, [scheduler, cartCues, isPanicking]);

  // Gestione Scorciatoie da Tastiera Globali (Spacebar per GO, ESC per Panic)
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignora se l'utente sta digitando in un input o textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        handleGo();
      } else if (e.code === 'Escape') {
        e.preventDefault();
        handlePanic();
      } else if (e.code === 'KeyP') {
        e.preventDefault();
        handlePauseResume();
      } else if (e.code === 'Period') {
        e.preventDefault();
        handleHardStop();
      } else if (e.code === 'ArrowDown') {
        e.preventDefault();
        scheduler.advancePlayhead();
        setStandbyCue(scheduler.getStandbyCue());
        setCues([...scheduler.cues]);
      } else if (e.code === 'ArrowUp') {
        e.preventDefault();
        scheduler.previousPlayhead();
        setStandbyCue(scheduler.getStandbyCue());
        setCues([...scheduler.cues]);
      } else if (workspaceMode === 'cart' && e.key >= '1' && e.key <= '9') {
        const idx = parseInt(e.key, 10) - 1;
        if (cartCues[idx]) {
          handleTriggerCartCue(cartCues[idx].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [scheduler, workspaceMode, cartCues]);

  // ─── Azioni di Trasporto ───────────────────────────────────────

  const handleGo = useCallback(() => {
    scheduler.go();
    setCues([...scheduler.cues]);
    setStandbyCue(scheduler.getStandbyCue());
  }, [scheduler]);

  const handlePanic = useCallback(() => {
    scheduler.panic(1.0); // Dissolvenza di 1.0s
    setIsPanicking(true);
  }, [scheduler]);

  const handleHardStop = useCallback(() => {
    scheduler.hardStop();
    cartCues.forEach((c) => c.stop());
    setCues([...scheduler.cues]);
    setCartCues([...cartCues]);
    setRunningCount(0);
    setIsPanicking(false);
  }, [scheduler, cartCues]);

  const handlePauseResume = useCallback(() => {
    const isAnyRunning = Array.from(scheduler.runningCues).some((c) => c.state === CueState.RUNNING);
    if (isAnyRunning) {
      scheduler.pause();
    } else {
      scheduler.resume();
    }
    setCues([...scheduler.cues]);
  }, [scheduler]);

  const handleReset = useCallback(() => {
    scheduler.reset();
    setElapsedShowTime(0);
    setCues([...scheduler.cues]);
    setStandbyCue(scheduler.getStandbyCue());
  }, [scheduler]);

  const handleLoad = useCallback(() => {
    scheduler.load();
    setCues([...scheduler.cues]);
  }, [scheduler]);

  // ─── Gestione Cue List ─────────────────────────────────────────

  const handleAddCue = (type) => {
    const count = scheduler.cues.length + 1;
    let newCue;

    if (type === CueType.GROUP) {
      newCue = new GroupCue({
        number: String(count),
        name: `Nuovo Gruppo ${count}`,
        mode: GroupMode.TIMELINE,
      });
    } else if (type === CueType.AUDIO) {
      newCue = new AudioCue({
        number: String(count),
        name: `Nuova Audio Cue ${count}`,
        targetId: 'audio_track.wav',
        duration: 8.0,
      });
    } else if (type === CueType.MIC) {
      newCue = new MicCue({
        number: String(count),
        name: `Live Mic ${count}`,
        inputDeviceName: 'Ingresso Microfono 1',
      });
    } else if (type === CueType.NETWORK) {
      newCue = new NetworkCue({
        number: String(count),
        name: `Network OSC Cue ${count}`,
        destination: '127.0.0.1',
        port: 53000,
        oscAddress: '/live/grandMaster',
      });
    } else if (type === CueType.MIDI) {
      newCue = new MidiCue({
        number: String(count),
        name: `MIDI Cue ${count}`,
        channel: 1,
        note: 60,
        velocity: 127,
      });
    } else if (type === CueType.TIMECODE) {
      newCue = new TimecodeCue({
        number: String(count),
        name: `Timecode Generator ${count}`,
        fps: 25,
        startTimecode: '01:00:00:00',
        duration: 30.0,
      });
    } else {
      newCue = new BaseCue({
        number: String(count),
        name: `Nuova ${type.toUpperCase()} Cue`,
        type,
        duration: type === CueType.VIDEO ? 5.0 : 1.0,
      });
    }

    scheduler.addCue(newCue);
    setCues([...scheduler.cues]);
    setSelectedCueId(newCue.id);
    if (!standbyCue) setStandbyCue(scheduler.getStandbyCue());
  };

  const handleSelectCue = (cueId) => {
    setSelectedCueId(cueId);
  };

  const handleGoSpecificCue = (cueId) => {
    scheduler.go(cueId);
    setCues([...scheduler.cues]);
    setStandbyCue(scheduler.getStandbyCue());
  };

  const handleStopSpecificCue = (cueId) => {
    scheduler.stop(cueId);
    setCues([...scheduler.cues]);
  };

  const handleDeleteCue = (cueId) => {
    scheduler.removeCue(cueId);
    setCues([...scheduler.cues]);
    setStandbyCue(scheduler.getStandbyCue());
    if (selectedCueId === cueId) setSelectedCueId(null);
  };

  const handleToggleArm = (cueId) => {
    const target = scheduler.findCueById(cueId);
    if (target) {
      if (target.armed) target.disarm();
      else target.arm();
      setCues([...scheduler.cues]);
    }
  };

  const handleUpdateCue = (cueId, patch) => {
    const target = scheduler.findCueById(cueId);
    if (target) {
      Object.assign(target, patch);
      if (target instanceof GroupCue && patch.mode) {
        target.updateDuration();
      }
      setCues([...scheduler.cues]);
      setStandbyCue(scheduler.getStandbyCue());
    }
  };

  // ─── Gestione Cart Cues ────────────────────────────────────────

  const handleTriggerCartCue = (cellId) => {
    const cell = cartCues.find((c) => c.id === cellId);
    if (cell) {
      if (cell.state === CueState.RUNNING) {
        cell.stop();
      } else {
        cell.start();
      }
      setCartCues([...cartCues]);
    }
  };

  const handleStopCartCue = (cellId) => {
    const cell = cartCues.find((c) => c.id === cellId);
    if (cell) {
      cell.stop();
      setCartCues([...cartCues]);
    }
  };

  const handleAddCartCue = () => {
    const newCell = new BaseCue({
      id: `cart_${Date.now()}`,
      name: `Cart Sound ${cartCues.length + 1}`,
      duration: 3.0,
      color: 'blue',
    });
    setCartCues([...cartCues, newCell]);
  };

  const handleUpdateCartCue = (cellId, patch) => {
    setCartCues((prev) =>
      prev.map((c) => (c.id === cellId ? Object.assign(c, patch) : c))
    );
  };

  const handleDeleteCartCue = (cellId) => {
    setCartCues((prev) => prev.filter((c) => c.id !== cellId));
  };

  // Cue selezionata per l'Inspector
  const selectedCue = scheduler.findCueById(selectedCueId);

  // Calcolo progresso dell'azione in Standby / Running
  const standbyProgress = standbyCue && standbyCue.getActionProgress ? standbyCue.getActionProgress() : 0;

  return (
    <div className="flex-1 flex flex-col bg-[#141416] text-mac-text overflow-hidden select-none">
      {/* ══ QLab Toolbar Superiore ═══════════════════════════════════════════ */}
      <div className="h-10 bg-[#1c1c20] border-b border-[#2d2d38] flex items-center justify-between px-3 shrink-0">
        {/* Pulsanti Rapidi Nuove Cues */}
        <div className="flex items-center space-x-1 overflow-x-auto">
          {[
            { type: CueType.GROUP, icon: FolderPlus, label: 'Group' },
            { type: CueType.AUDIO, icon: Volume2, label: 'Audio' },
            { type: CueType.MIC, icon: Mic, label: 'Mic' },
            { type: CueType.VIDEO, icon: Video, label: 'Video' },
            { type: CueType.TEXT, icon: FileText, label: 'Text' },
            { type: CueType.FADE, icon: Sliders, label: 'Fade' },
            { type: CueType.LIGHT, icon: Sparkles, label: 'Light' },
            { type: CueType.NETWORK, icon: Send, label: 'Network' },
            { type: CueType.MIDI, icon: Radio, label: 'MIDI' },
            { type: CueType.TIMECODE, icon: Clock, label: 'Timecode' },
          ].map((tool) => {
            const Icon = tool.icon;
            return (
              <MacButton
                key={tool.type}
                variant="toolbar"
                size="sm"
                icon={Icon}
                onClick={() => handleAddCue(tool.type)}
                title={`Crea nuova ${tool.label} Cue`}
              >
                {tool.label}
              </MacButton>
            );
          })}
        </div>

        {/* Destra: Switcher Cue List / Cue Cart & Config Colonne */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Switcher Modalità Workspace */}
          <div className="flex bg-black/40 p-0.5 rounded border border-zinc-800 text-[11px]">
            <button
              onClick={() => setWorkspaceMode('cuelist')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                workspaceMode === 'cuelist'
                  ? 'bg-mac-accent text-white font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <List size={12} />
              <span>Cue List</span>
            </button>
            <button
              onClick={() => setWorkspaceMode('cart')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                workspaceMode === 'cart'
                  ? 'bg-mac-accent text-white font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <LayoutGrid size={12} />
              <span>Cue Cart</span>
            </button>
            <button
              onClick={() => setWorkspaceMode('stages')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                workspaceMode === 'stages'
                  ? 'bg-mac-accent text-white font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Maximize2 size={12} />
              <span>Stage Geo</span>
            </button>
          </div>

          {/* Configurazione Colonne Dropdown (solo in Cue List) */}
          {workspaceMode === 'cuelist' && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsColumnsMenuOpen(!isColumnsMenuOpen)}
                className="p-1 rounded text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
                title="Configura Colonne Visibili"
              >
                <Columns size={14} />
              </button>

              {isColumnsMenuOpen && (
                <div
                  className="absolute right-0 top-8 w-44 bg-[#1c1c20] border border-[#2d2d38] rounded-lg shadow-2xl p-2 z-50 text-xs"
                  onMouseLeave={() => setIsColumnsMenuOpen(false)}
                >
                  <div className="text-[10px] uppercase font-bold text-zinc-500 mb-1.5 px-1">Colonne Visibili</div>
                  {Object.keys(columnsConfig).map((col) => (
                    <label key={col} className="flex items-center space-x-2 px-1 py-0.5 hover:bg-white/5 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={columnsConfig[col]}
                        onChange={(e) => setColumnsConfig({ ...columnsConfig, [col]: e.target.checked })}
                        className="rounded bg-zinc-800 border-zinc-700 text-mac-accent focus:ring-0"
                      />
                      <span className="capitalize text-zinc-300">{col}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="h-4 w-[1px] bg-[#33333d]" />
          <div className="flex items-center space-x-1.5 text-[11px] text-zinc-400">
            <span className={`w-2 h-2 rounded-full ${runningCount > 0 ? 'bg-emerald-500 animate-ping' : 'bg-zinc-600'}`} />
            <span>{runningCount > 0 ? `${runningCount} Attive` : 'Standby'}</span>
          </div>
        </div>
      </div>

      {/* ══ QLab Transport Bar (Tasto GO Gigante & Pannello Controlli) ═══════ */}
      <div className="h-24 bg-[#161619] border-b border-[#2d2d38] px-4 flex items-center justify-between shrink-0 shadow-lg relative">
        {/* Sinistra: Tasto GO Gigante con Barra di Progresso Integrata */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <MacButton
              variant="qlab-go"
              size="huge"
              icon={Play}
              onClick={handleGo}
              title="Esegui Cue in Standby (Barra Spaziatrice)"
              className="shadow-2xl shadow-green-950/80 hover:scale-[1.02] active:scale-95 transition-all w-36 h-20 text-2xl"
            >
              GO
            </MacButton>

            {/* Barra di Progresso Dinamica sul Bordo Inferiore del GO */}
            {standbyCue && standbyCue.state === CueState.RUNNING && (
              <div className="absolute -bottom-1 inset-x-0 h-1.5 bg-black/60 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-400 transition-all duration-75 shadow-sm shadow-emerald-400"
                  style={{ width: `${Math.round(standbyProgress * 100)}%` }}
                />
              </div>
            )}
          </div>

          {/* Tasti di Trasporto Ausiliari: Panic, Pause, Stop, Load, Reset */}
          <div className="flex flex-col space-y-1.5">
            <div className="flex space-x-1.5">
              <MacButton
                variant="panic"
                size="sm"
                icon={Square}
                onClick={handlePanic}
                title="Panic / Dissolvenza di Emergenza (ESC)"
                className={isPanicking ? 'animate-pulse' : ''}
              >
                Panic (ESC)
              </MacButton>
              <MacButton
                variant="destructive"
                size="sm"
                icon={Square}
                onClick={handleHardStop}
                title="Hard Stop Immediato (.)"
              >
                Stop
              </MacButton>
            </div>

            <div className="flex space-x-1.5">
              <MacButton
                variant="default"
                size="sm"
                icon={Pause}
                onClick={handlePauseResume}
                title="Pausa / Riprendi (P)"
              >
                Pausa
              </MacButton>
              <MacButton
                variant="default"
                size="sm"
                icon={Download}
                onClick={handleLoad}
                title="Pre-carica Cue in Standby (L)"
              >
                Load
              </MacButton>
              <MacButton
                variant="default"
                size="sm"
                icon={RotateCcw}
                onClick={handleReset}
                title="Reset Workspace a Inizio"
              >
                Reset
              </MacButton>
            </div>
          </div>
        </div>

        {/* Centro: Display Standby Cue Grande e Visibile & Timecode HUD */}
        <div className="flex-1 max-w-xl mx-4 flex items-center space-x-3">
          <div className="flex-1 px-4 py-2 bg-black/60 rounded-xl border border-[#33333d] flex flex-col justify-center shadow-inner">
            <div className="flex items-center justify-between text-[10px] text-zinc-400 uppercase tracking-wider font-mono mb-0.5">
              <span className="flex items-center space-x-1 text-amber-400 font-bold">
                <span>● IN STANDBY:</span>
              </span>
              <span>{standbyCue ? `Tipo: ${standbyCue.type.toUpperCase()}` : 'Coda vuota'}</span>
            </div>

            <div className="text-sm font-bold text-white truncate font-mono flex items-center space-x-2">
              {standbyCue ? (
                <>
                  <span className="text-amber-400 font-extrabold">[{standbyCue.number || '-'}]</span>
                  <span className="truncate">{standbyCue.name}</span>
                </>
              ) : (
                <span className="text-zinc-600 font-normal">Nessuna Cue pronta all'avvio</span>
              )}
            </div>

            {standbyCue && (
              <div className="flex items-center space-x-4 text-[10px] text-zinc-400 font-mono mt-1 pt-1 border-t border-zinc-800">
                <span>Pre: {standbyCue.preWait}s</span>
                <span>Durata: {standbyCue.duration}s</span>
                <span>Post: {standbyCue.postWait}s</span>
                <span className="text-blue-400 capitalize">{standbyCue.continueMode.replace('_', ' ')}</span>
              </div>
            )}
          </div>

          {/* Timecode HUD Live Monitor */}
          <TimecodeHUD
            timecodeStr="01:00:00:00"
            chaserState={runningCount > 0 ? ChaserState.LOCKED : ChaserState.OFFLINE}
            fps={25}
            source="MTC"
          />
        </div>

        {/* Destra: Orologio Show Time & Contatore Cues */}
        <div className="text-right flex flex-col justify-center">
          <div className="text-2xl font-mono font-bold text-zinc-100 tracking-wider">
            {formatShowTime(elapsedShowTime)}
          </div>
          <div className="text-[10px] text-zinc-400 font-mono flex items-center justify-end space-x-2">
            <span>Show Time</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-zinc-300 font-semibold">{runningCount} Cue attive</span>
          </div>
        </div>
      </div>

      {/* ══ Area Contenuto: Cue List o Cue Cart ═════════════════════════════ */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {workspaceMode === 'cuelist' ? (
          <>
            {/* Tabella Cue List */}
            <div className="flex-1 flex overflow-hidden">
              <CueListTable
                cues={cues}
                standbyCueId={standbyCue ? standbyCue.id : null}
                selectedCueId={selectedCueId}
                columnsConfig={columnsConfig}
                onSelectCue={handleSelectCue}
                onGoCue={handleGoSpecificCue}
                onStopCue={handleStopSpecificCue}
                onDeleteCue={handleDeleteCue}
                onToggleArm={handleToggleArm}
              />
            </div>

            {/* Cue Inspector Dockable Inferiore */}
            <div
              className={`border-t border-[#2d2d38] bg-[#161619] transition-all duration-200 flex flex-col shrink-0 ${
                isInspectorOpen ? (selectedCue && (selectedCue.type === CueType.AUDIO || selectedCue.type === CueType.MIC) ? 'h-80' : 'h-52') : 'h-7'
              }`}
            >
              {/* Barra Toggle Inspector */}
              <div
                onClick={() => setIsInspectorOpen(!isInspectorOpen)}
                className="h-7 bg-[#1c1c21] border-b border-[#2d2d34] px-3 flex items-center justify-between text-xs text-zinc-400 cursor-pointer hover:bg-white/5 select-none"
              >
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-zinc-300">Cue Inspector</span>
                  {selectedCue && (
                    <span className="font-mono text-[10px] text-amber-400">
                      — [{selectedCue.number || '-'}] {selectedCue.name}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-1 text-zinc-500">
                  <span className="text-[10px]">{isInspectorOpen ? 'Comprimi' : 'Espandi'}</span>
                  {isInspectorOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                </div>
              </div>

              {/* Corpo Inspector */}
              {isInspectorOpen && (
                <div className="flex-1 overflow-hidden">
                  <CueInspector cue={selectedCue} onUpdateCue={handleUpdateCue} />
                </div>
              )}
            </div>
          </>
        ) : workspaceMode === 'stages' ? (
          /* Stage Geometry Editor */
          <StageGeometryEditor />
        ) : (
          /* Cue Cart a Griglia */
          <CueCartGrid
            cues={cartCues}
            onTriggerCue={handleTriggerCartCue}
            onStopCue={handleStopCartCue}
            onAddCartCue={handleAddCartCue}
            onUpdateCartCue={handleUpdateCartCue}
            onDeleteCartCue={handleDeleteCartCue}
          />
        )}
      </div>
    </div>
  );
}

// ─── Helpers: Formattazione Tempo Show ─────────────────────────────
function formatShowTime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 100);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

// ─── Demo Show Populator ──────────────────────────────────────────
function initDemoShow(scheduler) {
  // 1. Audio di sala con Auto-continue
  const q1 = new AudioCue({
    number: '1.0',
    name: 'Musica di Ingresso Sala / Preshow',
    targetId: 'preshow_track_01.wav',
    duration: 12.0,
    inPoint: 0.5,
    outPoint: 11.5,
    postWait: 2.0,
    continueMode: ContinueMode.AUTO_CONTINUE,
    color: 'blue',
  });
  q1.addSlice(3.0, 1);
  q1.addSlice(6.5, 2);

  // 2. Luce di scena
  const q2 = new BaseCue({
    number: '2.0',
    name: 'Sala Buio / Truss Blue Ambiance',
    type: CueType.LIGHT,
    duration: 3.0,
    continueMode: ContinueMode.AUTO_FOLLOW,
    color: 'purple',
  });

  // 3. Gruppo Timeline (Intro Show: Video + Audio + Strobo contemporanei)
  const q3 = new GroupCue({
    number: '3.0',
    name: 'Intro Show (Audio + Video + Strobo)',
    mode: GroupMode.TIMELINE,
    color: 'orange',
  });
  q3.addChild(
    new BaseCue({
      number: '3.1',
      name: 'Sigla Apertura HD (Wall LED)',
      type: CueType.VIDEO,
      targetId: 'sigla_ledwall_4k.mp4',
      duration: 8.0,
    })
  );
  q3.addChild(
    new AudioCue({
      number: '3.2',
      name: 'Theme Song 5.1 Surround',
      targetId: 'theme_surround_mix.wav',
      channels: 6,
      duration: 8.0,
    })
  );
  q3.addChild(
    new BaseCue({
      number: '3.3',
      name: 'Fade In Volume Master',
      type: CueType.FADE,
      preWait: 0.5,
      duration: 2.0,
    })
  );

  // 4. Testo di benvenuto
  const q4 = new BaseCue({
    number: '4.0',
    name: 'Titolo di Benvenuto Proiettore',
    type: CueType.TEXT,
    duration: 5.0,
    color: 'green',
  });

  // 5. Gruppo Playlist (Stacchi comici in sequenza)
  const q5 = new GroupCue({
    number: '5.0',
    name: 'Stacchi Musicali Commedia',
    mode: GroupMode.PLAYLIST,
  });
  q5.addChild(
    new AudioCue({
      number: '5.1',
      name: 'Rullo Tamburi / Suspense',
      targetId: 'drumroll.wav',
      duration: 2.5,
    })
  );
  q5.addChild(
    new AudioCue({
      number: '5.2',
      name: 'Jingle Entrata Presentatore',
      targetId: 'jingle_in.wav',
      duration: 3.5,
    })
  );

  // 6. Mic Cue (Live Microfono Presentatore)
  const q6 = new MicCue({
    number: '6.0',
    name: 'Live Mic Presentatore (Arco Wireless)',
    inputDeviceName: 'Wireless Mic Rec 1 (Dante)',
    micGain: 3.0,
    color: 'green',
  });

  // 7. Network Cue OSC verso Lightkey
  const q7 = new BaseCue({
    number: '7.0',
    name: 'OSC Command -> Lightkey Blackout',
    type: CueType.NETWORK,
    targetId: '127.0.0.1:8000 (/showsuite/blackout)',
    duration: 0.5,
    color: 'red',
  });

  scheduler.addCue(q1);
  scheduler.addCue(q2);
  scheduler.addCue(q3);
  scheduler.addCue(q4);
  scheduler.addCue(q5);
  scheduler.addCue(q6);
  scheduler.addCue(q7);
}
