/**
 * AudioFadeController.js — Controller per Fade temporizzati della matrice audio (QLab 5)
 * 
 * Gestisce:
 * - Dissolvenze temporizzate su Master, Fader di Uscita, Trim d'ingresso e singoli crosspoint
 * - Curve di interpolazione (Linear, Smoothstep S-curve, Exponential, Decibel logaritmico)
 * - Avanzamento fluido a 60 FPS con precisione di interpolazione
 */

import { FadeCurveType, interpolateCurve, MIN_DB, MAX_DB } from './AudioMath.js';

export default class AudioFadeController {
  constructor(mixer) {
    this.mixer = mixer;
    this.activeFade = null;
  }

  /**
   * Avvia una dissolvenza temporizzata sulla matrice audio
   * 
   * @param {Object} targetLevels Oggetto contenente i livelli target:
   *   - master: number (dB)
   *   - outputMasters: { [outIdx]: number (dB) }
   *   - inputTrims: { [inIdx]: number (dB) }
   *   - crosspoints: Array<{ inIdx: number, outIdx: number, targetDb: number }>
   * @param {number} duration Durata della dissolvenza in secondi
   * @param {string} curve Tipo di curva ('smoothstep', 'linear', 'exponential', 'decibel')
   * @param {Function} onComplete Callback facoltativo al completamento
   */
  startFade(targetLevels = {}, duration = 1.0, curve = FadeCurveType.SMOOTHSTEP, onComplete = null) {
    if (!this.mixer) return false;

    const fadeDuration = Math.max(0.01, Number(duration) || 1.0);

    // Cattura lo stato di partenza
    const fadePlan = {
      duration: fadeDuration,
      elapsedTime: 0,
      curve,
      onComplete,
      isFading: true,
      items: [],
    };

    // 1. Master Level
    if (targetLevels.master !== undefined) {
      fadePlan.items.push({
        type: 'master',
        startDb: this.mixer.masterLevel,
        targetDb: Math.min(MAX_DB, targetLevels.master),
      });
    }

    // 2. Output Masters
    if (targetLevels.outputMasters && typeof targetLevels.outputMasters === 'object') {
      for (const [outStr, targetDb] of Object.entries(targetLevels.outputMasters)) {
        const outIdx = parseInt(outStr, 10);
        if (outIdx >= 0 && outIdx < this.mixer.outputCount) {
          fadePlan.items.push({
            type: 'outputMaster',
            outIdx,
            startDb: this.mixer.outputMasters[outIdx],
            targetDb: Math.min(MAX_DB, targetDb),
          });
        }
      }
    }

    // 3. Input Trims
    if (targetLevels.inputTrims && typeof targetLevels.inputTrims === 'object') {
      for (const [inStr, targetDb] of Object.entries(targetLevels.inputTrims)) {
        const inIdx = parseInt(inStr, 10);
        if (inIdx >= 0 && inIdx < this.mixer.inputCount) {
          fadePlan.items.push({
            type: 'inputTrim',
            inIdx,
            startDb: this.mixer.inputTrims[inIdx],
            targetDb: Math.min(MAX_DB, targetDb),
          });
        }
      }
    }

    // 4. Crosspoints
    if (Array.isArray(targetLevels.crosspoints)) {
      for (const cp of targetLevels.crosspoints) {
        const { inIdx, outIdx, targetDb } = cp;
        if (
          inIdx >= 0 &&
          inIdx < this.mixer.inputCount &&
          outIdx >= 0 &&
          outIdx < this.mixer.outputCount
        ) {
          fadePlan.items.push({
            type: 'crosspoint',
            inIdx,
            outIdx,
            startDb: this.mixer.crosspoints[inIdx][outIdx],
            targetDb: Math.min(MAX_DB, targetDb),
          });
        }
      }
    }

    this.activeFade = fadePlan;
    return true;
  }

  /**
   * Avanza la dissolvenza temporizzata di dt secondi
   * 
   * @param {number} dt Delta time in secondi (es. 1/60s)
   * @returns {boolean} true se la dissolvenza è ancora attiva, false se terminata
   */
  tick(dt) {
    if (!this.activeFade || !this.activeFade.isFading) {
      return false;
    }

    const fade = this.activeFade;
    fade.elapsedTime += dt;
    const rawT = Math.min(1.0, fade.elapsedTime / fade.duration);
    const curveT = interpolateCurve(rawT, fade.curve);

    // Applica l'interpolazione a tutti gli elementi della dissolvenza
    for (const item of fade.items) {
      const currentDb = item.startDb + (item.targetDb - item.startDb) * curveT;

      switch (item.type) {
        case 'master':
          this.mixer.setMaster(currentDb);
          break;
        case 'outputMaster':
          this.mixer.setOutputMaster(item.outIdx, currentDb);
          break;
        case 'inputTrim':
          this.mixer.setInputTrim(item.inIdx, currentDb);
          break;
        case 'crosspoint':
          this.mixer.setCrosspoint(item.inIdx, item.outIdx, currentDb);
          break;
      }
    }

    // Se completato
    if (rawT >= 1.0) {
      fade.isFading = false;
      const callback = fade.onComplete;
      this.activeFade = null;
      if (typeof callback === 'function') {
        callback();
      }
      return false;
    }

    return true;
  }

  stopFade() {
    if (this.activeFade) {
      this.activeFade.isFading = false;
      this.activeFade = null;
      return true;
    }
    return false;
  }

  isFading() {
    return Boolean(this.activeFade && this.activeFade.isFading);
  }

  getProgress() {
    if (!this.activeFade) return 1.0;
    return Math.min(1.0, this.activeFade.elapsedTime / this.activeFade.duration);
  }
}
