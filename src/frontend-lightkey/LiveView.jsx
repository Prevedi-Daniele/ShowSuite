/**
 * LiveView.jsx — Vista Live Show di Lightkey (STEP 3.2)
 *
 * Layout:
 *   ┌─────────────────────────────────────────────────────┐
 *   │  Override Strip: GM · SPD · BLIND · FREEZE · BLACKOUT│
 *   ├───────────────────────────────────┬─────────────────┤
 *   │  Trigger Grid (6×8)               │  Fader Gruppo   │
 *   │  [cell][cell]…                    │  [||][||][||]   │
 *   ├───────────────────────────────────┴─────────────────┤
 *   │  Cue List integrata (h-52)                          │
 *   └─────────────────────────────────────────────────────┘
 */

import React, { useState, useCallback, useEffect } from 'react';
import { CellType, TriggerMode } from '../core/control/LiveController.js';
import CueListPanel from './CueListPanel.jsx';
import MacButton from '../shared/components/MacButton.jsx';
import {
  Eye, EyeOff, Snowflake, Zap, Music,
  Sliders, Plus, Trash2, Volume2, Radio,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Miniatura colore cella (bg con gradiente e glow per le celle attive)
// ─────────────────────────────────────────────────────────────────────────────
function cellBg(cell) {
  if (cell.type === CellType.EMPTY) return '#16161c';
  return cell.active ? cell.color : `${cell.color}40`;
}

function cellBorder(cell) {
  if (cell.type === CellType.EMPTY) return '#2a2a35';
  if (cell.active) return cell.color;
  return `${cell.color}60`;
}

// ─────────────────────────────────────────────────────────────────────────────
// TriggerCell — Singolo pulsante della griglia
// ─────────────────────────────────────────────────────────────────────────────
function TriggerCell({ cell, onPress, onRelease, onDoubleClick }) {
  const isEmpty = cell.type === CellType.EMPTY;
  const isFlash = cell.mode === TriggerMode.FLASH;

  return (
    <button
      className={`relative rounded flex flex-col items-center justify-center select-none transition-all duration-75 overflow-hidden ${
        isEmpty
          ? 'cursor-default opacity-30'
          : cell.active
          ? 'scale-[0.93] shadow-lg cursor-pointer'
          : 'hover:opacity-90 cursor-pointer'
      }`}
      style={{
        backgroundColor: cellBg(cell),
        border: `1px solid ${cellBorder(cell)}`,
        boxShadow: cell.active && !isEmpty ? `0 0 8px ${cell.color}88` : undefined,
      }}
      onMouseDown={() => !isEmpty && onPress(cell.id)}
      onMouseUp={() => !isEmpty && onRelease(cell.id)}
      onDoubleClick={() => !isEmpty && onDoubleClick?.(cell.id)}
      title={isEmpty ? '' : `${cell.label} (${cell.mode})`}
    >
      {!isEmpty && (
        <>
          <span
            className="text-[9px] font-bold text-center leading-tight px-0.5 drop-shadow"
            style={{ color: cell.active ? (isLightColor(cell.color) ? '#111' : '#fff') : '#ccc' }}
          >
            {cell.label}
          </span>
          {/* Badge modalità: F=Flash, ◉=Latch */}
          <span
            className="absolute top-0.5 right-0.5 text-[7px] font-mono opacity-50"
            style={{ color: cell.active ? '#fff' : '#888' }}
          >
            {isFlash ? '⚡' : '◉'}
          </span>
          {/* Glow animato sulle celle attive FLASH */}
          {cell.active && isFlash && (
            <div
              className="absolute inset-0 rounded animate-pulse opacity-20"
              style={{ backgroundColor: cell.color }}
            />
          )}
        </>
      )}
    </button>
  );
}

/** Heuristica: colore chiaro → testo scuro */
function isLightColor(hex) {
  const c = hex.replace('#', '');
  if (c.length < 6) return false;
  const r = parseInt(c.substr(0, 2), 16);
  const g = parseInt(c.substr(2, 2), 16);
  const b = parseInt(c.substr(4, 2), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 160;
}

// ─────────────────────────────────────────────────────────────────────────────
// GroupFader — Fader verticale per un gruppo di fari
// ─────────────────────────────────────────────────────────────────────────────
function GroupFader({ group, onChange, onRemove, isDefault }) {
  const pct = Math.round(group.faderLevel * 100);

  return (
    <div className="flex flex-col items-center gap-1" style={{ minWidth: 44 }}>
      {/* Nome gruppo */}
      <div
        className="text-[9px] text-zinc-400 font-semibold text-center leading-tight w-full truncate"
        title={group.name}
      >
        {group.name}
      </div>

      {/* Pista + cursore verticale */}
      <div className="relative flex items-center justify-center" style={{ height: 100, width: 24 }}>
        {/* Pista */}
        <div
          className="absolute rounded-full bg-zinc-800"
          style={{ width: 4, height: 100, left: 10, top: 0 }}
        />
        {/* Fill */}
        <div
          className="absolute rounded-full transition-all"
          style={{
            width: 4,
            left: 10,
            bottom: 0,
            height: `${pct}%`,
            backgroundColor: pct > 60 ? '#0a84ff' : pct > 30 ? '#f59e0b' : '#ef4444',
          }}
        />
        {/* Input range rotato per simulare il fader verticale */}
        <input
          type="range"
          min="0"
          max="100"
          value={pct}
          onChange={(e) => onChange(group.id, Number(e.target.value) / 100)}
          style={{
            position: 'absolute',
            width: 100,
            height: 20,
            left: -38,
            top: 40,
            transform: 'rotate(-90deg)',
            cursor: 'pointer',
            accentColor: '#0a84ff',
            opacity: 0,
          }}
        />
        {/* Knob visivo */}
        <div
          className="absolute rounded bg-zinc-300 shadow"
          style={{
            width: 14,
            height: 7,
            left: 5,
            bottom: `calc(${pct}% - 3px)`,
            pointerEvents: 'none',
            transition: 'bottom 0.05s',
          }}
        />
      </div>

      {/* Valore % */}
      <div
        className="text-[10px] font-mono font-bold"
        style={{ color: pct > 60 ? '#0a84ff' : pct > 30 ? '#f59e0b' : '#ef4444' }}
      >
        {pct}%
      </div>

      {/* Elimina (solo gruppi custom) */}
      {!isDefault && (
        <button
          onClick={() => onRemove(group.id)}
          className="text-zinc-700 hover:text-red-400 transition-colors mt-0.5"
          title="Rimuovi gruppo"
        >
          <Trash2 size={9} />
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Modale di configurazione cella
// ─────────────────────────────────────────────────────────────────────────────
function CellEditModal({ cell, onSave, onClose }) {
  const [label,  setLabel]  = useState(cell.label);
  const [color,  setColor]  = useState(cell.color !== '#252530' ? cell.color : '#0a84ff');
  const [mode,   setMode]   = useState(cell.mode);
  const [type,   setType]   = useState(cell.type === CellType.EMPTY ? CellType.SCENE : cell.type);

  // ESC per chiudere
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[#1c1c20] border border-zinc-700 rounded-xl p-5 w-72 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold text-white mb-4">Configura Cella #{cell.id}</h3>

        <div className="space-y-3 text-[12px]">
          {/* Etichetta */}
          <div>
            <label className="text-zinc-400 block mb-1">Etichetta</label>
            <input
              autoFocus
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              maxLength={16}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-white focus:outline-none focus:border-mac-accent"
            />
          </div>

          {/* Colore */}
          <div>
            <label className="text-zinc-400 block mb-1">Colore</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-9 h-9 rounded cursor-pointer bg-transparent border-0"
                style={{ padding: 0 }}
              />
              <span className="font-mono text-zinc-400 text-[11px]">{color.toUpperCase()}</span>
            </div>
          </div>

          {/* Tipo */}
          <div>
            <label className="text-zinc-400 block mb-1">Tipo</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-white focus:outline-none focus:border-mac-accent"
            >
              <option value={CellType.SCENE}>Scena / Look</option>
              <option value={CellType.CUE}>Cue List</option>
              <option value={CellType.PALETTE}>Palette</option>
              <option value={CellType.BLACKOUT}>Blackout</option>
              <option value={CellType.EMPTY}>Vuota</option>
            </select>
          </div>

          {/* Modalità */}
          <div>
            <label className="text-zinc-400 block mb-1">Modalità</label>
            <div className="flex gap-2">
              {[TriggerMode.LATCH, TriggerMode.FLASH].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex-1 py-1.5 rounded text-[11px] font-semibold border transition-colors ${
                    mode === m
                      ? 'bg-mac-accent border-mac-accent text-white'
                      : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-white'
                  }`}
                >
                  {m === TriggerMode.FLASH ? '⚡ Flash' : '◉ Latch'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Anteprima */}
        <div className="mt-3 rounded flex items-center justify-center h-10 text-xs font-bold border"
          style={{ backgroundColor: `${color}30`, borderColor: color, color: '#fff' }}
        >
          {label || '(vuota)'}
        </div>

        {/* Azioni */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => onSave({ label: label.trim(), color, mode, type })}
            className="flex-1 bg-mac-accent hover:bg-blue-500 text-white py-1.5 rounded text-sm font-semibold transition-colors"
          >
            Salva
          </button>
          <button
            onClick={onClose}
            className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-1.5 rounded text-sm transition-colors"
          >
            Annulla
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// LiveView — Componente principale
// ─────────────────────────────────────────────────────────────────────────────
export default function LiveView({
  // Cue List
  cues, activeCueIndex, nextCueIndex, fadeState, manualCrossfade, isBlackout,
  onGo, onBack, onPause, onStop, onManualCrossfadeChange,
  onAddCue, onDeleteCue, onSelectCue, onToggleBlackout,
  // BPM
  bpm, onTapTempo,
  // LiveController (istanza mutabile + stato React sincronizzato)
  liveController,
  grandMaster, speedMaster, isBlind, isFrozen,
  onGrandMasterChange, onSpeedMasterChange, onToggleBlind, onToggleFreeze,
  // Palette apply (per celle di tipo PALETTE)
  onApplyPalette,
}) {
  const [gridCells,   setGridCells]   = useState(() => [...liveController.cells]);
  const [groups,      setGroups]      = useState(() => [...liveController.groups]);
  const [editingCell, setEditingCell] = useState(null); // null | idx

  const DEFAULT_GROUP_IDS = ['grp_spots', 'grp_wash', 'grp_all'];

  // ── Trigger Grid Handlers ────────────────────────────────────────
  const handleCellPress = useCallback((cellIdx) => {
    const updated = liveController.activateCell(cellIdx);
    if (!updated) return;

    // Esegui azione associata al tipo
    if (updated.type === CellType.PALETTE && updated.linkedId && updated.active && onApplyPalette) {
      onApplyPalette(updated.linkedId);
    } else if (updated.type === CellType.BLACKOUT) {
      onToggleBlackout?.();
    }

    setGridCells([...liveController.cells]);
  }, [liveController, onApplyPalette, onToggleBlackout]);

  const handleCellRelease = useCallback((cellIdx) => {
    liveController.releaseCell(cellIdx);
    setGridCells([...liveController.cells]);
  }, [liveController]);

  const handleSaveCell = useCallback((patch) => {
    liveController.updateCell(editingCell, patch);
    setGridCells([...liveController.cells]);
    setEditingCell(null);
  }, [liveController, editingCell]);

  // ── Group Fader Handlers ─────────────────────────────────────────
  const handleGroupFaderChange = useCallback((groupId, level) => {
    liveController.setGroupFader(groupId, level);
    setGroups([...liveController.groups]);
  }, [liveController]);

  const handleRemoveGroup = useCallback((groupId) => {
    liveController.removeGroup(groupId);
    setGroups([...liveController.groups]);
  }, [liveController]);

  const handleAddGroup = useCallback(() => {
    liveController.addGroup(`Gr. ${liveController.groups.length + 1}`);
    setGroups([...liveController.groups]);
  }, [liveController]);

  // ── Computed ─────────────────────────────────────────────────────
  const gmPct  = Math.round(grandMaster * 100);
  const spdPct = Math.round(((speedMaster - 0.1) / 3.9) * 100);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#141416] text-mac-text">

      {/* ══════════════════════════════════════════════════════════
          OVERRIDE STRIP
          ══════════════════════════════════════════════════════════ */}
      <div className="h-11 bg-[#0d0d10] border-b border-zinc-800/80 flex items-center px-3 gap-3 shrink-0">

        {/* Grand Master */}
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-zinc-500 uppercase font-mono tracking-widest select-none">GM</span>
          <div className="relative w-24 h-4 flex items-center rounded overflow-hidden bg-zinc-800/80">
            <div
              className="absolute inset-y-0 left-0 transition-all"
              style={{
                width: `${gmPct}%`,
                backgroundColor: gmPct > 60 ? '#0a84ff' : gmPct > 30 ? '#f59e0b' : '#ef4444',
                opacity: 0.75,
              }}
            />
            <input
              type="range" min="0" max="100" value={gmPct}
              onChange={(e) => onGrandMasterChange(Number(e.target.value) / 100)}
              className="relative w-full h-full opacity-0 cursor-pointer z-10"
              style={{ accentColor: '#0a84ff' }}
            />
          </div>
          <span
            className="text-[11px] font-mono font-bold w-7 text-right"
            style={{ color: gmPct > 60 ? '#0a84ff' : gmPct > 30 ? '#f59e0b' : '#ef4444' }}
          >
            {gmPct}%
          </span>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        {/* Speed Master */}
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-zinc-500 uppercase font-mono tracking-widest select-none">SPD</span>
          <div className="relative w-16 h-4 flex items-center rounded overflow-hidden bg-zinc-800/80">
            <div
              className="absolute inset-y-0 left-0 bg-emerald-600/70 transition-all"
              style={{ width: `${spdPct}%` }}
            />
            <input
              type="range" min="10" max="400" value={Math.round(speedMaster * 100)}
              onChange={(e) => onSpeedMasterChange(Number(e.target.value) / 100)}
              className="relative w-full h-full opacity-0 cursor-pointer z-10"
            />
          </div>
          <span className="text-[11px] font-mono font-bold text-emerald-400 w-8">
            {speedMaster.toFixed(1)}x
          </span>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        {/* BLIND */}
        <button
          onClick={onToggleBlind}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold border transition-all ${
            isBlind
              ? 'bg-amber-500 border-amber-400 text-black shadow-md shadow-amber-500/40'
              : 'bg-zinc-800/60 border-zinc-700 text-zinc-500 hover:text-amber-300 hover:border-amber-700'
          }`}
        >
          {isBlind ? <EyeOff size={11} /> : <Eye size={11} />}
          BLIND
        </button>

        {/* FREEZE */}
        <button
          onClick={onToggleFreeze}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold border transition-all ${
            isFrozen
              ? 'bg-sky-500 border-sky-400 text-black shadow-md shadow-sky-500/40'
              : 'bg-zinc-800/60 border-zinc-700 text-zinc-500 hover:text-sky-300 hover:border-sky-700'
          }`}
        >
          <Snowflake size={11} />
          FREEZE
        </button>

        {/* BLACKOUT */}
        <button
          onClick={onToggleBlackout}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold border transition-all ${
            isBlackout
              ? 'bg-red-600 border-red-500 text-white shadow-md shadow-red-600/40 animate-pulse'
              : 'bg-zinc-800/60 border-zinc-700 text-zinc-500 hover:text-red-400 hover:border-red-700'
          }`}
        >
          <Zap size={11} />
          BLACKOUT
        </button>

        {/* Avviso Blind (banner) */}
        {isBlind && (
          <div className="text-amber-400 text-[9px] font-bold tracking-widest animate-pulse select-none">
            ⚠ BLIND — Nessun output DMX al palco
          </div>
        )}
        {isFrozen && !isBlind && (
          <div className="text-sky-400 text-[9px] font-bold tracking-widest select-none">
            ❄ FREEZE — Output DMX congelato
          </div>
        )}

        <div className="flex-1" />

        {/* BPM + Tap */}
        <div className="flex items-center gap-1.5 bg-zinc-900/80 px-2 py-1 rounded border border-zinc-800">
          <Music size={10} className="text-zinc-500" />
          <span className="text-[9px] text-zinc-500 font-mono uppercase">BPM</span>
          <span className="text-[12px] font-mono font-bold text-mac-accent">{bpm.toFixed(1)}</span>
          <button
            onClick={onTapTempo}
            className="bg-zinc-700 hover:bg-mac-accent text-white text-[9px] font-bold px-1.5 py-0.5 rounded transition-colors"
          >
            TAP
          </button>
        </div>

        {/* Indicatore DMX live */}
        <div className="flex items-center gap-1 text-[10px] text-zinc-500">
          <Radio size={10} className={isFrozen ? 'text-sky-400' : isBlind ? 'text-amber-400' : 'text-emerald-500'} />
          <span className={isFrozen ? 'text-sky-400' : isBlind ? 'text-amber-400' : 'text-emerald-500'}>
            {isFrozen ? 'FROZEN' : isBlind ? 'BLIND' : 'LIVE'}
          </span>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          AREA CENTRALE: Trigger Grid + Fader Gruppo
          ══════════════════════════════════════════════════════════ */}
      <div className="flex-1 flex overflow-hidden min-h-0">

        {/* ── Trigger Grid ───────────────────────────────────────── */}
        <div className="flex-1 p-2.5 flex flex-col min-w-0 overflow-hidden">
          {/* Header griglia */}
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 text-[9px] text-zinc-600 uppercase tracking-widest font-semibold">
              <Sliders size={10} />
              Griglia Trigger
              <span className="text-zinc-700 normal-case tracking-normal font-normal">
                {liveController.gridCols}×{liveController.gridRows} · Doppio click per configurare
              </span>
            </div>
            <div className="flex items-center gap-2 text-[9px] text-zinc-700">
              <span>◉ Latch</span>
              <span>⚡ Flash</span>
            </div>
          </div>

          {/* Griglia */}
          <div
            className="flex-1 min-h-0"
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${liveController.gridCols}, 1fr)`,
              gridTemplateRows: `repeat(${liveController.gridRows}, 1fr)`,
              gap: 3,
            }}
          >
            {gridCells.map((cell) => (
              <TriggerCell
                key={cell.id}
                cell={cell}
                onPress={handleCellPress}
                onRelease={handleCellRelease}
                onDoubleClick={(idx) => setEditingCell(idx)}
              />
            ))}
          </div>
        </div>

        {/* Separatore verticale */}
        <div className="w-px bg-zinc-800/80 shrink-0" />

        {/* ── Group Faders ───────────────────────────────────────── */}
        <div className="w-52 flex flex-col p-2.5 overflow-y-auto overflow-x-hidden bg-[#101014] shrink-0">
          <div className="flex items-center gap-1.5 text-[9px] text-zinc-600 uppercase tracking-widest font-semibold mb-3">
            <Volume2 size={10} />
            Fader Gruppo
          </div>

          {/* Riga fader */}
          <div className="flex flex-row flex-wrap gap-3 flex-1 items-start justify-center">
            {groups.map((grp) => (
              <GroupFader
                key={grp.id}
                group={grp}
                onChange={handleGroupFaderChange}
                onRemove={handleRemoveGroup}
                isDefault={DEFAULT_GROUP_IDS.includes(grp.id)}
              />
            ))}
          </div>

          {/* Aggiungi gruppo custom */}
          <button
            onClick={handleAddGroup}
            className="mt-3 flex items-center justify-center gap-1 text-[9px] text-zinc-700 hover:text-mac-accent transition-colors py-1 border border-dashed border-zinc-800 hover:border-mac-accent/40 rounded"
          >
            <Plus size={9} />
            Aggiungi Gruppo
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          CUE LIST INTEGRATA (sempre visibile in Live Mode)
          ══════════════════════════════════════════════════════════ */}
      <div className="border-t border-zinc-800/80 shrink-0" style={{ height: 196 }}>
        <CueListPanel
          cues={cues}
          activeCueIndex={activeCueIndex}
          nextCueIndex={nextCueIndex}
          fadeState={fadeState}
          manualCrossfade={manualCrossfade}
          onGo={onGo}
          onBack={onBack}
          onPause={onPause}
          onStop={onStop}
          onManualCrossfadeChange={onManualCrossfadeChange}
          onAddCue={onAddCue}
          onDeleteCue={onDeleteCue}
          onSelectCue={onSelectCue}
          onToggleBlackout={onToggleBlackout}
          isBlackout={isBlackout}
        />
      </div>

      {/* ── Modale configurazione cella ───────────────────────────── */}
      {editingCell !== null && (
        <CellEditModal
          cell={gridCells[editingCell]}
          onSave={handleSaveCell}
          onClose={() => setEditingCell(null)}
        />
      )}
    </div>
  );
}
