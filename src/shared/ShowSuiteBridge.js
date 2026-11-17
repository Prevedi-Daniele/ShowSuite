/**
 * ShowSuiteBridge.js — Router e Bridge OSC/ShowControl in-process tra QLab e Lightkey
 * 
 * Permette la comunicazione diretta a latenza zero tra QLab e Lightkey:
 * - Routing interno di messaggi OSC da NetworkCue verso i comandi di Lightkey (/live/...)
 * - Trigger di preset, scene, fader di gruppo, blackout, blind, freeze, Grand Master
 * - Esecuzione cue luci da parte di cue QLab
 * - Configurazione globale attiva/disattiva e tracciamento diagnostico
 */

import { OSCDictionary } from '../core/control/OSCDictionary.js';

class ShowSuiteBridge {
  constructor() {
    this.enabled = true;
    this.dictionary = new OSCDictionary();

    // Riferimenti ai controller condivisi nel processo
    this.liveController = null;
    this.cueEngine = null;
    this.paletteManager = null;
    this.effectsEngine = null;
    this.cueScheduler = null;

    // Cronologia diagnostica dei messaggi instradati internamente
    this.routingHistory = [];
    this.maxHistory = 100;

    // Listeners per eventi UI/diagnostica
    this.listeners = {
      message: [],
      route: [],
      configChange: [],
    };
  }

  // ─── Configurazione e Stato ─────────────────────────────────────

  setEnabled(val) {
    this.enabled = Boolean(val);
    this.emit('configChange', { enabled: this.enabled });
  }

  isEnabled() {
    return this.enabled;
  }

  // ─── Registrazione Motori nel Processo ──────────────────────────

  registerLightkey(engines = {}) {
    if (engines.liveController) this.liveController = engines.liveController;
    if (engines.cueEngine) this.cueEngine = engines.cueEngine;
    if (engines.paletteManager) this.paletteManager = engines.paletteManager;
    if (engines.effectsEngine) this.effectsEngine = engines.effectsEngine;
  }

  registerQLab(engines = {}) {
    if (engines.cueScheduler) this.cueScheduler = engines.cueScheduler;
  }

  getContext() {
    return {
      liveController: this.liveController,
      cueEngine: this.cueEngine,
      paletteManager: this.paletteManager,
      effectsEngine: this.effectsEngine,
      cueScheduler: this.cueScheduler,
    };
  }

  // ─── Routing OSC In-Process ────────────────────────────────────

  /**
   * Riceve ed esegue un comando OSC indirizzato a Lightkey o QLab all'interno dello stesso processo
   * 
   * @param {string} address Indirizzo OSC (es. "/live/blackout", "/live/grandMaster", "/live/cue/go")
   * @param {Array<any>} [args=[]] Argomenti OSC
   * @param {string} [source='qlab'] Modulo di provenienza ('qlab' | 'lightkey')
   * @returns {{ handled: boolean, replyAddress?: string, replyArgs?: Array<any>, data?: any, error?: string }}
   */
  routeOsc(address, args = [], source = 'qlab') {
    if (!this.enabled) {
      return { handled: false, error: 'Bridge OSC interno disabilitato nelle opzioni' };
    }

    if (!address || typeof address !== 'string') {
      return { handled: false, error: 'Indirizzo OSC non valido' };
    }

    const context = this.getContext();
    const result = this.dictionary.dispatch(address, args, context);

    const logEntry = {
      timestamp: Date.now(),
      source,
      address,
      args,
      handled: result.handled,
      result,
    };

    this.routingHistory.push(logEntry);
    if (this.routingHistory.length > this.maxHistory) {
      this.routingHistory.shift();
    }

    this.emit('message', logEntry);
    return result;
  }

  /**
   * Helper per triggerare una specifica cella / preset della griglia Lightkey
   */
  triggerLightkeyCell(cellIndex) {
    return this.routeOsc(`/live/cell/${cellIndex}/trigger`, [], 'qlab');
  }

  /**
   * Helper per triggerare il tasto GO della Cue List di Lightkey
   */
  triggerLightkeyGo() {
    return this.routeOsc('/live/cue/go', [], 'qlab');
  }

  /**
   * Helper per impostare il Grand Master di Lightkey (0..1 o 0..100)
   */
  setLightkeyGrandMaster(level) {
    return this.routeOsc('/live/grandMaster', [level], 'qlab');
  }

  /**
   * Helper per attivare/disattivare il Blackout di Lightkey
   */
  setLightkeyBlackout(state = true) {
    return this.routeOsc('/live/blackout', [state ? 1 : 0], 'qlab');
  }

  // ─── Event Management ──────────────────────────────────────────

  on(event, cb) {
    if (this.listeners[event]) this.listeners[event].push(cb);
    return () => this.off(event, cb);
  }

  off(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(l => l !== cb);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      for (const cb of this.listeners[event]) {
        try { cb(data); } catch (e) { console.error(`Errore nel listener ShowSuiteBridge "${event}":`, e); }
      }
    }
  }
}

// Istanza singleton condivisa nell'intero processo
const showSuiteBridge = new ShowSuiteBridge();
export default showSuiteBridge;
export { ShowSuiteBridge };
