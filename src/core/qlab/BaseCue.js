/**
 * BaseCue.js — Classe Base gerarchica per tutte le Cue di QLab 5 in ShowSuite
 * 
 * Gestisce:
 * - Stati operativi: Armed, Disarmed, Loaded, Running, Paused, Broken, Completed
 * - Timing: Pre-wait, Duration, Post-wait
 * - Follow Action: Do not continue, Auto-continue, Auto-follow
 * - Eventi e ciclo di vita a 60 FPS
 */

import { CueState, CuePhase, ContinueMode, CueType } from './CueTypes.js';

let cueIdCounter = 1;

export default class BaseCue {
  constructor(options = {}) {
    this.id = options.id || `cue_${Date.now()}_${cueIdCounter++}`;
    this.number = options.number !== undefined ? String(options.number) : '';
    this.name = options.name || 'Untitled Cue';
    this.notes = options.notes || '';
    this.type = options.type || CueType.BASE;
    this.color = options.color || 'none'; // 'none' | 'red' | 'orange' | 'green' | 'blue' | 'purple'
    this.flagged = Boolean(options.flagged);

    // Stato di armamento (se false = disarmed, non esegue l'azione ma propaga timing/follow)
    this.armed = options.armed !== undefined ? Boolean(options.armed) : true;

    // Gestione temporale (in secondi)
    this.preWait = Math.max(0, Number(options.preWait) || 0);
    this.duration = Math.max(0, Number(options.duration) || 0);
    this.postWait = Math.max(0, Number(options.postWait) || 0);

    // Modalità di avanzamento
    this.continueMode = options.continueMode || ContinueMode.DO_NOT_CONTINUE;

    // Riferimenti gerarchici e target
    this.targetId = options.targetId || null;
    this.parentId = options.parentId || null;

    // Stato corrente
    this.state = options.state || CueState.IDLE;
    this.brokenReason = options.brokenReason || null;
    if (this.brokenReason) {
      this.state = CueState.BROKEN;
    }

    // Timer e avanzamento interno
    this.currentPhase = CuePhase.NONE;
    this.elapsedTime = 0;       // Tempo totale dall'inizio dello start()
    this.preWaitElapsed = 0;    // Tempo trascorso in Pre-wait
    this.actionElapsed = 0;     // Tempo trascorso nell'Azione principale
    this.postWaitElapsed = 0;   // Tempo trascorso in Post-wait

    // Flag per evitare doppie emissioni dell'evento di continuazione
    this.followTriggered = false;

    // Callbacks personalizzabili
    this.onStart = options.onStart || null;
    this.onActionStart = options.onActionStart || null;
    this.onActionEnd = options.onActionEnd || null;
    this.onComplete = options.onComplete || null;
    this.onStop = options.onStop || null;
  }

  // ─── Gestione Armamento e Stato Broken ─────────────────────────

  arm() {
    this.armed = true;
  }

  disarm() {
    this.armed = false;
  }

  setBroken(reason = 'Unknown error') {
    this.brokenReason = reason;
    this.state = CueState.BROKEN;
  }

  clearBroken() {
    this.brokenReason = null;
    if (this.state === CueState.BROKEN) {
      this.state = CueState.IDLE;
    }
  }

  isBroken() {
    return this.state === CueState.BROKEN || Boolean(this.brokenReason);
  }

  isArmed() {
    return this.armed && !this.isBroken();
  }

  // ─── Ciclo di Vita: Load, Start, Pause, Resume, Stop ──────────

  /**
   * Pre-carica la cue (es. buffering audio, apertura stream video).
   */
  load() {
    if (this.isBroken()) return false;
    if (this.state === CueState.IDLE || this.state === CueState.COMPLETED) {
      this.state = CueState.LOADED;
      return true;
    }
    return false;
  }

