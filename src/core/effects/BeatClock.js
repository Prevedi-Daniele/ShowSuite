/**
 * BeatClock - Generatore di clock musicale, sincronizzazione al Beat e Tap Tempo per ShowSuite
 * Fornisce una fase continua perfettamente allineata al BPM per tutti gli effetti dinamici.
 */

export const MusicalDivision = {
  DIV_1_16: '1/16', // Semicroma (0.25 beat)
  DIV_1_8: '1/8',   // Croma (0.5 beat)
  DIV_1_4: '1/4',   // Semiminima (1 beat - 1 quarto)
  DIV_1_2: '1/2',   // Minima (2 beat)
  DIV_1_1: '1/1',   // 1 Misura / 1 Bar (4 beat)
  DIV_2_1: '2/1',   // 2 Misure (8 beat)
  DIV_4_1: '4/1',   // 4 Misure (16 beat)
  DIV_8_1: '8/1',   // 8 Misure (32 beat)
};

// Moltiplicatori di beat per ciascuna suddivisione
const divisionMultipliers = {
  [MusicalDivision.DIV_1_16]: 0.25,
  [MusicalDivision.DIV_1_8]: 0.5,
  [MusicalDivision.DIV_1_4]: 1.0,
  [MusicalDivision.DIV_1_2]: 2.0,
  [MusicalDivision.DIV_1_1]: 4.0,
  [MusicalDivision.DIV_2_1]: 8.0,
  [MusicalDivision.DIV_4_1]: 16.0,
  [MusicalDivision.DIV_8_1]: 32.0,
};

export default class BeatClock {
  constructor(initialBpm = 120.0) {
    this.bpm = initialBpm;
    this.anchorTime = Date.now(); // Tempo di riferimento per fase 0
    this.tapHistory = [];
    this.lastTapTime = 0;
    this.lastBeatNumber = -1;
  }

  setBpm(newBpm) {
    this.bpm = Math.max(20, Math.min(320, parseFloat(newBpm) || 120.0));
  }

  /**
   * Resetta la fase allineandola all'istante corrente (Downbeat)
   */
  resync(now = Date.now()) {
    this.anchorTime = now;
  }

  /**
   * Registra un tocco di Tap Tempo. Calcola la media degli intervalli recenti.
   * Resetta la cronologia se passano più di 2.5 secondi tra due tap.
   */
  tap(now = Date.now()) {
    // Se è passato troppo tempo dall'ultimo tap, riavvia la sequenza
    if (now - this.lastTapTime > 2500) {
      this.tapHistory = [];
    }

    this.tapHistory.push(now);
    this.lastTapTime = now;
    this.resync(now); // Allinea il downbeat all'istante del tap

    if (this.tapHistory.length >= 2) {
      // Mantieni gli ultimi 6 tap per una media scorrevole stabile
      if (this.tapHistory.length > 6) {
        this.tapHistory.shift();
      }

      let totalDelta = 0;
      for (let i = 1; i < this.tapHistory.length; i++) {
        totalDelta += this.tapHistory[i] - this.tapHistory[i - 1];
      }

      const avgDeltaMs = totalDelta / (this.tapHistory.length - 1);
      if (avgDeltaMs > 0) {
        const calculatedBpm = 60000 / avgDeltaMs;
        this.setBpm(Number(calculatedBpm.toFixed(1)));
      }
    }

    return this.bpm;
  }

  /**
   * Restituisce la durata in millisecondi di un singolo quarto (1 beat)
   */
  getBeatDurationMs() {
    return 60000 / this.bpm;
  }

  /**
   * Calcola la fase continua in [0, 1) per una determinata suddivisione musicale
   * @param {number} now - Timestamp corrente
   * @param {string} division - Suddivisione (MusicalDivision)
   * @returns {number} Fase normalizzata in [0, 1)
   */
  getPhase(now = Date.now(), division = MusicalDivision.DIV_1_1) {
    const beatDurationMs = this.getBeatDurationMs();
    const multiplier = divisionMultipliers[division] || 4.0;
    const cycleDurationMs = beatDurationMs * multiplier;

    const elapsed = now - this.anchorTime;
    const rawPhase = (elapsed / cycleDurationMs) % 1.0;
    return rawPhase < 0 ? rawPhase + 1.0 : rawPhase;
  }

  /**
   * Restituisce true all'istante di ogni beat (downbeat) per animazioni o trigger a tempo
   */
  checkBeatPulse(now = Date.now()) {
    const elapsed = now - this.anchorTime;
    const currentBeat = Math.floor(elapsed / this.getBeatDurationMs());
    if (currentBeat !== this.lastBeatNumber) {
      this.lastBeatNumber = currentBeat;
      return true;
    }
    return false;
  }
}
