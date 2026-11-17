/**
 * CueCartGrid.jsx — Cue Cart a griglia in stile QLab 5
 * 
 * Permette:
 * - Griglia di pad/pulsanti colorati per trigger live istantaneo di clip audio, jingle e scene
 * - Indicatori grafici di playback in corso con anello/fill circolare di progresso
 * - Configurazione rapida di nome, colore, hotkey, tipo e durata
 * - Tasti di trigger click-to-fire o click-to-stop
 */

import React, { useState } from 'react';
import { CueState } from '../core/qlab/index.js';
import {
  Volume2,
  Play,
  Square,
  Settings,
  Plus,
  Trash2,
  Sparkles,
} from 'lucide-react';

const CART_COLORS = [
  { id: 'zinc', bg: '#27272a', active: '#3f3f46', border: '#52525b', text: '#ffffff' },
  { id: 'red', bg: '#7f1d1d', active: '#b91c1c', border: '#ef4444', text: '#fca5a5' },
  { id: 'orange', bg: '#7c2d12', active: '#c2410c', border: '#f97316', text: '#fdba74' },
  { id: 'green', bg: '#14532d', active: '#15803d', border: '#22c55e', text: '#86efac' },
  { id: 'cyan', bg: '#164e63', active: '#0e7490', border: '#06b6d4', text: '#67e8f9' },
  { id: 'blue', bg: '#1e3a8a', active: '#1d4ed8', border: '#3b82f6', text: '#93c5fd' },
  { id: 'purple', bg: '#581c87', active: '#7e22ce', border: '#a855f7', text: '#d8b4fe' },
];

