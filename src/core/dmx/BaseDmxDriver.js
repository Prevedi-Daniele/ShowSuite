import EventEmitter from 'events';

/**
 * BaseDmxDriver - Classe astratta base per qualsiasi hardware o protocollo DMX
 */
export default class BaseDmxDriver extends EventEmitter {
  constructor(name, options = {}) {
    super();
    this.name = name;
    this.options = options;
    this.isConnected = false;
    this.lastError = null;
  }

  /**
   * Connette o apre la porta/socket
   * @returns {Promise<boolean>}
   */
  async connect() {
    throw new Error('Il metodo connect() deve essere implementato dal driver derivato');
  }

  /**
   * Disconnette o chiude la porta/socket
   * @returns {Promise<boolean>}
   */
  async disconnect() {
    throw new Error('Il metodo disconnect() deve essere implementato dal driver derivato');
  }

  /**
   * Invia un frame DMX da 512 canali
   * @param {number} universeIndex - Indice universo (0-based)
   * @param {Uint8Array|Buffer} dmxBuffer - Buffer da 512 byte (canali 1-512)
   * @returns {Promise<boolean>}
   */
  async send(universeIndex, dmxBuffer) {
    throw new Error('Il metodo send() deve essere implementato dal driver derivato');
  }

  /**
   * Ritorna lo stato del driver
   */
  getStatus() {
    return {
      name: this.name,
      connected: this.isConnected,
      error: this.lastError,
      options: this.options,
    };
  }
}
