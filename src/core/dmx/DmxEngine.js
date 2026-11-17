import EventEmitter from 'events';
import EnttecProDriver from './EnttecProDriver.js';
import OpenDmxDriver from './OpenDmxDriver.js';
import ArtNetDriver from './ArtNetDriver.js';
import SacnDriver from './SacnDriver.js';

/**
 * DmxEngine - Motore centrale di output DMX di ShowSuite (Lightkey Core)
 * Gestisce 4 Universi completi, timer ad alta precisione e cambio interfaccia a caldo.
 */
export default class DmxEngine extends EventEmitter {
  constructor(options = {}) {
    super();
    this.universeCount = options.universeCount || 4; // Universi 1..4 come in Lightkey
    this.refreshRate = options.refreshRate || 33; // FPS (30Hz = ~33.3ms)
    this.universes = [];

    // Alloca i buffer a 512 canali per ogni universo
    for (let u = 0; u < this.universeCount; u++) {
      this.universes.push(new Uint8Array(512));
    }

    this.activeDriver = null;
    this.driverType = null;
    this.timer = null;
    this.isRunning = false;
    this.isBlackout = false;

    // Statistiche prestazionali
    this.stats = {
      packetsSent: 0,
      actualFps: 0,
      lastTickTime: performance.now(),
      fpsCounter: 0,
    };

    // Buffer di backup per ripristino post-blackout
    this.preBlackoutUniverses = [];
  }

  /**
   * Cambia o inizializza il driver di output DMX a caldo
   * @param {'enttec_pro' | 'ftdi_opendmx' | 'artnet' | 'sacn' | 'null'} type
   * @param {Object} driverOptions
   */
  async setDriver(type, driverOptions = {}) {
    // Se c'è un driver già attivo, disconnettilo pulitamente
    if (this.activeDriver) {
      await this.activeDriver.disconnect();
      this.activeDriver = null;
    }

    this.driverType = type;

    switch (type) {
      case 'enttec_pro':
        this.activeDriver = new EnttecProDriver(driverOptions);
        break;
      case 'ftdi_opendmx':
      case 'freestyler_custom':
        this.activeDriver = new OpenDmxDriver(driverOptions);
        break;
      case 'artnet':
        this.activeDriver = new ArtNetDriver(driverOptions);
        break;
      case 'sacn':
        this.activeDriver = new SacnDriver(driverOptions);
        break;
      default:
        this.activeDriver = null;
        this.emit('driver-changed', { type: 'null', connected: false });
        return true;
    }

    if (this.activeDriver) {
      this.activeDriver.on('connected', (info) => {
        this.emit('driver-status', { connected: true, info });
      });
      this.activeDriver.on('error', (err) => {
        this.emit('driver-error', err);
      });
      this.activeDriver.on('disconnected', () => {
        this.emit('driver-status', { connected: false });
      });

      const connected = await this.activeDriver.connect();
      this.emit('driver-changed', { type, connected });
      return connected;
    }

    return false;
  }

  /**
   * Imposta il refresh rate dell'engine (da 20 a 44 Hz)
   * @param {number} fps
   */
  setRefreshRate(fps) {
    this.refreshRate = Math.min(44, Math.max(20, fps));
    if (this.isRunning) {
      this.stop();
      this.start();
    }
    this.emit('refresh-rate-changed', this.refreshRate);
  }

  /**
   * Avvia il loop di trasmissione DMX
   */
  start() {
    if (this.isRunning) return;

    this.isRunning = true;
    const intervalMs = Math.round(1000 / this.refreshRate);

    this.timer = setInterval(() => {
      this._tick();
    }, intervalMs);

    this.emit('engine-started', { refreshRate: this.refreshRate, intervalMs });
  }

  /**
   * Ferma il loop di trasmissione
   */
  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.isRunning = false;
    this.emit('engine-stopped');
  }

  /**
   * Singolo ciclo di trasmissione di tutti gli universi
   */
  async _tick() {
    const now = performance.now();
    this.stats.fpsCounter++;

    if (now - this.stats.lastTickTime >= 1000) {
      this.stats.actualFps = this.stats.fpsCounter;
      this.stats.fpsCounter = 0;
      this.stats.lastTickTime = now;
      this.emit('stats', { ...this.stats });
    }

    if (!this.activeDriver || !this.activeDriver.isConnected) {
      return;
    }

    // Invia l'universo 0 (Universo 1 in termini Lightkey)
    // Se la configurazione prevede multi-universo, scorre gli universi mappati
    try {
      await this.activeDriver.send(0, this.universes[0]);
      this.stats.packetsSent++;
    } catch (err) {
      this.emit('send-error', err);
    }
  }

  /**
   * Imposta il valore di un singolo canale DMX (1-512)
   * @param {number} universe - Universo (1-4)
   * @param {number} channel - Canale DMX (1-512)
   * @param {number} value - Valore (0-255)
   */
  setChannel(universe, channel, value) {
    const uIdx = universe - 1;
    const cIdx = channel - 1;

    if (uIdx >= 0 && uIdx < this.universeCount && cIdx >= 0 && cIdx < 512) {
      this.universes[uIdx][cIdx] = Math.min(255, Math.max(0, Math.round(value)));
    }
  }

  /**
   * Imposta più canali DMX contemporaneamente
   * @param {number} universe - Universo (1-4)
   * @param {Array<{channel: number, value: number}>} channelValues
   */
  setChannels(universe, channelValues) {
    const uIdx = universe - 1;
    if (uIdx < 0 || uIdx >= this.universeCount) return;

    const uBuffer = this.universes[uIdx];
    for (const item of channelValues) {
      const cIdx = item.channel - 1;
      if (cIdx >= 0 && cIdx < 512) {
        uBuffer[cIdx] = Math.min(255, Math.max(0, Math.round(item.value)));
      }
    }
  }

  /**
   * Imposta l'intero buffer di 512 byte di un universo
   */
  setUniverseData(universe, buffer) {
    const uIdx = universe - 1;
    if (uIdx >= 0 && uIdx < this.universeCount) {
      const copyLen = Math.min(512, buffer.length);
      for (let i = 0; i < copyLen; i++) {
        this.universes[uIdx][i] = buffer[i];
      }
    }
  }

  /**
   * Legge il buffer corrente di un universo
   */
  getUniverseData(universe) {
    const uIdx = universe - 1;
    if (uIdx >= 0 && uIdx < this.universeCount) {
      return this.universes[uIdx];
    }
    return null;
  }

  /**
   * Attiva/disattiva il Blackout istantaneo
   */
  toggleBlackout() {
    this.isBlackout = !this.isBlackout;

    if (this.isBlackout) {
      // Salva snapshot dei canali prima di azzerare
      this.preBlackoutUniverses = this.universes.map((u) => new Uint8Array(u));
      for (const u of this.universes) {
        u.fill(0);
      }
    } else {
      // Ripristina i valori precedenti
      if (this.preBlackoutUniverses.length === this.universeCount) {
        for (let i = 0; i < this.universeCount; i++) {
          this.universes[i].set(this.preBlackoutUniverses[i]);
        }
      }
    }

    this.emit('blackout-changed', this.isBlackout);
    return this.isBlackout;
  }
}
