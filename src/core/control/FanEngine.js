/**
 * FanEngine - Motore di fanning spaziale per proiettori DMX (stile Lightkey)
 * Permette di distribuire attributi (Pan, Tilt, Colore/Hue, Intensità) su più proiettori
 * con curve matematiche: lineare, simmetrica (center-out / ali) e alternata/spread.
 */

export const FanMode = {
  LINEAR: 'linear',       // Da sinistra a destra / dal primo all'ultimo
  SYMMETRIC: 'symmetric', // Dal centro verso l'esterno a specchio (effetto a V / ali)
  SPREAD: 'spread',       // Alternato a coppie o specchiato sui lati
};

export const FanAttribute = {
  PAN: 'pan',
  TILT: 'tilt',
  HUE: 'hue',
  INTENSITY: 'intensity',
};

export default class FanEngine {
  /**
   * Applica il fanning a un insieme di valori
   * @param {number} count - Numero di proiettori selezionati (>= 1)
   * @param {number} baseValue - Valore base centrale (0..1 per pan/tilt/intensity, 0..360 per hue)
   * @param {number} amount - Quantità di fanning (-1.0 a +1.0)
   * @param {string} mode - 'linear' | 'symmetric' | 'spread'
   * @param {string} attribute - 'pan' | 'tilt' | 'hue' | 'intensity'
   * @returns {number[]} Array di valori calcolati per ciascun proiettore
   */
  static calculateFan(count, baseValue, amount, mode = FanMode.LINEAR, attribute = FanAttribute.PAN) {
    if (count <= 1 || amount === 0) {
      return Array(count).fill(baseValue);
    }

    const results = [];
    const isHue = attribute === FanAttribute.HUE;

    // Normalizziamo l'intervallo di escursione
    // Per pan/tilt: escursione massima +/- 0.5 (quindi copre l'intero 0..1)
    // Per hue: escursione massima 180° (o 360° per un giro completo)
    const maxRange = isHue ? 180 : 0.5;
    const spreadDelta = amount * maxRange;

    for (let i = 0; i < count; i++) {
      let factor = 0; // -1 .. +1

      switch (mode) {
        case FanMode.LINEAR: {
          // Distribuzione lineare uniforme: da -1 (primo faro) a +1 (ultimo faro)
          factor = (2 * i) / (count - 1) - 1;
          break;
        }

        case FanMode.SYMMETRIC: {
          // Dal centro (0) verso i bordi (+1 a destra, -1 a sinistra)
          const mid = (count - 1) / 2;
          if (mid === 0) {
            factor = 0;
          } else {
            const distanceFromCenter = (i - mid) / mid; // -1 .. +1
            factor = distanceFromCenter;
          }
          break;
        }

        case FanMode.SPREAD: {
          // A specchio dal centro (valore assoluto: 0 al centro, 1 verso entrambi i lati)
          const mid = (count - 1) / 2;
          if (mid === 0) {
            factor = 0;
          } else {
            factor = Math.abs((i - mid) / mid) * (i < mid ? -1 : 1);
          }
          break;
        }

        default:
          factor = 0;
      }

      let val = baseValue + factor * spreadDelta;

      if (isHue) {
        // Hue circolare (0..360)
        val = ((val % 360) + 360) % 360;
      } else {
        // Clamping tra 0 e 1
        val = Math.max(0, Math.min(1, val));
      }

      results.push(val);
    }

    return results;
  }

  /**
   * Applica il fanning direttamente a un array di istanze o oggetti fixture
   * @param {Array} fixtures - Array di fixture
   * @param {string} attribute - 'pan' | 'tilt' | 'hue' | 'intensity'
   * @param {number} baseValue - Valore base
   * @param {number} amount - Ampiezza fanning (-1..1)
   * @param {string} mode - Modalità di fanning
   */
  static applyToFixtures(fixtures, attribute, baseValue, amount, mode = FanMode.LINEAR) {
    if (!fixtures || fixtures.length === 0) return fixtures;

    const values = this.calculateFan(fixtures.length, baseValue, amount, mode, attribute);

    return fixtures.map((fix, idx) => {
      const val = values[idx];
      const updatedState = { ...fix.state };

      if (attribute === FanAttribute.PAN) {
        updatedState.pan = val;
      } else if (attribute === FanAttribute.TILT) {
        updatedState.tilt = val;
      } else if (attribute === FanAttribute.INTENSITY) {
        updatedState.intensity = val;
      } else if (attribute === FanAttribute.HUE) {
        // Converte Hue calcolato mantenendo saturazione e luminosità attuali
        const rgb = this.hueToRgb(val);
        updatedState.color = {
          ...updatedState.color,
          r: rgb.r,
          g: rgb.g,
          b: rgb.b,
        };
      }

      return {
        ...fix,
        state: updatedState,
      };
    });
  }

  /**
   * Converte Hue (0..360) in RGB standard (saturazione 100%, luminosità 100%)
   */
  static hueToRgb(hue) {
    const h = (hue % 360) / 60;
    const c = 1;
    const x = c * (1 - Math.abs((h % 2) - 1));
    let r = 0, g = 0, b = 0;

    if (h >= 0 && h < 1) { r = c; g = x; b = 0; }
    else if (h >= 1 && h < 2) { r = x; g = c; b = 0; }
    else if (h >= 2 && h < 3) { r = 0; g = c; b = x; }
    else if (h >= 3 && h < 4) { r = 0; g = x; b = c; }
    else if (h >= 4 && h < 5) { r = x; g = 0; b = c; }
    else if (h >= 5 && h < 6) { r = c; g = 0; b = x; }

    return { r, g, b };
  }
}
