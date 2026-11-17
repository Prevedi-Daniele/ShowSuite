/**
 * TimecodeInspectorTab.jsx — Scheda Inspector dedicata per TimecodeCue (QLab 5)
 * 
 * Configura:
 * - Formato output: MTC (MIDI Timecode) o LTC (Audio Linear Timecode SMPTE 12M)
 * - Frame rate: 24, 25, 29.97 DF, 30 fps
 * - Start Timecode (HH:MM:SS:FF)
 * - Durata emissione timecode
 * - Calcolo preview frame correnti
 * - Tasto "Test Emetti Timecode"
 */

import React, { useState } from 'react';
import { TimecodeOutputFormat } from '../core/timecode/TimecodeCue.js';
import { SMPTEFrameRate } from '../core/timecode/SMPTETimecode.js';
import { Clock, Play, CheckCircle2, Zap, Radio, Volume2 } from 'lucide-react';

export default function TimecodeInspectorTab({ cue, onUpdateCue }) {
  const [testActive, setTestActive] = useState(false);
  const [currentTcPreview, setCurrentTcPreview] = useState(cue.startTimecode ? cue.startTimecode.toString() : '01:00:00:00');

  const outputFormat = cue.outputFormat || TimecodeOutputFormat.MTC;
  const fps = cue.fps || SMPTEFrameRate.FPS_25;
  const isDropFrame = cue.isDropFrame !== undefined ? cue.isDropFrame : (fps === 29.97);
  const startTimecodeStr = cue.startTimecode ? cue.startTimecode.toString() : '01:00:00:00';
  const destination = cue.destination || 'default';

  const handleField = (key, val) => {
    onUpdateCue(cue.id, { [key]: val });
  };

  const handleFpsChange = (newFpsVal) => {
    const numericFps = parseFloat(newFpsVal);
    const df = numericFps === 29.97;
    onUpdateCue(cue.id, {
      fps: numericFps,
      isDropFrame: df,
    });
  };

  const handleToggleTest = () => {
    if (!testActive) {
      setTestActive(true);
      if (typeof cue.start === 'function' && cue.state !== 'running') {
        cue.start();
      }
    } else {
      setTestActive(false);
      if (typeof cue.stop === 'function') {
        cue.stop();
      }
    }
  };

  return (
    <div className="p-3 space-y-4 overflow-y-auto max-h-[280px]">
      {/* Intestazione */}
      <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Clock size={14} className="text-amber-400" />
          <span className="font-semibold text-zinc-200 uppercase tracking-wider text-[11px]">
            Generatore & Output Timecode (SMPTE 12M)
          </span>
        </div>

        <button
          onClick={handleToggleTest}
          className={`px-3 py-1 rounded text-[11px] font-medium flex items-center space-x-1.5 transition-all shadow-sm ${
            testActive
              ? 'bg-amber-600 hover:bg-amber-500 text-white animate-pulse'
              : 'bg-zinc-700 hover:bg-zinc-600 text-white'
          }`}
          title="Avvia o ferma l'emissione di test locale del timecode"
        >
          {testActive ? <Zap size={12} /> : <Play size={12} />}
          <span>{testActive ? 'Emissione Attiva (Stop)' : 'Test Play Timecode'}</span>
        </button>
      </div>

      {/* Grid Parametri Principali */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Formato di Trasmissione */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Formato Output</label>
          <select
            value={outputFormat}
            onChange={(e) => handleField('outputFormat', e.target.value)}
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
          >
            <option value={TimecodeOutputFormat.MTC}>MTC (MIDI Timecode)</option>
            <option value={TimecodeOutputFormat.LTC}>LTC (Audio SMPTE 12M Line)</option>
          </select>
        </div>

        {/* Frame Rate */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Frame Rate (FPS)</label>
          <select
            value={fps}
            onChange={(e) => handleFpsChange(e.target.value)}
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
          >
            <option value={24}>24 fps (Cinema / Film)</option>
            <option value={25}>25 fps (EBU / Broadcast PAL)</option>
            <option value={29.97}>29.97 fps (NTSC Drop-Frame)</option>
            <option value={30}>30 fps (SMPTE Standard)</option>
          </select>
        </div>

        {/* Drop Frame Flag */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Modalità Drop Frame</label>
          <div className="flex items-center space-x-2 h-7 px-2 bg-[#121214] border border-[#2d2d38] rounded">
            <input
              type="checkbox"
              id="tc-df-toggle"
              checked={isDropFrame}
              onChange={(e) => handleField('isDropFrame', e.target.checked)}
              className="rounded bg-zinc-800 border-zinc-700 text-amber-500"
            />
            <label htmlFor="tc-df-toggle" className="text-xs text-zinc-300 font-mono cursor-pointer">
              {isDropFrame ? 'Drop-Frame (;)' : 'Non-Drop Frame (:)'}
            </label>
          </div>
        </div>
      </div>

      {/* Start Timecode & Destination */}
      <div className="bg-[#121214] p-3 rounded border border-zinc-800 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Start SMPTE Timecode */}
          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">
              Start Timecode (HH:MM:SS:FF)
            </label>
            <input
              type="text"
              value={startTimecodeStr}
              onChange={(e) => handleField('startTimecode', e.target.value)}
              placeholder="01:00:00:00"
              className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-amber-400 font-mono text-sm font-bold tracking-wider focus:outline-none focus:border-mac-accent"
            />
          </div>

          {/* Destinazione / Porta */}
          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">
              {outputFormat === TimecodeOutputFormat.MTC ? 'Interfaccia MIDI di Uscita' : 'Canale Audio LTC di Linea'}
            </label>
            <div className="flex items-center space-x-2">
              {outputFormat === TimecodeOutputFormat.MTC ? (
                <Radio size={14} className="text-pink-400 shrink-0" />
              ) : (
                <Volume2 size={14} className="text-emerald-400 shrink-0" />
              )}
              <input
                type="text"
                value={destination}
                onChange={(e) => handleField('destination', e.target.value)}
                placeholder="default o nome dispositivo..."
                className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
              />
            </div>
          </div>
        </div>

        {/* Display Digitale Timecode di Anteprima */}
        <div className="p-2.5 bg-black/80 rounded border border-zinc-800 flex items-center justify-between">
          <div className="text-[10px] uppercase font-mono text-zinc-400">
            <span>Formato Timecode Attivo:</span>
            <span className="ml-2 px-1.5 py-0.5 rounded bg-zinc-800 text-amber-400 font-bold">
              {outputFormat.toUpperCase()} @ {fps} fps {isDropFrame ? '(DF)' : '(NDF)'}
            </span>
          </div>

          <div className="text-lg font-mono font-black text-amber-400 tracking-widest">
            {cue.getCurrentTimecode ? cue.getCurrentTimecode().toString() : startTimecodeStr}
          </div>
        </div>
      </div>
    </div>
  );
}
