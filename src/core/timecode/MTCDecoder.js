/**
 * MTCDecoder.js — Decoder e Generatore MIDI Timecode (MTC) per ShowSuite
 * 
 * Implementa le specifiche MIDI Timecode (MMA):
 * 1. Quarter-Frame Messages (0xF1 data):
 *    - 8 pacchetti quarter-frame (pezzi 0..7) inviati a 4x il frame rate
 *    - Ricostruzione del timecode SMPTE con compensazione latenza standard (+2 frame al pezzo 7)
 *    - Rilevamento automatico del frame rate (24, 25, 29.97 DF, 30 fps)
 * 2. Full-Frame SysEx Messages:
 *    - F0 7F <deviceId> 01 01 hr mn sc fr F7
 *    - Riposizionamento e seek istantaneo del timecode
 * 3. MTCGenerator:
 *    - Generazione dei byte MTC Quarter Frame e Full Frame SysEx da inviare ad uscite MIDI
 */

import SMPTETimecode, { SMPTEFrameRate, MTC_RATE_CODES } from './SMPTETimecode.js';

export class MTCGenerator {
  /**
   * Converte il frame rate in codice rate MTC a 2 bit (0..3)
   */
  static getRateCode(fps, isDropFrame = false) {
    if (fps === 24) return MTC_RATE_CODES.FPS_24;
    if (fps === 25) return MTC_RATE_CODES.FPS_25;
    if (fps === 29.97 || isDropFrame) return MTC_RATE_CODES.FPS_29_97_DF;
    return MTC_RATE_CODES.FPS_30;
  }

  /**
   * Genera la sequenza di 8 messaggi Quarter-Frame MTC per un timecode SMPTE dato
   * @param {SMPTETimecode} tc 
   * @returns {Array<Uint8Array>} Array di 8 messaggi MIDI [0xF1, data]
   */
  static createQuarterFrames(tc) {
    const rateCode = MTCGenerator.getRateCode(tc.fps, tc.isDropFrame);
    const messages = [];

    const pieces = [
      tc.frames & 0x0F,                                           // 0: Frame LSB
      (tc.frames >> 4) & 0x01,                                    // 1: Frame MSB
      tc.seconds & 0x0F,                                          // 2: Second LSB
      (tc.seconds >> 4) & 0x03,                                   // 3: Second MSB
      tc.minutes & 0x0F,                                          // 4: Minute LSB
      (tc.minutes >> 4) & 0x03,                                   // 5: Minute MSB
      tc.hours & 0x0F,                                            // 6: Hour LSB
      ((rateCode & 0x03) << 1) | ((tc.hours >> 4) & 0x01),        // 7: Hour MSB + Rate
    ];

    for (let piece = 0; piece < 8; piece++) {
      const dataByte = ((piece & 0x07) << 4) | (pieces[piece] & 0x0F);
      messages.push(new Uint8Array([0xF1, dataByte]));
    }

    return messages;
  }

  /**
   * Genera un messaggio Full-Frame SysEx MTC
   * F0 7F <deviceId> 01 01 hr mn sc fr F7
   */
  static createFullFrameSysEx(tc, deviceId = 0x7F) {
    const rateCode = MTCGenerator.getRateCode(tc.fps, tc.isDropFrame);
    const hoursWithRate = ((rateCode & 0x03) << 5) | (tc.hours & 0x1F);

    return new Uint8Array([
      0xF0,
      0x7F,
      deviceId & 0x7F,
      0x01, // Sub-ID #1 = MIDI Time Code
      0x01, // Sub-ID #2 = Full Message
      hoursWithRate,
      tc.minutes & 0x3F,
      tc.seconds & 0x3F,
      tc.frames & 0x1F,
      0xF7,
    ]);
  }
}

