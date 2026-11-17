/**
 * AudioMatrixMixer.js — Motore Audio Matrix Mixer N x M di QLab 5 per ShowSuite
 * 
 * Implementa:
 * - Matrice di routing completa N Canali Ingresso -> M Canali Uscita
 * - Fader Master, Fader individuali d'Uscita, Trim d'Ingresso e Crosspoint Faders in dB
 * - Calcolo accurato del guadagno lineare effettivo
 * - Mute indipendenti per Master, Ingressi e Uscite
 * - Elaborazione buffer audio PCM Float32 a blocchi con sommatoria e mixing
 * - Misuratori di picco (Peak Meters) con decadimento balistico esponenziale
 * - Motore di dissolvenza temporizzata integrato (AudioFadeController)
 */

import { dbToLinear, linearToDb, MIN_DB, MAX_DB, NEG_INF_DB, FadeCurveType } from './AudioMath.js';
import AudioFadeController from './AudioFadeController.js';
import AudioTarget from './AudioTarget.js';

export default class AudioMatrixMixer {
  /**
   * @param {number} inputCount Numero canali in ingresso (N)
   * @param {number} outputCount Numero canali in uscita (M)
   * @param {AudioTarget|null} target Target audio associato
   */
  constructor(inputCount = 2, outputCount = 2, target = null) {
    this.inputCount = Math.max(1, parseInt(inputCount, 10) || 2);
    this.outputCount = Math.max(1, parseInt(outputCount, 10) || 2);
    this.target = target || new AudioTarget({ inputChannels: this.inputCount, outputDeviceChannels: this.outputCount });

    // Master Fader (livello generale in dB)
    this.masterLevel = 0.0;
    this.masterMute = false;

    // Fader Master di Uscita (M canali) in dB
    this.outputMasters = new Array(this.outputCount).fill(0.0);
    this.outputMutes = new Array(this.outputCount).fill(false);

    // Trim d'Ingresso (N canali) in dB
    this.inputTrims = new Array(this.inputCount).fill(0.0);
    this.inputMutes = new Array(this.inputCount).fill(false);

    // Matrice Crosspoint N x M in dB
    // Default: routing 1:1 diretto (0 dB sulla diagonale, -INF sulle altre celle)
    this.crosspoints = this._createDefaultCrosspoints(this.inputCount, this.outputCount);

    // Misuratori di picco (ampiezza lineare [0.0..1.0])
    this.inputPeaks = new Float32Array(this.inputCount);
    this.outputPeaks = new Float32Array(this.outputCount);
    this.crosspointPeaks = Array.from({ length: this.inputCount }, () => new Float32Array(this.outputCount));

    // Controller per Fade Cues temporizzate
    this.fadeController = new AudioFadeController(this);
  }

  _createDefaultCrosspoints(inCount, outCount) {
    const matrix = [];
    for (let i = 0; i < inCount; i++) {
      const row = new Float32Array(outCount);
      for (let j = 0; j < outCount; j++) {
        // Se 1:1 (diagonale) oppure mono distribuito su L/R se 1 in e 2 out
        if (i === j || (inCount === 1 && j < 2)) {
          row[j] = 0.0;
        } else {
          row[j] = NEG_INF_DB;
        }
      }
      matrix.push(row);
    }
    return matrix;
  }

  // ─── Setters & Getters dei Livelli (in dB) ────────────────────

  setMaster(db) {
    this.masterLevel = Math.max(NEG_INF_DB, Math.min(MAX_DB, Number(db) || 0.0));
  }

  setOutputMaster(outputIdx, db) {
    if (outputIdx >= 0 && outputIdx < this.outputCount) {
      this.outputMasters[outputIdx] = Math.max(NEG_INF_DB, Math.min(MAX_DB, Number(db) || 0.0));
    }
  }

  setInputTrim(inputIdx, db) {
    if (inputIdx >= 0 && inputIdx < this.inputCount) {
      this.inputTrims[inputIdx] = Math.max(NEG_INF_DB, Math.min(MAX_DB, Number(db) || 0.0));
    }
  }

  setCrosspoint(inputIdx, outputIdx, db) {
    if (inputIdx >= 0 && inputIdx < this.inputCount && outputIdx >= 0 && outputIdx < this.outputCount) {
      this.crosspoints[inputIdx][outputIdx] = Math.max(NEG_INF_DB, Math.min(MAX_DB, Number(db) || 0.0));
    }
  }

  getCrosspoint(inputIdx, outputIdx) {
    if (inputIdx >= 0 && inputIdx < this.inputCount && outputIdx >= 0 && outputIdx < this.outputCount) {
      return this.crosspoints[inputIdx][outputIdx];
    }
    return NEG_INF_DB;
  }

  // ─── Mute Toggles ─────────────────────────────────────────────

