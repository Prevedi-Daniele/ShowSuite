/**
 * AudioTarget.js — Modello dati per il target audio multicanale di QLab 5
 * 
 * Gestisce:
 * - Metadati del file sorgente (durata, sample rate, canali in ingresso)
 * - Mappatura dei canali d'uscita verso patch fisici (es. Dante, ASIO, WASAPI, CoreAudio/ALSA)
 * - Nomi delle piste e configurazioni surround (Stereo, Quad, 5.1, 7.1, Multi-point)
 */

export const SurroundProfile = {
  MONO: 'mono',         // 1ch
  STEREO: 'stereo',     // 2ch (L, R)
  LCR: 'lcr',           // 3ch (L, C, R)
  QUAD: 'quad',         // 4ch (L, R, Ls, Rs)
  SURROUND_5_1: '5.1',  // 6ch (L, R, C, LFE, Ls, Rs)
  SURROUND_7_1: '7.1',  // 8ch (L, R, C, LFE, Ls, Rs, Bsl, Bsr)
  CUSTOM: 'custom',
};

const DEFAULT_SURROUND_NAMES = {
  [SurroundProfile.MONO]: ['Main'],
  [SurroundProfile.STEREO]: ['Left', 'Right'],
  [SurroundProfile.LCR]: ['Left', 'Center', 'Right'],
  [SurroundProfile.QUAD]: ['Left Front', 'Right Front', 'Left Rear', 'Right Rear'],
  [SurroundProfile.SURROUND_5_1]: ['Left', 'Right', 'Center', 'Sub / LFE', 'Left Surround', 'Right Surround'],
  [SurroundProfile.SURROUND_7_1]: [
    'Left', 'Right', 'Center', 'Sub / LFE', 'Left Surround', 'Right Surround', 'Back Left', 'Back Right'
  ],
};

export default class AudioTarget {
  constructor(options = {}) {
    this.id = options.id || `audio_target_${Date.now()}`;
    this.name = options.name || 'Sorgente Audio Multicanale';
    this.filePath = options.filePath || null;
    this.duration = Math.max(0, Number(options.duration) || 0);
    this.sampleRate = options.sampleRate || 48000;
    this.inputChannels = Math.max(1, parseInt(options.inputChannels, 10) || 2);
    this.profile = options.profile || (this.inputChannels === 6 ? SurroundProfile.SURROUND_5_1 : SurroundProfile.STEREO);

    // Etichette dei canali d'ingresso
    this.inputChannelNames = Array.isArray(options.inputChannelNames)
      ? options.inputChannelNames
      : this._generateDefaultNames(this.inputChannels, this.profile);

    // Patch di destinazione hardware (es. Scheda Audio USB, Loopback)
    this.outputDeviceName = options.outputDeviceName || 'Default System Audio';
    this.outputDeviceChannels = Math.max(1, parseInt(options.outputDeviceChannels, 10) || 8);
  }

  _generateDefaultNames(count, profile) {
    if (DEFAULT_SURROUND_NAMES[profile] && DEFAULT_SURROUND_NAMES[profile].length === count) {
      return [...DEFAULT_SURROUND_NAMES[profile]];
    }
    return Array.from({ length: count }, (_, i) => `In ${i + 1}`);
  }

  setInputChannels(count, profile = SurroundProfile.CUSTOM) {
    this.inputChannels = Math.max(1, count);
    this.profile = profile;
    this.inputChannelNames = this._generateDefaultNames(this.inputChannels, this.profile);
  }

  setOutputDevice(name, channels = 8) {
    this.outputDeviceName = name;
    this.outputDeviceChannels = Math.max(1, channels);
  }

  toJSON() {
    return {
      id: this.id,
      name: this.name,
      filePath: this.filePath,
      duration: this.duration,
      sampleRate: this.sampleRate,
      inputChannels: this.inputChannels,
      profile: this.profile,
      inputChannelNames: this.inputChannelNames,
      outputDeviceName: this.outputDeviceName,
      outputDeviceChannels: this.outputDeviceChannels,
    };
  }
}
