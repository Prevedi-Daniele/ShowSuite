/**
 * MotionGenerators - Generatori procedurali di traiettorie 2D Pan / Tilt per teste mobili
 * Supporta: Cerchio/Ellisse, Figura a 8 (Lissajous), Spirale e Oscillazione Lineare.
 */

export const MotionShape = {
  CIRCLE: 'circle',
  FIGURE_EIGHT: 'figure_eight',
  SPIRAL: 'spiral',
  LINEAR: 'linear',
};

export default class MotionGenerators {
  /**
   * Valuta le coordinate Pan & Tilt per una forma geometrica alla fase t
   * @param {string} shape - Tipo di traiettoria (MotionShape)
   * @param {number} t - Fase normalizzata (0.0 .. 1.0)
   * @param {Object} options - Configurazione (center, size, rotation)
   * @returns {{ pan: number, tilt: number }} Coordinate normalizzate [0, 1]
   */
  static evaluate(shape, t, options = {}) {
    const centerPan = options.center?.pan !== undefined ? options.center.pan : 0.5;
    const centerTilt = options.center?.tilt !== undefined ? options.center.tilt : 0.5;
    const sizeX = options.size?.x !== undefined ? options.size.x : 0.25;
    const sizeY = options.size?.y !== undefined ? options.size.y : 0.25;
    const rotationDeg = options.rotation || 0;
    const rotRad = (rotationDeg * Math.PI) / 180;

    const angle = t * 2 * Math.PI;
    let localX = 0;
    let localY = 0;

    switch (shape) {
      case MotionShape.CIRCLE: {
        // Cerchio / Ellisse standard
        localX = Math.cos(angle) * sizeX;
        localY = Math.sin(angle) * sizeY;
        break;
      }

      case MotionShape.FIGURE_EIGHT: {
        // Figura a 8 (curva di Lissajous con rapporto armonico 1:2)
        localX = Math.sin(angle) * sizeX;
        localY = Math.sin(2 * angle) * 0.5 * sizeY;
        break;
      }

      case MotionShape.SPIRAL: {
        // Spirale ciclica che si allarga e restringe armonicamente
        const radiusMod = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(angle * 0.5));
        localX = Math.cos(angle) * sizeX * radiusMod;
        localY = Math.sin(angle) * sizeY * radiusMod;
        break;
      }

      case MotionShape.LINEAR: {
        // Oscillazione lineare avanti e indietro lungo l'asse
        const osc = Math.sin(angle);
        localX = osc * sizeX;
        localY = 0;
        break;
      }

      default:
        localX = Math.cos(angle) * sizeX;
        localY = Math.sin(angle) * sizeY;
    }

    // Applica rotazione 2D del piano di movimento
    const rotatedX = localX * Math.cos(rotRad) - localY * Math.sin(rotRad);
    const rotatedY = localX * Math.sin(rotRad) + localY * Math.cos(rotRad);

    const pan = Math.max(0, Math.min(1, centerPan + rotatedX));
    const tilt = Math.max(0, Math.min(1, centerTilt + rotatedY));

    return { pan, tilt };
  }
}
