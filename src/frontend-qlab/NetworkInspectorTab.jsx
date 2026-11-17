/**
 * NetworkInspectorTab.jsx — Scheda Inspector dedicata per NetworkCue (QLab 5)
 * 
 * Configura:
 * - Protocollo di rete: OSC, UDP plain text, TCP plain text, RAW HEX
 * - Destinazione: IP / Hostname e Porta (con default sensati per OSC 53000 o locale)
 * - Parametri OSC: Indirizzo (/live/..., /go, custom) e argomenti tipizzati
 * - Parametri RAW HEX: stringa esadecimale con validatore byte e transport UDP/TCP
 * - Parametri UDP/TCP plain text: stringa payload
 * - Tasto "Test Invio Ora" con feedback visivo e supporto bridge interno ShowSuite
 */

import React, { useState } from 'react';
import { NetworkProtocol, NetworkTransport } from '../core/control/NetworkCue.js';
import { Send, Zap, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function NetworkInspectorTab({ cue, onUpdateCue }) {
  const [testStatus, setTestStatus] = useState(null); // null | 'sending' | 'success' | 'error'
  const [testMessage, setTestMessage] = useState('');

  const protocol = cue.protocol || NetworkProtocol.OSC;
  const destination = cue.destination || '127.0.0.1';
  const port = cue.port !== undefined ? cue.port : 53000;
  const oscAddress = cue.oscAddress || '/show/action';
  const messageText = cue.messageText || '';
  const hexString = cue.hexString || '';
  const transport = cue.transport || NetworkTransport.UDP;

  const handleField = (key, val) => {
    onUpdateCue(cue.id, { [key]: val });
  };

  const handleTestTransmit = async () => {
    setTestStatus('sending');
    setTestMessage('Trasmissione in corso...');

    try {
      if (typeof cue.transmit === 'function') {
        const res = await cue.transmit();
        setTestStatus('success');
        if (res && res.viaBridge) {
          setTestMessage('Inviato con successo via Bridge OSC interno a Lightkey!');
        } else {
          setTestMessage(`Inviato con successo a ${destination}:${port} (${protocol.toUpperCase()})`);
        }
      } else {
        setTestStatus('success');
        setTestMessage(`Comando ${protocol.toUpperCase()} simulato con successo`);
      }
    } catch (err) {
      setTestStatus('error');
      setTestMessage(`Errore di trasmissione: ${err.message || err}`);
    }

    setTimeout(() => {
      setTestStatus(null);
      setTestMessage('');
    }, 4000);
  };

  return (
    <div className="p-3 space-y-4 overflow-y-auto max-h-[280px]">
      {/* Intestazione e Azione Rapida Test */}
      <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Send size={14} className="text-mac-accent" />
          <span className="font-semibold text-zinc-200 uppercase tracking-wider text-[11px]">
            Configurazione Network & Show Control
          </span>
        </div>

        <button
          onClick={handleTestTransmit}
          disabled={testStatus === 'sending'}
          className={`px-3 py-1 rounded text-[11px] font-medium flex items-center space-x-1.5 transition-all shadow-sm ${
            testStatus === 'sending'
              ? 'bg-zinc-700 text-zinc-400 cursor-wait'
              : testStatus === 'success'
              ? 'bg-emerald-600 text-white'
              : testStatus === 'error'
              ? 'bg-red-600 text-white'
              : 'bg-mac-accent hover:bg-blue-600 text-white active:scale-95'
          }`}
          title="Invia immediatamente il pacchetto per verificare la connessione"
        >
          {testStatus === 'sending' ? (
            <RefreshCw size={12} className="animate-spin" />
          ) : testStatus === 'success' ? (
            <CheckCircle2 size={12} />
          ) : testStatus === 'error' ? (
            <AlertCircle size={12} />
          ) : (
            <Zap size={12} />
          )}
          <span>{testStatus === 'sending' ? 'Invio...' : 'Test Trasmissione Ora'}</span>
        </button>
      </div>

      {testMessage && (
        <div
          className={`px-3 py-1.5 rounded text-[11px] flex items-center space-x-2 font-mono ${
            testStatus === 'success'
              ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
              : 'bg-red-950/60 border border-red-800 text-red-300'
          }`}
        >
          {testStatus === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
          <span>{testMessage}</span>
        </div>
      )}

      {/* Grid Parametri Principali */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Protocollo */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Protocollo</label>
          <select
            value={protocol}
            onChange={(e) => handleField('protocol', e.target.value)}
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-mac-accent"
          >
            <option value={NetworkProtocol.OSC}>OSC (Open Sound Control)</option>
            <option value={NetworkProtocol.UDP}>UDP Plain Text</option>
            <option value={NetworkProtocol.TCP}>TCP Stream Text</option>
            <option value={NetworkProtocol.HEX}>RAW HEX (Codici Macchina / RS232)</option>
          </select>
        </div>

        {/* Destinazione Host / IP */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Destinazione (IP / Host)</label>
          <input
            type="text"
            value={destination}
            onChange={(e) => handleField('destination', e.target.value)}
            placeholder="127.0.0.1 o 192.168.1.50"
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
          />
        </div>

        {/* Porta */}
        <div>
          <label className="block text-[10px] text-zinc-400 uppercase font-mono mb-1">Porta Destinazione</label>
          <input
            type="number"
            min="1"
            max="65535"
            value={port}
            onChange={(e) => handleField('port', parseInt(e.target.value, 10) || 0)}
            className="w-full bg-[#121214] border border-[#2d2d38] rounded px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-mac-accent"
          />
        </div>
      </div>

      {/* Sezione Specifica in base al protocollo */}
      {protocol === NetworkProtocol.OSC && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800/80 space-y-3">
          <div className="text-[10px] uppercase font-bold text-blue-400 flex items-center justify-between">
            <span>Dettagli Messaggio OSC</span>
            <span className="text-zinc-500 font-normal lowercase">compatibile con QLab 5 & Lightkey bridge</span>
          </div>

          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">OSC Address</label>
            <input
              type="text"
              value={oscAddress}
              onChange={(e) => handleField('oscAddress', e.target.value)}
              placeholder="/live/grandMaster o /cue/1/start"
              className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-emerald-400 font-mono text-xs focus:outline-none focus:border-mac-accent"
            />
          </div>

          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">
              Preset Rapidi Comandi Interni Lightkey
            </label>
            <div className="flex flex-wrap gap-1.5">
              {[
                { label: 'Blackout ON', addr: '/live/blackout', args: [1] },
                { label: 'Blackout OFF', addr: '/live/blackout', args: [0] },
                { label: 'Grand Master 100%', addr: '/live/grandMaster', args: [1.0] },
                { label: 'Grand Master 50%', addr: '/live/grandMaster', args: [0.5] },
                { label: 'Speed Master 1x', addr: '/live/speedMaster', args: [1.0] },
                { label: 'Lightkey Cue GO', addr: '/live/cue/go', args: [] },
                { label: 'Trigger Grid Cell 0', addr: '/live/cell/0/trigger', args: [] },
              ].map((p, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    handleField('oscAddress', p.addr);
                    handleField('oscArguments', p.args);
                  }}
                  className="px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-[10px] font-mono text-zinc-300 rounded border border-zinc-700 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {protocol === NetworkProtocol.HEX && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800/80 space-y-3">
          <div className="text-[10px] uppercase font-bold text-amber-400 flex items-center justify-between">
            <span>Payload RAW HEX Byte Stream</span>
            <div className="flex items-center space-x-2">
              <span className="text-zinc-400 text-[10px]">Trasporto:</span>
              <select
                value={transport}
                onChange={(e) => handleField('transport', e.target.value)}
                className="bg-[#1a1a1e] border border-zinc-700 rounded px-1.5 py-0.5 text-white text-[10px]"
              >
                <option value={NetworkTransport.UDP}>UDP Datagram</option>
                <option value={NetworkTransport.TCP}>TCP Stream</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[10px] text-zinc-400 font-mono mb-1">
              Byte Esadecimali (es. "01 03 00 00 00 02 C4 0B" o "0xAA, 0xBB")
            </label>
            <input
              type="text"
              value={hexString}
              onChange={(e) => handleField('hexString', e.target.value)}
              placeholder="01 02 03 04 05"
              className="w-full bg-[#1a1a1e] border border-zinc-700 rounded px-2 py-1 text-amber-300 font-mono text-xs focus:outline-none focus:border-mac-accent"
            />
          </div>
        </div>
      )}

      {(protocol === NetworkProtocol.UDP || protocol === NetworkProtocol.TCP) && (
        <div className="bg-[#121214] p-3 rounded border border-zinc-800/80 space-y-2">
          <div className="text-[10px] uppercase font-bold text-purple-400">
            <span>Payload Testo Plain Text ({protocol.toUpperCase()})</span>
          </div>
          <textarea
            rows={2}
            value={messageText}
            onChange={(e) => handleField('messageText', e.target.value)}
            placeholder="Messaggio stringa, sequenza di controllo o comando ASCII (CR/LF opzionale)..."
            className="w-full bg-[#1a1a1e] border border-zinc-700 rounded p-2 text-zinc-200 font-mono text-xs focus:outline-none focus:border-mac-accent resize-none"
          />
        </div>
      )}
    </div>
  );
}
