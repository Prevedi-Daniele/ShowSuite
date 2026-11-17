/**
 * CueScheduler.js — Scheduler del motore Cue di QLab 5 per ShowSuite
 * 
 * Gestisce:
 * - Sequenza master delle Cue (radice e annidate)
 * - Playhead / Standby pointer con avanzamento automatico al tasto GO
 * - Gestione automatica di Auto-continue e Auto-follow
 * - Loop di tick ad alta precisione (60 FPS o delta time variabile)
 * - Trasporto globale: GO, Stop, Pause, Resume, Panic (con dissolvenza), Hard Stop
 */

import BaseCue from './BaseCue.js';
import GroupCue from './GroupCue.js';
import { CueState } from './CueTypes.js';

export default class CueScheduler {
  constructor() {
    // Lista radice delle Cue del workspace
    this.cues = [];

    // Indice della Cue attualmente in Standby (puntatore playhead per il prossimo GO)
    this.standbyIndex = 0;

    // Set di tutte le Cue attualmente attive (in esecuzione o in pausa)
    this.runningCues = new Set();

    // Gestione Panic: stato di dissolvenza d'emergenza
    this.isPanicking = false;
    this.panicFadeTime = 1.0;
    this.panicElapsed = 0;

    // Listeners per eventi del motore
    this.listeners = {
      cueStarted: [],
      cueCompleted: [],
      cueStopped: [],
      cuePaused: [],
      cueResumed: [],
      playheadMoved: [],
      cueListChanged: [],
      panicStarted: [],
      panicFinished: [],
    };
  }

