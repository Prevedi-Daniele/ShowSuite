import React, { useState } from 'react';
import {
  Sun,
  Palette,
  Eye,
  Disc,
  Zap,
  Sliders,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronRight,
  Maximize2,
  Wind,
} from 'lucide-react';
import ColorPickerHUD from './ColorPickerHUD';
import PanTiltPad from './PanTiltPad';
import GoboWheelHUD from './GoboWheelHUD';
import FanningHUD from './FanningHUD';
import { FanEngine } from '../core/control/index.js';

export default function FixturePropertiesHUD({
  fixtures = [],
  selectedIds = [],
  onUpdateFixtureState,
  onUpdateFixtureCalibration,
}) {
  // Tab selezionata nell'HUD: 'all' (a sezioni) o singola tab
  const [activeTab, setActiveTab] = useState('intensity'); // 'intensity' | 'color' | 'position' | 'beam' | 'fan'

  // Trova i fari attualmente selezionati
  const selectedFixtures = fixtures.filter((f) => selectedIds.includes(f.id));
  const primaryFixture = selectedFixtures[0] || null;
  const count = selectedFixtures.length;

  if (count === 0 || !primaryFixture) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-zinc-500">
        <div className="w-12 h-12 rounded-full bg-zinc-800/40 border border-zinc-700/50 flex items-center justify-center mb-3">
          <Eye size={22} className="text-zinc-600" />
        </div>
        <p className="text-xs font-medium text-zinc-400">Nessun proiettore selezionato</p>
        <p className="text-[11px] text-zinc-600 mt-1">
          Clicca su un faro o trascina un riquadro sul palco per visualizzare e regolare le sue proprietà DMX.
        </p>
      </div>
    );
  }

  const state = primaryFixture.state || {};
  const calibration = primaryFixture.calibration || {};

  // Propaga modifiche a tutti i fari selezionati
  const handleStateChange = (patch) => {
    selectedIds.forEach((id) => {
      onUpdateFixtureState?.(id, patch);
    });
  };

  // Gestione applicazione fanning
  const handleApplyFan = (attribute, mode, amount) => {
    if (selectedFixtures.length < 2) return;

    let baseVal = 0.5;
    if (attribute === 'pan') baseVal = state.pan !== undefined ? state.pan : 0.5;
    else if (attribute === 'tilt') baseVal = state.tilt !== undefined ? state.tilt : 0.5;
    else if (attribute === 'intensity') baseVal = state.intensity !== undefined ? state.intensity : 1;
    else if (attribute === 'hue') baseVal = 180;

    const values = FanEngine.calculateFan(selectedFixtures.length, baseVal, amount, mode, attribute);

    selectedFixtures.forEach((fix, idx) => {
      const val = values[idx];
      const patch = {};

      if (attribute === 'pan') patch.pan = val;
      else if (attribute === 'tilt') patch.tilt = val;
      else if (attribute === 'intensity') patch.intensity = val;
      else if (attribute === 'hue') {
        const rgb = FanEngine.hueToRgb(val);
        patch.color = { ...(fix.state?.color || {}), r: rgb.r, g: rgb.g, b: rgb.b };
      }

      onUpdateFixtureState?.(fix.id, patch);
    });
  };

  // Reset Fanning (riporta tutti i fari allo stesso valore del primo)
  const handleResetFan = () => {
    selectedIds.forEach((id) => {
      onUpdateFixtureState?.(id, {
        pan: state.pan || 0.5,
        tilt: state.tilt || 0.5,
        intensity: state.intensity !== undefined ? state.intensity : 1,
        color: state.color || { r: 1, g: 1, b: 1 },
      });
    });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden text-zinc-300">
      {/* Header Info Fixture */}
      <div className="p-3 bg-black/40 border-b border-[#2d2d38] space-y-1">
        <div className="flex items-center justify-between">
          <span className="font-bold text-white text-sm truncate">
            {count > 1 ? `${count} Proiettori Selezionati` : primaryFixture.name}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-mac-accent/20 text-mac-accent font-mono font-medium">
            {primaryFixture.category || 'Moving Head'}
          </span>
        </div>
        <div className="text-[11px] text-zinc-400 font-mono">
          {count > 1
            ? `ID: ${selectedFixtures.map((f) => f.name || f.id).slice(0, 3).join(', ')}${count > 3 ? '...' : ''}`
            : `Universo ${primaryFixture.universe || 1} • Canale DMX ${primaryFixture.address || 1}`}
        </div>
      </div>

      {/* Tabs di Navigazione Proprietà (Icone Stile Lightkey) */}
      <div className="flex bg-[#19191d] border-b border-[#2d2d38] p-1 gap-1">
        <button
          onClick={() => setActiveTab('intensity')}
          className={`flex-1 py-1.5 flex flex-col items-center justify-center rounded text-[10px] transition-colors ${
            activeTab === 'intensity' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
          title="Dimmer & Strobo"
        >
          <Sun size={13} className="mb-0.5" />
          <span>Dimmer</span>
        </button>

        <button
          onClick={() => setActiveTab('color')}
          className={`flex-1 py-1.5 flex flex-col items-center justify-center rounded text-[10px] transition-colors ${
            activeTab === 'color' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
          title="Colore HSB & RGB"
        >
          <Palette size={13} className="mb-0.5" />
          <span>Colore</span>
        </button>

        <button
          onClick={() => setActiveTab('position')}
          className={`flex-1 py-1.5 flex flex-col items-center justify-center rounded text-[10px] transition-colors ${
            activeTab === 'position' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
          title="Posizione Pan & Tilt"
        >
          <Eye size={13} className="mb-0.5" />
          <span>Pan/Tilt</span>
        </button>

        <button
          onClick={() => setActiveTab('beam')}
          className={`flex-1 py-1.5 flex flex-col items-center justify-center rounded text-[10px] transition-colors ${
            activeTab === 'beam' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
          title="Gobo & Fascio Ottico"
        >
          <Disc size={13} className="mb-0.5" />
          <span>Gobo</span>
        </button>

        {count > 1 && (
          <button
            onClick={() => setActiveTab('fan')}
            className={`flex-1 py-1.5 flex flex-col items-center justify-center rounded text-[10px] transition-colors ${
              activeTab === 'fan' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
            }`}
            title="Fanning Spaziale"
          >
            <Layers size={13} className="mb-0.5" />
            <span>Fanning</span>
          </button>
        )}
      </div>

      {/* Contenuto Tab Attiva */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* TAB 1: INTENSITY & SHUTTER */}
        {activeTab === 'intensity' && (
          <div className="space-y-4">
            {/* Dimmer Master */}
            <div className="space-y-2 bg-black/30 p-3 rounded-lg border border-[#2d2d38]">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                  <Sun size={14} className="text-yellow-400" /> Intensità Dimmer
                </span>
                <span className="font-mono text-white font-bold text-sm">
                  {Math.round((state.intensity !== undefined ? state.intensity : 1) * 100)}%
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="100"
                value={Math.round((state.intensity !== undefined ? state.intensity : 1) * 100)}
                onChange={(e) => handleStateChange({ intensity: parseInt(e.target.value) / 100 })}
                className="w-full h-2 bg-zinc-800 rounded appearance-none cursor-pointer accent-yellow-400"
              />

              {/* Tasti Rapidi Percentuali Dimmer */}
              <div className="flex gap-1 pt-1">
                {[0, 25, 50, 75, 100].map((pct) => (
                  <button
                    key={pct}
                    onClick={() => handleStateChange({ intensity: pct / 100 })}
                    className="flex-1 py-1 bg-black/40 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded border border-zinc-800 text-[10px] font-mono transition-colors"
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>

            {/* Shutter / Strobe Mode */}
            <div className="space-y-2 bg-black/30 p-3 rounded-lg border border-[#2d2d38]">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                  <Zap size={14} className="text-amber-400" /> Shutter & Strobo
                </span>
                <span className="font-mono text-zinc-400 text-[11px]">
                  {state.shutter === 0 ? 'Chiuso' : state.shutter > 1 ? `Strobo ${state.shutter} Hz` : 'Aperto'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-1.5 text-[10px]">
                <button
                  onClick={() => handleStateChange({ shutter: 0 })}
                  className={`py-1.5 rounded border ${
                    state.shutter === 0
                      ? 'bg-red-500/30 border-red-500 text-red-200 font-bold'
                      : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
                  }`}
                >
                  Chiuso (Black)
                </button>
                <button
                  onClick={() => handleStateChange({ shutter: 1 })}
                  className={`py-1.5 rounded border ${
                    state.shutter === 1
                      ? 'bg-emerald-500/30 border-emerald-500 text-emerald-200 font-bold'
                      : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
                  }`}
                >
                  Aperto (Open)
                </button>
                <button
                  onClick={() => handleStateChange({ shutter: state.shutter > 1 ? 1 : 12 })}
                  className={`py-1.5 rounded border ${
                    state.shutter > 1
                      ? 'bg-amber-500/40 border-amber-500 text-amber-200 font-bold animate-pulse'
                      : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
                  }`}
                >
                  Strobo Flash
                </button>
              </div>

              {state.shutter > 1 && (
                <div className="pt-2 space-y-1">
                  <div className="flex justify-between text-[10px] text-zinc-400">
                    <span>Frequenza Strobo (Hz)</span>
                    <span className="font-mono text-white">{state.shutter} Hz</span>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="25"
                    value={state.shutter}
                    onChange={(e) => handleStateChange({ shutter: parseInt(e.target.value) })}
                    className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-amber-400"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: COLOR PICKER (HSB / RGB / KELVIN) */}
        {activeTab === 'color' && (
          <ColorPickerHUD
            color={state.color || { r: 1, g: 1, b: 1 }}
            onChange={(newCol) => handleStateChange({ color: newCol })}
          />
        )}

        {/* TAB 3: POSITION (PAN / TILT) */}
        {activeTab === 'position' && (
          <PanTiltPad
            pan={state.pan !== undefined ? state.pan : 0.5}
            tilt={state.tilt !== undefined ? state.tilt : 0.5}
            calibration={calibration}
            onChange={(newPos) => handleStateChange(newPos)}
            onCalibrationChange={(newCal) => {
              selectedIds.forEach((id) => onUpdateFixtureCalibration?.(id, newCal));
            }}
          />
        )}

        {/* TAB 4: GOBO & OPTICS */}
        {activeTab === 'beam' && (
          <div className="space-y-4">
            <GoboWheelHUD
              gobo={state.gobo || 0}
              goboRotate={state.goboRotate || 0}
              prism={state.prism || 0}
              onChange={(patch) => handleStateChange(patch)}
            />

            {/* Ottiche: Zoom & Focus & Frost */}
            <div className="space-y-3 bg-black/20 p-2.5 rounded-lg border border-[#2d2d38]">
              <span className="font-semibold text-zinc-300 text-[11px] block">Ottica Fascio</span>

              {/* Zoom */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-400">
                  <span>Zoom Fascio</span>
                  <span className="font-mono text-white">{Math.round((state.zoom || 0.5) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((state.zoom || 0.5) * 100)}
                  onChange={(e) => handleStateChange({ zoom: parseInt(e.target.value) / 100 })}
                  className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                />
              </div>

              {/* Focus */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-400">
                  <span>Messa a Fuoco (Focus)</span>
                  <span className="font-mono text-white">{Math.round((state.focus || 0.5) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((state.focus || 0.5) * 100)}
                  onChange={(e) => handleStateChange({ focus: parseInt(e.target.value) / 100 })}
                  className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                />
              </div>

              {/* Frost */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-400">
                  <span>Filtro Frost (Diffusore)</span>
                  <span className="font-mono text-white">{Math.round((state.frost || 0) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((state.frost || 0) * 100)}
                  onChange={(e) => handleStateChange({ frost: parseInt(e.target.value) / 100 })}
                  className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: FANNING (SPATIAL MULTI-SELECTION) */}
        {activeTab === 'fan' && (
          <FanningHUD
            fixtures={selectedFixtures}
            selectedIds={selectedIds}
            onApplyFan={handleApplyFan}
            onResetFan={handleResetFan}
          />
        )}
      </div>
    </div>
  );
}
