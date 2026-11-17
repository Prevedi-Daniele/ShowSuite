/**
 * DipSwitchCalculator - Calcolatore di Dip Switch per indirizzamento DMX (stile Lightkey & FreeStyler)
 */
export default class DipSwitchCalculator {
  /**
   * Converte un indirizzo DMX (1-512) nella configurazione dei 10 dip switch
   * @param {number} address - Indirizzo DMX da 1 a 512
   * @param {boolean} dmxModeDip10 - Se true, il dip 10 è impostato su ON (standard DMX mode su molti fari)
   * @returns {boolean[]} Array di 10 booleani [dip1..dip10], dove true = ON (Up), false = OFF (Down)
   */
  static addressToDipSwitches(address, dmxModeDip10 = true) {
    const clampedAddress = Math.max(1, Math.min(512, Math.floor(address)));
    const dips = [];

    // DIP 1..9 corrispondono ai bit 0..8 (valori 1, 2, 4, 8, 16, 32, 64, 128, 256)
    for (let i = 0; i < 9; i++) {
      const bitValue = 1 << i;
      dips.push((clampedAddress & bitValue) !== 0);
    }

    // DIP 10
    dips.push(!!dmxModeDip10);

    return dips;
  }

  /**
   * Converte un array di dip switch nell'indirizzo DMX risultante
   * @param {boolean[]} dips - Array di booleani
   * @returns {number} Indirizzo DMX calcolato (1-512)
   */
  static dipSwitchesToAddress(dips) {
    let address = 0;
    const len = Math.min(9, dips.length);

    for (let i = 0; i < len; i++) {
      if (dips[i]) {
        address |= (1 << i);
      }
    }

    return address;
  }

  /**
   * Formatta i dip switch in una stringa leggibile (es. "100100000 1" per display o UI)
   */
  static formatDipString(dips) {
    return dips.map((d) => (d ? '1' : '0')).join('');
  }
}
