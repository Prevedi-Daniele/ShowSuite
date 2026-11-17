import React, { useState, useEffect, useRef, useCallback } from 'react';
import MacButton from '../shared/components/MacButton';
import MacSegmentedControl from '../shared/components/MacSegmentedControl';
import StageCanvas2D from './StageCanvas2D';
import AddFixtureModal from './AddFixtureModal';
import FixturePropertiesHUD from './FixturePropertiesHUD';
import PalettesPanel from './PalettesPanel';
import CueListPanel from './CueListPanel';
import EffectsPanel from './EffectsPanel';
import LiveView from './LiveView';
import { PaletteManager, CueEngine, PaletteType, LiveController } from '../core/control/index.js';
import { EffectsEngine } from '../core/effects/index.js';
import showSuiteBridge from '../shared/ShowSuiteBridge.js';
import {
  Sparkles,
  Sliders,
  Palette,
  Plus,
  Trash2,
  ListMusic,
  Radio,
  Wand2,
} from 'lucide-react';

export default function LightkeyMainView() {
  const [viewMode, setViewMode] = useState('design'); // 'design' | 'live'
  const [fixtures, setFixtures] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Motori di Controllo Palettes & Cue List
  const [paletteManager] = useState(() => new PaletteManager());
  const [cueEngine] = useState(() => new CueEngine());
  const [palettes, setPalettes] = useState(() => paletteManager.getPalettes());
  const [cues, setCues] = useState(() => cueEngine.cues);
  const [activeCueIndex, setActiveCueIndex] = useState(() => cueEngine.activeCueIndex);
  const [nextCueIndex, setNextCueIndex] = useState(() => cueEngine.nextCueIndex);
  const [fadeState, setFadeState] = useState({ isFading: false, progress: 0, isPaused: false });
  const [manualCrossfade, setManualCrossfade] = useState(0);
  const [isBlackout, setIsBlackout] = useState(false);

  // Effects Engine (BPM, waveform effects, motion generators)
  const [effectsEngine] = useState(() => new EffectsEngine(120.0));
  const [bpm, setBpm] = useState(() => effectsEngine.clock.bpm);
  const [effects, setEffects] = useState(() => [...effectsEngine.effects]);

  // Live Controller (Grand Master, Speed Master, Blind, Freeze, Trigger Grid, Group Faders)
  const [liveController] = useState(() => new LiveController());
  const [grandMaster, setGrandMaster] = useState(1.0);
  const [speedMaster, setSpeedMaster] = useState(1.0);
  const [isBlind, setIsBlind]         = useState(false);
  const [isFrozen, setIsFrozen]       = useState(false);

  // Pannello inferiore dockable (Design mode): 'cues' | 'palettes' | 'effects' | 'collapsed'
  const [bottomDrawer, setBottomDrawer] = useState('cues');

  const viewOptions = [
    { id: 'design', label: 'Design View', icon: Sparkles },
    { id: 'live', label: 'Live Show (Cues)', icon: Sliders },
  ];

  // Inizializza fari e profili da IPC (o setup predefinito per il palco)
  useEffect(() => {
    // Registra i motori di Lightkey nel Bridge OSC interno di ShowSuite
    showSuiteBridge.registerLightkey({
      liveController,
      cueEngine,
      paletteManager,
      effectsEngine,
    });
    if (window.showsuite?.patch) {
      window.showsuite.patch.getProfiles().then((profs) => {
        if (profs && profs.length > 0) setProfiles(profs);
      });

      window.showsuite.patch.getFixtures().then((initialFixtures) => {
        if (initialFixtures && initialFixtures.length > 0) {
          setFixtures(initialFixtures);
        } else {
          setupDefaultStage();
        }
      });
    } else {
      setupDefaultStage();
    }
  }, []);

  const setupDefaultStage = () => {
    // 4 Spot sul truss posteriore + 2 Par sul truss frontale
    const defaultFixtures = [
      {
        id: 'spot_1',
        name: 'Spot Post. 1',
        universe: 1,
        address: 1,
        category: 'moving_head',
        position: { x: 250, y: 120 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 1.0,
          shutter: 1,
          pan: 0.35,
          tilt: 0.65,
          zoom: 0.4,
          focus: 0.5,
          frost: 0,
          gobo: 0.28,
          goboRotate: 0.2,
          prism: 0,
          color: { r: 0.1, g: 0.6, b: 1.0 },
        },
      },
      {
        id: 'spot_2',
        name: 'Spot Post. 2',
        universe: 1,
        address: 17,
        category: 'moving_head',
        position: { x: 420, y: 120 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 1.0,
          shutter: 1,
          pan: 0.45,
          tilt: 0.7,
          zoom: 0.4,
          focus: 0.5,
          frost: 0,
          gobo: 0.28,
          goboRotate: 0.2,
          prism: 0,
          color: { r: 0.1, g: 0.6, b: 1.0 },
        },
      },
      {
        id: 'spot_3',
        name: 'Spot Post. 3',
        universe: 1,
        address: 33,
        category: 'moving_head',
        position: { x: 580, y: 120 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 1.0,
          shutter: 1,
          pan: 0.55,
          tilt: 0.7,
          zoom: 0.4,
          focus: 0.5,
          frost: 0,
          gobo: 0.28,
          goboRotate: -0.2,
          prism: 0,
          color: { r: 1.0, g: 0.2, b: 0.5 },
        },
      },
      {
        id: 'spot_4',
        name: 'Spot Post. 4',
        universe: 1,
        address: 49,
        category: 'moving_head',
        position: { x: 750, y: 120 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 1.0,
          shutter: 1,
          pan: 0.65,
          tilt: 0.65,
          zoom: 0.4,
          focus: 0.5,
          frost: 0,
          gobo: 0.28,
          goboRotate: -0.2,
          prism: 0,
          color: { r: 1.0, g: 0.2, b: 0.5 },
        },
      },
      {
        id: 'par_1',
        name: 'Wash Front. 1',
        universe: 1,
        address: 65,
        category: 'par',
        position: { x: 300, y: 480 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 0.8,
          shutter: 1,
          pan: 0.5,
          tilt: 0.4,
          zoom: 0.7,
          focus: 0.5,
          frost: 0.3,
          gobo: 0,
          goboRotate: 0,
          prism: 0,
          color: { r: 1.0, g: 0.8, b: 0.2 },
        },
      },
      {
        id: 'par_2',
        name: 'Wash Front. 2',
        universe: 1,
        address: 69,
        category: 'par',
        position: { x: 700, y: 480 },
        calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
        state: {
          intensity: 0.8,
          shutter: 1,
          pan: 0.5,
          tilt: 0.4,
          zoom: 0.7,
          focus: 0.5,
          frost: 0.3,
          gobo: 0,
          goboRotate: 0,
          prism: 0,
          color: { r: 1.0, g: 0.8, b: 0.2 },
        },
      },
    ];

    setFixtures(defaultFixtures);
    setSelectedIds(['spot_1']);
  };

  // Loop animazione fluida a 60 FPS: Effects → Cue dissolvenze → Group Faders → Grand Master → DMX
  const fixturesRef = useRef(fixtures);
  fixturesRef.current = fixtures;

  useEffect(() => {
    let animId;
    const tickLoop = (timestamp) => {
      const now = timestamp / 1000; // secondi

      // 1. Applica effetti waveform/motion (con SpeedMaster sul tempo)
      let currentFixtures = fixturesRef.current;
      if (effectsEngine.effects.length > 0) {
        currentFixtures = effectsEngine.applyEffects(currentFixtures, now * liveController.speedMaster);
      }

      // 2. Applica le dissolvenze Cue sopra gli effetti
      if (cueEngine.fade.isFading || cueEngine.isManualMode) {
        const res = cueEngine.tick(currentFixtures);
        currentFixtures = res.updatedFixtures;
        setFadeState({
          isFading: res.isFading,
          progress: res.progress,
          isPaused: cueEngine.fade.isPaused,
        });
      }

      // 3. Aggiorna lo stato React (valori pre-GM, per il display)
      if (
        effectsEngine.effects.some((e) => e.active) ||
        cueEngine.fade.isFading ||
        cueEngine.isManualMode
      ) {
        setFixtures([...currentFixtures]);
      }

      // 4. Applica Group Faders + Grand Master solo per l'output DMX (non modifica lo stato React)
      if (!liveController.isFrozen) {
        let dmxOutput = liveController.applyGroupFaders(currentFixtures);
        dmxOutput = liveController.applyGrandMaster(dmxOutput);

        // 5. Invia al backend DMX (solo se non in Blind mode)
        if (!liveController.isBlind && window.showsuite?.patch?.updateFixtureState) {
          dmxOutput.forEach((f) => {
            window.showsuite.patch.updateFixtureState(f.id, f.state);
          });
        }
      }

      animId = requestAnimationFrame(tickLoop);
    };

    animId = requestAnimationFrame(tickLoop);
    return () => cancelAnimationFrame(animId);
  }, [cueEngine, effectsEngine, liveController]);

  // Aggiornamento proprietà di stato di una fixture dall'Inspector
  const handleUpdateFixtureState = (fixtureId, statePatch) => {
    setFixtures((prev) =>
      prev.map((f) => (f.id === fixtureId ? { ...f, state: { ...f.state, ...statePatch } } : f))
    );

    if (window.showsuite?.patch?.updateFixtureState) {
      window.showsuite.patch.updateFixtureState(fixtureId, statePatch);
    }
  };

  // Aggiornamento calibrazione e inversione assi
  const handleUpdateFixtureCalibration = (fixtureId, calibPatch) => {
    setFixtures((prev) =>
      prev.map((f) => (f.id === fixtureId ? { ...f, calibration: { ...f.calibration, ...calibPatch } } : f))
    );
  };

  // Spostamento drag-and-drop
  const handleFixtureMove = (fixtureId, newX, newY) => {
    setFixtures((prev) =>
      prev.map((f) => (f.id === fixtureId ? { ...f, position: { ...f.position, x: newX, y: newY } } : f))
    );
  };

  // Aggiunta nuovo faro
  const handleAddFixture = (newConfig) => {
    const newFix = {
      id: `fix_${Date.now()}`,
      name: newConfig.name,
      universe: newConfig.universe,
      address: newConfig.address,
      category: 'moving_head',
      position: { x: newConfig.x, y: newConfig.y },
      calibration: { invertPan: false, invertTilt: false, swapPanTilt: false },
      state: { intensity: 1.0, shutter: 1, pan: 0.5, tilt: 0.5, zoom: 0.5, color: { r: 1, g: 1, b: 1 }, gobo: 0, prism: 0 },
    };

    setFixtures((prev) => [...prev, newFix]);
    setSelectedIds([newFix.id]);
  };

  // Eliminazione faro selezionato
  const handleDeleteSelected = () => {
    setFixtures((prev) => prev.filter((f) => !selectedIds.includes(f.id)));
    setSelectedIds([]);
  };

  // --- Handlers Cue List & Playback GO ---
  const handleGo = () => {
    if (cueEngine.go(fixtures)) {
      setActiveCueIndex(cueEngine.activeCueIndex);
      setNextCueIndex(cueEngine.nextCueIndex);
      setFadeState({
        isFading: true,
        progress: 0,
        isPaused: false,
      });
    }
  };

  const handleBack = () => {
    if (cueEngine.back(fixtures)) {
      setActiveCueIndex(cueEngine.activeCueIndex);
      setNextCueIndex(cueEngine.nextCueIndex);
      setFadeState({
        isFading: true,
        progress: 0,
        isPaused: false,
      });
    }
  };

  const handlePause = () => {
    cueEngine.pause();
    setFadeState((prev) => ({ ...prev, isPaused: cueEngine.fade.isPaused }));
  };

  const handleStop = () => {
    cueEngine.stop();
    setFadeState({ isFading: false, progress: 1.0, isPaused: false });
  };

  const handleManualCrossfade = (val) => {
    setManualCrossfade(val);
    cueEngine.setManualCrossfade(val);
  };

  const handleAddCue = (newCueConfig) => {
    const snapshots = CueEngine.takeSnapshot(fixtures);
    cueEngine.addCue({
      ...newCueConfig,
      fixtureSnapshots: snapshots,
    });
    setCues([...cueEngine.cues]);
  };

  const handleDeleteCue = (cueId) => {
    cueEngine.removeCue(cueId);
    setCues([...cueEngine.cues]);
    setActiveCueIndex(cueEngine.activeCueIndex);
    setNextCueIndex(cueEngine.nextCueIndex);
  };

  const handleSelectCue = (idx) => {
    cueEngine.nextCueIndex = idx;
    setNextCueIndex(idx);
  };

  const handleToggleBlackout = () => {
    setIsBlackout((prev) => {
      const next = !prev;
      if (next) {
        // Applica blackout immediato a tutte le fixture
        setFixtures((all) => all.map((f) => ({ ...f, state: { ...f.state, intensity: 0 } })));
      }
      return next;
    });

    if (window.showsuite?.dmx?.toggleBlackout) {
      window.showsuite.dmx.toggleBlackout();
    }
  };

  // --- Handlers Palettes ---
  const handleApplyPalette = (paletteId) => {
    const targets = selectedIds.length > 0 ? selectedIds : fixtures.map((f) => f.id);

    setFixtures((prev) =>
      prev.map((f) => {
        if (targets.includes(f.id)) {
          const newState = paletteManager.applyToState(paletteId, f.state);
          if (window.showsuite?.patch?.updateFixtureState) {
            window.showsuite.patch.updateFixtureState(f.id, newState);
          }
          return { ...f, state: newState };
        }
        return f;
      })
    );
  };

  const handleSavePalette = (name, type) => {
    const firstSelected = fixtures.find((f) => selectedIds.includes(f.id)) || fixtures[0];
    if (!firstSelected) return;

    const palData = {};
    if (type === PaletteType.COLOR) {
      palData.color = { ...(firstSelected.state?.color || { r: 1, g: 1, b: 1 }) };
    } else if (type === PaletteType.POSITION) {
      palData.pan = firstSelected.state?.pan || 0.5;
      palData.tilt = firstSelected.state?.tilt || 0.5;
    } else if (type === PaletteType.BEAM) {
      palData.zoom = firstSelected.state?.zoom || 0.5;
      palData.focus = firstSelected.state?.focus || 0.5;
      palData.frost = firstSelected.state?.frost || 0;
      palData.gobo = firstSelected.state?.gobo || 0;
      palData.prism = firstSelected.state?.prism || 0;
    } else if (type === PaletteType.PRESET) {
      Object.assign(palData, firstSelected.state);
    }

    paletteManager.addPalette({
      name,
      type,
      data: palData,
      isCustom: true,
      icon: type === PaletteType.COLOR ? 'Palette' : type === PaletteType.POSITION ? 'Target' : 'Sparkles',
    });

    setPalettes([...paletteManager.getPalettes()]);
  };

  const handleDeletePalette = (id) => {
    paletteManager.removePalette(id);
    setPalettes([...paletteManager.getPalettes()]);
  };

  // --- Handlers Effects Engine ---
  const handleBpmChange = (newBpm) => {
    effectsEngine.clock.setBpm(newBpm);
    setBpm(newBpm);
  };

  const handleTapTempo = () => {
    const newBpm = effectsEngine.clock.tap();
    if (newBpm) setBpm(Math.round(newBpm * 10) / 10);
  };

  const handleToggleEffect = (id) => {
    const effect = effectsEngine.effects.find((e) => e.id === id);
    if (effect) {
      effect.active = !effect.active;
      setEffects([...effectsEngine.effects]);
    }
  };

  const handleAddEffect = (template) => {
    effectsEngine.addEffect(template || {});
    setEffects([...effectsEngine.effects]);
  };

  const handleRemoveEffect = (id) => {
    effectsEngine.removeEffect(id);
    setEffects([...effectsEngine.effects]);
  };

  const handleUpdateEffect = (id, patch) => {
    effectsEngine.updateEffect(id, patch);
    setEffects([...effectsEngine.effects]);
  };

  // --- Handlers Live Controller (Grand Master, Speed Master, Blind, Freeze) ---
  const handleGrandMasterChange = (val) => {
    liveController.setGrandMaster(val);
    setGrandMaster(val);
  };

  const handleSpeedMasterChange = (val) => {
    liveController.setSpeedMaster(val);
    setSpeedMaster(val);
  };

  const handleToggleBlind = () => {
    const next = liveController.toggleBlind();
    setIsBlind(next);
  };

  const handleToggleFreeze = () => {
    const next = liveController.toggleFreeze();
    setIsFrozen(next);
  };

  return (
    <div className="flex-1 flex flex-col bg-[#141416] text-mac-text overflow-hidden select-none">

      {/* ══ Lightkey Top Toolbar ═══════════════════════════════════════════════ */}
      <div className="h-10 bg-[#1c1c20] border-b border-[#2d2d38] flex items-center justify-between px-3 shrink-0">

        {/* Sinistra: Selettore Vista + Aggiungi/Elimina (solo Design) */}
        <div className="flex items-center space-x-3">
          <MacSegmentedControl
            options={viewOptions}
            value={viewMode}
            onChange={(mode) => setViewMode(mode)}
            size="sm"
          />
          <div className="h-4 w-[1px] bg-[#33333d]" />
          {viewMode === 'design' && (
            <div className="flex items-center space-x-1">
              <MacButton
                variant="toolbar"
                size="sm"
                icon={Plus}
                onClick={() => setIsAddModalOpen(true)}
                title="Aggiungi Faro"
              >
                Aggiungi
              </MacButton>
              {selectedIds.length > 0 && (
                <MacButton
                  variant="destructive"
                  size="sm"
                  icon={Trash2}
                  onClick={handleDeleteSelected}
                >
                  Elimina ({selectedIds.length})
                </MacButton>
              )}
            </div>
          )}
        </div>

        {/* Destra: Drawer tab (solo Design) + BPM + Status */}
        <div className="flex items-center space-x-2">
          {viewMode === 'design' && (
            <>
              <div className="flex bg-black/40 p-0.5 rounded border border-zinc-800 text-[11px]">
                {[
                  { id: 'cues',     icon: ListMusic, label: 'Cue List' },
                  { id: 'palettes', icon: Palette,   label: 'Palette'  },
                  { id: 'effects',  icon: Wand2,     label: 'Effetti'  },
                ].map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => setBottomDrawer(bottomDrawer === id ? 'collapsed' : id)}
                    className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                      bottomDrawer === id
                        ? 'bg-mac-accent text-white font-semibold'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    <Icon size={12} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
              <div className="h-4 w-[1px] bg-[#33333d]" />
            </>
          )}

          {/* BPM Master */}
          <div className="flex items-center space-x-2 bg-black/40 px-2.5 py-1 rounded border border-zinc-800 text-xs">
            <span className="text-[10px] text-zinc-400 uppercase font-mono">BPM:</span>
            <span className="font-mono font-bold text-mac-accent">{bpm.toFixed(1)}</span>
            <MacButton size="sm" variant="default" className="text-[10px] h-5 px-1.5 font-bold" onClick={handleTapTempo}>
              TAP
            </MacButton>
          </div>

          {/* DMX Status */}
          <div className="flex items-center space-x-1.5 text-[11px]">
            <span
              className={`w-2 h-2 rounded-full ${
                isBlind ? 'bg-amber-400' : isFrozen ? 'bg-sky-400' : 'bg-emerald-500 shadow-sm shadow-emerald-500/50'
              }`}
            />
            <span className={isBlind ? 'text-amber-400' : isFrozen ? 'text-sky-400' : 'text-zinc-400'}>
              {isBlind ? 'BLIND' : isFrozen ? 'FROZEN' : 'DMX 40Hz'}
            </span>
          </div>
        </div>
      </div>

      {/* ══ Contenuto: Design View o Live View ═══════════════════════════════ */}
      {viewMode === 'design' ? (
        <>
          {/* Stage Canvas 2D + Inspector HUD */}
          <div className="flex-1 flex overflow-hidden relative">
            <StageCanvas2D
              fixtures={fixtures}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              onFixtureMove={handleFixtureMove}
              onAddFixture={() => setIsAddModalOpen(true)}
            />
            <div className="w-80 bg-[#19191d] border-l border-[#2d2d38] flex flex-col z-10 shadow-2xl overflow-hidden">
              <FixturePropertiesHUD
                fixtures={fixtures}
                selectedIds={selectedIds}
                onUpdateFixtureState={handleUpdateFixtureState}
                onUpdateFixtureCalibration={handleUpdateFixtureCalibration}
              />
            </div>
          </div>

          {/* Cassetto Inferiore: Cue List | Palettes | Effetti */}
          {bottomDrawer !== 'collapsed' && (
            <div className="h-52 border-t border-[#2d2d38] bg-[#161619] shadow-2xl flex flex-col shrink-0">
              {bottomDrawer === 'cues' && (
                <CueListPanel
                  cues={cues}
                  activeCueIndex={activeCueIndex}
                  nextCueIndex={nextCueIndex}
                  fadeState={fadeState}
                  manualCrossfade={manualCrossfade}
                  onGo={handleGo}
                  onBack={handleBack}
                  onPause={handlePause}
                  onStop={handleStop}
                  onManualCrossfadeChange={handleManualCrossfade}
                  onAddCue={handleAddCue}
                  onDeleteCue={handleDeleteCue}
                  onSelectCue={handleSelectCue}
                  onToggleBlackout={handleToggleBlackout}
                  isBlackout={isBlackout}
                />
              )}
              {bottomDrawer === 'palettes' && (
                <PalettesPanel
                  palettes={palettes}
                  selectedIds={selectedIds}
                  onApplyPalette={handleApplyPalette}
                  onSavePalette={handleSavePalette}
                  onDeletePalette={handleDeletePalette}
                />
              )}
              {bottomDrawer === 'effects' && (
                <EffectsPanel
                  effects={effects}
                  bpm={bpm}
                  onBpmChange={handleBpmChange}
                  onTapTempo={handleTapTempo}
                  onToggleEffect={handleToggleEffect}
                  onAddEffect={handleAddEffect}
                  onRemoveEffect={handleRemoveEffect}
                  onUpdateEffect={handleUpdateEffect}
                />
              )}
            </div>
          )}
        </>
      ) : (
        /* ── LIVE VIEW (occupa tutto lo spazio rimasto sotto la toolbar) ── */
        <LiveView
          cues={cues}
          activeCueIndex={activeCueIndex}
          nextCueIndex={nextCueIndex}
          fadeState={fadeState}
          manualCrossfade={manualCrossfade}
          isBlackout={isBlackout}
          bpm={bpm}
          liveController={liveController}
          grandMaster={grandMaster}
          speedMaster={speedMaster}
          isBlind={isBlind}
          isFrozen={isFrozen}
          onGo={handleGo}
          onBack={handleBack}
          onPause={handlePause}
          onStop={handleStop}
          onManualCrossfadeChange={handleManualCrossfade}
          onAddCue={handleAddCue}
          onDeleteCue={handleDeleteCue}
          onSelectCue={handleSelectCue}
          onToggleBlackout={handleToggleBlackout}
          onTapTempo={handleTapTempo}
          onApplyPalette={handleApplyPalette}
          onGrandMasterChange={handleGrandMasterChange}
          onSpeedMasterChange={handleSpeedMasterChange}
          onToggleBlind={handleToggleBlind}
          onToggleFreeze={handleToggleFreeze}
        />
      )}

      {/* Modale Aggiungi Proiettore */}
      <AddFixtureModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        profiles={profiles}
        onAdd={handleAddFixture}
      />
    </div>
  );
}
