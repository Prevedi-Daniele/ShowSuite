/**
 * AudioCue.js — Modello specializzato per le Audio Cue di QLab 5 in ShowSuite
 * 
 * Estende BaseCue con:
 * - Punti di In e Out (inPoint, outPoint)
 * - Slicing grafico con marcatori temporali e contatori di loop
 * - Playback rate (vari-speed 0.25x - 2.0x) e Pitch shifting (-24 .. +24 semitoni)
 * - Opzione Infinite Loop / Play Count
 * - Istanza AudioMatrixMixer N x M integrata con fader e crosspoints
 */

import BaseCue from './BaseCue.js';
import { CueType } from './CueTypes.js';
import { AudioMatrixMixer, AudioTarget, SurroundProfile } from './audio/index.js';

export default class AudioCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.AUDIO,
    });

    this.filePath = options.filePath || options.targetId || null;
    this.sampleRate = options.sampleRate || 48000;
    this.channels = options.channels || 2;

    // Punti di In e Out
    this.inPoint = Math.max(0, Number(options.inPoint) || 0);
    this.outPoint = options.outPoint !== undefined ? Number(options.outPoint) : (this.duration || 10.0);
    if (this.outPoint < this.inPoint) this.outPoint = this.inPoint + (this.duration || 1.0);

    // Loop e Ripetizioni
    this.playCount = Math.max(1, parseInt(options.playCount, 10) || 1);
    this.infiniteLoop = Boolean(options.infiniteLoop);

    // Vari-speed e Pitch
    this.playbackRate = options.playbackRate !== undefined ? Math.max(0.1, Number(options.playbackRate)) : 1.0;
    this.pitchShift = options.pitchShift !== undefined ? Number(options.pitchShift) : 0.0; // semitoni
    this.preservePitch = options.preservePitch !== undefined ? Boolean(options.preservePitch) : true;

    // Slices temporali: [{ id, time, loopCount }]
    this.slices = Array.isArray(options.slices) ? options.slices : [];

    // Matrice di Missaggio Audio dedicata
    const target = new AudioTarget({
      name: this.name,
      filePath: this.filePath,
      duration: this.outPoint - this.inPoint,
      inputChannels: this.channels,
      profile: this.channels === 6 ? SurroundProfile.SURROUND_5_1 : SurroundProfile.STEREO,
      outputDeviceChannels: options.outputChannels || 8,
    });

    this.matrix = options.matrix instanceof AudioMatrixMixer
      ? options.matrix
      : new AudioMatrixMixer(this.channels, options.outputChannels || 8, target);

    this.updateEffectiveDuration();
  }

  updateEffectiveDuration() {
    const rawSpan = Math.max(0.01, this.outPoint - this.inPoint);
    const speed = Math.max(0.1, this.playbackRate);
    if (this.infiniteLoop) {
      this.duration = Infinity;
    } else {
      this.duration = (rawSpan / speed) * this.playCount;
    }
  }

  setInPoint(time) {
    this.inPoint = Math.max(0, Number(time) || 0);
    if (this.outPoint <= this.inPoint) {
      this.outPoint = this.inPoint + 0.1;
    }
    this.updateEffectiveDuration();
  }

  setOutPoint(time) {
    this.outPoint = Math.max(this.inPoint + 0.05, Number(time) || this.inPoint + 1.0);
    this.updateEffectiveDuration();
  }

  setPlaybackRate(rate) {
    this.playbackRate = Math.max(0.2, Math.min(4.0, Number(rate) || 1.0));
    this.updateEffectiveDuration();
  }

  setPitchShift(semitones) {
    this.pitchShift = Math.max(-24, Math.min(24, Number(semitones) || 0));
  }

  addSlice(time, loopCount = 1) {
    const id = `slice_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    const sliceTime = Math.max(this.inPoint, Math.min(this.outPoint, Number(time) || this.inPoint));
    const newSlice = { id, time: sliceTime, loopCount: Math.max(0, loopCount) };
    this.slices.push(newSlice);
    this.slices.sort((a, b) => a.time - b.time);
    return newSlice;
  }

  removeSlice(sliceId) {
    this.slices = this.slices.filter((s) => s.id !== sliceId);
  }

  tick(dt) {
    // Avanza anche il mixer e i VU meter
    if (this.matrix) {
      this.matrix.tick(dt);
    }
    return super.tick(dt);
  }

  toJSON() {
    return {
      ...super.toJSON(),
      filePath: this.filePath,
      sampleRate: this.sampleRate,
      channels: this.channels,
      inPoint: this.inPoint,
      outPoint: this.outPoint,
      playCount: this.playCount,
      infiniteLoop: this.infiniteLoop,
      playbackRate: this.playbackRate,
      pitchShift: this.pitchShift,
      preservePitch: this.preservePitch,
      slices: this.slices,
      matrix: this.matrix ? this.matrix.toJSON() : null,
    };
  }
}
