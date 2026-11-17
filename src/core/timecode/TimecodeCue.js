/**
 * TimecodeCue.js — Timecode Output Cue per ShowSuite (conforme a QLab 5)
 * 
 * Modello cue specializzato per la generazione e trasmissione di Timecode verso
 * apparati esterni (mixer audio/luci, media server, broadcast switcher):
 * - Formati di uscita: MTC (MIDI Timecode) o LTC (Linear Audio Timecode)
 * - Frame rate configurabili: 24, 25, 29.97 DF, 30 fps
 * - Calcolo ad alta precisione del timecode corrente in funzione della durata di riproduzione
 * - Emissione MTC Quarter-Frame e SysEx Full-Frame all'avvio
 */

import BaseCue from '../qlab/BaseCue.js';
import { CueType } from '../qlab/CueTypes.js';
import SMPTETimecode, { SMPTEFrameRate } from './SMPTETimecode.js';
import { MTCGenerator } from './MTCDecoder.js';
import { LTCGenerator } from './LTCDecoder.js';

export const TimecodeOutputFormat = {
  MTC: 'mtc',
  LTC: 'ltc',
};

export default class TimecodeCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.TIMECODE,
    });

    this.fps = options.fps === 29.97 ? 29.97 : Number(options.fps) || SMPTEFrameRate.FPS_25;
    this.isDropFrame = options.isDropFrame !== undefined ? Boolean(options.isDropFrame) : (this.fps === 29.97);

    // Timecode di inizio
    const startStr = options.startTimecode || '01:00:00:00';
    this.startTimecode = startStr instanceof SMPTETimecode
      ? startStr.clone()
      : SMPTETimecode.fromString(startStr, this.fps, this.isDropFrame);

    // Formato di trasmissione ('mtc' | 'ltc')
    this.outputFormat = options.outputFormat || TimecodeOutputFormat.MTC;

    // Destinazione (porta MIDI o canale audio)
    this.destination = options.destination || 'default';

    // Callback e listeners
    this.onTimecodeOutput = options.onTimecodeOutput || null;

    // Stato runtime
    this.lastEmittedFrame = -1;
  }

  /**
   * Calcola il timecode SMPTE corrente in base all'avanzamento dell'azione
   */
  getCurrentTimecode() {
    const elapsedSeconds = this.actionElapsed;
    const additionalFrames = Math.floor(elapsedSeconds * this.fps);
    return this.startTimecode.addFrames(additionalFrames);
  }

  // ─── Override Ciclo di Vita BaseCue ────────────────────────────

  _enterActionPhase() {
    super._enterActionPhase();

    // All'avvio dell'azione, invia Full-Frame SysEx per posizionare immediatamente i ricevitori
    if (this.armed) {
      const tc = this.getCurrentTimecode();
      if (this.outputFormat === TimecodeOutputFormat.MTC) {
        const fullFrame = MTCGenerator.createFullFrameSysEx(tc);
        this._emitOutput(tc, fullFrame);
      }
    }
  }

  tick(dt = 0.016) {
    const result = super.tick(dt);

    if (this.armed && this.currentPhase === 'action') {
      const tc = this.getCurrentTimecode();
      const currentFrameNum = tc.toFrames();

      // Se siamo passati a un nuovo frame, emetti i pacchetti
      if (currentFrameNum !== this.lastEmittedFrame) {
        this.lastEmittedFrame = currentFrameNum;

        if (this.outputFormat === TimecodeOutputFormat.MTC) {
          const qfList = MTCGenerator.createQuarterFrames(tc);
          this._emitOutput(tc, qfList);
        } else if (this.outputFormat === TimecodeOutputFormat.LTC) {
          const ltcBits = LTCGenerator.encodeBits(tc);
          this._emitOutput(tc, ltcBits);
        }
      }
    }

    return result;
  }

  _emitOutput(timecode, payload) {
    if (typeof this.onTimecodeOutput === 'function') {
      try {
        this.onTimecodeOutput(this, timecode, payload);
      } catch (err) {
        console.error('Errore in onTimecodeOutput di TimecodeCue:', err);
      }
    }
  }

  // ─── Serializzazione ───────────────────────────────────────────

  toJSON() {
    return {
      ...super.toJSON(),
      startTimecode: this.startTimecode.toString(),
      fps: this.fps,
      isDropFrame: this.isDropFrame,
      outputFormat: this.outputFormat,
      destination: this.destination,
    };
  }
}