  // ─── Registrazione Eventi ───────────────────────────────────────

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((cb) => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      for (const cb of this.listeners[event]) {
        try {
          cb(data);
        } catch (err) {
          console.error(`Errore nel listener per l'evento "${event}":`, err);
        }
      }
    }
  }

  // ─── Gestione Playhead e Navigazione ────────────────────────────

  getStandbyCue() {
    if (this.standbyIndex >= 0 && this.standbyIndex < this.cues.length) {
      return this.cues[this.standbyIndex];
    }
    return null;
  }

  setStandbyIndex(idx) {
    if (this.cues.length === 0) {
      this.standbyIndex = 0;
    } else {
      this.standbyIndex = Math.max(0, Math.min(this.cues.length - 1, idx));
    }
    this.emit('playheadMoved', { standbyIndex: this.standbyIndex, cue: this.getStandbyCue() });
  }

  setStandbyCueById(cueId) {
    const idx = this.cues.findIndex((c) => c.id === cueId);
    if (idx !== -1) {
      this.setStandbyIndex(idx);
      return true;
    }
    return false;
  }

  advancePlayhead() {
    if (this.standbyIndex < this.cues.length - 1) {
      this.setStandbyIndex(this.standbyIndex + 1);
    }
  }

  previousPlayhead() {
    if (this.standbyIndex > 0) {
      this.setStandbyIndex(this.standbyIndex - 1);
    }
  }

  // ─── Trasporto Globale: GO, Stop, Pause, Resume, Panic ──────────

  /**
   * Tasto GO standard di QLab:
   * Avvia la cue in Standby (oppure la cue con ID specificato)
   * e sposta automaticamente il playhead alla cue successiva.
   */
  go(cueId = null) {
    let targetCue = null;

    if (cueId) {
      targetCue = this.findCueById(cueId);
      if (!targetCue) return false;

      // Se la cue è nella radice, posiziona il playhead dopo di essa
      const rootIdx = this.cues.findIndex((c) => c.id === cueId);
      if (rootIdx !== -1) {
        this.standbyIndex = Math.min(this.cues.length - 1, rootIdx + 1);
        this.emit('playheadMoved', { standbyIndex: this.standbyIndex, cue: this.getStandbyCue() });
      }
    } else {
      targetCue = this.getStandbyCue();
      if (!targetCue) return false;

      // Avanzamento automatico del playhead al cue successivo
      this.advancePlayhead();
    }

    return this.startCue(targetCue);
  }

  /**
   * Avvia una specifica cue e la inserisce nel loop di scheduling
   */
  startCue(cue) {
    if (!cue || cue.isBroken()) return false;

    // Se è già in esecuzione, fermala prima di riavviarla (comportamento standard QLab)
    if (this.runningCues.has(cue)) {
      cue.stop();
      this.runningCues.delete(cue);
    }

    const started = cue.start();
    if (!started) return false;

    this.runningCues.add(cue);
    this.emit('cueStarted', cue);

    return true;
  }

  /**
   * Ferma una specifica Cue oppure tutte le Cue in esecuzione
   */
  stop(cueId = null) {
    if (cueId) {
      const cue = this.findCueById(cueId);
      if (cue && this.runningCues.has(cue)) {
        cue.stop();
        this.runningCues.delete(cue);
        this.emit('cueStopped', cue);
        return true;
      }
      return false;
    }

    // Ferma tutto
    const stoppedAny = this.runningCues.size > 0;
    for (const cue of Array.from(this.runningCues)) {
      cue.stop();
      this.emit('cueStopped', cue);
    }
    this.runningCues.clear();
    this.isPanicking = false;
    return stoppedAny;
  }

  /**
   * Mette in pausa una specifica Cue oppure tutte le Cue attive
   */
  pause(cueId = null) {
    if (cueId) {
      const cue = this.findCueById(cueId);
      if (cue && cue.pause()) {
        this.emit('cuePaused', cue);
        return true;
      }
      return false;
    }

    let pausedAny = false;
    for (const cue of this.runningCues) {
      if (cue.pause()) {
        pausedAny = true;
        this.emit('cuePaused', cue);
      }
    }
    return pausedAny;
  }

  /**
   * Riprende una specifica Cue oppure tutte le Cue in pausa
   */
  resume(cueId = null) {
    if (cueId) {
      const cue = this.findCueById(cueId);
      if (cue && cue.resume()) {
        this.emit('cueResumed', cue);
        return true;
      }
      return false;
    }

    let resumedAny = false;
    for (const cue of this.runningCues) {
      if (cue.resume()) {
        resumedAny = true;
        this.emit('cueResumed', cue);
      }
    }
    return resumedAny;
  }

  /**
   * Panic (Tasto Esc in QLab):
   * Dissolve l'uscita audio/video e ferma gradualmente tutte le cue attive.
   * 
   * @param {number} fadeTime Durata della dissolvenza di emergenza in secondi (default: 1.0s)
   */
  panic(fadeTime = 1.0) {
    if (this.runningCues.size === 0) return;

    this.isPanicking = true;
    this.panicFadeTime = Math.max(0.1, fadeTime);
    this.panicElapsed = 0;
    this.emit('panicStarted', { fadeTime: this.panicFadeTime });
  }

  /**
   * Arresto immediato senza dissolvenza
   */
  hardStop() {
    this.stop();
  }

  /**
   * Pre-carica la cue in Standby o specifica
   */
  load(cueId = null) {
    const cue = cueId ? this.findCueById(cueId) : this.getStandbyCue();
    if (cue) {
      return cue.load();
    }
    return false;
  }

  /**
   * Reset totale: ferma tutto e reimposta il playhead al primo cue
   */
  reset() {
    this.stop();
    for (const cue of this.cues) {
      cue.reset();
    }
    this.setStandbyIndex(0);
  }

  // ─── Loop Temporale (tick) ad Alta Precisione ───────────────────

  /**
   * Avanza il tempo dello scheduler di `dt` secondi (eseguito a 60 FPS o via RAF/timer).
   * Elabora il ciclo di vita di tutte le cue in esecuzione,
   * triggera automaticamente i seguiti (Auto-continue / Auto-follow)
   * e gestisce l'eventuale dissolvenza del Panic.
   * 
   * @param {number} dt Delta time in secondi (es. 1/60 = 0.016667s)
   */
  tick(dt) {
    if (this.runningCues.size === 0) {
      return;
    }

    // 1. Gestione Panic
    if (this.isPanicking) {
      this.panicElapsed += dt;
      if (this.panicElapsed >= this.panicFadeTime) {
        this.isPanicking = false;
        this.stop();
        this.emit('panicFinished', {});
        return;
      }
    }

    const cuesToIterate = Array.from(this.runningCues);
    const cuesToFollow = [];

    for (const cue of cuesToIterate) {
      const result = cue.tick(dt);

      // Se la cue richiede l'avvio della successiva (Auto-continue / Auto-follow)
      if (result.shouldTriggerNext) {
        cuesToFollow.push(cue);
      }

      // Se la cue ha completato il suo intero ciclo
      if (result.completed) {
        this.runningCues.delete(cue);
        this.emit('cueCompleted', cue);
      }
    }

    // 2. Triggering dei follow action (cue successive)
    for (const parentCue of cuesToFollow) {
      this._triggerNextCueAfter(parentCue);
    }
  }

  /**
   * Individua e avvia la cue successiva a una data cue per Auto-continue / Auto-follow
   */
  _triggerNextCueAfter(cue) {
    // Se la cue appartiene ad un gruppo
    if (cue.parentId) {
      const parentGroup = this.findCueById(cue.parentId);
      if (parentGroup && parentGroup instanceof GroupCue) {
        const childIdx = parentGroup.children.findIndex((c) => c.id === cue.id);
        if (childIdx !== -1 && childIdx < parentGroup.children.length - 1) {
          const nextChild = parentGroup.children[childIdx + 1];
          if (nextChild && nextChild.armed && !nextChild.isBroken()) {
            this.startCue(nextChild);
            return;
          }
        }
      }
    }

    // Altrimenti cerca nella lista radice
    const rootIdx = this.cues.findIndex((c) => c.id === cue.id);
    if (rootIdx !== -1 && rootIdx < this.cues.length - 1) {
      const nextCue = this.cues[rootIdx + 1];
      if (nextCue && !nextCue.isBroken()) {
        this.startCue(nextCue);
        // Avanza il playhead se era fermo sulla cue appena avviata
        if (this.standbyIndex === rootIdx + 1) {
          this.advancePlayhead();
        }
      }
    }
  }

  // ─── Gestione CRUD Cue List ────────────────────────────────────

  addCue(cue, index = null) {
    if (!(cue instanceof BaseCue)) {
      throw new Error('La cue deve essere un\'istanza di BaseCue');
    }

    if (index !== null && index >= 0 && index <= this.cues.length) {
      this.cues.splice(index, 0, cue);
    } else {
      this.cues.push(cue);
    }

    this.emit('cueListChanged', this.cues);
    return cue;
  }

  removeCue(cueId) {
    const idx = this.cues.findIndex((c) => c.id === cueId);
    if (idx !== -1) {
      const [removed] = this.cues.splice(idx, 1);
      if (this.runningCues.has(removed)) {
        removed.stop();
        this.runningCues.delete(removed);
      }
      if (this.standbyIndex >= this.cues.length) {
        this.standbyIndex = Math.max(0, this.cues.length - 1);
      }
      this.emit('cueListChanged', this.cues);
      return removed;
    }

    // Cerca anche all'interno dei gruppi
    for (const c of this.cues) {
      if (c instanceof GroupCue) {
        const removedFromGroup = c.removeChild(cueId);
        if (removedFromGroup) {
          if (this.runningCues.has(removedFromGroup)) {
            removedFromGroup.stop();
            this.runningCues.delete(removedFromGroup);
          }
          this.emit('cueListChanged', this.cues);
          return removedFromGroup;
        }
      }
    }

    return null;
  }

  findCueById(cueId) {
    const searchRecursive = (list) => {
      for (const cue of list) {
        if (cue.id === cueId) return cue;
        if (cue instanceof GroupCue && cue.children.length > 0) {
          const found = searchRecursive(cue.children);
          if (found) return found;
        }
      }
      return null;
    };

    return searchRecursive(this.cues);
  }

  findCueByNumber(number) {
    const numStr = String(number).trim().toLowerCase();
    const searchRecursive = (list) => {
      for (const cue of list) {
        if (String(cue.number).trim().toLowerCase() === numStr) return cue;
        if (cue instanceof GroupCue && cue.children.length > 0) {
          const found = searchRecursive(cue.children);
          if (found) return found;
        }
      }
      return null;
    };

    return searchRecursive(this.cues);
  }

  /**
   * Restituisce una vista piatta di tutte le cue con livello di indentazione gerarchica
   */
  getFlattenedCues() {
    const result = [];
    const traverse = (list, depth = 0) => {
      for (const cue of list) {
        result.push({ cue, depth });
        if (cue instanceof GroupCue && cue.children.length > 0) {
          traverse(cue.children, depth + 1);
        }
      }
    };
    traverse(this.cues, 0);
    return result;
  }

  toJSON() {
    return {
      standbyIndex: this.standbyIndex,
      cues: this.cues.map((c) => c.toJSON()),
    };
  }
}
