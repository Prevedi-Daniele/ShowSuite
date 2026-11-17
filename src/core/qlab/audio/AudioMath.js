/**
 * AudioMath.js — Utilità matematiche e conversioni dB/lineare per Audio Matrix Mixer (QLab 5)
 */

export const MIN_DB = -60.0;     // Sotto i -60 dB viene considerato silenzio (-Infinity)
export const MAX_DB = 12.0;      // Headroom massimo consentito (+12 dB)
export const NEG_INF_DB = -100.0; // Valore sentinella per mute / silenzio assoluto

/**
 * Converte un livello in decibel (dB) in guadagno lineare [0.0, ...].
 * - Valori <= MIN_DB (-60 dB) restituiscono 0.0 (silenzio perfetto).
 * - 0 dB restituisce 1.0 (unity gain).
 * - +6 dB restituisce ~2.0 (raddoppio ampiezza).
 * 
 * @param {number} db Livello in dB
 * @returns {number} Guadagno lineare
 */
export function dbToLinear(db) {
  if (db === undefined || db === null || isNaN(db) || db <= MIN_DB) {
    return 0.0;
  }
  const clampedDb = Math.min(MAX_DB, db);
  return Math.pow(10, clampedDb / 20);
}

/**
 * Converte un guadagno lineare in decibel (dB).
 * - Valori <= 0.001 restituiscono NEG_INF_DB (-100 dB).
 * - 1.0 restituisce 0 dB.
 * 
 * @param {number} linear Guadagno lineare
 * @returns {number} Livello in decibel
 */
export function linearToDb(linear) {
  if (linear === undefined || linear === null || isNaN(linear) || linear <= 0.001) {
    return NEG_INF_DB;
  }
  const db = 20 * Math.log10(linear);
  return Math.max(NEG_INF_DB, Math.min(MAX_DB, db));
}

/**
 * Formatta un valore dB per l'interfaccia (es. "+0.0", "-6.5", "-INF")
 */
export function formatDb(db) {
  if (db === undefined || db === null || isNaN(db) || db <= MIN_DB) {
    return '-INF';
  }
  const sign = db > 0 ? '+' : '';
  return `${sign}${db.toFixed(1)} dB`;
}

/**
 * Tipi di curve di dissolvenza supportati per i Fade audio
 */
export const FadeCurveType = {
  LINEAR: 'linear',
  SMOOTHSTEP: 'smoothstep', // S-Curve standard QLab (Ease-in / Ease-out)
  EXPONENTIAL: 'exponential',
  DECIBEL: 'decibel',       // Dissolvenza percettiva logaritmica
};

/**
 * Calcola il fattore di interpolazione t (0..1) in base alla curva
 * 
 * @param {number} t Progresso temporale normalizzato [0.0, 1.0]
 * @param {string} curve Tipo di curva
 * @returns {number} Progresso interpolato [0.0, 1.0]
 */
export function interpolateCurve(t, curve = FadeCurveType.SMOOTHSTEP) {
  const clampedT = Math.max(0, Math.min(1, t));

  switch (curve) {
    case FadeCurveType.LINEAR:
      return clampedT;

    case FadeCurveType.SMOOTHSTEP:
      // Hermite smoothstep: 3t^2 - 2t^3
      return clampedT * clampedT * (3 - 2 * clampedT);

    case FadeCurveType.EXPONENTIAL:
      // Crescita esponenziale
      return (Math.exp(clampedT * 3) - 1) / (Math.exp(3) - 1);

    case FadeCurveType.DECIBEL:
      // Dissolvenza logaritmica naturale per l'udito umano
      if (clampedT <= 0) return 0;
      return Math.pow(clampedT, 2.5);

    default:
      return clampedT;
  }
}
