import React, { useState } from 'react';
import { FanEngine, FanMode, FanAttribute } from '../core/control/index.js';
import { GitCommit, AlignCenter, RefreshCw, Zap, SlidersHorizontal } from 'lucide-react';
import MacButton from '../shared/components/MacButton';

export default function FanningHUD({
  fixtures = [],
  selectedIds = [],
  onApplyFan,
  onResetFan,
}) {
  const [attribute, setAttribute] = useState(FanAttribute.PAN);
  const [mode, setMode] = useState(FanMode.LINEAR);
  const [amount, setAmount] = useState(0.4); // 40%

  const selectedCount = selectedIds.length;
  if (selectedCount < 2) {
    return (
      <div className="p-3 bg-black/20 rounded-lg border border-[#2d2d38] text-[11px] text-zinc-500 text-center">
        Seleziona almeno 2 proiettori per abilitare il fanning spaziale.
      </div>
    );
  }

  // Calcola anteprima della distribuzione numerica per i proiettori selezionati
  const previewValues = FanEngine.calculateFan(
    selectedCount,
    attribute === FanAttribute.HUE ? 180 : 0.5,
    amount,
    mode,
    attribute
  );

  const handleSliderChange = (newAmount) => {
    setAmount(newAmount);
    onApplyFan?.(attribute, mode, newAmount);
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    onApplyFan?.(attribute, newMode, amount);
  };

  const handleAttributeChange = (newAttr) => {
    setAttribute(newAttr);
    onApplyFan?.(newAttr, mode, amount);
  };

  return (
    <div className="space-y-3 select-none text-xs">
      {/* 1. Attributo Target */}
      <div className="space-y-1">
        <span className="text-[10px] text-zinc-400 font-semibold block">Attributo Fanning</span>
        <div className="grid grid-cols-4 gap-1 text-[10px]">
          {[
            { id: FanAttribute.PAN, label: 'Pan' },
            { id: FanAttribute.TILT, label: 'Tilt' },
            { id: FanAttribute.HUE, label: 'Colore' },
            { id: FanAttribute.INTENSITY, label: 'Dimmer' },
          ].map((attr) => (
            <button
              key={attr.id}
              onClick={() => handleAttributeChange(attr.id)}
              className={`py-1 rounded border transition-colors ${
                attribute === attr.id
                  ? 'bg-mac-accent text-white font-semibold border-mac-accent shadow-sm'
                  : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
              }`}
            >
              {attr.label}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Modalità di Distribuzione */}
      <div className="space-y-1">
        <span className="text-[10px] text-zinc-400 font-semibold block">Curva di Distribuzione</span>
        <div className="grid grid-cols-3 gap-1 text-[10px]">
          {[
            { id: FanMode.LINEAR, label: 'Lineare' },
            { id: FanMode.SYMMETRIC, label: 'Simmetrico' },
            { id: FanMode.SPREAD, label: 'Spread' },
          ].map((m) => (
            <button
              key={m.id}
              onClick={() => handleModeChange(m.id)}
              className={`py-1 rounded border transition-colors ${
                mode === m.id
                  ? 'bg-mac-accent/30 text-mac-accent font-semibold border-mac-accent'
                  : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Slider Ampiezza Fanning */}
      <div className="space-y-2 bg-black/30 p-2.5 rounded-lg border border-[#2d2d38]">
        <div className="flex justify-between text-[10px]">
          <span className="text-zinc-300 font-medium flex items-center gap-1">
            <SlidersHorizontal size={11} className="text-mac-accent" /> Ampiezza (Spread)
          </span>
          <span className="font-mono text-white font-bold">{Math.round(amount * 100)}%</span>
        </div>

        <input
          type="range"
          min="-100"
          max="100"
          value={Math.round(amount * 100)}
          onChange={(e) => handleSliderChange(parseInt(e.target.value) / 100)}
          className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
        />

        {/* 4. Grafico Visivo Mini-Curva dei Fari */}
        <div className="pt-1">
          <div className="h-10 w-full bg-[#111114] rounded border border-zinc-800/80 flex items-end justify-between px-2 py-1 gap-1">
            {previewValues.map((val, idx) => {
              // Altezza barra proporzionale al valore (0..1 o 0..360)
              const heightPct = attribute === FanAttribute.HUE ? (val / 360) * 100 : val * 100;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end">
                  <div
                    className="w-full rounded-t transition-all duration-75 bg-mac-accent/80 hover:bg-mac-accent"
                    style={{ height: `${Math.max(10, heightPct)}%` }}
                    title={`Faro ${idx + 1}: ${Math.round(heightPct)}%`}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[8px] text-zinc-500 font-mono pt-0.5">
            <span>Faro 1</span>
            <span>Centro</span>
            <span>Faro {selectedCount}</span>
          </div>
        </div>
      </div>

      {/* Tasto Reset Fanning */}
      <div className="flex gap-2">
        <button
          onClick={onResetFan}
          className="w-full py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white font-medium text-[11px] border border-zinc-700 flex items-center justify-center gap-1.5 transition-colors"
        >
          <RefreshCw size={11} /> Reset Allineamento (0%)
        </button>
      </div>
    </div>
  );
}