  setMasterMute(isMuted) {
    this.masterMute = Boolean(isMuted);
  }

  setInputMute(inputIdx, isMuted) {
    if (inputIdx >= 0 && inputIdx < this.inputCount) {
      this.inputMutes[inputIdx] = Boolean(isMuted);
    }
  }

  setOutputMute(outputIdx, isMuted) {
    if (outputIdx >= 0 && outputIdx < this.outputCount) {
      this.outputMutes[outputIdx] = Boolean(isMuted);
    }
  }

  // ─── Calcolo Guadagno Lineare Effettivo ────────────────────────

  /**
   * Calcola il guadagno lineare complessivo tra input i e output j.
   * G = G_master * G_outputMaster[j] * G_inputTrim[i] * G_crosspoint[i][j]
   * 
   * Se qualsiasi elemento è in Mute, il guadagno effettivo è 0.0.
   * 
   * @param {number} inputIdx Indice canale d'ingresso (0..N-1)
   * @param {number} outputIdx Indice canale d'uscita (0..M-1)
   * @returns {number} Guadagno lineare [0.0, ...]
   */
  getEffectiveLinearGain(inputIdx, outputIdx) {
    if (this.masterMute || this.inputMutes[inputIdx] || this.outputMutes[outputIdx]) {
      return 0.0;
    }

    const gMaster = dbToLinear(this.masterLevel);
    if (gMaster <= 0) return 0.0;

    const gOut = dbToLinear(this.outputMasters[outputIdx]);
    if (gOut <= 0) return 0.0;

    const gIn = dbToLinear(this.inputTrims[inputIdx]);
    if (gIn <= 0) return 0.0;

    const gCross = dbToLinear(this.crosspoints[inputIdx][outputIdx]);
    if (gCross <= 0) return 0.0;

    return gMaster * gOut * gIn * gCross;
  }

  // ─── Elaborazione Audio PCM & Peak Metering ────────────────────

  /**
   * Esegue il mixaggio dei buffer PCM in ingresso sui buffer di uscita
   * e calcola i picchi di segnale per ciascun canale.
   * 
   * @param {Array<Float32Array>} inputBuffers Array di N buffer (uno per canale d'ingresso)
   * @param {number} sampleCount Numero di campioni da processare (es. 256, 512, 1024)
   * @returns {Array<Float32Array>} Array di M buffer PCM mixati d'uscita
   */
  process(inputBuffers, sampleCount = 512) {
    // Inizializza i buffer d'uscita a zero
    const outputBuffers = [];
    for (let j = 0; j < this.outputCount; j++) {
      outputBuffers.push(new Float32Array(sampleCount));
    }

    if (!inputBuffers || inputBuffers.length === 0) {
      return outputBuffers;
    }

    // 1. Calcola picchi d'ingresso
    for (let i = 0; i < this.inputCount; i++) {
      const inBuf = inputBuffers[i];
      if (inBuf) {
        let maxPeak = 0;
        for (let s = 0; s < sampleCount; s++) {
          const abs = Math.abs(inBuf[s]);
          if (abs > maxPeak) maxPeak = abs;
        }
        if (maxPeak > this.inputPeaks[i]) {
          this.inputPeaks[i] = maxPeak;
        }
      }
    }

    // 2. Mixaggio a matrice
    for (let j = 0; j < this.outputCount; j++) {
      const outBuf = outputBuffers[j];
      let outMaxPeak = 0;

      for (let i = 0; i < this.inputCount; i++) {
        const inBuf = inputBuffers[i];
        if (!inBuf) continue;

        const gain = this.getEffectiveLinearGain(i, j);
        if (gain <= 0.0) continue;

        let cpMaxPeak = 0;
        for (let s = 0; s < sampleCount; s++) {
          const val = inBuf[s] * gain;
          outBuf[s] += val;
          const absVal = Math.abs(val);
          if (absVal > cpMaxPeak) cpMaxPeak = absVal;
        }

        if (cpMaxPeak > this.crosspointPeaks[i][j]) {
          this.crosspointPeaks[i][j] = cpMaxPeak;
        }
      }

      // Calcola picco finale d'uscita
      for (let s = 0; s < sampleCount; s++) {
        const abs = Math.abs(outBuf[s]);
        if (abs > outMaxPeak) outMaxPeak = abs;
      }
      if (outMaxPeak > this.outputPeaks[j]) {
        this.outputPeaks[j] = outMaxPeak;
      }
    }

    return outputBuffers;
  }

