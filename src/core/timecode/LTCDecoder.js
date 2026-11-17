/**
 * LTCDecoder.js — Decoder e Generatore Audio LTC (Linear Timecode - SMPTE 12M) per ShowSuite
 * 
 * Implementa le specifiche SMPTE 12M per il timecode audio:
 * - Modulazione Bi-phase Mark Code (BMC / Manchester bifase):
 *   - Transizione all'inizio di ogni cella di bit
 *   - Bit '1': transizione aggiuntiva a metà della cella (2 transizioni per bit)
 *   - Bit '0': nessuna transizione aggiuntiva a metà (1 transizione per bit)
 * - Struttura frame a 80 bit con parola di sincronizzazione standard (Sync Word: 0011 1111 1111 1101)
 * - Rilevamento passaggi per lo zero (zero-crossing) con isteresi per tolleranza al rumore
 * - Estrazione e decodifica BCD di Ore, Minuti, Secondi, Frame e Drop-Frame flag
 * - Generatore LTC Audio per test, playback e trasmissione su scheda audio
 */

import SMPTETimecode, { SMPTEFrameRate } from './SMPTETimecode.js';

// Sync Word standard SMPTE 12M (bit 64..79: 0011 1111 1111 1101)
const SYNC_WORD_FORWARD = [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1];

export class LTCGenerator {
  /**
   * Genera il frame a 80 bit per un dato timecode SMPTE
   * @param {SMPTETimecode} tc 
   * @returns {Uint8Array} Array di 80 elementi binari (0 o 1)
   */
  static encodeBits(tc) {
    const bits = new Uint8Array(80);

    const fUnits = tc.frames % 10;
    const fTens = Math.floor(tc.frames / 10);
    const sUnits = tc.seconds % 10;
    const sTens = Math.floor(tc.seconds / 10);
    const mUnits = tc.minutes % 10;
    const mTens = Math.floor(tc.minutes / 10);
    const hUnits = tc.hours % 10;
    const hTens = Math.floor(tc.hours / 10);

    // Frame units (bit 0..3)
    bits[0] = fUnits & 1;
    bits[1] = (fUnits >> 1) & 1;
    bits[2] = (fUnits >> 2) & 1;
    bits[3] = (fUnits >> 3) & 1;

    // Frame tens (bit 8..9)
    bits[8] = fTens & 1;
    bits[9] = (fTens >> 1) & 1;

    // Drop Frame flag (bit 10)
    bits[10] = tc.isDropFrame ? 1 : 0;

    // Seconds units (bit 16..19)
    bits[16] = sUnits & 1;
    bits[17] = (sUnits >> 1) & 1;
    bits[18] = (sUnits >> 2) & 1;
    bits[19] = (sUnits >> 3) & 1;

    // Seconds tens (bit 24..26)
    bits[24] = sTens & 1;
    bits[25] = (sTens >> 1) & 1;
    bits[26] = (sTens >> 2) & 1;

    // Minutes units (bit 32..35)
    bits[32] = mUnits & 1;
    bits[33] = (mUnits >> 1) & 1;
    bits[34] = (mUnits >> 2) & 1;
    bits[35] = (mUnits >> 3) & 1;

    // Minutes tens (bit 40..42)
    bits[40] = mTens & 1;
    bits[41] = (mTens >> 1) & 1;
    bits[42] = (mTens >> 2) & 1;

    // Hours units (bit 48..51)
    bits[48] = hUnits & 1;
    bits[49] = (hUnits >> 1) & 1;
    bits[50] = (hUnits >> 2) & 1;
    bits[51] = (hUnits >> 3) & 1;

    // Hours tens (bit 56..57)
    bits[56] = hTens & 1;
    bits[57] = (hTens >> 1) & 1;

    // Sync word standard (bit 64..79)
    for (let i = 0; i < 16; i++) {
      bits[64 + i] = SYNC_WORD_FORWARD[i];
    }

    return bits;
  }

