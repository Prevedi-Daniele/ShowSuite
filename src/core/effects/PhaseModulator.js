/**
 * PhaseModulator - Modulatore di fase e fanning temporale tra proiettori DMX
 * Genera sfasamenti d'onda (offset di fase) su insiemi di fari per effetti onda (waves),
 * inseguimenti (chases) e movimenti sincronizzati o speculari.
 */

export const PhaseDistribution = {
  LINEAR: 'linear',       // Da 0° a N° lungo la fila dei fari
  SYMMETRIC: 'symmetric', // Speculare dal centro verso i due lati
  ODD_EVEN: 'odd_even',   // Fari pari e dispari sfasati a 180°
  RANDOM: 'random',       // Sfasamento casuale ma deterministico per faro
};

export default class PhaseModulator {
  /**
   * Calcola l'offset di fase per ciascun faro nell'insieme
   * @param {number} count - Numero totale di fari (>= 1)
   * @param {string} distribution - Tipo di distribuzione (PhaseDistribution)
   * @param {number} spreadDegrees - Ampiezza totale di sfasamento (es. 360° per un'onda completa)
   * @returns {number[]} Array di offset di fase normalizzati in [0, 1) per ogni faro
   */
  static calculateOffsets(count, distribution = PhaseDistribution.LINEAR, spreadDegrees = 360) {
    if (count <= 1) return [0];

    const spreadFactor = spreadDegrees / 360;
    const offsets = [];

    for (let i = 0; i < count; i++) {
      let phaseOffset = 0;

      switch (distribution) {
        case PhaseDistribution.LINEAR: {
          // Distribuzione uniforme lungo l'array: faro 0 = 0, ultimo faro = spreadFactor
          phaseOffset = (i / (count - 1)) * spreadFactor;
          break;
        }

        case PhaseDistribution.SYMMETRIC: {
          // Sfasamento speculare dal centro verso i due bordi
          const mid = (count - 1) / 2;
          if (mid === 0) {
            phaseOffset = 0;
          } else {
            const distFromCenter = Math.abs(i - mid) / mid;
            phaseOffset = distFromCenter * spreadFactor;
          }
          break;
        }

        case PhaseDistribution.ODD_EVEN: {
          // Fari alternati: fari pari a 0, fari dispari a 180° (o spreadFactor / 2)
          phaseOffset = (i % 2 === 0 ? 0 : 0.5) * spreadFactor;
          break;
        }

        case PhaseDistribution.RANDOM: {
          // Hash pseudo-casuale deterministico basato sull'indice del faro
          const pseudoRand = ((Math.sin(i * 12.9898 + 78.233) * 43758.5453) % 1 + 1) % 1;
          phaseOffset = pseudoRand * spreadFactor;
          break;
        }

        default:
          phaseOffset = (i / (count - 1)) * spreadFactor;
      }

      // Normalizza in [0, 1)
      offsets.push(((phaseOffset % 1) + 1) % 1);
    }

    return offsets;
  }
}