  /**
   * Decadimento balistico esponenziale dei misuratori di picco (Peak Meters)
   * Simula l'inerzia visiva degli indicatori digitali delle console pro audio (es. -20 dB/s)
   * 
   * @param {number} dt Delta time in secondi (es. 1/60s = 0.01667s)
   * @param {number} decayRateDbPerSec Velocità di decadimento in dB al secondo (default: 24 dB/s)
   */
  decayPeaks(dt, decayRateDbPerSec = 24.0) {
    const decayFactor = Math.pow(10, -(decayRateDbPerSec * dt) / 20);

    for (let i = 0; i < this.inputCount; i++) {
      this.inputPeaks[i] = Math.max(0, this.inputPeaks[i] * decayFactor);
      for (let j = 0; j < this.outputCount; j++) {
        this.crosspointPeaks[i][j] = Math.max(0, this.crosspointPeaks[i][j] * decayFactor);
      }
    }

    for (let j = 0; j < this.outputCount; j++) {
      this.outputPeaks[j] = Math.max(0, this.outputPeaks[j] * decayFactor);
    }
  }

  // ─── Integrazione Dissolvenze Temporizzate ──────────────────────

  /**
   * Avvia una dissolvenza programmata sui fader e crosspoint della matrice
   */
  fadeTo(targetLevels, duration = 1.0, curve = FadeCurveType.SMOOTHSTEP, onComplete = null) {
    return this.fadeController.startFade(targetLevels, duration, curve, onComplete);
  }

  stopFade() {
    return this.fadeController.stopFade();
  }

  isFading() {
    return this.fadeController.isFading();
  }

  /**
   * Aggiornamento del frame a 60 FPS (avanza dissolvenza e decadimento VU meter)
   */
  tick(dt) {
    this.fadeController.tick(dt);
    this.decayPeaks(dt);
  }

  // ─── Ridimensionamento Dinamico Matrice ─────────────────────────

  resize(newInputCount, newOutputCount) {
    const newIn = Math.max(1, newInputCount);
    const newOut = Math.max(1, newOutputCount);

    const newMatrix = this._createDefaultCrosspoints(newIn, newOut);
    const newInTrims = new Array(newIn).fill(0.0);
    const newInMutes = new Array(newIn).fill(false);
    const newOutMasters = new Array(newOut).fill(0.0);
    const newOutMutes = new Array(newOut).fill(false);

    // Copia i valori esistenti
    for (let i = 0; i < Math.min(this.inputCount, newIn); i++) {
      newInTrims[i] = this.inputTrims[i];
      newInMutes[i] = this.inputMutes[i];
      for (let j = 0; j < Math.min(this.outputCount, newOut); j++) {
        newMatrix[i][j] = this.crosspoints[i][j];
      }
    }

    for (let j = 0; j < Math.min(this.outputCount, newOut); j++) {
      newOutMasters[j] = this.outputMasters[j];
      newOutMutes[j] = this.outputMutes[j];
    }

    this.inputCount = newIn;
    this.outputCount = newOut;
    this.crosspoints = newMatrix;
    this.inputTrims = newInTrims;
    this.inputMutes = newInMutes;
    this.outputMasters = newOutMasters;
    this.outputMutes = newOutMutes;

    this.inputPeaks = new Float32Array(newIn);
    this.outputPeaks = new Float32Array(newOut);
    this.crosspointPeaks = Array.from({ length: newIn }, () => new Float32Array(newOut));

    if (this.target) {
      this.target.setInputChannels(newIn);
      this.target.setOutputDevice(this.target.outputDeviceName, newOut);
    }
  }

  // ─── Serializzazione JSON ──────────────────────────────────────

  toJSON() {
    return {
      inputCount: this.inputCount,
      outputCount: this.outputCount,
      masterLevel: this.masterLevel,
      masterMute: this.masterMute,
      outputMasters: [...this.outputMasters],
      outputMutes: [...this.outputMutes],
      inputTrims: [...this.inputTrims],
      inputMutes: [...this.inputMutes],
      crosspoints: this.crosspoints.map((row) => Array.from(row)),
      target: this.target ? this.target.toJSON() : null,
    };
  }

  fromJSON(data) {
    if (!data) return;
    this.resize(data.inputCount || 2, data.outputCount || 2);
    if (data.masterLevel !== undefined) this.masterLevel = data.masterLevel;
    if (data.masterMute !== undefined) this.masterMute = data.masterMute;
    if (Array.isArray(data.outputMasters)) this.outputMasters = [...data.outputMasters];
    if (Array.isArray(data.outputMutes)) this.outputMutes = [...data.outputMutes];
    if (Array.isArray(data.inputTrims)) this.inputTrims = [...data.inputTrims];
    if (Array.isArray(data.inputMutes)) this.inputMutes = [...data.inputMutes];
    if (Array.isArray(data.crosspoints)) {
      for (let i = 0; i < Math.min(this.inputCount, data.crosspoints.length); i++) {
        const row = data.crosspoints[i];
        if (Array.isArray(row)) {
          for (let j = 0; j < Math.min(this.outputCount, row.length); j++) {
            this.crosspoints[i][j] = row[j];
          }
        }
      }
    }
  }
}
