/**
 * TimecodeHUD.jsx — Display digitale e Monitor di Sincronizzazione Timecode (SMPTE 12M)
 * 
 * Fornisce una visualizzazione ad alta leggibilità e contrasto per:
 * - Timecode SMPTE corrente (HH:MM:SS:FF) con subframes
 * - Stato della macchina a stati TimecodeChaser:
 *     - OFFLINE (nessun segnale)
 *     - LOCKING (sincronizzazione in corso)
 *     - LOCKED (aggancio stabile / frame-accurate)
 *     - FREEWHEELING (tolleranza dropout attiva)
 * - Frame rate attivo (24, 25, 29.97 DF, 30 fps)
 * - Sorgente (MTC o LTC Audio)
 */

import React, { useState, useEffect } from 'react';
import { ChaserState } from '../core/timecode/TimecodeChaser.js';
import { Clock, ShieldCheck, Activity, AlertTriangle, Disc } from 'lucide-react';

export default function TimecodeHUD({ timecodeStr = '00:00:00:00', chaserState = ChaserState.OFFLINE, fps = 25, source = 'MTC' }) {
  const getBadgeColor = () => {
    switch (chaserState) {
      case ChaserState.LOCKED:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case ChaserState.LOCKING:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/40 animate-pulse';
      case ChaserState.FREEWHEELING:
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40 animate-pulse';
      case ChaserState.OFFLINE:
      default:
        return 'bg-zinc-800/60 text-zinc-500 border-zinc-700/50';
    }
  };

  const getStatusIcon = () => {
    switch (chaserState) {
      case ChaserState.LOCKED:
        return <ShieldCheck size={12} className="text-emerald-400" />;
      case ChaserState.LOCKING:
        return <Activity size={12} className="text-blue-400 animate-spin" />;
      case ChaserState.FREEWHEELING:
        return <AlertTriangle size={12} className="text-amber-400" />;
      case ChaserState.OFFLINE:
      default:
        return <Clock size={12} className="text-zinc-500" />;
    }
  };

  return (
    <div className="flex items-center space-x-2 bg-black/60 px-2.5 py-1 rounded-lg border border-[#33333d] shadow-inner select-none">
      {/* Indicatore Sorgente & Frame Rate */}
      <div className="flex flex-col text-[9px] font-mono leading-tight text-zinc-400 border-r border-zinc-800 pr-2">
        <span className="font-bold text-zinc-300 flex items-center gap-1">
          <Disc size={10} className={chaserState === ChaserState.LOCKED ? 'text-emerald-400 animate-spin' : 'text-zinc-500'} />
          {source}
        </span>
        <span className="text-[8px] text-zinc-500">{fps} FPS</span>
      </div>

      {/* Cifre Timecode SMPTE Digitali */}
      <div className="text-base font-mono font-black text-amber-400 tracking-wider px-1">
        {timecodeStr}
      </div>

      {/* Badge Stato Macchina Chaser */}
      <div
        className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider border flex items-center gap-1 ${getBadgeColor()}`}
      >
        {getStatusIcon()}
        <span>{chaserState}</span>
      </div>
    </div>
  );
}
