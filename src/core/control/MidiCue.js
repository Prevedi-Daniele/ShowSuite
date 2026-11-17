/**
 * MidiCue.js — MIDI Cues & MIDI Show Control (MSC) per ShowSuite (conforme a QLab 5)
 * 
 * Supporta:
 * 1. Note On (canale 1-16, nota 0-127 o nome 'C4', velocity 0-127)
 * 2. Note Off (canale 1-16, nota 0-127, velocity 0-127)
 * 3. Control Change / CC (canale 1-16, control 0-127, value 0-127)
 * 4. Program Change / PC (canale 1-16, program 0-127, Bank MSB/LSB opzionale)
 * 5. Pitch Bend (canale 1-16, valore 14-bit -8192..+8191 o 0..16383)
 * 6. MIDI Show Control (MSC) standard MMA RP-002:
 *    - SysEx: F0 7F <deviceId> 02 <commandFormat> <command> [Q_number 00 Q_list 00 Q_path] F7
 *    - Comandi: GO, STOP, RESUME, TIMED_GO, LOAD, SET, FIRE, ALL_OFF, RESTORE, RESET, GO_OFF
 *    - Categorie: Lighting (0x01), Sound (0x10), Machinery (0x20), Video (0x30), All (0x7F)
 */

import BaseCue from '../qlab/BaseCue.js';
import { CueType } from '../qlab/CueTypes.js';

export const MidiMessageType = {
  NOTE_ON: 'note_on',
  NOTE_OFF: 'note_off',
  CONTROL_CHANGE: 'control_change',
  PROGRAM_CHANGE: 'program_change',
  PITCH_BEND: 'pitch_bend',
  MSC: 'msc',
};

// MSC Device Types (Command Format)
export const MSCFormat = {
  LIGHTING: 0x01,
  SOUND: 0x10,
  MACHINERY: 0x20,
  VIDEO: 0x30,
  PROJECTION: 0x40,
  PROCESS_CONTROL: 0x50,
  PYRO: 0x60,
  ALL: 0x7F,
};

// MSC Command Codes
export const MSCCommand = {
  GO: 0x01,
  STOP: 0x02,
  RESUME: 0x03,
  TIMED_GO: 0x04,
  LOAD: 0x05,
  SET: 0x06,
  FIRE: 0x07,
  ALL_OFF: 0x08,
  RESTORE: 0x09,
  RESET: 0x0A,
  GO_OFF: 0x0B,
};

// Nomi note musicali
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

/**
 * Converte un nome nota (es. 'C4', 'A#3', 'Gb2') in numero MIDI (0-127)
 */