  /**
   * Sintetizza un segnale audio PCM Float32Array modulato BMC per il timecode specificato
   * 
   * @param {SMPTETimecode} startTc Timecode iniziale
   * @param {number} sampleRate Frequenza di campionamento (es. 48000)
   * @param {number} numFrames Numero di frame da generare
   * @returns {Float32Array} Buffer audio PCM normalizzato in [-1.0, 1.0]
   */
  static generateAudio(startTc, sampleRate = 48000, numFrames = 1) {
    const fps = startTc.fps === 29.97 ? 29.97 : Number(startTc.fps) || 25;
    const samplesPerBit = sampleRate / (fps * 80);
    const totalSamples = Math.ceil(numFrames * 80 * samplesPerBit);
    const output = new Float32Array(totalSamples);

    let curTc = startTc.clone();
    let sampleIdx = 0;
    let signalLevel = 1.0;

    for (let f = 0; f < numFrames; f++) {
      const bits = LTCGenerator.encodeBits(curTc);

      for (let b = 0; b < 80; b++) {
        const bitVal = bits[b];
        const bitStartSample = Math.round(sampleIdx);
        const bitEndSample = Math.round(sampleIdx + samplesPerBit);
        const bitMidSample = Math.round(sampleIdx + samplesPerBit / 2);

        // All'inizio della cella c'è sempre un'inversione di polarità
        signalLevel = -signalLevel;

        if (bitVal === 1) {
          // Bit '1': prima metà al livello corrente, poi inversione a metà cella
          for (let s = bitStartSample; s < bitMidSample && s < totalSamples; s++) {
            output[s] = signalLevel;
          }
          signalLevel = -signalLevel;
          for (let s = bitMidSample; s < bitEndSample && s < totalSamples; s++) {
            output[s] = signalLevel;
          }
        } else {
          // Bit '0': livello costante per tutta la cella
          for (let s = bitStartSample; s < bitEndSample && s < totalSamples; s++) {
            output[s] = signalLevel;
          }
        }

        sampleIdx += samplesPerBit;
      }

      curTc = curTc.addFrames(1);
    }

    return output;
  }
}

export default class LTCDecoder {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 48000;
    this.expectedFps = options.expectedFps || SMPTEFrameRate.FPS_25;

    // Rilevamento Zero-Crossing
    this.prevSample = 0;
    this.samplesSinceLastZero = 0;

    // Stato decodifica BMC
    this.halfBitWaiting = false;

    // Registro a scorrimento per gli 80 bit
    this.bitHistory = [];
    this.maxHistory = 160;

    // Ultimo timecode decodificato
    this.lastDecodedTimecode = null;

