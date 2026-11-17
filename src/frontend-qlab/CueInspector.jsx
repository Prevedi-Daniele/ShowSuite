/**
 * CueInspector.jsx — Inspector contestuale delle proprietà di una Cue (QLab 5)
 * 
 * Permette la modifica in tempo reale di:
 * - Basics: Numero, Nome, Colore, Flag, Armed/Disarmed, Target, Note
 * - Timing: Pre-Wait, Duration, Post-Wait, Continue Mode (Do Not Continue, Auto-Continue, Auto-Follow)
 * - Proprietà specifiche di gruppo (Timeline, Playlist, Start-First, Random)
 * - Audio & Mic: integrazione diretta con AudioInspector (Waveform, Slices, Vari-speed, Matrix Mixer)
 */

import React, { useState, useEffect } from 'react';
import { ContinueMode, GroupMode, CueType, CueState } from '../core/qlab/index.js';
import AudioInspector from './AudioInspector.jsx';
import NetworkInspectorTab from './NetworkInspectorTab.jsx';
import MidiInspectorTab from './MidiInspectorTab.jsx';
import TimecodeInspectorTab from './TimecodeInspectorTab.jsx';
import {
  Clock,
  Sliders,
  Tag,
  AlertTriangle,
  FolderTree,
  Eye,
  CheckCircle2,
  XCircle,
  FileText,
  Music,
  Mic,
  Send,
  Radio,
} from 'lucide-react';

const CUE_COLORS = [
  { id: 'none', label: 'Nessuno', bg: '#27272a', border: '#3f3f46' },
  { id: 'red', label: 'Rosso', bg: '#ef4444', border: '#dc2626' },
  { id: 'orange', label: 'Arancione', bg: '#f97316', border: '#ea580c' },
  { id: 'green', label: 'Verde', bg: '#22c55e', border: '#16a34a' },
  { id: 'blue', label: 'Blu', bg: '#3b82f6', border: '#2563eb' },
  { id: 'purple', label: 'Viola', bg: '#a855f7', border: '#9333ea' },
];

