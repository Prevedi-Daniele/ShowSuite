/**
 * src/core/qlab/audio/index.js — Barrel exports per il motore Audio Matrix Mixer di QLab 5
 */

export { default as AudioMatrixMixer } from './AudioMatrixMixer.js';
export { default as AudioFadeController } from './AudioFadeController.js';
export { default as AudioTarget, SurroundProfile } from './AudioTarget.js';
export {
  dbToLinear,
  linearToDb,
  formatDb,
  interpolateCurve,
  FadeCurveType,
  MIN_DB,
  MAX_DB,
  NEG_INF_DB,
} from './AudioMath.js';