    // Callbacks
    this.onTimecode = options.onTimecode || null;
    this.listeners = {
      timecode: [],
      error: [],
    };
  }

  on(event, cb) {
    if (this.listeners[event]) this.listeners[event].push(cb);
    return () => this.off(event, cb);
  }

  off(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(l => l !== cb);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      for (const cb of this.listeners[event]) {
        try { cb(data); } catch (e) { console.error(`Errore nel listener LTC "${event}":`, e); }
      }
    }
  }

  /**
   * Elabora un blocco di campioni audio PCM
   * @param {Float32Array|Int16Array|Array<number>} audioSamples Campioni audio
   * @returns {Array<SMPTETimecode>} Lista dei frame timecode decodificati in questo blocco
   */
  processAudio(audioSamples) {
    const samples = audioSamples instanceof Float32Array ? audioSamples : new Float32Array(audioSamples);
    const decodedFrames = [];

    const nominalSamplesPerBit = this.sampleRate / (this.expectedFps * 80);
    const halfBitThresholdMin = nominalSamplesPerBit * 0.25;
    const halfBitThresholdMax = nominalSamplesPerBit * 0.75;
    const fullBitThresholdMin = nominalSamplesPerBit * 0.75;
    const fullBitThresholdMax = nominalSamplesPerBit * 1.5;

    for (let i = 0; i < samples.length; i++) {
      const sample = samples[i];
      this.samplesSinceLastZero++;

      // Rilevamento del passaggio per lo zero (zero-crossing) con soglia di isteresi
      const zeroCrossed = (this.prevSample <= 0 && sample > 0) || (this.prevSample >= 0 && sample < 0);

      if (zeroCrossed) {
        const interval = this.samplesSinceLastZero;
        this.samplesSinceLastZero = 0;

        // Classificazione intervallo in Half-Bit (1) o Full-Bit (0)
        if (interval >= halfBitThresholdMin && interval < halfBitThresholdMax) {
          // Mezza cella: due mezze celle consecutive formano un bit '1'
          if (this.halfBitWaiting) {
            this._pushBit(1, decodedFrames);
            this.halfBitWaiting = false;
          } else {
            this.halfBitWaiting = true;
          }
        } else if (interval >= fullBitThresholdMin && interval <= fullBitThresholdMax) {
          // Cella intera: bit '0'
          this.halfBitWaiting = false;
          this._pushBit(0, decodedFrames);
        } else if (interval > fullBitThresholdMax) {
          // Timeout / intervallo spurio: reset stato di mezza cella
          this.halfBitWaiting = false;
        }
      }

      this.prevSample = sample;
    }

    return decodedFrames;
  }

  /**
   * Inserisce un bit estratto nel registro e controlla la sync word
   */
  _pushBit(bit, decodedFrames) {
    this.bitHistory.push(bit);
    if (this.bitHistory.length > this.maxHistory) {
      this.bitHistory.shift();
    }

    // Controlla se gli ultimi 16 bit corrispondono alla Sync Word (0011 1111 1111 1101)
    if (this.bitHistory.length >= 80) {
      const syncStart = this.bitHistory.length - 16;
      let syncMatch = true;
      for (let i = 0; i < 16; i++) {
        if (this.bitHistory[syncStart + i] !== SYNC_WORD_FORWARD[i]) {
          syncMatch = false;
          break;
        }
      }

      if (syncMatch) {
        // Frame completo identificato! Gli 80 bit precedenti formano il frame SMPTE
        const frameStart = this.bitHistory.length - 80;
        const frameBits = this.bitHistory.slice(frameStart, this.bitHistory.length);

        const tc = this._decodeFrameBits(frameBits);
        if (tc) {
          this.lastDecodedTimecode = tc;
          decodedFrames.push(tc);

          if (typeof this.onTimecode === 'function') {
            this.onTimecode(tc);
          }
          this.emit('timecode', tc);
        }
      }
    }
  }

  /**
   * Decodifica gli 80 bit del frame in un'istanza SMPTETimecode
   */
  _decodeFrameBits(bits) {
    if (bits.length !== 80) return null;

    // Helper per leggere interi BCD da sequenze di bit little-endian
    const readBcd = (start, length) => {
      let val = 0;
      for (let i = 0; i < length; i++) {
        val |= (bits[start + i] << i);
      }
      return val;
    };

    const fUnits = readBcd(0, 4);
    const fTens = readBcd(8, 2);
    const frames = fTens * 10 + fUnits;

    const isDropFrame = Boolean(bits[10]);

    const sUnits = readBcd(16, 4);
    const sTens = readBcd(24, 3);
    const seconds = sTens * 10 + sUnits;

    const mUnits = readBcd(32, 4);
    const mTens = readBcd(40, 3);
    const minutes = mTens * 10 + mUnits;

    const hUnits = readBcd(48, 4);
    const hTens = readBcd(56, 2);
    const hours = hTens * 10 + hUnits;

    // Validazione valori
    if (hours > 23 || minutes > 59 || seconds > 59 || frames > 30) {
      return null;
    }

    return new SMPTETimecode(hours, minutes, seconds, frames, 0, this.expectedFps, isDropFrame);
  }
}