export default function CueCartGrid({
  cues = [],
  onTriggerCue,
  onStopCue,
  onAddCartCue,
  onUpdateCartCue,
  onDeleteCartCue,
}) {
  const [editingCellId, setEditingCellId] = useState(null);

  // Default: griglia 4x4 con celle
  const getCellColor = (colorId, isRunning) => {
    const config = CART_COLORS.find((c) => c.id === colorId) || CART_COLORS[0];
    return isRunning ? config.active : config.bg;
  };

  const getBorderColor = (colorId, isRunning) => {
    const config = CART_COLORS.find((c) => c.id === colorId) || CART_COLORS[0];
    return isRunning ? config.border : '#2d2d38';
  };

  return (
    <div className="flex-1 flex flex-col bg-[#121214] p-4 overflow-auto select-none">
      {/* Header Cart */}
      <div className="flex items-center justify-between pb-3 border-b border-[#222228] mb-4">
        <div className="flex items-center space-x-2">
          <Sparkles size={16} className="text-mac-accent" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">QLab 5 Cue Cart</h2>
          <span className="text-xs text-zinc-500 font-mono">({cues.length} Pulsanti configurati)</span>
        </div>

        <button
          type="button"
          onClick={onAddCartCue}
          className="flex items-center space-x-1.5 px-3 py-1 bg-mac-accent hover:bg-blue-600 text-white rounded text-xs font-semibold shadow transition-colors"
        >
          <Plus size={13} />
          <span>Aggiungi Cart Cell</span>
        </button>
      </div>

      {/* Griglia Pad */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 flex-1">
        {cues.map((cell, idx) => {
          const isRunning = cell.state === CueState.RUNNING;
          const progress = cell.getActionProgress ? cell.getActionProgress() : 0;
          const hotkey = idx < 9 ? String(idx + 1) : null;

          return (
            <div
              key={cell.id}
              onClick={() => {
                if (isRunning) onStopCue(cell.id);
                else onTriggerCue(cell.id);
              }}
              style={{
                backgroundColor: getCellColor(cell.color, isRunning),
                borderColor: getBorderColor(cell.color, isRunning),
              }}
              className={`h-28 rounded-xl border flex flex-col justify-between p-3 cursor-pointer transition-all duration-75 relative overflow-hidden group shadow-lg active:scale-95 ${
                isRunning ? 'ring-2 ring-emerald-400/80 shadow-emerald-950/50' : 'hover:border-zinc-500'
              }`}
            >
              {/* Barra di Progresso di Sfondo per celle attive */}
              {isRunning && (
                <div
                  className="absolute inset-y-0 left-0 bg-white/15 pointer-events-none transition-all duration-75"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              )}

              {/* Riga superiore cella: Hotkey & Icona */}
              <div className="flex items-center justify-between relative z-10">
                <div className="flex items-center space-x-1.5">
                  <Volume2 size={13} className={isRunning ? 'text-white' : 'text-zinc-400'} />
                  {hotkey && (
                    <span className="px-1.5 py-0.2 bg-black/40 rounded text-[9px] font-mono text-zinc-300 font-bold border border-white/10">
                      [{hotkey}]
                    </span>
                  )}
                </div>

                {/* Pulsante configurazione cella */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingCellId(cell.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-black/40 rounded text-zinc-300 hover:text-white"
                  title="Configura Cell"
                >
                  <Settings size={11} />
                </button>
              </div>

              {/* Centro: Nome e Note */}
              <div className="relative z-10">
                <div className="text-xs font-bold text-white truncate drop-shadow">
                  {cell.name || `Cart ${idx + 1}`}
                </div>
                <div className="text-[10px] text-zinc-400 truncate font-mono">
                  {cell.targetId || `${cell.duration || 0}s`}
                </div>
              </div>

              {/* Fondo: Stato e Azione Play/Stop */}
              <div className="flex items-center justify-between text-[10px] relative z-10 pt-1 border-t border-white/10">
                <span className={`font-mono ${isRunning ? 'text-emerald-300 font-bold' : 'text-zinc-400'}`}>
                  {isRunning ? `${Math.round(progress * 100)}%` : 'Pronto'}
                </span>

                <div className="flex items-center space-x-1">
                  {isRunning ? (
                    <Square size={11} className="text-red-400 fill-red-400" />
                  ) : (
                    <Play size={11} className="text-zinc-400 fill-zinc-400" />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modale Rapida di Configurazione Cart Cell */}
      {editingCellId && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
          onClick={() => setEditingCellId(null)}
        >
          {(() => {
            const cell = cues.find((c) => c.id === editingCellId);
            if (!cell) return null;

            return (
              <div
                className="bg-[#1c1c20] border border-zinc-700 rounded-xl p-5 w-80 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <h3 className="text-sm font-semibold text-white mb-3">Configura Cart Button</h3>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-zinc-400 block mb-1">Nome Pulsante</label>
                    <input
                      type="text"
                      value={cell.name}
                      onChange={(e) => onUpdateCartCue(cell.id, { name: e.target.value })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-white focus:outline-none focus:border-mac-accent"
                    />
                  </div>

                  <div>
                    <label className="text-zinc-400 block mb-1">Target / Audio File</label>
                    <input
                      type="text"
                      value={cell.targetId || ''}
                      onChange={(e) => onUpdateCartCue(cell.id, { targetId: e.target.value })}
                      placeholder="es. jingle_sigla.mp3"
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-white font-mono focus:outline-none focus:border-mac-accent"
                    />
                  </div>

                  <div>
                    <label className="text-zinc-400 block mb-1">Durata (sec)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={cell.duration}
                      onChange={(e) => onUpdateCartCue(cell.id, { duration: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-white font-mono focus:outline-none focus:border-mac-accent"
                    />
                  </div>

                  <div>
                    <label className="text-zinc-400 block mb-1">Colore Pad</label>
                    <div className="flex space-x-2 pt-1">
                      {CART_COLORS.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => onUpdateCartCue(cell.id, { color: c.id })}
                          style={{ backgroundColor: c.active }}
                          className={`w-6 h-6 rounded-full border border-white/20 transition-transform ${
                            cell.color === c.id ? 'scale-125 ring-2 ring-white' : 'opacity-80'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center mt-5 pt-3 border-t border-zinc-800">
                  <button
                    type="button"
                    onClick={() => {
                      onDeleteCartCue(cell.id);
                      setEditingCellId(null);
                    }}
                    className="text-red-400 hover:text-red-300 text-xs flex items-center space-x-1"
                  >
                    <Trash2 size={12} />
                    <span>Elimina</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setEditingCellId(null)}
                    className="px-4 py-1.5 bg-mac-accent hover:bg-blue-600 text-white rounded font-semibold text-xs transition-colors"
                  >
                    Chiudi
                  </button>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