  /**
   * Avvia l'esecuzione della Cue (chiamato dal tasto GO o da un Auto-continue).
   */
  start() {
    if (this.isBroken()) {
      return false;
    }

    this.state = CueState.RUNNING;
    this.elapsedTime = 0;
    this.preWaitElapsed = 0;
    this.actionElapsed = 0;
    this.postWaitElapsed = 0;
    this.followTriggered = false;

    // Se c'è preWait, si parte da quella fase
    if (this.preWait > 0) {
      this.currentPhase = CuePhase.PRE_WAIT;
    } else {
      this._enterActionPhase();
    }

    if (typeof this.onStart === 'function') {
      this.onStart(this);
    }

    return true;
  }

  _enterActionPhase() {
    this.currentPhase = CuePhase.ACTION;

    // Se disarmata, l'azione non viene eseguita fisicamente (skip immediato della durata)
    if (!this.armed) {
      this.actionElapsed = this.duration;
      this._checkActionCompletion();
      return;
    }

    if (typeof this.onActionStart === 'function') {
      this.onActionStart(this);
    }

    // Se la durata è 0, transita subito al completamento azione
    if (this.duration === 0) {
      this._checkActionCompletion();
    }
  }

  _checkActionCompletion() {
    if (typeof this.onActionEnd === 'function') {
      this.onActionEnd(this);
    }

    // Se c'è postWait, entra in post_wait, altrimenti completa
    if (this.postWait > 0) {
      this.currentPhase = CuePhase.POST_WAIT;
    } else {
      this._completeCue();
    }
  }

  _completeCue() {
    this.currentPhase = CuePhase.COMPLETED;
    this.state = CueState.COMPLETED;

    if (typeof this.onComplete === 'function') {
      this.onComplete(this);
    }
  }

  /**
   * Mette in pausa l'esecuzione (congelando i timer).
   */
  pause() {
    if (this.state === CueState.RUNNING) {
      this.state = CueState.PAUSED;
      return true;
    }
    return false;
  }

  /**
   * Riprende l'esecuzione dallo stato di pausa.
   */
  resume() {
    if (this.state === CueState.PAUSED) {
      this.state = CueState.RUNNING;
      return true;
    }
    return false;
  }

  /**
   * Ferma immediatamente la Cue e resetta i progressi.
   */
  stop() {
    const wasRunning = this.state === CueState.RUNNING || this.state === CueState.PAUSED;
    this.state = CueState.IDLE;
    this.currentPhase = CuePhase.NONE;
    this.elapsedTime = 0;
    this.preWaitElapsed = 0;
    this.actionElapsed = 0;
    this.postWaitElapsed = 0;
    this.followTriggered = false;

    if (wasRunning && typeof this.onStop === 'function') {
      this.onStop(this);
    }

    return wasRunning;
  }

  /**
   * Reset completo allo stato iniziale
   */
  reset() {
    this.stop();
    if (this.brokenReason) {
      this.state = CueState.BROKEN;
    } else {
      this.state = CueState.IDLE;
    }
  }

  // ─── Avanzamento Temporale ad Alta Precisione (tick) ────────────

