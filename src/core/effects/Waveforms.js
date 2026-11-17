/**
 * Waveforms - Forme d'onda matematiche e curve di Bézier personalizzabili per l'Effects Engine
 * Tutte le funzioni accettano una fase normalizzata t in [0, 1) e restituiscono un valore in [0, 1].
 */

export const WaveformType = {
  SINE: 'sine',
  SAWTOOTH: 'sawtooth',
  RAMP: 'ramp', // Dente di sega invertito (salita continua e snap a zero)
  SQUARE: 'square',
  TRIANGLE: 'triangle',
  BEZIER: 'bezier',
};

export default class Waveforms {
  /**
   * Calcola il valore della forma d'onda specificata alla fase t
   * @param {string} type - Tipo di onda (WaveformType)
   * @param {number} t - Fase normalizzata (0.0 .. 1.0)
   * @param {Object} options - Parametri addizionali (dutyCycle, bezierPoints)
   * @returns {number} Valore normalizzato in [0, 1]
   */
  static evaluate(type, t, options = {}) {
    // Normalizza t nell'intervallo [0, 1)
    const phase = ((t % 1) + 1) % 1;

    switch (type) {
      case WaveformType.SINE: {
        // Onda sinusoidale morbida da 0 a 1: 0.5 + 0.5 * sin(2*PI * phase - PI/2)
        // con partenza dal minimo a phase=0
        return 0.5 + 0.5 * Math.sin(2 * Math.PI * phase - Math.PI / 2);
      }

      case WaveformType.SAWTOOTH: {
        // Discesa lineare da 1 a 0 con snap a 1
        return 1.0 - phase;
      }

      case WaveformType.RAMP: {
        // Salita lineare da 0 a 1 con snap a 0
        return phase;
      }

      case WaveformType.SQUARE: {
        // Onda quadra con duty cycle regolabile (default 50%)
        const duty = options.dutyCycle !== undefined ? options.dutyCycle : 0.5;
        return phase < duty ? 1.0 : 0.0;
      }

      case WaveformType.TRIANGLE: {
        // Salita triangolare da 0 a 1 e discesa da 1 a 0
        return phase < 0.5 ? phase * 2.0 : 2.0 - phase * 2.0;
      }

      case WaveformType.BEZIER: {
        // Curva cubica di Bézier P0=(0,0), P1=(x1,y1), P2=(x2,y2), P3=(1,1)
        const p1x = options.p1x !== undefined ? options.p1x : 0.25;
        const p1y = options.p1y !== undefined ? options.p1y : 0.1;
        const p2x = options.p2x !== undefined ? options.p2x : 0.25;
        const p2y = options.p2y !== undefined ? options.p2y : 1.0;
        return this.evaluateCubicBezier(phase, p1x, p1y, p2x, p2y);
      }

      default:
        return phase;
    }
  }

  /**
   * Risolve una curva cubica di Bézier per x = t e restituisce y (simile a CSS cubic-bezier)
   */
  static evaluateCubicBezier(t, x1, y1, x2, y2) {
    if (t <= 0) return 0;
    if (t >= 1) return 1;

    // Risoluzione dell'ascissa x(u) = t tramite metodo di Newton-Raphson per trovare u
    let u = t;
    for (let i = 0; i < 8; i++) {
      const currentX = this.bezierCoord(u, x1, x2) - t;
      if (Math.abs(currentX) < 1e-5) break;
      const slope = this.bezierSlope(u, x1, x2);
      if (Math.abs(slope) < 1e-5) break;
      u -= currentX / slope;
      u = Math.max(0, Math.min(1, u));
    }

    return Math.max(0, Math.min(1, this.bezierCoord(u, y1, y2)));
  }

  static bezierCoord(u, p1, p2) {
    // 3*(1-u)^2 * u * p1 + 3*(1-u) * u^2 * p2 + u^3
    const oneMinusU = 1 - u;
    return 3 * oneMinusU * oneMinusU * u * p1 + 3 * oneMinusU * u * u * p2 + u * u * u;
  }

  static bezierSlope(u, p1, p2) {
    const oneMinusU = 1 - u;
    return 3 * oneMinusU * oneMinusU * p1 + 6 * oneMinusU * u * (p2 - p1) + 3 * u * u * (1 - p2);
  }
}
