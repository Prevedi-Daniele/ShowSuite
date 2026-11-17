/**
 * CueListTable.jsx — Tabella gerarchica delle Cue in stile QLab 5
 * 
 * Supporta:
 * - Annidamento ad albero con expand/collapse per GroupCues
 * - Colonne configurabili (Q#, Stato, Tipo, Nome, Target, Pre-Wait, Durata, Post-Wait, Seguito, Note)
 * - Barra di progresso live 60 FPS direttamente nella cella della durata
 * - Cursore Standby ad alta visibilità (indicatore giallo/oro della prossima cue al GO)
 * - Tasti rapidi di riga: Arm/Disarm, Trigger GO singolo, Elimina
 */

import React, { useState } from 'react';
import {
  CueType,
  CueState,
  ContinueMode,
  GroupMode,
} from '../core/qlab/index.js';
import {
  Volume2,
  Video,
  FileText,
  Sliders,
  Send,
  Radio,
  Clock,
  Mic,
  Folder,
  FolderOpen,
  Play,
  Square,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ArrowDownRight,
  ChevronRight,
  ChevronDown,
  Trash2,
  Shield,
  ShieldOff,
  Tag,
  CornerDownRight,
  Sparkles,
} from 'lucide-react';

const CUE_TYPE_ICONS = {
  [CueType.BASE]: Play,
  [CueType.GROUP]: Folder,
  [CueType.AUDIO]: Volume2,
  [CueType.MIC]: Mic,
  [CueType.VIDEO]: Video,
  [CueType.CAMERA]: Video,
  [CueType.TEXT]: FileText,
  [CueType.FADE]: Sliders,
  [CueType.LIGHT]: Sparkles,
  [CueType.NETWORK]: Send,
  [CueType.MIDI]: Radio,
  [CueType.TIMECODE]: Clock,
};