export default function CueInspector({ cue, onUpdateCue }) {
  const [activeTab, setActiveTab] = useState('basics'); // 'basics' | 'timing' | 'audio' | 'network' | 'midi' | 'timecode' | 'notes'

  const isAudioOrMic = cue && (cue.type === CueType.AUDIO || cue.type === CueType.MIC);
  const isNetwork = cue && cue.type === CueType.NETWORK;
  const isMidi = cue && cue.type === CueType.MIDI;
  const isTimecode = cue && cue.type === CueType.TIMECODE;

  // Se l'utente seleziona una cue specifica, switch automatico su tab dedicata se pertinente
  useEffect(() => {
    if (isAudioOrMic && activeTab !== 'basics' && activeTab !== 'timing' && activeTab !== 'notes' && activeTab !== 'audio') {
      setActiveTab('audio');
    } else if (isNetwork && activeTab !== 'basics' && activeTab !== 'timing' && activeTab !== 'notes' && activeTab !== 'network') {
      setActiveTab('network');
    } else if (isMidi && activeTab !== 'basics' && activeTab !== 'timing' && activeTab !== 'notes' && activeTab !== 'midi') {
      setActiveTab('midi');
    } else if (isTimecode && activeTab !== 'basics' && activeTab !== 'timing' && activeTab !== 'notes' && activeTab !== 'timecode') {
      setActiveTab('timecode');
    }
  }, [cue?.id, isAudioOrMic, isNetwork, isMidi, isTimecode]);

  if (!cue) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-zinc-500 bg-[#161619] select-none">
        Seleziona una Cue nella tabella per visualizzarne e modificarne le proprietà.
      </div>
    );
  }

  const handleFieldChange = (field, value) => {
    onUpdateCue(cue.id, { [field]: value });
  };

  return (
    <div className="h-full flex flex-col bg-[#161619] text-mac-text select-none text-xs">
      {/* Header Tabs dell'Inspector */}
      <div className="h-7 bg-[#1c1c20] border-b border-[#2d2d38] px-3 flex items-center justify-between shrink-0">
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('basics')}
            className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
              activeTab === 'basics'
                ? 'text-white border-b-2 border-mac-accent'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Tag size={12} />
            <span>Generale</span>
          </button>

          <button
            onClick={() => setActiveTab('timing')}
            className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
              activeTab === 'timing'
                ? 'text-white border-b-2 border-mac-accent'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Clock size={12} />
            <span>Tempi & Seguito</span>
          </button>

          {/* Scheda Dedicata Audio & Matrix Mixer per Audio e Mic Cues */}
          {isAudioOrMic && (
            <button
              onClick={() => setActiveTab('audio')}
              className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
                activeTab === 'audio'
                  ? 'text-white border-b-2 border-mac-accent'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {cue.type === CueType.MIC ? <Mic size={12} className="text-emerald-400" /> : <Music size={12} className="text-mac-accent" />}
              <span>Audio & Matrix Mixer</span>
            </button>
          )}

          {/* Scheda Dedicata Network & OSC */}
          {isNetwork && (
            <button
              onClick={() => setActiveTab('network')}
              className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
                activeTab === 'network'
                  ? 'text-white border-b-2 border-mac-accent'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Send size={12} className="text-blue-400" />
              <span>Network & OSC</span>
            </button>
          )}

          {/* Scheda Dedicata MIDI & MSC */}
          {isMidi && (
            <button
              onClick={() => setActiveTab('midi')}
              className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
                activeTab === 'midi'
                  ? 'text-white border-b-2 border-mac-accent'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Radio size={12} className="text-pink-400" />
              <span>MIDI & MSC</span>
            </button>
          )}

          {/* Scheda Dedicata Timecode */}
          {isTimecode && (
            <button
              onClick={() => setActiveTab('timecode')}
              className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
                activeTab === 'timecode'
                  ? 'text-white border-b-2 border-mac-accent'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Clock size={12} className="text-amber-400" />
              <span>Timecode Output</span>
            </button>
          )}

          <button
            onClick={() => setActiveTab('notes')}
            className={`pb-1 transition-colors flex items-center space-x-1 font-medium ${
              activeTab === 'notes'
                ? 'text-white border-b-2 border-mac-accent'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <FileText size={12} />
            <span>Note</span>
          </button>
        </div>

        {/* Info Cue ID & Stato */}
        <div className="flex items-center space-x-2 text-[10px] text-zinc-400 font-mono">
          <span>ID: {cue.id}</span>
          <span
            className={`px-1.5 py-0.2 rounded font-semibold uppercase ${
              cue.state === CueState.RUNNING
                ? 'bg-emerald-500/20 text-emerald-400'
                : cue.state === CueState.PAUSED
                ? 'bg-amber-500/20 text-amber-400'
                : cue.state === CueState.BROKEN
                ? 'bg-red-500/20 text-red-400'
                : 'bg-zinc-800 text-zinc-400'
            }`}
          >
            {cue.state}
          </span>
        </div>
      </div>

      {/* Contenuto Tab */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {activeTab === 'basics' && (
          <div className="p-3 overflow-y-auto grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Numero Cue */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Q# (Numero)</label>
              <input
                type="text"
                value={cue.number}
                onChange={(e) => handleFieldChange('number', e.target.value)}
                placeholder="es. 1, 2.5"
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>

            {/* Nome Cue */}
            <div className="col-span-2">
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Nome Cue</label>
              <input
                type="text"
                value={cue.name}
                onChange={(e) => handleFieldChange('name', e.target.value)}
                placeholder="Descrizione della cue..."
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>

            {/* Target */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Target / File</label>
              <input
                type="text"
                value={cue.targetId || ''}
                onChange={(e) => handleFieldChange('targetId', e.target.value)}
                placeholder="File audio/video o ID..."
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-zinc-300 font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>

            {/* Colore Cue */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Colore Etichetta</label>
              <div className="flex items-center space-x-1.5 pt-1">
                {CUE_COLORS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => handleFieldChange('color', c.id)}
                    style={{ backgroundColor: c.bg }}
                    title={c.label}
                    className={`w-4 h-4 rounded-full transition-transform ${
                      cue.color === c.id ? 'scale-125 ring-2 ring-white shadow-md' : 'opacity-70 hover:opacity-100'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Switch Armed / Flagged */}
            <div className="flex items-center space-x-4 pt-4">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cue.armed}
                  onChange={(e) => handleFieldChange('armed', e.target.checked)}
                  className="rounded bg-zinc-800 border-zinc-700 text-mac-accent focus:ring-0"
                />
                <span className={cue.armed ? 'text-emerald-400 font-medium' : 'text-zinc-500'}>
                  {cue.armed ? 'Armed' : 'Disarmed'}
                </span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cue.flagged}
                  onChange={(e) => handleFieldChange('flagged', e.target.checked)}
                  className="rounded bg-zinc-800 border-zinc-700 text-amber-500 focus:ring-0"
                />
                <span className={cue.flagged ? 'text-amber-400 font-medium' : 'text-zinc-500'}>Flagged</span>
              </label>
            </div>

            {/* Modalità Gruppo se la Cue è un GroupCue */}
            {cue.type === CueType.GROUP && (
              <div className="col-span-2">
                <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">
                  Modalità Gruppo (Group Mode)
                </label>
                <select
                  value={cue.mode || GroupMode.TIMELINE}
                  onChange={(e) => handleFieldChange('mode', e.target.value)}
                  className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
                >
                  <option value={GroupMode.TIMELINE}>Timeline: Avvia tutti i figli simultaneamente</option>
                  <option value={GroupMode.PLAYLIST}>Playlist: Esegui i figli in sequenza</option>
                  <option value={GroupMode.START_FIRST_AND_GO_TO_NEXT}>Start First: Avvia primo e avanza ad ogni GO</option>
                  <option value={GroupMode.RANDOM}>Random: Esegui un figlio a caso</option>
                </select>
              </div>
            )}
          </div>
        )}

        {activeTab === 'timing' && (
          <div className="p-3 overflow-y-auto grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Pre-Wait */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Pre-Wait (sec)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={cue.preWait}
                onChange={(e) => handleFieldChange('preWait', Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
              <span className="text-[10px] text-zinc-500">Ritardo prima dell'avvio</span>
            </div>

            {/* Duration */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Durata (sec)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={cue.duration}
                onChange={(e) => handleFieldChange('duration', Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
              <span className="text-[10px] text-zinc-500">Durata dell'azione</span>
            </div>

            {/* Post-Wait */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Post-Wait (sec)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={cue.postWait}
                onChange={(e) => handleFieldChange('postWait', Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
              <span className="text-[10px] text-zinc-500">Pausa prima del seguito</span>
            </div>

            {/* Continue Mode */}
            <div>
              <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Azione Seguito (Continue)</label>
              <select
                value={cue.continueMode}
                onChange={(e) => handleFieldChange('continueMode', e.target.value)}
                className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
              >
                <option value={ContinueMode.DO_NOT_CONTINUE}>Do Not Continue (Attendi GO)</option>
                <option value={ContinueMode.AUTO_CONTINUE}>Auto-Continue (Simultaneo / Pre+Post)</option>
                <option value={ContinueMode.AUTO_FOLLOW}>Auto-Follow (Al termine azione)</option>
              </select>
              <span className="text-[10px] text-zinc-500">
                {cue.continueMode === ContinueMode.AUTO_CONTINUE
                  ? 'Attiva la successiva dopo Pre+Post'
                  : cue.continueMode === ContinueMode.AUTO_FOLLOW
                  ? 'Attiva la successiva a fine durata'
                  : 'Si ferma e aspetta il tasto GO'}
              </span>
            </div>
          </div>
        )}

        {/* Scheda Dedicata Audio & Matrix Mixer */}
        {activeTab === 'audio' && isAudioOrMic && (
          <AudioInspector cue={cue} onUpdateCue={onUpdateCue} />
        )}

        {/* Scheda Dedicata Network & OSC */}
        {activeTab === 'network' && isNetwork && (
          <NetworkInspectorTab cue={cue} onUpdateCue={onUpdateCue} />
        )}

        {/* Scheda Dedicata MIDI & MSC */}
        {activeTab === 'midi' && isMidi && (
          <MidiInspectorTab cue={cue} onUpdateCue={onUpdateCue} />
        )}

        {/* Scheda Dedicata Timecode Output */}
        {activeTab === 'timecode' && isTimecode && (
          <TimecodeInspectorTab cue={cue} onUpdateCue={onUpdateCue} />
        )}

        {activeTab === 'notes' && (
          <div className="p-3">
            <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Note di Regia</label>
            <textarea
              rows={3}
              value={cue.notes}
              onChange={(e) => handleFieldChange('notes', e.target.value)}
              placeholder="Inserisci note di regia, cambi scena, avvertimenti tecnici..."
              className="w-full bg-[#121214] border border-[#2d2d38] rounded p-2 text-zinc-200 text-xs focus:outline-none focus:border-mac-accent resize-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
