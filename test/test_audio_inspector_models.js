/**
 * test_audio_inspector_models.js — Test Suite STEP 5.2
 * Verifica modelli e logica di AudioInspector (AudioCue, MicCue, Slices, Vari-speed, In/Out Points)
 */

import {
  AudioCue,
  MicCue,
  CueType,
  CueState,
} from '../src/core/qlab/index.js';

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) {
    console.log(`   ✓ ${label}`);
    passed++;
  } else {
    console.error(`   ✗ FALLITO: ${label}`);
    failed++;
    process.exitCode = 1;
  }
}

function approx(a, b, eps = 0.01) {
  return Math.abs(a - b) < eps;
}

console.log('=== TEST AUDIO & MIC INSPECTOR MODELS (STEP 5.2) ===\n');

// ─────────────────────────────────────────────────────────────────
// [1] Test AudioCue: In/Out Points, Durata Effettiva e Vari-speed
// ─────────────────────────────────────────────────────────────────
console.log('[1] Test AudioCue: In/Out Points, Durata Effettiva e Vari-speed:');
{
  const audioCue = new AudioCue({
    number: 'A1',
    name: 'Canzone Test',
    inPoint: 2.0,
    outPoint: 10.0,
    playbackRate: 1.0,
    playCount: 1,
  });

  assert(audioCue.type === CueType.AUDIO, 'Tipo cue: AUDIO');
  assert(audioCue.inPoint === 2.0 && audioCue.outPoint === 10.0, 'In-Point = 2.0s, Out-Point = 10.0s');
  assert(approx(audioCue.duration, 8.0), 'Durata nominale (10.0 - 2.0) = 8.0s a 1.0x');

  // Test Vari-speed (2.0x -> durata dimezzata a 4.0s)
  audioCue.setPlaybackRate(2.0);
  assert(approx(audioCue.duration, 4.0), 'Durata a 2.0x (8.0s / 2.0) = 4.0s');

  // Test Vari-speed (0.5x -> durata raddoppiata a 16.0s)
  audioCue.setPlaybackRate(0.5);
  assert(approx(audioCue.duration, 16.0), 'Durata a 0.5x (8.0s / 0.5) = 16.0s');

  // Reset rate e test ripetizioni multiple
  audioCue.setPlaybackRate(1.0);
  audioCue.playCount = 3;
  audioCue.updateEffectiveDuration();
  assert(approx(audioCue.duration, 24.0), 'Durata con 3 ripetizioni (8.0s * 3) = 24.0s');

  // Test Infinite Loop
  audioCue.infiniteLoop = true;
  audioCue.updateEffectiveDuration();
  assert(audioCue.duration === Infinity, 'Infinite Loop impostato -> durata = Infinity');
}

// ─────────────────────────────────────────────────────────────────
// [2] Test AudioCue: Pitch Shifting e Slicing Grafico
// ─────────────────────────────────────────────────────────────────
console.log('\n[2] Test AudioCue: Pitch Shifting e Gestione Slices:');
{
  const audioCue = new AudioCue({
    number: 'A2',
    name: 'Voice Track',
    inPoint: 0.0,
    outPoint: 20.0,
  });

  // Pitch shift
  audioCue.setPitchShift(5); // +5 semitoni
  assert(audioCue.pitchShift === 5, 'Pitch Shift impostato a +5 semitoni');
  audioCue.setPitchShift(-12); // -1 ottava
  assert(audioCue.pitchShift === -12, 'Pitch Shift impostato a -12 semitoni');

  // Slicing: aggiunta slice temporali
  const s1 = audioCue.addSlice(5.0, 1);
  const s2 = audioCue.addSlice(12.0, 2);
  const s0 = audioCue.addSlice(2.5, 1); // aggiunta non ordinata

  assert(audioCue.slices.length === 3, 'Aggiunte 3 slice temporali');
  // Verifica ordinamento cronologico automatico
  assert(audioCue.slices[0].time === 2.5 && audioCue.slices[1].time === 5.0 && audioCue.slices[2].time === 12.0, 'Slices ordinate cronologicamente in modo automatico');

  // Rimozione slice
  audioCue.removeSlice(s1.id);
  assert(audioCue.slices.length === 2, 'Slice rimossa con successo (2 rimanenti)');
}

// ─────────────────────────────────────────────────────────────────
// [3] Test MicCue: Live Input, Device e Gain Trim
// ─────────────────────────────────────────────────────────────────
console.log('\n[3] Test MicCue: Live Input, Device e Gain Trim:');
{
  const micCue = new MicCue({
    number: 'M1',
    name: 'Microfono Cantante',
    inputDeviceName: 'Focusrite Scarlett 2i2 USB',
    channels: 2,
    micGain: 6.0,
  });

  assert(micCue.type === CueType.MIC, 'Tipo cue: MIC');
  assert(micCue.inputDeviceName === 'Focusrite Scarlett 2i2 USB', 'Nome device memorizzato');
  assert(micCue.channels === 2, 'Canali microfono: 2ch');
  assert(micCue.micGain === 6.0, 'Mic Gain iniziale: +6.0 dB');

  // Verifica che il Gain si sia propagato sui Trim della matrice interna
  assert(micCue.matrix !== null, 'Matrice di missaggio integrata presente');
  assert(micCue.matrix.inputTrims[0] === 6.0 && micCue.matrix.inputTrims[1] === 6.0, 'Trim d\'ingresso matrice sincronizzati al Mic Gain (+6.0 dB)');

  // Modifica Mic Gain
  micCue.setMicGain(12.0);
  assert(micCue.matrix.inputTrims[0] === 12.0, 'Modifica dinamica Mic Gain (+12.0 dB) applicata alla matrice');
}

// ─────────────────────────────────────────────────────────────────
// Riepilogo
// ─────────────────────────────────────────────────────────────────
console.log('\n' + '='.repeat(58));
if (failed === 0) {
  console.log(` TUTTI I TEST AUDIO/MIC INSPECTOR SUPERATI AL 100%! (${passed}/${passed + failed})`);
} else {
  console.log(` ✗ ${failed} TEST FALLITI su ${passed + failed} totali`);
}
console.log('='.repeat(58) + '\n');
