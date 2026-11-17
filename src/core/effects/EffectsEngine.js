import BeatClock, { MusicalDivision } from './BeatClock.js';
import Waveforms, { WaveformType } from './Waveforms.js';
import MotionGenerators, { MotionShape } from './MotionGenerators.js';
import PhaseModulator, { PhaseDistribution } from './PhaseModulator.js';
import EffectInstance, { EffectAttribute } from './EffectInstance.js';

/**
 * Converte Hue (0..360) in RGB standard [0, 1]
 */
function hueToRgb(hue) {
  const h = (hue % 360) / 60;
  const c = 1;
  const x = c * (1 - Math.abs((h % 2) - 1));
  let r = 0, g = 0, b = 0;

  if (h >= 0 && h < 1) { r = c; g = x; b = 0; }
  else if (h >= 1 && h < 2) { r = x; g = c; b = 0; }
  else if (h >= 2 && h < 3) { r = 0; g = c; b = x; }
  else if (h >= 3 && h < 4) { r = 0; g = x; b = c; }
  else if (h >= 4 && h < 5) { r = x; g = 0; b = c; }
  else if (h >= 5 && h < 6) { r = c; g = 0; b = x; }

  return { r, g, b };
}

export default class EffectsEngine {
  constructor(initialBpm = 120.0) {
    this.clock = new BeatClock(initialBpm);
    this.effects = [];
    this.initDefaultTemplates();
  }

  initDefaultTemplates() {
    // 1. Movimento Circolare Pan/Tilt
    const circleMotion = new EffectInstance({
      id: 'fx_circle_motion',
      name: 'Ballyhoo Circolare',
      enabled: false,
      attribute: EffectAttribute.PAN_TILT,
      motionShape: MotionShape.CIRCLE,
      motionCenter: { pan: 0.5, tilt: 0.55 },
      motionSize: { x: 0.25, y: 0.2 },
      division: MusicalDivision.DIV_1_1, // 1 misura
      phaseSpread: 360,
      distribution: PhaseDistribution.LINEAR,
    });

    // 2. Figura a 8 / Infinito
    const figure8Motion = new EffectInstance({
      id: 'fx_figure8_motion',
      name: 'Figura a 8 (Lissajous)',
      enabled: false,
      attribute: EffectAttribute.PAN_TILT,
      motionShape: MotionShape.FIGURE_EIGHT,
      motionCenter: { pan: 0.5, tilt: 0.5 },
      motionSize: { x: 0.3, y: 0.2 },
      division: MusicalDivision.DIV_2_1, // 2 misure
      phaseSpread: 360,
      distribution: PhaseDistribution.SYMMETRIC,
    });

    // 3. Onda Dimmer Sinusoidale (Chase fluido)
    const dimmerWave = new EffectInstance({
      id: 'fx_dimmer_wave',
      name: 'Onda Dimmer Sinusoidale',
      enabled: false,
      attribute: EffectAttribute.INTENSITY,
      waveform: WaveformType.SINE,
      depth: 1.0,
      baseValue: 0.5,
      division: MusicalDivision.DIV_1_2, // 2 beat
      phaseSpread: 360,
      distribution: PhaseDistribution.LINEAR,
    });

    // 4. Arcobaleno Cromatico (Rainbow Wave)
    const rainbowWave = new EffectInstance({
      id: 'fx_rainbow_wave',
      name: 'Onda Arcobaleno (Rainbow)',
      enabled: false,
      attribute: EffectAttribute.COLOR_HUE,
      waveform: WaveformType.RAMP,
      depth: 1.0,
      baseValue: 0.5,
      division: MusicalDivision.DIV_2_1, // 2 misure
      phaseSpread: 360,
      distribution: PhaseDistribution.LINEAR,
    });

    this.effects = [circleMotion, figure8Motion, dimmerWave, rainbowWave];
  }

  addEffect(config) {
    const fx = new EffectInstance(config);
    this.effects.push(fx);
    return fx;
  }

  removeEffect(id) {
    const idx = this.effects.findIndex((e) => e.id === id);
    if (idx !== -1) {
      this.effects.splice(idx, 1);
      return true;
    }
    return false;
  }

  getEffectById(id) {
    return this.effects.find((e) => e.id === id) || null;
  }

  toggleEffect(id, forceState = null) {
    const fx = this.getEffectById(id);
    if (fx) {
      fx.enabled = forceState !== null ? forceState : !fx.enabled;
      return fx.enabled;
    }
    return false;
  }

  /**
   * Applica tutti gli effetti attivi all'array di fari
   * @param {Array} fixtures - Array di fixture
   * @param {number} now - Timestamp corrente
   * @returns {Array} Array di fixture con stati aggiornati
   */
  applyEffects(fixtures, now = Date.now()) {
    if (!fixtures || fixtures.length === 0) return fixtures;

    const activeEffects = this.effects.filter((e) => e.enabled);
    if (activeEffects.length === 0) return fixtures;

    // Clona per evitare mutazioni indesiderate dello stato base
    const modifiedFixtures = fixtures.map((f) => ({
      ...f,
      state: {
        ...f.state,
        color: { ...(f.state?.color || { r: 1, g: 1, b: 1 }) },
      },
    }));

    activeEffects.forEach((fx) => {
      // Determina quali fari sono bersaglio dell'effetto
      const targetFixtures = fx.fixtureIds && fx.fixtureIds.length > 0
        ? modifiedFixtures.filter((f) => fx.fixtureIds.includes(f.id))
        : modifiedFixtures;

      if (targetFixtures.length === 0) return;

      // 1. Fase base del clock musicale per la divisione specificata
      const masterPhase = this.clock.getPhase(now, fx.division);

      // 2. Calcola sfasamenti per ciascun faro target
      const phaseOffsets = PhaseModulator.calculateOffsets(
        targetFixtures.length,
        fx.distribution,
        fx.phaseSpread
      );

      targetFixtures.forEach((fix, idx) => {
        const fixturePhase = (masterPhase + phaseOffsets[idx]) % 1.0;

        // Modulazione in base all'attributo
        switch (fx.attribute) {
          case EffectAttribute.PAN_TILT: {
            const coords = MotionGenerators.evaluate(fx.motionShape, fixturePhase, {
              center: fx.motionCenter,
              size: fx.motionSize,
              rotation: fx.motionRotation,
            });
            fix.state.pan = coords.pan;
            fix.state.tilt = coords.tilt;
            break;
          }

          case EffectAttribute.INTENSITY: {
            const waveVal = Waveforms.evaluate(fx.waveform, fixturePhase, fx.waveformOptions);
            // Scala tra (baseValue - depth/2) e (baseValue + depth/2) o da 0 a depth
            const intensity = Math.max(0, Math.min(1, waveVal * fx.depth));
            fix.state.intensity = intensity;
            break;
          }

          case EffectAttribute.COLOR_HUE: {
            const waveVal = Waveforms.evaluate(fx.waveform, fixturePhase, fx.waveformOptions);
            const hueDeg = (waveVal * 360) % 360;
            const rgb = hueToRgb(hueDeg);
            fix.state.color.r = rgb.r;
            fix.state.color.g = rgb.g;
            fix.state.color.b = rgb.b;
            break;
          }

          case EffectAttribute.ZOOM: {
            const waveVal = Waveforms.evaluate(fx.waveform, fixturePhase, fx.waveformOptions);
            fix.state.zoom = Math.max(0, Math.min(1, waveVal * fx.depth));
            break;
          }

          default:
            break;
        }
      });
    });

    return modifiedFixtures;
  }
}
