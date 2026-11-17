/**
 * ShowControlManager.js — Controller Centrale di Rete e Show Control per ShowSuite
 * 
 * Unifica e orchestra l'intero ecosistema di comunicazione per lo spettacolo:
 * 1. Server & Client OSC con dizionario completo compatibile QLab 5 e Lightkey
 * 2. Gestione e instradamento Network Cues (OSC, UDP, TCP, HEX raw)
 * 3. Gestione e instradamento MIDI Cues (Note On/Off, CC, PC, Pitch Bend e MSC)
 * 4. Ricevitore MIDI Show Control (MSC): comandi GO, STOP, RESUME, LOAD, RESET
 *    mappati automaticamente su CueScheduler e LiveController
 * 5. Mappature trigger MIDI (Note/CC -> Azioni Show)
 */

import OSCController from './OSCController.js';
import OscPacket from './OscPacket.js';
import NetworkCue, { NetworkProtocol, NetworkTransport } from './NetworkCue.js';
import MidiCue, {
  MidiMessageType,
  MSCFormat,
  MSCCommand,
  noteNameToNumber,
  numberToNoteName,
} from './MidiCue.js';
import {
  SMPTETimecode,
  SMPTEFrameRate,
  MTCDecoder,
  LTCDecoder,
  TimecodeChaser,
  TimecodeTriggerAction,
} from '../timecode/index.js';

export default class ShowControlManager {
  constructor(options = {}) {
    // Riferimenti ai motori di ShowSuite
    this.cueScheduler = options.cueScheduler || null;
    this.liveController = options.liveController || null;
    this.cueEngine = options.cueEngine || null;

    // Configurazione MSC Locale
    this.mscDeviceId = options.mscDeviceId !== undefined ? options.mscDeviceId : 1; // Device ID proprio (0-111)
    this.mscFormat = options.mscFormat !== undefined ? options.mscFormat : MSCFormat.ALL;

    // Controller OSC
    this.osc = new OSCController({
      listenPort: options.oscListenPort || 53000,
      listenHost: options.oscListenHost || '0.0.0.0',
      targetHost: options.oscTargetHost || '127.0.0.1',
      targetPort: options.oscTargetPort || 53000,
      context: {
        cueScheduler: this.cueScheduler,
        liveController: this.liveController,
        cueEngine: this.cueEngine,
      },
    });

    // Mappe trigger MIDI personalizzati (es. "note_on:1:60" -> callback o azione)
    this.midiTriggers = new Map();

    // Timecode Engine (MTC, LTC, Timecode Chaser)
    this.timecodeChaser = new TimecodeChaser({
      cueScheduler: this.cueScheduler,
      fps: options.timecodeFps || SMPTEFrameRate.FPS_25,
      isDropFrame: options.timecodeDropFrame || false,
    });

    this.mtcDecoder = new MTCDecoder({
      onTimecode: (tc) => {
        this.timecodeChaser.updateIncomingTimecode(tc);
      },
    });

    this.ltcDecoder = new LTCDecoder({
      expectedFps: options.timecodeFps || SMPTEFrameRate.FPS_25,
      sampleRate: options.audioSampleRate || 48000,
      onTimecode: (tc) => {
        this.timecodeChaser.updateIncomingTimecode(tc);
      },
    });

    // Log trasmissioni recenti
    this.networkHistory = [];
    this.midiHistory = [];

    // Setup listener OSC
    this.osc.receiver.on('command', (evt) => {
      this.networkHistory.push({
        type: 'osc_rx',
        address: evt.address,
        args: evt.args,
        result: evt.result,
        timestamp: Date.now(),
      });
      if (this.networkHistory.length > 100) this.networkHistory.shift();
    });
  }

  // ─── Collegamento Motori ────────────────────────────────────────

  attachCueScheduler(cueScheduler) {
    this.cueScheduler = cueScheduler;
    this.osc.setContext({ cueScheduler });
    this.timecodeChaser.attachCueScheduler(cueScheduler);
  }

  attachLiveController(liveController) {
    this.liveController = liveController;
    this.osc.setContext({ liveController });
  }

  attachCueEngine(cueEngine) {
    this.cueEngine = cueEngine;
    this.osc.setContext({ cueEngine });
  }

  // ─── Controllo Ciclo di Vita Server ────────────────────────────

  async start() {
    await this.osc.start();
    return true;
  }

  stop() {
    this.osc.stop();
  }

  // ─── Invio Trasmissioni di Rete (OSC, UDP, TCP, HEX) ────────────

  async sendOsc(host, port, address, args = [], types = null) {
    const bytes = await this.osc.send(host, port, address, args, types);
    this.networkHistory.push({
      type: 'osc_tx',
      host,
      port,
      address,
      args,
      timestamp: Date.now(),
    });
    return bytes;
  }

