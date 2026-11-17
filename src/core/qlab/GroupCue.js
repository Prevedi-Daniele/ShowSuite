/**
 * GroupCue.js — Cue Gerarchica Contenitore (Group Cue) di QLab 5 per ShowSuite
 * 
 * Supporta le 4 modalità native di QLab 5:
 * 1. TIMELINE: Avvia tutti i figli simultaneamente
 * 2. PLAYLIST: Riproduce i figli in sequenza uno dopo l'altro
 * 3. START_FIRST_AND_GO_TO_NEXT: Avvia il primo figlio e avanza l'indice interno ad ogni GO successivo
 * 4. RANDOM: Seleziona e avvia un figlio in modo casuale
 */

import BaseCue from './BaseCue.js';
import { CueType, GroupMode, CueState, CuePhase } from './CueTypes.js';

export default class GroupCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.GROUP,
    });

    this.mode = options.mode || GroupMode.TIMELINE;
    this.children = [];
    this.activeChildIndex = 0;

    // Bag per la riproduzione Random senza ripetizioni immediate
    this._unplayedRandomIndices = [];

    // Se forniti children iniziali, aggiungili
    if (Array.isArray(options.children)) {
      options.children.forEach((child) => this.addChild(child));
    }

    this.updateDuration();
  }

  // ─── Gestione Figli Gerarchici ────────────────────────────────

  addChild(cue, index = null) {
    if (!(cue instanceof BaseCue)) {
      throw new Error('Il figlio deve essere un\'istanza di BaseCue');
    }
    cue.parentId = this.id;

    if (index !== null && index >= 0 && index <= this.children.length) {
      this.children.splice(index, 0, cue);
    } else {
      this.children.push(cue);
    }

    this._resetRandomBag();
    this.updateDuration();
    return cue;
  }

  removeChild(cueId) {
    const idx = this.children.findIndex((c) => c.id === cueId);
    if (idx !== -1) {
      const removed = this.children.splice(idx, 1)[0];
      removed.parentId = null;
      this._resetRandomBag();
      this.updateDuration();
      return removed;
    }
    return null;
  }

  getChild(cueId) {
    return this.children.find((c) => c.id === cueId) || null;
  }

  moveChild(cueId, newIndex) {
    const idx = this.children.findIndex((c) => c.id === cueId);
    if (idx !== -1 && newIndex >= 0 && newIndex < this.children.length) {
      const [cue] = this.children.splice(idx, 1);
      this.children.splice(newIndex, 0, cue);
      this._resetRandomBag();
      this.updateDuration();
      return true;
    }
    return false;
  }

  /**
   * Calcola dinamicamente la durata del gruppo in base alla modalità
   */
  updateDuration() {
    if (this.children.length === 0) {
      this.duration = 0;
      return;
    }

    switch (this.mode) {
      case GroupMode.TIMELINE: {
        let maxSpan = 0;
        for (const child of this.children) {
          if (child.armed && !child.isBroken()) {
            const span = child.preWait + child.duration + child.postWait;
            if (span > maxSpan) maxSpan = span;
          }
        }
        this.duration = maxSpan;
        break;
      }

      case GroupMode.PLAYLIST: {
        let sumSpan = 0;
        for (const child of this.children) {
          if (child.armed && !child.isBroken()) {
            const span = child.preWait + child.duration + child.postWait;
            sumSpan += span;
          }
        }
        this.duration = sumSpan;
        break;
      }

      case GroupMode.START_FIRST_AND_GO_TO_NEXT:
      case GroupMode.RANDOM: {
        const child = this.children[this.activeChildIndex] || this.children[0];
        if (child && child.armed && !child.isBroken()) {
          this.duration = child.preWait + child.duration + child.postWait;
        } else {
          this.duration = 0;
        }
        break;
      }
    }
  }

  _resetRandomBag() {
    this._unplayedRandomIndices = this.children
      .map((_, i) => i)
      .filter((i) => this.children[i].armed && !this.children[i].isBroken());
  }

  // ─── Ciclo di Vita Sovrascritto ───────────────────────────────

  load() {
    super.load();
    for (const child of this.children) {
      child.load();
    }
    return true;
  }

  start() {
    if (this.isBroken()) return false;

    this.updateDuration();
    return super.start();
  }

  _enterActionPhase() {
    this.currentPhase = CuePhase.ACTION;

    if (!this.armed) {
      this.actionElapsed = this.duration;
      this._checkActionCompletion();
      return;
    }

    if (typeof this.onActionStart === 'function') {
      this.onActionStart(this);
    }

    if (this.children.length === 0) {
      this._checkActionCompletion();
      return;
    }

    this._startChildrenForMode();
  }

  _startChildrenForMode() {
    if (this.children.length === 0) {
      this._checkActionCompletion();
      return;
    }

    switch (this.mode) {
      case GroupMode.TIMELINE: {
        // Avvia tutti i figli contemporaneamente
        for (const child of this.children) {
          if (child.armed && !child.isBroken()) {
            child.start();
          }
        }
        break;
      }

      case GroupMode.PLAYLIST: {
        // Avvia il primo figlio armato
        this.activeChildIndex = 0;
        this._startNextArmedChildInPlaylist(0);
        break;
      }

      case GroupMode.START_FIRST_AND_GO_TO_NEXT: {
        // Avvia il figlio all'indice corrente
        const targetChild = this.children[this.activeChildIndex];
        if (targetChild && targetChild.armed && !targetChild.isBroken()) {
          targetChild.start();
        }
        // Avanza l'indice per il prossimo trigger esterno
        this.activeChildIndex = (this.activeChildIndex + 1) % this.children.length;
        break;
      }

      case GroupMode.RANDOM: {
        // Seleziona un figlio a caso dal bag non ancora suonato
        if (this._unplayedRandomIndices.length === 0) {
          this._resetRandomBag();
        }

        if (this._unplayedRandomIndices.length > 0) {
          const randomIndex = Math.floor(Math.random() * this._unplayedRandomIndices.length);
          const chosenIndex = this._unplayedRandomIndices.splice(randomIndex, 1)[0];
          const child = this.children[chosenIndex];
          if (child) {
            this.activeChildIndex = chosenIndex;
            child.start();
          }
        }
        break;
      }
    }
  }

  _startNextArmedChildInPlaylist(startIndex) {
    let idx = startIndex;
    while (idx < this.children.length) {
      const child = this.children[idx];
      if (child.armed && !child.isBroken()) {
        this.activeChildIndex = idx;
        child.start();
        return true;
      }
      idx++;
    }
    // Nessun altro figlio armato: playlist completata
    this._checkActionCompletion();
    return false;
  }

  pause() {
    super.pause();
    for (const child of this.children) {
      if (child.state === CueState.RUNNING) {
        child.pause();
      }
    }
    return true;
  }

  resume() {
    super.resume();
    for (const child of this.children) {
      if (child.state === CueState.PAUSED) {
        child.resume();
      }
    }
    return true;
  }

  stop() {
    const wasRunning = super.stop();
    for (const child of this.children) {
      child.stop();
    }
    this.activeChildIndex = 0;
    this._resetRandomBag();
    return wasRunning;
  }

  reset() {
    super.reset();
    for (const child of this.children) {
      child.reset();
    }
    this.activeChildIndex = 0;
    this._resetRandomBag();
  }

  // ─── Avanzamento Temporale Figli (tick) ─────────────────────────

  tick(dt) {
    if (this.state !== CueState.RUNNING) {
      return super.tick(dt);
    }

    // Se siamo ancora in PRE_WAIT, avanza solo il timer del gruppo
    if (this.currentPhase === CuePhase.PRE_WAIT) {
      return super.tick(dt);
    }

    // Se siamo in POST_WAIT, avanza solo la post-wait del gruppo
    if (this.currentPhase === CuePhase.POST_WAIT) {
      return super.tick(dt);
    }

    // Fase ACTION: esecuzione e tick dei figli
    if (this.currentPhase === CuePhase.ACTION && this.armed) {
      switch (this.mode) {
        case GroupMode.TIMELINE: {
          let anyChildRunning = false;
          for (const child of this.children) {
            if (child.state === CueState.RUNNING) {
              child.tick(dt);
            }
            if (child.state === CueState.RUNNING || child.state === CueState.PAUSED) {
              anyChildRunning = true;
            }
          }

          // Se tutti i figli hanno terminato, completa l'azione del gruppo
          if (!anyChildRunning) {
            this._checkActionCompletion();
          }
          break;
        }

        case GroupMode.PLAYLIST: {
          const currentChild = this.children[this.activeChildIndex];
          if (currentChild && currentChild.state === CueState.RUNNING) {
            const childResult = currentChild.tick(dt);

            // Se il figlio richiede di avanzare (Auto-continue / Auto-follow) oppure è completato
            if (childResult.shouldTriggerNext || currentChild.state === CueState.COMPLETED) {
              const nextStarted = this._startNextArmedChildInPlaylist(this.activeChildIndex + 1);
              if (!nextStarted) {
                this._checkActionCompletion();
              }
            }
          } else if (!currentChild || currentChild.state === CueState.COMPLETED) {
            const nextStarted = this._startNextArmedChildInPlaylist(this.activeChildIndex + 1);
            if (!nextStarted) {
              this._checkActionCompletion();
            }
          }
          break;
        }

        case GroupMode.START_FIRST_AND_GO_TO_NEXT:
        case GroupMode.RANDOM: {
          const activeChild = this.children[this.activeChildIndex];
          if (activeChild && activeChild.state === CueState.RUNNING) {
            activeChild.tick(dt);
          }
          if (!activeChild || activeChild.state === CueState.COMPLETED) {
            this._checkActionCompletion();
          }
          break;
        }
      }
    }

    return super.tick(dt);
  }

  toJSON() {
    return {
      ...super.toJSON(),
      mode: this.mode,
      children: this.children.map((c) => c.toJSON()),
    };
  }
}
