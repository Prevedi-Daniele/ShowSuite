import EventEmitter from 'events';
import FixtureInstance from './FixtureInstance.js';
import { builtInProfiles } from './builtins/index.js';

/**
 * PatchManager - Gestore del Patch DMX (Universi 1-4) e Collision Detection per ShowSuite
 */
export default class PatchManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.universeCount = options.universeCount || 4;
    this.fixtures = []; // Array di FixtureInstance
  }

  /**
   * Verifica se un range di indirizzi su un dato universo è già occupato
   * @param {number} universe - Universo (1-4)
   * @param {number} startAddress - Indirizzo iniziale (1-512)
   * @param {number} channelCount - Numero di canali occupati
   * @param {string|null} excludeFixtureId - ID fixture da escludere (per controlli di modifica)
   * @returns {boolean} True se c'è collisione, False se libero
   */
  hasCollision(universe, startAddress, channelCount, excludeFixtureId = null) {
    const endAddress = startAddress + channelCount - 1;

    // Controllo limiti dell'universo DMX512
    if (startAddress < 1 || endAddress > 512) {
      return true;
    }

    for (const f of this.fixtures) {
      if (excludeFixtureId && f.id === excludeFixtureId) continue;
      if (f.universe !== universe) continue;

      const fRange = f.getChannelRange();
      // Sovrapposizione intervalli
      if (startAddress <= fRange.end && endAddress >= fRange.start) {
        return true;
      }
    }

    return false;
  }

  /**
   * Trova il primo indirizzo DMX libero su un universo per un dato numero di canali
   * @param {number} universe - Universo (1-4)
   * @param {number} channelCount - Numero canali richiesti
   * @returns {number|null} Indirizzo DMX disponibile (1-512) oppure null se pieno
   */
  findNextAvailableAddress(universe, channelCount) {
    for (let addr = 1; addr <= 512 - channelCount + 1; addr++) {
      if (!this.hasCollision(universe, addr, channelCount)) {
        return addr;
      }
    }
    return null;
  }

  /**
   * Aggiunge un proiettore al patch con verifica automatica
   */
  addFixture(fixture) {
    if (!(fixture instanceof FixtureInstance)) {
      throw new Error('L\'oggetto da aggiungere deve essere un\'istanza di FixtureInstance');
    }

    const range = fixture.getChannelRange();
    if (this.hasCollision(fixture.universe, range.start, range.count)) {
      throw new Error(
        `Collisione DMX sull'Universo ${fixture.universe}: canali ${range.start}-${range.end} già occupati.`
      );
    }

    this.fixtures.push(fixture);
    this.emit('fixture-added', fixture);
    this.emit('patch-changed');
    return fixture;
  }

  /**
   * Rimuove un proiettore per ID
   */
  removeFixture(fixtureId) {
    const idx = this.fixtures.findIndex((f) => f.id === fixtureId);
    if (idx !== -1) {
      const removed = this.fixtures.splice(idx, 1)[0];
      this.emit('fixture-removed', removed);
      this.emit('patch-changed');
      return true;
    }
    return false;
  }

  /**
   * Restituisce tutti i proiettori di un universo
   */
  getFixturesByUniverse(universe) {
    return this.fixtures.filter((f) => f.universe === universe);
  }

  /**
   * Restituisce un proiettore dato il suo ID
   */
  getFixtureById(id) {
    return this.fixtures.find((f) => f.id === id) || null;
  }

  /**
   * Esegue il rendering di tutti i proiettori patchati direttamente nei buffer del DmxEngine
   * @param {Object} dmxEngine - Istanza del DmxEngine
   */
  renderAllToDmx(dmxEngine) {
    if (!dmxEngine) return;

    for (let u = 1; u <= this.universeCount; u++) {
      const uBuffer = dmxEngine.getUniverseData(u);
      if (!uBuffer) continue;

      // Renderizza ogni fixture assegnata a questo universo
      const uFixtures = this.getFixturesByUniverse(u);
      for (const fix of uFixtures) {
        fix.renderToDmx(uBuffer);
      }
    }
  }

  /**
   * Esporta l'intera configurazione di patch in un oggetto serializzabile JSON
   */
  exportToJson() {
    return {
      version: '1.0',
      universeCount: this.universeCount,
      fixtures: this.fixtures.map((f) => ({
        id: f.id,
        name: f.name,
        profileId: f.profile?.id,
        modeName: f.mode?.name,
        universe: f.universe,
        address: f.address,
        position: f.position,
        calibration: f.calibration,
      })),
    };
  }
}