  async sendUdp(host, port, data) {
    const bytes = data instanceof Uint8Array ? data : new TextEncoder().encode(String(data));
    this.networkHistory.push({
      type: 'udp_tx',
      host,
      port,
      bytes,
      timestamp: Date.now(),
    });

    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const dgram = await import('dgram');
        const client = dgram.createSocket('udp4');
        return new Promise((resolve) => {
          client.send(Buffer.from(bytes), 0, bytes.length, port, host, (err) => {
            try { client.close(); } catch (e) {}
            resolve(bytes);
          });
        });
      }
    } catch (e) {}

    return bytes;
  }

  async sendTcp(host, port, data) {
    const bytes = data instanceof Uint8Array ? data : new TextEncoder().encode(String(data));
    this.networkHistory.push({
      type: 'tcp_tx',
      host,
      port,
      bytes,
      timestamp: Date.now(),
    });

    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const net = await import('net');
        return new Promise((resolve) => {
          const client = new net.Socket();
          client.connect(port, host, () => {
            client.write(Buffer.from(bytes));
            client.end();
            resolve(bytes);
          });
          client.on('error', () => {
            client.destroy();
            resolve(bytes);
          });
        });
      }
    } catch (e) {}

    return bytes;
  }

  async sendHex(host, port, hexString, transport = NetworkTransport.UDP) {
    const bytes = NetworkCue.hexStringToBytes(hexString);
    if (transport === NetworkTransport.TCP) {
      return this.sendTcp(host, port, bytes);
    } else {
      return this.sendUdp(host, port, bytes);
    }
  }

  // ─── Invio Messaggi MIDI ────────────────────────────────────────

  async sendMidi(rawBytes, port = 'default') {
    const bytes = rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes);
    this.midiHistory.push({
      type: 'midi_tx',
      port,
      bytes,
      parsed: MidiCue.parseBytes(bytes),
      timestamp: Date.now(),
    });
    if (this.midiHistory.length > 100) this.midiHistory.shift();

    return bytes;
  }

  // ─── Ricezione ed Elaborazione Messaggi MIDI in Ingresso ────────

  /**
   * Elabora un pacchetto MIDI ricevuto (Note, CC, PC, SysEx MSC o MTC Timecode)
   * e innesca le azioni corrispondenti su QLab / Lightkey.
   */
  processIncomingMidi(rawBytes) {
    const bytes = rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes);
    if (!bytes || bytes.length === 0) return { handled: false, error: 'Byte MIDI non validi' };

    // 0. Gestione MIDI Timecode MTC (Quarter Frame 0xF1 o Full Frame SysEx F0 7F ... 01 01)
    if (bytes[0] === 0xF1 || (bytes[0] === 0xF0 && bytes.length >= 10 && bytes[1] === 0x7F && bytes[3] === 0x01 && bytes[4] === 0x01)) {
      const tc = this.mtcDecoder.processMidi(bytes);
      this.midiHistory.push({
        type: 'mtc_rx',
        bytes,
        timecode: tc ? tc.toString() : null,
        timestamp: Date.now(),
      });
      return { handled: true, isMtc: true, timecode: tc };
    }

    const parsed = MidiCue.parseBytes(rawBytes);
    if (!parsed) return { handled: false, error: 'Byte MIDI non validi' };

    this.midiHistory.push({
      type: 'midi_rx',
      bytes: rawBytes,
      parsed,
      timestamp: Date.now(),
    });

    // 1. Gestione MIDI Show Control (MSC)
    if (parsed.type === MidiMessageType.MSC) {
      return this._handleIncomingMsc(parsed);
    }

    // 2. Gestione Note On / Control Change tramite MIDI Triggers registrati
    if (parsed.type === MidiMessageType.NOTE_ON && parsed.velocity > 0) {
      const triggerKey = `note_on:${parsed.channel}:${parsed.note}`;
      if (this.midiTriggers.has(triggerKey)) {
        const handler = this.midiTriggers.get(triggerKey);
        handler(parsed, this);
        return { handled: true, trigger: triggerKey };
      }
    } else if (parsed.type === MidiMessageType.CONTROL_CHANGE) {
      const triggerKey = `cc:${parsed.channel}:${parsed.controlNumber}`;
      if (this.midiTriggers.has(triggerKey)) {
        const handler = this.midiTriggers.get(triggerKey);
        handler(parsed, this);
        return { handled: true, trigger: triggerKey };
      }
    }

    return { handled: false, parsed };
  }

  /**
   * Elabora campioni audio PCM provenienti da un canale d'ingresso audio LTC
   * @param {Float32Array|Int16Array|Array<number>} samples 
   */
  processIncomingLtcAudio(samples) {
    const decodedFrames = this.ltcDecoder.processAudio(samples);
    return decodedFrames;
  }

  /**
   * Mappa un trigger temporizzato da Timecode (SMPTE) su una Cue
   * @param {string} cueId ID o numero della cue
   * @param {string|SMPTETimecode} timecode Target timecode (es. "01:00:15:00")
   * @param {string} [action='start'] Azione ('start', 'stop', 'load', 'pause')
   */
  mapTimecodeTrigger(cueId, timecode, action = TimecodeTriggerAction.START) {
    return this.timecodeChaser.registerCueTrigger(cueId, timecode, action);
  }

  /**
   * Loop di tick temporale per il freewheeling e timecode chasing
   */
  tick(dt = 0.016) {
    this.timecodeChaser.tick(dt);
  }

  /**
   * Interpreta i comandi MSC conformi a RP-002 e li instrada al CueScheduler
   */
  _handleIncomingMsc(msc) {
    // Verifica corrispondenza Device ID (accetta proprio ID, oppure All-Call 0x7F)
    const isTargetDevice = (msc.deviceId === 0x7F) || (msc.deviceId === this.mscDeviceId);
    if (!isTargetDevice) {
      return { handled: false, ignored: 'deviceId_mismatch' };
    }

    // Verifica compatibilità categoria di comando
    const isTargetFormat = (msc.commandFormat === MSCFormat.ALL) ||
                           (this.mscFormat === MSCFormat.ALL) ||
                           (msc.commandFormat === this.mscFormat);
    if (!isTargetFormat) {
      return { handled: false, ignored: 'format_mismatch' };
    }

    if (!this.cueScheduler) {
      return { handled: false, error: 'CueScheduler non configurato' };
    }

    const { command, cueNumber } = msc;

    switch (command) {
      case MSCCommand.GO: {
        if (cueNumber) {
          const cue = this.cueScheduler.findCueByNumber(cueNumber);
          if (cue) {
            this.cueScheduler.startCue(cue);
            return { handled: true, action: 'msc_go_cue', cueNumber };
          }
          return { handled: false, error: `Cue MSC "${cueNumber}" non trovata` };
        } else {
          this.cueScheduler.go();
          return { handled: true, action: 'msc_go' };
        }
      }

      case MSCCommand.STOP: {
        if (cueNumber) {
          const cue = this.cueScheduler.findCueByNumber(cueNumber);
          if (cue) {
            cue.stop();
            this.cueScheduler.runningCues.delete(cue);
            this.cueScheduler.emit('cueStopped', cue);
            return { handled: true, action: 'msc_stop_cue', cueNumber };
          }
        } else {
          this.cueScheduler.stop();
          return { handled: true, action: 'msc_stop' };
        }
        break;
      }

      case MSCCommand.RESUME: {
        if (cueNumber) {
          const cue = this.cueScheduler.findCueByNumber(cueNumber);
          if (cue) cue.resume();
        } else {
          this.cueScheduler.resume();
        }
        return { handled: true, action: 'msc_resume' };
      }

      case MSCCommand.LOAD: {
        if (cueNumber) {
          const cue = this.cueScheduler.findCueByNumber(cueNumber);
          if (cue) cue.load();
        } else {
          const standby = this.cueScheduler.getStandbyCue();
          if (standby) standby.load();
        }
        return { handled: true, action: 'msc_load' };
      }

      case MSCCommand.RESET: {
        this.cueScheduler.stop();
        this.cueScheduler.setStandbyIndex(0);
        return { handled: true, action: 'msc_reset' };
      }

      case MSCCommand.ALL_OFF: {
        this.cueScheduler.hardStop();
        if (this.liveController) {
          this.liveController.setBlackout(true);
        }
        return { handled: true, action: 'msc_all_off' };
      }
    }

    return { handled: false, command };
  }

  // ─── Registrazione Trigger MIDI ────────────────────────────────

  /**
   * Mappa una nota MIDI (Note On) a un'azione
   * @param {number} channel Canale 1-16
   * @param {number|string} note Numero nota (0-127) o nome (es. 'C4')
   * @param {Function} handler Callback da invocare
   */
  mapMidiNote(channel, note, handler) {
    const noteNum = noteNameToNumber(note);
    const key = `note_on:${channel}:${noteNum}`;
    this.midiTriggers.set(key, handler);
  }

  /**
   * Mappa un Control Change MIDI a un'azione
   * @param {number} channel Canale 1-16
   * @param {number} controlNumber Numero controller (0-127)
   * @param {Function} handler Callback da invocare (riceve parsed, manager)
   */
  mapMidiCC(channel, controlNumber, handler) {
    const key = `cc:${channel}:${controlNumber}`;
    this.midiTriggers.set(key, handler);
  }
}
