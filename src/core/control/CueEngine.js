/**
 * CueEngine - Motore per Cue List, Scene Theatrical/Live e Crossfader per ShowSuite
 * Gestisce:
 * - Sequenza ordinata di Cue con numerazione decimale (1.0, 2.0, ecc.)
 * - Crossfade temporizzato a 60 FPS con tempi di salita (Fade In) e discesa (Fade Out)
 * - Tasto GO per avanzamento automatico alla scena successiva
 * - Crossfader manuale A/B (0% -> 100%)
 * - Interpolazione ottica intelligente (Dimmer morbido, Pan/Tilt fluido, Snap Gobo/Prisma)
 */

export class Cue {
  constructor(config = {}) {
    this.id = config.id || `cue_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    this.number = config.number !== undefined ? config.number : 1.0;
    this.name = config.name || `Scena ${this.number}`;
    this.fadeIn = config.fadeIn !== undefined ? config.fadeIn : 2.0;   // Secondi
    this.fadeOut = config.fadeOut !== undefined ? config.fadeOut : 2.0; // Secondi
    this.notes = config.notes || '';
    // Mappa fixtureId -> stato fixture salvato
    this.fixtureSnapshots = config.fixtureSnapshots ? JSON.parse(JSON.stringify(config.fixtureSnapshots)) : {};
  }
}

export default class CueEngine {
  constructor() {
    this.cues = [];
    this.activeCueIndex = -1; // -1 = nessuna cue attiva
    this.nextCueIndex = 0;

    // Stato di dissolvenza attiva
    this.fade = {
      isFading: false,
      isPaused: false,
      progress: 0, // 0.0 .. 1.0
      startTime: 0,
      durationMs: 2000,
      fromStates: {},
      toStates: {},
    };

    // Crossfade manuale fader A/B (0.0 .. 1.0)
    this.manualCrossfade = 0.0;
    this.isManualMode = false;

    this.initDefaultCues();
  }

  initDefaultCues() {
    // 3 Cue predefinite per test e show immediato
    const cue1 = new Cue({
      number: 1.0,
      name: 'Intro Concerto - Blue Wash',
      fadeIn: 2.0,
      fixtureSnapshots: {
        spot_1: { intensity: 1, shutter: 1, pan: 0.35, tilt: 0.65, zoom: 0.4, color: { r: 0.1, g: 0.5, b: 1 }, gobo: 0, prism: 0 },
        spot_2: { intensity: 1, shutter: 1, pan: 0.45, tilt: 0.7, zoom: 0.4, color: { r: 0.1, g: 0.5, b: 1 }, gobo: 0, prism: 0 },
        spot_3: { intensity: 1, shutter: 1, pan: 0.55, tilt: 0.7, zoom: 0.4, color: { r: 0.1, g: 0.5, b: 1 }, gobo: 0, prism: 0 },
        spot_4: { intensity: 1, shutter: 1, pan: 0.65, tilt: 0.65, zoom: 0.4, color: { r: 0.1, g: 0.5, b: 1 }, gobo: 0, prism: 0 },
        par_1: { intensity: 0.8, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.7, color: { r: 0.2, g: 0.6, b: 1 } },
        par_2: { intensity: 0.8, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.7, color: { r: 0.2, g: 0.6, b: 1 } },
      },
    });

    const cue2 = new Cue({
      number: 2.0,
      name: 'Strofa 1 - Ambra Caldo & Incrocio',
      fadeIn: 3.0,
      fixtureSnapshots: {
        spot_1: { intensity: 0.9, shutter: 1, pan: 0.2, tilt: 0.5, zoom: 0.3, color: { r: 1, g: 0.6, b: 0.1 }, gobo: 0.28, prism: 0 },
        spot_2: { intensity: 0.9, shutter: 1, pan: 0.35, tilt: 0.6, zoom: 0.3, color: { r: 1, g: 0.6, b: 0.1 }, gobo: 0.28, prism: 0 },
        spot_3: { intensity: 0.9, shutter: 1, pan: 0.65, tilt: 0.6, zoom: 0.3, color: { r: 1, g: 0.6, b: 0.1 }, gobo: 0.28, prism: 0 },
        spot_4: { intensity: 0.9, shutter: 1, pan: 0.8, tilt: 0.5, zoom: 0.3, color: { r: 1, g: 0.6, b: 0.1 }, gobo: 0.28, prism: 0 },
        par_1: { intensity: 0.6, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.7, color: { r: 1, g: 0.4, b: 0.05 } },
        par_2: { intensity: 0.6, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.7, color: { r: 1, g: 0.4, b: 0.05 } },
      },
    });

    const cue3 = new Cue({
      number: 3.0,
      name: 'Ritornello - Esplosione Magenta Prisma',
      fadeIn: 1.5,
      fixtureSnapshots: {
        spot_1: { intensity: 1, shutter: 1, pan: 0.5, tilt: 0.3, zoom: 0.6, color: { r: 1, g: 0.1, b: 0.8 }, gobo: 0.28, prism: 1 },
        spot_2: { intensity: 1, shutter: 1, pan: 0.5, tilt: 0.3, zoom: 0.6, color: { r: 1, g: 0.1, b: 0.8 }, gobo: 0.28, prism: 1 },
        spot_3: { intensity: 1, shutter: 1, pan: 0.5, tilt: 0.3, zoom: 0.6, color: { r: 1, g: 0.1, b: 0.8 }, gobo: 0.28, prism: 1 },
        spot_4: { intensity: 1, shutter: 1, pan: 0.5, tilt: 0.3, zoom: 0.6, color: { r: 1, g: 0.1, b: 0.8 }, gobo: 0.28, prism: 1 },
        par_1: { intensity: 1.0, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.8, color: { r: 0.9, g: 0.8, b: 1 } },
        par_2: { intensity: 1.0, shutter: 1, pan: 0.5, tilt: 0.4, zoom: 0.8, color: { r: 0.9, g: 0.8, b: 1 } },
      },
    });

    this.cues = [cue1, cue2, cue3];
  }

  // Snapshot dello stato attuale di tutte le fixture
  static takeSnapshot(fixtures = []) {
    const snapshot = {};
    if (Array.isArray(fixtures)) {
      fixtures.forEach((f) => {
        snapshot[f.id] = JSON.parse(JSON.stringify(f.state || {}));
      });
    }
    return snapshot;
  }

  addCue(cueConfig) {
    const cue = new Cue(cueConfig);
    this.cues.push(cue);
    this.cues.sort((a, b) => a.number - b.number);
    return cue;
  }

  removeCue(cueId) {
    const idx = this.cues.findIndex((c) => c.id === cueId);
    if (idx !== -1) {
      this.cues.splice(idx, 1);
      if (this.activeCueIndex >= this.cues.length) this.activeCueIndex = this.cues.length - 1;
      if (this.nextCueIndex >= this.cues.length) this.nextCueIndex = 0;
      return true;
    }
    return false;
  }

  updateCue(cueId, patch) {
    const cue = this.cues.find((c) => c.id === cueId);
    if (cue) {
      Object.assign(cue, patch);
      this.cues.sort((a, b) => a.number - b.number);
      return true;
    }
    return false;
  }

  getActiveCue() {
    return this.activeCueIndex >= 0 && this.activeCueIndex < this.cues.length
      ? this.cues[this.activeCueIndex]
      : null;
  }

  getNextCue() {
    return this.nextCueIndex >= 0 && this.nextCueIndex < this.cues.length
      ? this.cues[this.nextCueIndex]
      : null;
  }

  /**
   * Tasto GO: avvia la transizione dissolvenza verso la prossima Cue
   * @param {Array} currentFixtures - Stato attuale dei proiettori
   */
  go(currentFixtures) {
    if (this.cues.length === 0) return false;

    const targetIndex = this.nextCueIndex;
    const targetCue = this.cues[targetIndex];
    if (!targetCue) return false;

    // Snapshot dello stato di partenza (quello attualmente visibile)
    const fromStates = CueEngine.takeSnapshot(currentFixtures);
    const toStates = targetCue.fixtureSnapshots || {};

    const durationSeconds = Math.max(0.1, targetCue.fadeIn || 2.0);

    this.fade = {
      isFading: true,
      isPaused: false,
      progress: 0.0,
      startTime: Date.now(),
      durationMs: durationSeconds * 1000,
      fromStates,
      toStates,
    };

    this.activeCueIndex = targetIndex;
    // La prossima cue in sequenza
    this.nextCueIndex = (targetIndex + 1) % this.cues.length;

    return true;
  }

  /**
   * Tasto BACK: torna alla Cue precedente
   */
  back(currentFixtures) {
    if (this.cues.length === 0) return false;
    const prevIndex = (this.activeCueIndex - 1 + this.cues.length) % this.cues.length;
    this.nextCueIndex = prevIndex;
    return this.go(currentFixtures);
  }

  pause() {
    if (this.fade.isFading) {
      this.fade.isPaused = !this.fade.isPaused;
    }
  }

  stop() {
    this.fade.isFading = false;
    this.fade.isPaused = false;
    this.fade.progress = 1.0;
  }

  /**
   * Crossfade manuale cursore A/B
   * @param {number} value - 0.0 (Cue A) .. 1.0 (Cue B)
   */
  setManualCrossfade(value) {
    this.manualCrossfade = Math.max(0, Math.min(1, value));
    this.isManualMode = true;
  }

  /**
   * Esegue l'interpolazione continua a 60 FPS
   * @param {Array} fixtures - Array di fixture correnti
   * @param {number} now - Timestamp corrente Date.now()
   * @returns {{ updatedFixtures: Array, isFading: boolean, progress: number }}
   */
  tick(fixtures, now = Date.now()) {
    if (!this.fade.isFading && !this.isManualMode) {
      return { updatedFixtures: fixtures, isFading: false, progress: 1.0 };
    }

    let progress = this.fade.progress;

    if (this.fade.isFading && !this.fade.isPaused) {
      const elapsed = now - this.fade.startTime;
      progress = Math.min(1.0, elapsed / this.fade.durationMs);
      this.fade.progress = progress;

      if (progress >= 1.0) {
        this.fade.isFading = false;
      }
    } else if (this.isManualMode) {
      progress = this.manualCrossfade;
    }

    // Curva di dissolvenza morbida Smoothstep (Ease in / Ease out)
    const smoothT = progress * progress * (3 - 2 * progress);

    const updated = fixtures.map((fix) => {
      const from = this.fade.fromStates[fix.id] || fix.state;
      const to = this.fade.toStates[fix.id] || fix.state;
      if (!to) return fix;

      const interpolatedState = CueEngine.interpolateState(from, to, smoothT);
      return {
        ...fix,
        state: interpolatedState,
      };
    });

    return {
      updatedFixtures: updated,
      isFading: this.fade.isFading,
      progress,
    };
  }

  /**
   * Interpola due stati fixture (from -> to) con fattore t (0..1)
   */
  static interpolateState(from, to, t) {
    const s = { ...from };

    // 1. Dimmer / Intensità (fade continuo)
    if (to.intensity !== undefined) {
      const fromInt = from.intensity !== undefined ? from.intensity : 1;
      s.intensity = fromInt + (to.intensity - fromInt) * t;
    }

    // 2. Colore RGB (interpolazione vettoriale dello spazio colore)
    if (to.color) {
      const fromCol = from.color || { r: 1, g: 1, b: 1 };
      s.color = {
        r: fromCol.r + ((to.color.r !== undefined ? to.color.r : 1) - fromCol.r) * t,
        g: fromCol.g + ((to.color.g !== undefined ? to.color.g : 1) - fromCol.g) * t,
        b: fromCol.b + ((to.color.b !== undefined ? to.color.b : 1) - fromCol.b) * t,
      };
    }

    // 3. Pan & Tilt (traiettoria spaziale fluida)
    if (to.pan !== undefined) {
      const fromPan = from.pan !== undefined ? from.pan : 0.5;
      s.pan = fromPan + (to.pan - fromPan) * t;
    }
    if (to.tilt !== undefined) {
      const fromTilt = from.tilt !== undefined ? from.tilt : 0.5;
      s.tilt = fromTilt + (to.tilt - fromTilt) * t;
    }

    // 4. Zoom & Focus & Frost
    if (to.zoom !== undefined) {
      const fromZoom = from.zoom !== undefined ? from.zoom : 0.5;
      s.zoom = fromZoom + (to.zoom - fromZoom) * t;
    }
    if (to.focus !== undefined) {
      const fromFocus = from.focus !== undefined ? from.focus : 0.5;
      s.focus = fromFocus + (to.focus - fromFocus) * t;
    }
    if (to.frost !== undefined) {
      const fromFrost = from.frost !== undefined ? from.frost : 0;
      s.frost = fromFrost + (to.frost - fromFrost) * t;
    }

    // 5. Gobo & Prisma & Shutter: Snap immediato a metà dissolvenza (t >= 0.5)
    // per evitare rotazioni di ruota intermedie indesiderate tipiche delle fixture motorizzate
    if (t >= 0.5) {
      if (to.gobo !== undefined) s.gobo = to.gobo;
      if (to.goboRotate !== undefined) s.goboRotate = to.goboRotate;
      if (to.prism !== undefined) s.prism = to.prism;
      if (to.shutter !== undefined) s.shutter = to.shutter;
    }

    return s;
  }
}