  /**
   * Avanza il tempo della cue di `dt` secondi.
   * Restituisce un oggetto di stato con l'indicazione se attivare la cue successiva.
   * 
   * @param {number} dt Delta time in secondi (es. 1/60 = 0.01666s)
   * @returns {Object} {
   *   completed: boolean,
   *   shouldTriggerNext: boolean,
   *   phase: string,
   *   progress: number (0..1),
   *   actionProgress: number (0..1)
   * }
   */
  tick(dt) {
    if (this.state !== CueState.RUNNING) {
      return {
        completed: this.state === CueState.COMPLETED,
        shouldTriggerNext: false,
        phase: this.currentPhase,
        progress: this.getProgress(),
        actionProgress: this.getActionProgress(),
      };
    }

    this.elapsedTime += dt;
    let shouldTriggerNext = false;

    // 1. Fase PRE-WAIT
    if (this.currentPhase === CuePhase.PRE_WAIT) {
      this.preWaitElapsed += dt;
      if (this.preWaitElapsed >= this.preWait) {
        // Tempo in eccesso traslato nella fase successiva
        const excess = this.preWaitElapsed - this.preWait;
        this.preWaitElapsed = this.preWait;
        this._enterActionPhase();

        // Se l'azione è già completata (es. durata 0 o disarmata), l'eccesso va alla post-wait
        if (this.currentPhase === CuePhase.ACTION && this.duration > 0 && this.armed) {
          this.actionElapsed += excess;
          if (this.actionElapsed >= this.duration) {
            this.actionElapsed = this.duration;
            this._checkActionCompletion();
          }
        }
      }
    }
    // 2. Fase ACTION
    else if (this.currentPhase === CuePhase.ACTION) {
      if (this.armed && this.duration > 0) {
        this.actionElapsed += dt;
        if (this.actionElapsed >= this.duration) {
          const excess = this.actionElapsed - this.duration;
          this.actionElapsed = this.duration;
          this._checkActionCompletion();

          if (this.currentPhase === CuePhase.POST_WAIT) {
            this.postWaitElapsed += excess;
            if (this.postWaitElapsed >= this.postWait) {
              this.postWaitElapsed = this.postWait;
              this._completeCue();
            }
          }
        }
      } else {
        // Durata zero o disarmata
        this._checkActionCompletion();
      }
    }
    // 3. Fase POST-WAIT
    else if (this.currentPhase === CuePhase.POST_WAIT) {
      this.postWaitElapsed += dt;
      if (this.postWaitElapsed >= this.postWait) {
        this.postWaitElapsed = this.postWait;
        this._completeCue();
      }
    }

    // ─── Verifica Condizione Follow Action (Auto-continue / Auto-follow) ───
    if (!this.followTriggered) {
      if (this.continueMode === ContinueMode.AUTO_CONTINUE) {
        // Auto-continue scatta al termine del Pre-wait + Post-wait della cue,
        // indipendentemente dal fatto che l'azione abbia finito o stia ancora suonando.
        // In QLab 5: trigger time = preWait + postWait
        const triggerTime = this.preWait + this.postWait;
        if (this.elapsedTime >= triggerTime) {
          this.followTriggered = true;
          shouldTriggerNext = true;
        }
      } else if (this.continueMode === ContinueMode.AUTO_FOLLOW) {
        // Auto-follow scatta DOPO che l'azione ha completato la sua durata + postWait
        // In QLab 5: trigger time = preWait + duration + postWait
        const effectiveDuration = this.armed ? this.duration : 0;
        const triggerTime = this.preWait + effectiveDuration + this.postWait;
        if (this.elapsedTime >= triggerTime) {
          this.followTriggered = true;
          shouldTriggerNext = true;
        }
      }
    }

    return {
      completed: this.state === CueState.COMPLETED,
      shouldTriggerNext,
      phase: this.currentPhase,
      progress: this.getProgress(),
      actionProgress: this.getActionProgress(),
    };
  }

  // ─── Metriche di Progresso ─────────────────────────────────────

  /**
   * Progresso dell'azione principale (0.0 → 1.0)
   */
  getActionProgress() {
    if (this.duration === 0) {
      return this.currentPhase === CuePhase.COMPLETED || this.currentPhase === CuePhase.POST_WAIT ? 1 : 0;
    }
    return Math.min(1, Math.max(0, this.actionElapsed / this.duration));
  }

  /**
   * Progresso dell'intero ciclo di vita (Pre-Wait + Duration + Post-Wait)
   */
  getProgress() {
    const total = this.getTotalTime();
    if (total === 0) {
      return this.state === CueState.COMPLETED ? 1 : 0;
    }
    return Math.min(1, Math.max(0, this.elapsedTime / total));
  }

  /**
   * Durata totale prevista compresi preWait e postWait
   */
  getTotalTime() {
    const act = this.armed ? this.duration : 0;
    return this.preWait + act + this.postWait;
  }

  // ─── Serializzazione JSON ──────────────────────────────────────

  toJSON() {
    return {
      id: this.id,
      number: this.number,
      name: this.name,
      notes: this.notes,
      type: this.type,
      color: this.color,
      flagged: this.flagged,
      armed: this.armed,
      preWait: this.preWait,
      duration: this.duration,
      postWait: this.postWait,
      continueMode: this.continueMode,
      targetId: this.targetId,
      parentId: this.parentId,
      state: this.state,
      brokenReason: this.brokenReason,
    };
  }
}
