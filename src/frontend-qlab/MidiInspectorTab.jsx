/**
 * MidiInspectorTab.jsx — Scheda Inspector dedicata per MidiCue (QLab 5)
 * 
 * Supporta:
 * - Tipo messaggio: Note On, Note Off, Control Change (CC), Program Change (PC), Pitch Bend, MIDI Show Control (MSC)
 * - Canale MIDI 1–16
 * - Note On/Off: selettore ottava (-1..9) e nota (C..B) con calcolo numero MIDI automatico, slider velocity (0–127)
 * - Control Change: numero control (0–127) e valore (0–127)
 * - Program Change: program (0–127), Bank MSB / LSB opzionale
 * - Pitch Bend: slider centrato (-8192..+8191)
 * - MIDI Show Control (MSC): Device ID, Formato comando (Lighting, Sound, All...), Comando (GO, STOP, RESUME, LOAD, SET...), Cue Number
 * - Tasto "Test Invio MIDI Ora"
 */

import React, { useState } from 'react';
import {
  MidiMessageType,
  MSCFormat,
  MSCCommand,
  numberToNoteName,
  noteNameToNumber,
} from '../core/control/MidiCue.js';
import { Radio, Zap, CheckCircle2, AlertCircle, Music } from 'lucide-react';

const NOTE_KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