export default class MTCDecoder {
  constructor(options = {}) {
    this.compensateLatency = options.compensateLatency !== undefined ? Boolean(options.compensateLatency) : true;

    // Buffer degli 8 pezzi del quarter-frame
    this.qfBuffer = new Uint8Array(8);
    this.qfReceivedMask = 0; // Bitmask per tracciare la ricezione di tutti gli 8 pezzi

    // Ultimo timecode calcolato
    this.currentTimecode = new SMPTETimecode(0, 0, 0, 0, 0, SMPTEFrameRate.FPS_25, false);

    // Callbacks
    this.onTimecode = options.onTimecode || null;
    this.onFullFrame = options.onFullFrame || null;
    this.onQuarterFrame = options.onQuarterFrame || null;

    this.listeners = {
      timecode: [],
      fullFrame: [],
      quarterFrame: [],
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
        try { cb(data); } catch (e) { console.error(`Errore nel listener MTC "${event}":`, e); }
      }
    }
  }

  /**
   * Processa un singolo messaggio MIDI (Quarter-Frame 0xF1 o SysEx Full Frame)
   * 
   * @param {Uint8Array|Array<number>} rawBytes 
   * @returns {SMPTETimecode|null} Il timecode aggiornato se completato, altrimenti null
   */
  processMidi(rawBytes) {
    const bytes = rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes);
    if (!bytes || bytes.length === 0) return null;

    // 1. Quarter-Frame Message (0xF1 data)
    if (bytes[0] === 0xF1 && bytes.length >= 2) {
      return this._handleQuarterFrame(bytes[1]);
    }

    // 2. SysEx Full-Frame Message (F0 7F ... 01 01 hr mn sc fr F7)
    if (bytes[0] === 0xF0 && bytes.length >= 10) {
      if (bytes[1] === 0x7F && bytes[3] === 0x01 && bytes[4] === 0x01) {
        return this._handleFullFrame(bytes);
      }
    }

    return null;
  }

  /**
   * Elabora un byte dati di Quarter-Frame
   */
  _handleQuarterFrame(dataByte) {
    const piece = (dataByte >> 4) & 0x07;
    const nibble = dataByte & 0x0F;

    this.qfBuffer[piece] = nibble;
    this.qfReceivedMask |= (1 << piece);

    if (typeof this.onQuarterFrame === 'function') {
      this.onQuarterFrame(piece, nibble);
    }
    this.emit('quarterFrame', { piece, nibble });

    // Quando arriva il pezzo 7 e abbiamo ricevuto tutti gli 8 pezzi (mask === 0xFF)
    if (piece === 7 && this.qfReceivedMask === 0xFF) {
      const frames = (this.qfBuffer[1] << 4) | this.qfBuffer[0];
      const seconds = (this.qfBuffer[3] << 4) | this.qfBuffer[2];
      const minutes = (this.qfBuffer[5] << 4) | this.qfBuffer[4];
      const hours = ((this.qfBuffer[7] & 0x01) << 4) | this.qfBuffer[6];
      const rateCode = (this.qfBuffer[7] >> 1) & 0x03;

      let fps = SMPTEFrameRate.FPS_25;
      let isDropFrame = false;

      switch (rateCode) {
        case MTC_RATE_CODES.FPS_24:
          fps = SMPTEFrameRate.FPS_24;
          break;
        case MTC_RATE_CODES.FPS_25:
          fps = SMPTEFrameRate.FPS_25;
          break;
        case MTC_RATE_CODES.FPS_29_97_DF:
          fps = SMPTEFrameRate.FPS_29_97;
          isDropFrame = true;
          break;
        case MTC_RATE_CODES.FPS_30:
          fps = SMPTEFrameRate.FPS_30;
          break;
      }

      let tc = new SMPTETimecode(hours, minutes, seconds, frames, 0, fps, isDropFrame);

      // Compensazione latenza standard MTC (+2 frame per il tempo impiegato dagli 8 QF a trasmettere)
      if (this.compensateLatency) {
        tc = tc.addFrames(2);
      }

      this.currentTimecode = tc;
      this.qfReceivedMask = 0; // Reset mask per il prossimo ciclo

      if (typeof this.onTimecode === 'function') {
        this.onTimecode(tc);
      }
      this.emit('timecode', tc);

      return tc;
    }

    return null;
  }

  /**
   * Elabora un messaggio SysEx Full Frame
   */
  _handleFullFrame(bytes) {
    const hrByte = bytes[5];
    const mn = bytes[6] & 0x3F;
    const sc = bytes[7] & 0x3F;
    const fr = bytes[8] & 0x1F;

    const rateCode = (hrByte >> 5) & 0x03;
    const hr = hrByte & 0x1F;

    let fps = SMPTEFrameRate.FPS_25;
    let isDropFrame = false;

    switch (rateCode) {
      case MTC_RATE_CODES.FPS_24:
        fps = SMPTEFrameRate.FPS_24;
        break;
      case MTC_RATE_CODES.FPS_25:
        fps = SMPTEFrameRate.FPS_25;
        break;
      case MTC_RATE_CODES.FPS_29_97_DF:
        fps = SMPTEFrameRate.FPS_29_97;
        isDropFrame = true;
        break;
      case MTC_RATE_CODES.FPS_30:
        fps = SMPTEFrameRate.FPS_30;
        break;
    }

    const tc = new SMPTETimecode(hr, mn, sc, fr, 0, fps, isDropFrame);
    this.currentTimecode = tc;
    this.qfReceivedMask = 0;

    if (typeof this.onFullFrame === 'function') {
      this.onFullFrame(tc);
    }
    this.emit('fullFrame', tc);
    this.emit('timecode', tc);

    return tc;
  }
}
