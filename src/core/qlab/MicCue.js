/**
 * MicCue.js — Modello specializzato per le Mic Cue (Live Input) di QLab 5
 * 
 * Estende BaseCue con:
 * - Sorgente live input hardware / microfono
 * - Canali fisici di ingresso (1ch Mono, 2ch Stereo, Multi-Mic)
 * - Gain trim live e VU meter del segnale in ingresso
 * - Istanza AudioMatrixMixer per il routing diretto verso le uscite
 */

import BaseCue from './BaseCue.js';
import { CueType } from './CueTypes.js';
import { AudioMatrixMixer, AudioTarget, SurroundProfile } from './audio/index.js';

export default class MicCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.MIC,
    });

    this.inputDeviceName = options.inputDeviceName || 'Microfono Predefinito';
    this.channels = options.channels || 1;
    this.micGain = options.micGain !== undefined ? Number(options.micGain) : 0.0; // dB

    // Matrice di Missaggio
    const target = new AudioTarget({
      name: this.name,
      inputChannels: this.channels,
      profile: this.channels === 1 ? SurroundProfile.MONO : SurroundProfile.STEREO,
      outputDeviceChannels: options.outputChannels || 8,
    });

    this.matrix = options.matrix instanceof AudioMatrixMixer
      ? options.matrix
      : new AudioMatrixMixer(this.channels, options.outputChannels || 8, target);

    // Se micGain è impostato, applicalo al trim d'ingresso
    for (let i = 0; i < this.channels; i++) {
      this.matrix.setInputTrim(i, this.micGain);
    }
  }

  setMicGain(db) {
    this.micGain = Math.max(-60, Math.min(24, Number(db) || 0));
    for (let i = 0; i < this.channels; i++) {
      this.matrix.setInputTrim(i, this.micGain);
    }
  }

  setInputDevice(deviceName, channels = 1) {
    this.inputDeviceName = deviceName;
    this.channels = Math.max(1, channels);
    this.matrix.resize(this.channels, this.matrix.outputCount);
  }

  tick(dt) {
    if (this.matrix) {
      this.matrix.tick(dt);
    }
    return super.tick(dt);
  }

  toJSON() {
    return {
      ...super.toJSON(),
      inputDeviceName: this.inputDeviceName,
      channels: this.channels,
      micGain: this.micGain,
      matrix: this.matrix ? this.matrix.toJSON() : null,
    };
  }
}