function formatTime(sec) {
  if (sec === undefined || sec === null || isNaN(sec)) return '00:00.00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 100);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

export default function CueListTable({
  cues = [],
  standbyCueId = null,
  selectedCueId = null,
  columnsConfig = {
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
  },
  onSelectCue,
  onGoCue,
  onStopCue,
  onDeleteCue,
  onToggleArm,
}) {
  // Set di ID dei gruppi espansi
  const [expandedGroupIds, setExpandedGroupIds] = useState(() => new Set());

  const toggleGroupExpand = (groupId, e) => {
    e.stopPropagation();
    setExpandedGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Funzione ricorsiva di rendering delle righe
  const renderRows = (cueList, depth = 0) => {
    return cueList.flatMap((cue) => {
      const isGroup = cue.type === CueType.GROUP;
      const isExpanded = expandedGroupIds.has(cue.id);
      const isStandby = cue.id === standbyCueId;
      const isSelected = cue.id === selectedCueId;
      const isRunning = cue.state === CueState.RUNNING;
      const isPaused = cue.state === CueState.PAUSED;
      const isBroken = cue.isBroken();

      const IconComponent = isGroup
        ? isExpanded
          ? FolderOpen
          : Folder
        : CUE_TYPE_ICONS[cue.type] || Play;

      // Calcolo progresso live
      const actionProgress = cue.getActionProgress ? cue.getActionProgress() : 0;
      const totalProgress = cue.getProgress ? cue.getProgress() : 0;

      // Colore etichetta riga se impostato
      const colorBorder =
        cue.color === 'red'
          ? 'border-l-4 border-l-red-500'
          : cue.color === 'orange'
          ? 'border-l-4 border-l-orange-500'
          : cue.color === 'green'
          ? 'border-l-4 border-l-emerald-500'
          : cue.color === 'blue'
          ? 'border-l-4 border-l-blue-500'
          : cue.color === 'purple'
          ? 'border-l-4 border-l-purple-500'
          : 'border-l-4 border-l-transparent';

      const row = (
        <div
          key={cue.id}
          onClick={() => onSelectCue(cue.id)}
          onDoubleClick={() => onGoCue(cue.id)}
          className={`h-7 flex items-center text-xs select-none cursor-pointer border-b border-white/[0.04] transition-colors relative ${colorBorder} ${
            isStandby
              ? 'bg-[#ffcc00]/15 ring-1 ring-[#ffcc00]/80 font-semibold text-white'
              : isSelected
              ? 'bg-[#0071e3]/30 text-white font-medium ring-1 ring-[#0071e3]/50'
              : isRunning
              ? 'bg-emerald-500/15 text-emerald-200'
              : 'hover:bg-white/[0.05] text-[#d1d1d6]'
          } ${!cue.armed ? 'opacity-40 italic' : ''}`}
        >
          {/* Cursore Standby Badge (Freccia Playhead QLab) */}
          <div className="w-6 flex items-center justify-center shrink-0">
            {isStandby && (
              <span className="w-2.5 h-2.5 rounded-full bg-[#ffcc00] shadow-[0_0_8px_rgba(255,204,0,0.8)]" />
            )}
            {isRunning && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shadow-sm shadow-emerald-400" />
            )}
          </div>

          {/* Colonna Q# */}
          {columnsConfig.number && (
            <div className="w-14 font-mono text-[11px] text-zinc-400 shrink-0 truncate px-1">
              {cue.number || '-'}
            </div>
          )}

          {/* Colonna Stato / Arm */}
          {columnsConfig.status && (
            <div className="w-10 flex items-center justify-center space-x-1 shrink-0">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleArm(cue.id);
                }}
                title={cue.armed ? 'Armata (click per disarmare)' : 'Disarmata (click per armare)'}
                className="hover:scale-110 transition-transform"
              >
                {cue.armed ? (
                  <Shield size={12} className="text-emerald-400" />
                ) : (
                  <ShieldOff size={12} className="text-zinc-600" />
                )}
              </button>

              {isBroken && (
                <AlertCircle size={12} className="text-red-500" title={cue.brokenReason || 'Errore Cue'} />
              )}
            </div>
          )}

          {/* Colonna Tipo con Icona */}
          {columnsConfig.type && (
            <div className="w-8 flex items-center justify-center shrink-0">
              <IconComponent
                size={13}
                className={
                  isRunning
                    ? 'text-emerald-400 animate-pulse'
                    : isGroup
                    ? 'text-amber-400'
                    : 'text-zinc-400'
                }
              />
            </div>
          )}

          {/* Colonna Nome con Indentazione Gerarchica */}
          {columnsConfig.name && (
            <div
              className="flex-1 min-w-[140px] flex items-center truncate px-2"
              style={{ paddingLeft: `${Math.max(8, depth * 20 + 8)}px` }}
            >
              {isGroup && (
                <button
                  type="button"
                  onClick={(e) => toggleGroupExpand(cue.id, e)}
                  className="mr-1 text-zinc-400 hover:text-white"
                >
                  {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                </button>
              )}
              {depth > 0 && !isGroup && (
                <CornerDownRight size={10} className="text-zinc-600 mr-1.5 shrink-0" />
              )}
              <span className="truncate">{cue.name}</span>
            </div>
          )}

          {/* Colonna Target */}
          {columnsConfig.target && (
            <div className="w-28 font-mono text-[10px] text-zinc-500 truncate px-2 shrink-0">
              {cue.targetId || '-'}
            </div>
          )}

          {/* Colonna Pre-Wait */}
          {columnsConfig.preWait && (
            <div className="w-20 font-mono text-[11px] text-right px-2 shrink-0 text-zinc-400">
              {cue.preWait > 0 ? formatTime(cue.preWait) : '-'}
            </div>
          )}

          {/* Colonna Durata con ProgressBar Live */}
          {columnsConfig.duration && (
            <div className="w-24 px-2 shrink-0 text-right font-mono text-[11px] relative overflow-hidden">
              {isRunning && (
                <div
                  className="absolute inset-y-0 left-0 bg-emerald-500/20 border-r border-emerald-400/50 transition-all duration-75 pointer-events-none"
                  style={{ width: `${Math.round(actionProgress * 100)}%` }}
                />
              )}
              <span className={`relative z-10 ${isRunning ? 'text-emerald-300 font-bold' : ''}`}>
                {cue.duration > 0 ? formatTime(cue.duration) : '-'}
              </span>
            </div>
          )}

          {/* Colonna Post-Wait */}
          {columnsConfig.postWait && (
            <div className="w-20 font-mono text-[11px] text-right px-2 shrink-0 text-zinc-400">
              {cue.postWait > 0 ? formatTime(cue.postWait) : '-'}
            </div>
          )}

          {/* Colonna Continue Mode */}
          {columnsConfig.continueMode && (
            <div className="w-24 flex items-center justify-center px-1 shrink-0 text-[10px] text-zinc-400">
              {cue.continueMode === ContinueMode.AUTO_CONTINUE && (
                <span className="flex items-center text-blue-400 font-medium space-x-0.5" title="Auto-Continue">
                  <ArrowRight size={11} />
                  <span>Cont</span>
                </span>
              )}
              {cue.continueMode === ContinueMode.AUTO_FOLLOW && (
                <span className="flex items-center text-emerald-400 font-medium space-x-0.5" title="Auto-Follow">
                  <ArrowDownRight size={11} />
                  <span>Follow</span>
                </span>
              )}
              {cue.continueMode === ContinueMode.DO_NOT_CONTINUE && (
                <span className="text-zinc-600">-</span>
              )}
            </div>
          )}

          {/* Colonna Note */}
          {columnsConfig.notes && (
            <div className="w-32 truncate px-2 text-[10px] text-zinc-500 shrink-0">
              {cue.notes || ''}
            </div>
          )}

          {/* Azioni Rapide Hover */}
          <div className="w-16 flex items-center justify-end space-x-1 pr-2 shrink-0 opacity-20 hover:opacity-100 transition-opacity">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (isRunning) onStopCue(cue.id);
                else onGoCue(cue.id);
              }}
              className="p-1 hover:text-white rounded hover:bg-white/10"
              title={isRunning ? 'Ferma Cue' : 'Avvia Cue Singola'}
            >
              {isRunning ? <Square size={10} className="text-red-400" /> : <Play size={10} />}
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteCue(cue.id);
              }}
              className="p-1 hover:text-red-400 rounded hover:bg-white/10"
              title="Elimina Cue"
            >
              <Trash2 size={10} />
            </button>
          </div>
        </div>
      );

      // Se è un gruppo ed è espanso, renderizza ricorsivamente i figli
      if (isGroup && isExpanded && cue.children && cue.children.length > 0) {
        return [row, ...renderRows(cue.children, depth + 1)];
      }

      return [row];
    });
  };

  return (
    <div className="flex-1 flex flex-col bg-[#121214] overflow-hidden select-none">
      {/* Header Tabella Colonne */}
      <div className="h-7 bg-[#1c1c21] border-b border-[#2c2c34] flex items-center text-[11px] font-semibold text-zinc-400 select-none shrink-0">
        <div className="w-6 shrink-0" />
        {columnsConfig.number && <div className="w-14 px-1 shrink-0">Q#</div>}
        {columnsConfig.status && <div className="w-10 text-center shrink-0">Stato</div>}
        {columnsConfig.type && <div className="w-8 text-center shrink-0">Tipo</div>}
        {columnsConfig.name && <div className="flex-1 min-w-[140px] px-2">Nome Cue</div>}
        {columnsConfig.target && <div className="w-28 px-2 shrink-0">Target</div>}
        {columnsConfig.preWait && <div className="w-20 text-right px-2 shrink-0">Pre-Wait</div>}
        {columnsConfig.duration && <div className="w-24 text-right px-2 shrink-0">Durata</div>}
        {columnsConfig.postWait && <div className="w-20 text-right px-2 shrink-0">Post-Wait</div>}
        {columnsConfig.continueMode && <div className="w-24 text-center px-1 shrink-0">Seguito</div>}
        {columnsConfig.notes && <div className="w-32 px-2 shrink-0">Note</div>}
        <div className="w-16 shrink-0" />
      </div>

      {/* Corpo righe Cue */}
      <div className="flex-1 overflow-auto">
        {cues.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-zinc-500">
            Nessuna Cue presente. Usa i pulsanti della barra in alto per aggiungere una nuova Cue.
          </div>
        ) : (
          renderRows(cues)
        )}
      </div>
    </div>
  );
}