export function noteNameToNumber(name) {
  if (typeof name === 'number') {
    return Math.max(0, Math.min(127, Math.round(name)));
  }
  if (!name || typeof name !== 'string') return 60; // Default C4

  const match = name.trim().match(/^([A-Ga-g])([#b]?)(-?\d+)$/);
  if (!match) return 60;

  let note = match[1].toUpperCase();
  const acc = match[2];
  const octave = parseInt(match[3], 10);

  let semitone = NOTE_NAMES.indexOf(note);
  if (acc === '#') semitone = (semitone + 1) % 12;
  else if (acc === 'b') semitone = (semitone + 11) % 12;

  // MIDI standard: C-1 = 0, C4 (Middle C) = 60
  const midiNum = (octave + 1) * 12 + semitone;
  return Math.max(0, Math.min(127, midiNum));
}

/**
 * Converte un numero MIDI (0-127) in nome nota (es. 60 -> 'C4')
 */
export function numberToNoteName(num) {
  const n = Math.max(0, Math.min(127, Math.round(num)));
  const semitone = n % 12;
  const octave = Math.floor(n / 12) - 1;
  return `${NOTE_NAMES[semitone]}${octave}`;
}

export default class MidiCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.MIDI,
    });

    // Tipologia messaggio MIDI
    this.midiMessageType = options.midiMessageType || MidiMessageType.NOTE_ON;

    // Parametri canale voce MIDI
    this.channel = options.channel !== undefined ? Math.max(1, Math.min(16, Number(options.channel))) : 1;
    this.note = options.note !== undefined ? noteNameToNumber(options.note) : 60; // 60 = C4
    this.velocity = options.velocity !== undefined ? Math.max(0, Math.min(127, Number(options.velocity))) : 100;
    this.controlNumber = options.controlNumber !== undefined ? Math.max(0, Math.min(127, Number(options.controlNumber))) : 0;
    this.controlValue = options.controlValue !== undefined ? Math.max(0, Math.min(127, Number(options.controlValue))) : 0;
    this.program = options.program !== undefined ? Math.max(0, Math.min(127, Number(options.program))) : 1;
    this.bankMSB = options.bankMSB !== undefined ? Math.max(0, Math.min(127, Number(options.bankMSB))) : null;
    this.bankLSB = options.bankLSB !== undefined ? Math.max(0, Math.min(127, Number(options.bankLSB))) : null;
    this.pitchBend = options.pitchBend !== undefined ? Number(options.pitchBend) : 0; // -8192 .. +8191

    // Parametri MIDI Show Control (MSC)
    this.mscDevice = options.mscDevice !== undefined ? Number(options.mscDevice) : 0x7F; // 0x7F = All-Call
    this.mscFormat = options.mscFormat !== undefined ? Number(options.mscFormat) : MSCFormat.SOUND;
    this.mscCommand = options.mscCommand !== undefined ? Number(options.mscCommand) : MSCCommand.GO;
    this.mscCue = options.mscCue !== undefined ? String(options.mscCue) : '';
    this.mscCueList = options.mscCueList !== undefined ? String(options.mscCueList) : '';
    this.mscCuePath = options.mscCuePath !== undefined ? String(options.mscCuePath) : '';

    // Porta MIDI di destinazione (se disponibile)
    this.midiOutputPort = options.midiOutputPort || 'default';

    // Callback di trasmissione
    this.onMidiSent = options.onMidiSent || null;

    // Traccia ultimo messaggio inviato
    this.lastMidiTransmission = null;
  }

  // ─── Compilazione Byte MIDI ────────────────────────────────────

  /**
   * Genera il buffer Uint8Array contenente i byte grezzi MIDI del messaggio
   */
  compileBytes() {
    const chIdx = (this.channel - 1) & 0x0F;

    switch (this.midiMessageType) {
      case MidiMessageType.NOTE_ON: {
        return new Uint8Array([0x90 | chIdx, this.note & 0x7F, this.velocity & 0x7F]);
      }

      case MidiMessageType.NOTE_OFF: {
        return new Uint8Array([0x80 | chIdx, this.note & 0x7F, this.velocity & 0x7F]);
      }

      case MidiMessageType.CONTROL_CHANGE: {
        return new Uint8Array([0xB0 | chIdx, this.controlNumber & 0x7F, this.controlValue & 0x7F]);
      }

      case MidiMessageType.PROGRAM_CHANGE: {
        // Se specificato Bank Select, invia CC 0 (MSB) e CC 32 (LSB) prima del PC
        const bytes = [];
        if (this.bankMSB !== null) {
          bytes.push(0xB0 | chIdx, 0x00, this.bankMSB & 0x7F);
        }
        if (this.bankLSB !== null) {
          bytes.push(0xB0 | chIdx, 0x20, this.bankLSB & 0x7F);
        }
        bytes.push(0xC0 | chIdx, this.program & 0x7F);
        return new Uint8Array(bytes);
      }

      case MidiMessageType.PITCH_BEND: {
        let val = Number(this.pitchBend) || 0;
        // Se specificato come valore bipolare (-8192..+8191), mappa con centro a 8192
        if (val >= -8192 && val <= 8191) {
          val = val + 8192;
        }
        val = Math.max(0, Math.min(16383, Math.round(val)));

        const lsb = val & 0x7F;
        const msb = (val >> 7) & 0x7F;
        return new Uint8Array([0xE0 | chIdx, lsb, msb]);
      }

      case MidiMessageType.MSC: {
        return MidiCue.encodeMscSysEx({
          deviceId: this.mscDevice,
          commandFormat: this.mscFormat,
          command: this.mscCommand,
          cueNumber: this.mscCue,
          cueList: this.mscCueList,
          cuePath: this.mscCuePath,
        });
      }

      default:
        return new Uint8Array(0);
    }
  }

  // ─── Encoder & Decoder MIDI Show Control (MSC) SysEx ───────────

  /**
   * Codifica un pacchetto SysEx MSC conforme a MMA RP-002
   * Formato: F0 7F <deviceId> 02 <commandFormat> <command> [Q_number 00 Q_list 00 Q_path] F7
   */
  static encodeMscSysEx(params = {}) {
    const deviceId = params.deviceId !== undefined ? (params.deviceId & 0x7F) : 0x7F;
    const commandFormat = params.commandFormat !== undefined ? (params.commandFormat & 0x7F) : MSCFormat.ALL;
    const command = params.command !== undefined ? (params.command & 0x7F) : MSCCommand.GO;

    const bytes = [0xF0, 0x7F, deviceId, 0x02, commandFormat, command];

    const encoder = new TextEncoder();

    if (params.cueNumber) {
      const qNumBytes = encoder.encode(String(params.cueNumber));
      for (const b of qNumBytes) bytes.push(b & 0x7F);

      if (params.cueList || params.cuePath) {
        bytes.push(0x00); // Delimitatore Q_list
        if (params.cueList) {
          const qListBytes = encoder.encode(String(params.cueList));
          for (const b of qListBytes) bytes.push(b & 0x7F);
        }

        if (params.cuePath) {
          bytes.push(0x00); // Delimitatore Q_path
          const qPathBytes = encoder.encode(String(params.cuePath));
          for (const b of qPathBytes) bytes.push(b & 0x7F);
        }
      }
    }

    bytes.push(0xF7); // End of SysEx
    return new Uint8Array(bytes);
  }

  /**
   * Decodifica un pacchetto binario MIDI (Canale voce standard o SysEx MSC)
   */
  static parseBytes(rawBytes) {
    const bytes = rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes);
    if (!bytes || bytes.length === 0) return null;

    // 1. SysEx MSC: F0 7F ... F7
    if (bytes[0] === 0xF0 && bytes.length >= 6) {
      if (bytes[1] === 0x7F && bytes[3] === 0x02) {
        const deviceId = bytes[2];
        const commandFormat = bytes[4];
        const command = bytes[5];

        let cueNumber = '';
        let cueList = '';
        let cuePath = '';

        if (bytes.length > 7) {
          const dataSlice = bytes.subarray(6, bytes.length - 1);
          // Separa per 0x00
          const parts = [];
          let cur = [];
          for (const b of dataSlice) {
            if (b === 0x00) {
              parts.push(new TextDecoder('ascii').decode(new Uint8Array(cur)));
              cur = [];
            } else {
              cur.push(b);
            }
          }
          if (cur.length > 0) {
            parts.push(new TextDecoder('ascii').decode(new Uint8Array(cur)));
          }

          if (parts.length > 0) cueNumber = parts[0];
          if (parts.length > 1) cueList = parts[1];
          if (parts.length > 2) cuePath = parts[2];
        }

        return {
          type: MidiMessageType.MSC,
          deviceId,
          commandFormat,
          command,
          cueNumber,
          cueList,
          cuePath,
        };
      }
    }

    // 2. Canale Voce Standard (3 byte o 2 byte)
    const status = bytes[0] & 0xF0;
    const channel = (bytes[0] & 0x0F) + 1;

    switch (status) {
      case 0x90:
        return {
          type: MidiMessageType.NOTE_ON,
          channel,
          note: bytes[1],
          noteName: numberToNoteName(bytes[1]),
          velocity: bytes[2],
        };
      case 0x80:
        return {
          type: MidiMessageType.NOTE_OFF,
          channel,
          note: bytes[1],
          noteName: numberToNoteName(bytes[1]),
          velocity: bytes[2],
        };
      case 0xB0:
        return {
          type: MidiMessageType.CONTROL_CHANGE,
          channel,
          controlNumber: bytes[1],
          controlValue: bytes[2],
        };
      case 0xC0:
        return {
          type: MidiMessageType.PROGRAM_CHANGE,
          channel,
          program: bytes[1],
        };
      case 0xE0: {
        const lsb = bytes[1];
        const msb = bytes[2];
        const value = (msb << 7) | lsb;
        return {
          type: MidiMessageType.PITCH_BEND,
          channel,
          value,
          bend: value - 8192,
        };
      }
    }

    return { type: 'unknown', bytes };
  }

  // ─── Trasmissione MIDI ─────────────────────────────────────────

  /**
   * Trasmette il messaggio MIDI attraverso il router o l'output configurato
   */
  async transmit(midiRouter = null) {
    if (!this.isArmed()) return null;

    const bytes = this.compileBytes();
    const transmissionData = {
      cue: this,
      messageType: this.midiMessageType,
      bytes,
      channel: this.channel,
      port: this.midiOutputPort,
      timestamp: Date.now(),
    };

    this.lastMidiTransmission = transmissionData;

    if (typeof this.onMidiSent === 'function') {
      try {
        this.onMidiSent(this, transmissionData);
      } catch (err) {
        console.error('Errore nel callback onMidiSent di MidiCue:', err);
      }
    }

    if (midiRouter && typeof midiRouter.sendMidi === 'function') {
      await midiRouter.sendMidi(bytes, this.midiOutputPort);
    }

    return transmissionData;
  }

  // ─── Override Ciclo di Vita BaseCue ────────────────────────────

  _enterActionPhase() {
    super._enterActionPhase();

    if (this.armed) {
      this.transmit().catch(e => {
        console.warn(`Errore durante la trasmissione di MidiCue "${this.number}":`, e);
      });
    }

    if (this.duration === 0) {
      this._checkActionCompletion();
    }
  }

  // ─── Serializzazione ───────────────────────────────────────────

  toJSON() {
    return {
      ...super.toJSON(),
      midiMessageType: this.midiMessageType,
      channel: this.channel,
      note: this.note,
      noteName: numberToNoteName(this.note),
      velocity: this.velocity,
      controlNumber: this.controlNumber,
      controlValue: this.controlValue,
      program: this.program,
      bankMSB: this.bankMSB,
      bankLSB: this.bankLSB,
      pitchBend: this.pitchBend,
      mscDevice: this.mscDevice,
      mscFormat: this.mscFormat,
      mscCommand: this.mscCommand,
      mscCue: this.mscCue,
      mscCueList: this.mscCueList,
      mscCuePath: this.mscCuePath,
      midiOutputPort: this.midiOutputPort,
    };
  }
}