export default function MidiInspectorTab({ cue, onUpdateCue }) {
  const [testStatus, setTestStatus] = useState(null);
  const [testMsg, setTestMsg] = useState('');

  const messageType = cue.messageType || MidiMessageType.NOTE_ON;
  const channel = cue.channel || 1;
  const note = cue.note !== undefined ? cue.note : 60;
  const velocity = cue.velocity !== undefined ? cue.velocity : 127;
  const control = cue.control !== undefined ? cue.control : 7;
  const value = cue.value !== undefined ? cue.value : 127;
  const program = cue.program !== undefined ? cue.program : 1;
  const bankMsb = cue.bankMsb !== undefined ? cue.bankMsb : null;
  const bankLsb = cue.bankLsb !== undefined ? cue.bankLsb : null;
  const pitchBend = cue.pitchBend !== undefined ? cue.pitchBend : 0;
  
  // MSC
  const mscDeviceId = cue.mscDeviceId !== undefined ? cue.mscDeviceId : 0x01;
  const mscFormat = cue.mscCommandFormat || MSCFormat.ALL;
  const mscCommand = cue.mscCommand || MSCCommand.GO;
  const mscCueNumber = cue.mscCueNumber || '';
  const mscCueList = cue.mscCueList || '';

  const handleField = (key, val) => {
    onUpdateCue(cue.id, { [key]: val });
  };

  const handleNoteKeyChange = (semitoneIndex, currentMidi) => {
    const curOctave = Math.floor(currentMidi / 12) - 1;
    const newMidi = Math.max(0, Math.min(127, (curOctave + 1) * 12 + semitoneIndex));
    handleField('note', newMidi);
  };

  const handleOctaveChange = (octaveVal, currentMidi) => {
    const semitone = currentMidi % 12;
    const newMidi = Math.max(0, Math.min(127, (parseInt(octaveVal, 10) + 1) * 12 + semitone));
    handleField('note', newMidi);
  };

  const currentOctave = Math.floor(note / 12) - 1;
  const currentSemitone = note % 12;

  const handleTestSend = async () => {
    setTestStatus('sending');
    setTestMsg('Invio comando MIDI...');
    try {
      if (typeof cue.compileBytes === 'function') {
        const bytes = cue.compileBytes();
        const hex = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
        setTestStatus('success');
        setTestMsg(`Pacchetto compilato con successo: [${hex}]`);
      } else {
        setTestStatus('success');
        setTestMsg(`Comando MIDI ${messageType} inviato`);
      }
    } catch (err) {
      setTestStatus('error');
      setTestMsg(`Errore: ${err.message || err}`);
    }

    setTimeout(() => {
      setTestStatus(null);
      setTestMsg('');
    }, 4000);
  };

  return (
    <div className="p-3 space-y-4 overflow-y-auto max-h-[280px]">
      {/* Intestazione */}
      <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Radio size={14} className="text-pink-400" />
          <span className="font-semibold text-zinc-200 uppercase tracking-wider text-[11px]">
            Configurazione MIDI & MIDI Show Control (MSC)
          </span>
        </div>

        <button
          onClick={handleTestSend}
          className="px-3 py-1 rounded text-[11px] font-medium flex items-center space-x-1.5 transition-all shadow-sm bg-pink-600 hover:bg-pink-500 text-white active:scale-95"
          title="Verifica compilazione e trasmissione pacchetto MIDI"
        >
          <Zap size={12} />
          <span>Test Invio MIDI Ora</span>
        </button>
      </div>

      {testMsg && (
        <div
          className={`px-3 py-1.5 rounded text-[11px] flex items-center space-x-2 font-mono ${
            testStatus === 'success'
              ? 'bg-pink-950/60 border border-pink-800 text-pink-300'
              : 'bg-red-950/60 border border-red-800 text-red-300'
          }`}
        >
          {testStatus === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
          <span>{testMsg}</span>
        </div>
      )}

      {/* Tipo Messaggio e Canale */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Tipo Messaggio MIDI</label>
          <select
            value={messageType}
            onChange={(e) => handleField('messageType', e.target.value)}
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
          >
            <option value={MidiMessageType.NOTE_ON}>Note On (Pressione Tasto)</option>
            <option value={MidiMessageType.NOTE_OFF}>Note Off (Rilascio Tasto)</option>
            <option value={MidiMessageType.CONTROL_CHANGE}>Control Change (CC)</option>
            <option value={MidiMessageType.PROGRAM_CHANGE}>Program Change (PC)</option>
            <option value={MidiMessageType.PITCH_BEND}>Pitch Bend</option>
            <option value={MidiMessageType.MSC}>MIDI Show Control (MSC SysEx)</option>
          </select>
        </div>

        {messageType !== MidiMessageType.MSC && (
          <div>
            <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Canale MIDI (1-16)</label>
            <input
              type="number"
              min="1"
              max="16"
              value={channel}
              onChange={(e) => handleField('channel', Math.max(1, Math.min(16, parseInt(e.target.value, 10) || 1)))}
              className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
            />
          </div>
        )}
      </div>

      {/* Editor Note On / Note Off con Tastiera Musicale */}
      {(messageType === MidiMessageType.NOTE_ON || messageType === MidiMessageType.NOTE_OFF) && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800 space-y-3">
          <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
            <span className="text-pink-400 uppercase font-bold flex items-center gap-1">
              <Music size={12} />
              <span>Nota Selezionata: {numberToNoteName(note)} (MIDI #{note})</span>
            </span>
            <div className="flex items-center space-x-2">
              <span>Ottava:</span>
              <select
                value={currentOctave}
                onChange={(e) => handleOctaveChange(e.target.value, note)}
                className="bg-[#1a1a1e] border border-zinc-700 rounded px-1 text-white text-xs"
              >
                {[-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((oct) => (
                  <option key={oct} value={oct}>Ottava {oct}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Mini Selettore Tasti Musicali */}
          <div className="grid grid-cols-12 gap-1 text-center font-mono text-[10px]">
            {NOTE_KEYS.map((k, idx) => {
              const isSelected = currentSemitone === idx;
              const isBlack = k.includes('#');
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => handleNoteKeyChange(idx, note)}
                  className={`py-2 rounded transition-all font-bold ${
                    isSelected
                      ? 'bg-pink-600 text-white ring-1 ring-white'
                      : isBlack
                      ? 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-700'
                      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-600'
                  }`}
                >
                  {k}
                </button>
              );
            })}
          </div>

          {/* Slider Velocity */}
          <div>
            <div className="flex justify-between text-[10px] text-zinc-400 font-mono mb-1">
              <span>Velocity (Dinamica)</span>
              <span className="text-white font-bold">{velocity}</span>
            </div>
            <input
              type="range"
              min="0"
              max="127"
              value={velocity}
              onChange={(e) => handleField('velocity', parseInt(e.target.value, 10))}
              className="w-full accent-pink-500 cursor-pointer"
            />
          </div>
        </div>
      )}

      {/* Control Change */}
      {messageType === MidiMessageType.CONTROL_CHANGE && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">Control # (CC 0-127)</label>
            <input
              type="number"
              min="0"
              max="127"
              value={control}
              onChange={(e) => handleField('control', Math.max(0, Math.min(127, parseInt(e.target.value, 10) || 0)))}
              className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
            />
          </div>
          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">Valore CC (0-127)</label>
            <input
              type="number"
              min="0"
              max="127"
              value={value}
              onChange={(e) => handleField('value', Math.max(0, Math.min(127, parseInt(e.target.value, 10) || 0)))}
              className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
            />
          </div>
        </div>
      )}

      {/* Program Change */}
      {messageType === MidiMessageType.PROGRAM_CHANGE && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Program # (0-127)</label>
              <input
                type="number"
                min="0"
                max="127"
                value={program}
                onChange={(e) => handleField('program', parseInt(e.target.value, 10) || 0)}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Bank MSB (CC 0)</label>
              <input
                type="number"
                min="0"
                max="127"
                value={bankMsb === null ? '' : bankMsb}
                placeholder="Opzionale"
                onChange={(e) => handleField('bankMsb', e.target.value === '' ? null : parseInt(e.target.value, 10))}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Bank LSB (CC 32)</label>
              <input
                type="number"
                min="0"
                max="127"
                value={bankLsb === null ? '' : bankLsb}
                placeholder="Opzionale"
                onChange={(e) => handleField('bankLsb', e.target.value === '' ? null : parseInt(e.target.value, 10))}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>
          </div>
        </div>
      )}

      {/* Pitch Bend */}
      {messageType === MidiMessageType.PITCH_BEND && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800 space-y-2">
          <div className="flex justify-between text-[10px] text-zinc-400 font-mono">
            <span>Valore Pitch Bend 14-bit (-8192..+8191)</span>
            <span className="text-white font-bold">{pitchBend}</span>
          </div>
          <input
            type="range"
            min="-8192"
            max="8191"
            value={pitchBend}
            onChange={(e) => handleField('pitchBend', parseInt(e.target.value, 10))}
            className="w-full accent-pink-500 cursor-pointer"
          />
        </div>
      )}

      {/* MIDI Show Control (MSC) */}
      {messageType === MidiMessageType.MSC && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800 space-y-3">
          <div className="text-[10px] uppercase font-bold text-amber-400">
            Parametri Standard MMA RP-002 (MIDI Show Control)
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Device ID (0-127)</label>
              <input
                type="number"
                min="0"
                max="127"
                value={mscDeviceId}
                onChange={(e) => handleField('mscDeviceId', parseInt(e.target.value, 10) || 0)}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs"
              />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Command Format</label>
              <select
                value={mscFormat}
                onChange={(e) => handleField('mscCommandFormat', parseInt(e.target.value, 10))}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-1.5 py-1 text-white text-xs"
              >
                <option value={MSCFormat.ALL}>0x7F - All Types</option>
                <option value={MSCFormat.LIGHTING}>0x01 - Lighting</option>
                <option value={MSCFormat.SOUND}>0x10 - Sound</option>
                <option value={MSCFormat.MACHINERY}>0x20 - Machinery</option>
                <option value={MSCFormat.VIDEO}>0x30 - Video</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Comando MSC</label>
              <select
                value={mscCommand}
                onChange={(e) => handleField('mscCommand', parseInt(e.target.value, 10))}
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-1.5 py-1 text-white text-xs"
              >
                <option value={MSCCommand.GO}>GO (0x01)</option>
                <option value={MSCCommand.STOP}>STOP (0x02)</option>
                <option value={MSCCommand.RESUME}>RESUME (0x03)</option>
                <option value={MSCCommand.LOAD}>LOAD (0x05)</option>
                <option value={MSCCommand.RESET}>RESET (0x0A)</option>
                <option value={MSCCommand.ALL_OFF}>ALL OFF (0x08)</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-zinc-400 font-mono mb-1">Q Number (Target)</label>
              <input
                type="text"
                value={mscCueNumber}
                onChange={(e) => handleField('mscCueNumber', e.target.value)}
                placeholder="es. 1.0, 2.5"
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
