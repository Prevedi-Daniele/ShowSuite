/**
 * TimecodeChaser.js — Motore di Sincronizzazione Timecode Chasing e Trigger Cues per ShowSuite
 * 
 * Gestisce:
 * 1. Chasing di Timecode da sorgenti multiple (MTC MIDI Timecode, Audio LTC o generatore interno)
 * 2. Macchina a stati di sincronizzazione:
 *    - OFFLINE: nessun segnale in ingresso
 *    - LOCKING: segnale rilevato, verifica coerenza sequenziale dei frame
 *    - LOCKED: sincronizzazione agganciata e stabile (chase attivo)
 *    - FREEWHEELING: tolleranza ai dropout di rete/audio (avanzamento autonomo fino a N frame)
 * 3. Trigger di Cue sincronizzato a Timecode SMPTE (24, 25, 29.97, 30 fps):
 *    - Avvio automatico (GO/Start), Stop o Preload di Cue quando il timecode raggiunge o attraversa il punto di trigger
 *    - Tolleranza e riarmo intelligente quando il timecode viene riavvolto o salta all'indietro
 */

import SMPTETimecode, { SMPTEFrameRate } from './SMPTETimecode.js';

export const ChaserState = {
  OFFLINE: 'offline',           // Nessun segnale timecode
  LOCKING: 'locking',           // Aggancio in corso (verifica continuità)
  LOCKED: 'locked',             // Agganciato e sincronizzato
  FREEWHEELING: 'freewheeling', // Perdita temporanea segnale: avanzamento autonomo
};

export const TimecodeTriggerAction = {
  START: 'start', // Avvia la cue (GO)
  STOP: 'stop',   // Ferma la cue
  LOAD: 'load',   // Pre-carica la cue
  PAUSE: 'pause', // Mette in pausa
};

