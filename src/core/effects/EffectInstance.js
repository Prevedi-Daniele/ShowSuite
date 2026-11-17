import { MusicalDivision } from './BeatClock.js';
import { WaveformType } from './Waveforms.js';
import { MotionShape } from './MotionGenerators.js';
import { PhaseDistribution } from './PhaseModulator.js';

export const EffectAttribute = {
  PAN_TILT: 'pan_tilt',
  INTENSITY: 'intensity',
  COLOR_HUE: 'color_hue',
  ZOOM: 'zoom',
};

export default class EffectInstance {
  constructor(config = {}) {
    this.id = config.id || `fx_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    this.name = config.name || 'Nuovo Effetto';
    this.enabled = config.enabled !== undefined ? config.enabled : true;
    this.attribute = config.attribute || EffectAttribute.INTENSITY;

    // Sincronizzazione musicale e fanning temporale
    this.division = config.division || MusicalDivision.DIV_1_1;
    this.phaseSpread = config.phaseSpread !== undefined ? config.phaseSpread : 360; // 360° = onda completa
    this.distribution = config.distribution || PhaseDistribution.LINEAR;

    // Fari bersaglio (se vuoto, si applica a tutti i fari compatibili)
    this.fixtureIds = config.fixtureIds ? [...config.fixtureIds] : [];

    // Parametri specifici per Movimento Pan/Tilt
    this.motionShape = config.motionShape || MotionShape.CIRCLE;
    this.motionCenter = config.motionCenter ? { ...config.motionCenter } : { pan: 0.5, tilt: 0.5 };
    this.motionSize = config.motionSize ? { ...config.motionSize } : { x: 0.25, y: 0.25 };
    this.motionRotation = config.motionRotation || 0;

    // Parametri specifici per Canali Scalari (Dimmer, Hue, Zoom)
    this.waveform = config.waveform || WaveformType.SINE;
    this.depth = config.depth !== undefined ? config.depth : 1.0;     // Ampiezza escursione (0..1)
    this.baseValue = config.baseValue !== undefined ? config.baseValue : 0.5; // Valore centrale di offset
    this.waveformOptions = config.waveformOptions ? { ...config.waveformOptions } : {};
  }
}
