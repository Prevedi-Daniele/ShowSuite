import React, { useState, useEffect } from 'react';
import MacModal from './MacModal';
import MacButton from './MacButton';
import MacToggle from './MacToggle';
import MacSegmentedControl from './MacSegmentedControl';
import showSuiteBridge from '../ShowSuiteBridge.js';
import { Sliders, Volume2, Network, Cpu, Check, RefreshCw, Zap } from 'lucide-react';

export default function GlobalSettingsModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('dmx');

  // Stato DMX
  const [dmxInterface, setDmxInterface] = useState('enttec_pro');
  const [dmxRefreshRate, setDmxRefreshRate] = useState(30);
  const [artnetSubnet, setArtnetSubnet] = useState(0);
  const [artnetUniverse, setArtnetUniverse] = useState(0);
  const [comPort, setComPort] = useState('COM3');

  // Stato Audio & MIDI
  const [audioDevice, setAudioDevice] = useState('default');
  const [bufferSize, setBufferSize] = useState('256');
  const [sampleRate, setSampleRate] = useState('48000');
  const [midiInput, setMidiInput] = useState('none');

  // Stato Network & OSC
  const [oscReceivePort, setOscReceivePort] = useState(53000);
  const [oscTransmitPort, setOscTransmitPort] = useState(53001);
  const [internalBridge, setInternalBridge] = useState(() => showSuiteBridge.isEnabled());
  const [routingStats, setRoutingStats] = useState(() => showSuiteBridge.routingHistory.length);

  // Stato Generale
  const [startupMode, setStartupMode] = useState('suite');

  useEffect(() => {
    setInternalBridge(showSuiteBridge.isEnabled());
    setRoutingStats(showSuiteBridge.routingHistory.length);
  }, [isOpen]);

  const handleApplySettings = async () => {
    // Applica configurazione del Bridge OSC Interno
    showSuiteBridge.setEnabled(internalBridge);

    if (window.showsuite?.dmx) {
      let driverOpts = {};
      if (dmxInterface === 'enttec_pro') {
        driverOpts = { port: comPort };
      } else if (dmxInterface === 'ftdi_opendmx' || dmxInterface === 'freestyler_custom') {
        driverOpts = { port: comPort };
      } else if (dmxInterface === 'artnet') {
        driverOpts = { subnet: artnetSubnet, universe: artnetUniverse, host: '255.255.255.255' };
      } else if (dmxInterface === 'sacn') {
        driverOpts = { universe: artnetUniverse + 1 };
      }

      await window.showsuite.dmx.setDriver(dmxInterface, driverOpts);
      await window.showsuite.dmx.setRefreshRate(dmxRefreshRate);
    }
    onClose();
  };

  const tabs = [
    { id: 'dmx', label: 'DMX Hardware', icon: Sliders },
    { id: 'audio', label: 'Audio & MIDI', icon: Volume2 },
    { id: 'network', label: 'Rete & OSC', icon: Network },
    { id: 'general', label: 'Generale', icon: Cpu },
  ];

  return (
    <MacModal
      isOpen={isOpen}
      onClose={onClose}
      title="Preferenze Globali di ShowSuite"
      width="max-w-3xl"
      footer={
        <>
          <MacButton variant="default" onClick={onClose}>
            Annulla
          </MacButton>
          <MacButton variant="primary" icon={Check} onClick={handleApplySettings}>
            Salva e Applica
          </MacButton>
        </>
      }
    >
      <div className="flex flex-col space-y-4">
        {/* Tab Selector */}
        <div className="flex justify-center border-b border-mac-border/50 pb-3">
          <MacSegmentedControl
            options={tabs}
            value={activeTab}
            onChange={setActiveTab}
            size="md"
          />
        </div>

        {/* Tab 1: DMX Hardware (FreeStyler style multi-interface) */}
        {activeTab === 'dmx' && (
          <div className="space-y-4">
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800">
              <label className="block text-xs font-semibold text-zinc-200 mb-1">
                Interfaccia DMX Primaria
              </label>
              <p className="text-[11px] text-zinc-400 mb-2">
                ShowSuite supporta sia interfacce professionali che adattatori economici/custom (stile FreeStyler).
              </p>
              <select
                value={dmxInterface}
                onChange={(e) => setDmxInterface(e.target.value)}
                className="w-full bg-[#161619] border border-zinc-700 rounded-md px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-mac-accent"
              >
                <optgroup label="USB / Seriale Hardware">
                  <option value="enttec_pro">Enttec DMX USB Pro / DMXking ultraDMX / Eurolite USB-DMX512 Pro</option>
                  <option value="ftdi_opendmx">FTDI Open DMX (cavo USB RS-485 generico, software break timing)</option>
                  <option value="freestyler_custom">Adattatore Seriale Custom FreeStyler / COM Port (250 kBaud)</option>
                  <option value="dmx4all">DMX4ALL Mini-USB DMX</option>
                  <option value="velleman">Velleman K8062 / VM116</option>
                </optgroup>
                <optgroup label="Ethernet / Protocolli IP">
                  <option value="artnet">Art-Net v4 (Broadcast / Unicast UDP 6454)</option>
                  <option value="sacn">Streaming ACN (ANSI E1.31 Multicast / Unicast)</option>
                </optgroup>
              </select>
            </div>

            {/* Dettagli configurazione in base al tipo */}
            {dmxInterface.includes('ftdi') || dmxInterface.includes('freestyler') ? (
              <div className="grid grid-cols-2 gap-3 p-3 bg-zinc-900/40 rounded-lg border border-zinc-800/80">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Porta COM / Seriale</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={comPort}
                      onChange={(e) => setComPort(e.target.value)}
                      className="flex-1 bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                    />
                    <MacButton size="sm" icon={RefreshCw} title="Scansiona porte COM" />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Baud Rate Seriale</label>
                  <select className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white">
                    <option value="250000">250,000 baud (DMX standard)</option>
                    <option value="115200">115,200 baud</option>
                    <option value="57600">57,600 baud</option>
                  </select>
                </div>
              </div>
            ) : null}

            {dmxInterface.startsWith('artnet') && (
              <div className="grid grid-cols-2 gap-3 p-3 bg-zinc-900/40 rounded-lg border border-zinc-800/80">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Art-Net Subnet (0-15)</label>
                  <input
                    type="number"
                    min="0"
                    max="15"
                    value={artnetSubnet}
                    onChange={(e) => setArtnetSubnet(parseInt(e.target.value) || 0)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Art-Net Universe (0-15)</label>
                  <input
                    type="number"
                    min="0"
                    max="15"
                    value={artnetUniverse}
                    onChange={(e) => setArtnetUniverse(parseInt(e.target.value) || 0)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  />
                </div>
              </div>
            )}

            <div className="p-3 bg-zinc-900/40 rounded-lg border border-zinc-800/80 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-zinc-300">DMX Output Refresh Rate</span>
                <p className="text-[11px] text-zinc-400">Consigliato: 30-40 Hz per fari motorizzati e dimmer analogici.</p>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="range"
                  min="20"
                  max="44"
                  value={dmxRefreshRate}
                  onChange={(e) => setDmxRefreshRate(parseInt(e.target.value))}
                  className="w-28 accent-mac-accent cursor-pointer"
                />
                <span className="font-mono text-xs w-8 text-right text-mac-accent">{dmxRefreshRate} Hz</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Audio & MIDI */}
        {activeTab === 'audio' && (
          <div className="space-y-4">
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-zinc-200 mb-1">Dispositivo di Uscita Audio (Master)</label>
                <select
                  value={audioDevice}
                  onChange={(e) => setAudioDevice(e.target.value)}
                  className="w-full bg-[#161619] border border-zinc-700 rounded-md px-2.5 py-1.5 text-xs text-white"
                >
                  <option value="default">Predefinito di Sistema (WASAPI / ALSA)</option>
                  <option value="multichannel">Interfaccia Multicanale ASIO / CoreAudio / JACK (8 In / 8 Out)</option>
                  <option value="virtual">Virtual Audio Cable / Dante Virtual Soundcard</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Buffer Size (Latenza)</label>
                  <select
                    value={bufferSize}
                    onChange={(e) => setBufferSize(e.target.value)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  >
                    <option value="64">64 samples (1.4 ms - Ultra Low Latency)</option>
                    <option value="128">128 samples (2.9 ms)</option>
                    <option value="256">256 samples (5.8 ms - Consigliato)</option>
                    <option value="512">512 samples (11.6 ms - Massima stabilità)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Sample Rate</label>
                  <select
                    value={sampleRate}
                    onChange={(e) => setSampleRate(e.target.value)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  >
                    <option value="44100">44,100 Hz (CD Audio)</option>
                    <option value="48000">48,000 Hz (Broadcast / Teatrale)</option>
                    <option value="96000">96,000 Hz (High Resolution)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800">
              <label className="block text-xs font-semibold text-zinc-200 mb-1">Porta MIDI In (Show Control & Triggers)</label>
              <select
                value={midiInput}
                onChange={(e) => setMidiInput(e.target.value)}
                className="w-full bg-[#161619] border border-zinc-700 rounded-md px-2.5 py-1.5 text-xs text-white"
              >
                <option value="none">Nessuna porta MIDI attiva</option>
                <option value="all">Tutti gli ingressi MIDI (Omni Mode)</option>
                <option value="usb_midi">USB MIDI Keyboard / Controller</option>
              </select>
            </div>
          </div>
        )}

        {/* Tab 3: Rete & OSC */}
        {activeTab === 'network' && (
          <div className="space-y-4">
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-3">
              <h4 className="text-xs font-semibold text-zinc-200">Protocollo OSC (Open Sound Control)</h4>
              <p className="text-[11px] text-zinc-400">
                Compatibile al 100% con il dizionario comandi di QLab e le API esterne di Lightkey.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Porta Ricezione (In)</label>
                  <input
                    type="number"
                    value={oscReceivePort}
                    onChange={(e) => setOscReceivePort(parseInt(e.target.value) || 53000)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  />
                  <span className="text-[10px] text-zinc-500">Default QLab: 53000</span>
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Porta Trasmissione (Out)</label>
                  <input
                    type="number"
                    value={oscTransmitPort}
                    onChange={(e) => setOscTransmitPort(parseInt(e.target.value) || 53001)}
                    className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                  />
                  <span className="text-[10px] text-zinc-500">Default QLab: 53001</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-3">
              <MacToggle
                checked={internalBridge}
                onChange={setInternalBridge}
                label="Bridge OSC Interno ShowSuite (In-Process Routing)"
                description="Consente alle Cue QLab (Network Cues /live/...) di triggerare istantaneamente preset, fader e scene di Lightkey all'interno dello stesso processo a latenza zero."
              />

              <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <Zap className={`w-3.5 h-3.5 ${internalBridge ? 'text-amber-400' : 'text-zinc-500'}`} />
                  Stato Routing In-Process:
                  <strong className={internalBridge ? 'text-green-400' : 'text-zinc-500'}>
                    {internalBridge ? 'Attivo (Zero-Latency)' : 'Disattivato'}
                  </strong>
                </span>
                <span className="font-mono text-zinc-500">
                  {routingStats} comandi instradati
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Generale */}
        {activeTab === 'general' && (
          <div className="space-y-4">
            <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-2">
              <label className="block text-xs font-semibold text-zinc-200">Modalità di Avvio Predefinita</label>
              <select
                value={startupMode}
                onChange={(e) => setStartupMode(e.target.value)}
                className="w-full bg-[#161619] border border-zinc-700 rounded-md px-2.5 py-1.5 text-xs text-white"
              >
                <option value="suite">ShowSuite Completo (Switcher Lightkey & QLab)</option>
                <option value="lightkey">Solo Lightkey (DMX Lighting Console)</option>
                <option value="qlab">Solo QLab (Audio/Video Show Controller)</option>
              </select>
              <p className="text-[11px] text-zinc-400 pt-1">
                Nota: Puoi sempre avviare una specifica sezione da terminale usando il parametro <code className="text-mac-accent">--standalone-lightkey</code> o <code className="text-qlab-accent">--standalone-qlab</code>.
              </p>
            </div>
          </div>
        )}
      </div>
    </MacModal>
  );
}