export default class TimecodeChaser {
  constructor(options = {}) {
    this.cueScheduler = options.cueScheduler || null;
    this.fps = options.fps || SMPTEFrameRate.FPS_25;
    this.isDropFrame = Boolean(options.isDropFrame);

    // Stato di sincronizzazione
    this.state = ChaserState.OFFLINE;

    // Timecode corrente agganciato
    this.currentTimecode = new SMPTETimecode(0, 0, 0, 0, 0, this.fps, this.isDropFrame);

    // Parametri di Locking e Freewheeling
    this.lockThreshold = options.lockThreshold || 3;        // Frame consecutivi richiesti per dichiarare LOCKED
    this.consecutiveGoodFrames = 0;
    this.freewheelMaxFrames = options.freewheelFrames || 10; // Max frame di freewheeling prima di OFFLINE
    this.freewheelCount = 0;
    this.lastReceivedTimestamp = 0;
    this.offlineTimeoutMs = options.offlineTimeoutMs || 600; // Timeout segnale (ms)

    // Registro trigger Cue registrati: Map<string, Array<TriggerDefinition>>
    // Formato trigger: { id, cueId, timecode, action, fired: boolean }
    this.registeredTriggers = new Map();

    // Callbacks ed eventi
    this.listeners = {
      stateChange: [],
      timecodeTick: [],
      triggerFired: [],
    };
  }

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
        try { cb(data); } catch (e) { console.error(`Errore nel listener TimecodeChaser "${event}":`, e); }
      }
    }
  }

  attachCueScheduler(scheduler) {
    this.cueScheduler = scheduler;
  }

  // ─── Registrazione e Gestione Trigger Cue ───────────────────────

  /**
   * Registra un trigger sincronizzato a timecode per una Cue
   * 
   * @param {string} cueId ID della cue da innescare
   * @param {string|SMPTETimecode} triggerTc Timecode target (es. "01:00:15:00")
   * @param {string} [action='start'] Azione da compiere ('start', 'stop', 'load', 'pause')
   */
  registerCueTrigger(cueId, triggerTc, action = TimecodeTriggerAction.START) {
    const tc = triggerTc instanceof SMPTETimecode ? triggerTc : SMPTETimecode.fromString(triggerTc, this.fps, this.isDropFrame);
    const triggerId = `trig_${cueId}_${tc.toFrames()}_${action}`;

    const triggerDef = {
      id: triggerId,
      cueId,
      timecode: tc,
      targetFrame: tc.toFrames(),
      action,
      fired: false,
    };

    if (!this.registeredTriggers.has(cueId)) {
      this.registeredTriggers.set(cueId, []);
    }
    this.registeredTriggers.get(cueId).push(triggerDef);

    return triggerDef;
  }

  removeCueTriggers(cueId) {
    return this.registeredTriggers.delete(cueId);
  }

  clearAllTriggers() {
    this.registeredTriggers.clear();
  }

  // ─── Ricezione Timecode da Sorgenti (MTC / LTC) ─────────────────

  /**
   * Aggiorna lo stato del chaser con un nuovo timecode SMPTE in ingresso
   * 
   * @param {SMPTETimecode} incomingTc Timecode ricevuto da decoder MTC o LTC
   */
  updateIncomingTimecode(incomingTc) {
    const now = Date.now();
    const prevTc = this.currentTimecode;
    const prevFrames = prevTc.toFrames();
    const incomingFrames = incomingTc.toFrames();

    this.lastReceivedTimestamp = now;

    // Calcolo scarto temporale rispetto al frame precedente
    const deltaFrames = incomingFrames - prevFrames;

    if (this.state === ChaserState.OFFLINE) {
      this._changeState(ChaserState.LOCKING);
      this.consecutiveGoodFrames = 1;
      this.currentTimecode = incomingTc.clone();
    } else if (this.state === ChaserState.LOCKING) {
      if (deltaFrames >= 0 && deltaFrames <= 2) {
        this.consecutiveGoodFrames++;
        if (this.consecutiveGoodFrames >= this.lockThreshold) {
          this._changeState(ChaserState.LOCKED);
        }
      } else {
        this.consecutiveGoodFrames = 1; // Reset contatore stabilità
      }
      this.currentTimecode = incomingTc.clone();
    } else if (this.state === ChaserState.LOCKED || this.state === ChaserState.FREEWHEELING) {
      if (this.state === ChaserState.FREEWHEELING) {
        this._changeState(ChaserState.LOCKED);
      }
      this.freewheelCount = 0;
      this.currentTimecode = incomingTc.clone();
    }

    // Gestione riarmo trigger se c'è stato un salto all'indietro (rewind)
    if (incomingFrames < prevFrames - 2) {
      this._rearmTriggers(incomingFrames);
    }

    // Verifica ed esecuzione trigger per le Cue
    this._checkTriggers(prevFrames, incomingFrames);

    this.emit('timecodeTick', {
      timecode: this.currentTimecode,
      state: this.state,
      incoming: incomingTc,
    });
  }

  // ─── Loop di Tick Temporale (Freewheeling & Dropout Detection) ──

  /**
   * Avanza il generatore interno o gestisce dropout/freewheeling
   * Chiamato regolarmente dal loop a 60 FPS o da un timer
   * 
   * @param {number} dt Delta time in secondi
   */
  tick(dt = 0.016) {
    const now = Date.now();
    const elapsedSinceRx = now - this.lastReceivedTimestamp;

    // Se siamo agganciati ma non arrivano frame da più del tempo nominale di un frame
    const nominalFrameDurationMs = (1.0 / this.fps) * 1000;

    if ((this.state === ChaserState.LOCKED || this.state === ChaserState.FREEWHEELING) && elapsedSinceRx > nominalFrameDurationMs * 1.5) {
      if (this.freewheelCount < this.freewheelMaxFrames) {
        // Freewheeling attivo: genera frame autonomo
        if (this.state !== ChaserState.FREEWHEELING) {
          this._changeState(ChaserState.FREEWHEELING);
        }
        this.freewheelCount++;
        const prevFrames = this.currentTimecode.toFrames();
        this.currentTimecode = this.currentTimecode.addFrames(1);
        const nextFrames = this.currentTimecode.toFrames();

        this._checkTriggers(prevFrames, nextFrames);

        this.emit('timecodeTick', {
          timecode: this.currentTimecode,
          state: this.state,
          freewheel: true,
        });
      } else if (elapsedSinceRx > this.offlineTimeoutMs) {
        // Dropout prolungato oltre il limite di freewheeling: dichiara OFFLINE
        this._changeState(ChaserState.OFFLINE);
        this.freewheelCount = 0;
        this.consecutiveGoodFrames = 0;
      }
    }
  }

  // ─── Verifica e Innesco Trigger ────────────────────────────────

  _checkTriggers(prevFrame, currentFrame) {
    for (const [cueId, triggers] of this.registeredTriggers.entries()) {
      for (const trigger of triggers) {
        if (trigger.fired) continue;

        // Se il timecode corrente ha raggiunto o superato il target frame
        // (gestisce sia atterraggio esatto che attraversamento tra prevFrame e currentFrame)
        const crossed = (prevFrame <= trigger.targetFrame && currentFrame >= trigger.targetFrame) ||
                        (Math.abs(currentFrame - trigger.targetFrame) <= 1);

        if (crossed) {
          trigger.fired = true;
          this._executeTriggerAction(trigger);
        }
      }
    }
  }

  _executeTriggerAction(trigger) {
    let targetCue = null;
    if (this.cueScheduler) {
      targetCue = this.cueScheduler.findCueById(trigger.cueId) ||
                  this.cueScheduler.findCueByNumber(trigger.cueId);
    }

    if (targetCue && this.cueScheduler) {
      switch (trigger.action) {
        case TimecodeTriggerAction.START:
          this.cueScheduler.startCue(targetCue);
          break;
        case TimecodeTriggerAction.STOP:
          this.cueScheduler.stop(targetCue.id);
          break;
        case TimecodeTriggerAction.PAUSE:
          this.cueScheduler.pause(targetCue.id);
          break;
        case TimecodeTriggerAction.LOAD:
          targetCue.load();
          break;
      }
    }

    this.emit('triggerFired', {
      trigger,
      cue: targetCue,
      timecode: this.currentTimecode,
    });
  }

  _rearmTriggers(currentFrame) {
    for (const [cueId, triggers] of this.registeredTriggers.entries()) {
      for (const trigger of triggers) {
        // Riarma i trigger che si trovano dopo il nuovo punto di riavvolgimento
        if (trigger.targetFrame > currentFrame) {
          trigger.fired = false;
        }
      }
    }
  }

  _changeState(newState) {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      this.emit('stateChange', { oldState, newState, timecode: this.currentTimecode });
    }
  }
}
