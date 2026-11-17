/**
 * test_audio_matrix.js — Test Suite STEP 5.1
 * Verifica Audio Matrix Mixer Engine (QLab 5) per ShowSuite:
 * - Conversioni matematiche dB / Lineare e curve di dissolvenza
 * - Matrice di routing N x M (Master, Output Masters, Input Trims, Crosspoints)
 * - Calcolo accurato del guadagno lineare effettivo e gestione Mute
 * - Elaborazione buffer PCM Float32, sommatoria canali e Peak Metering balistico
 * - Fade temporizzati (AudioFadeController) su fader e crosspoints
 * - Integrazione Target multicanale (Stereo, Quad, 5.1 Surround)
 */

import {
  AudioMatrixMixer,
  AudioFadeController,
  AudioTarget,
  SurroundProfile,
  dbToLinear,
  linearToDb,
  formatDb,
  interpolateCurve,
  FadeCurveType,
  MIN_DB,
  MAX_DB,
  NEG_INF_DB,
} from '../src/core/qlab/audio/index.js';

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

console.log('=== TEST AUDIO MATRIX MIXER ENGINE (STEP 5.1) ===\n');

// ─────────────────────────────────────────────────────────────────
// [1] Test Matematica Audio e Conversioni dB / Lineare
// ─────────────────────────────────────────────────────────────────
console.log('[1] Test Conversioni dB / Lineare e Curve di Dissolvenza:');
{
  assert(approx(dbToLinear(0.0), 1.0), '0 dB -> guadagno lineare 1.0 (Unity Gain)');
  assert(approx(dbToLinear(6.0), 1.995), '+6 dB -> guadagno lineare ~2.0 (raddoppio)');
  assert(approx(dbToLinear(-6.0), 0.501), '-6 dB -> guadagno lineare ~0.50 (dimezzamento)');
  assert(dbToLinear(-60.0) === 0.0, '-60 dB -> 0.0 (sotto la soglia di rumore)');
  assert(dbToLinear(-100.0) === 0.0, '-100 dB (NEG_INF) -> 0.0');

  assert(approx(linearToDb(1.0), 0.0), '1.0 lineare -> 0.0 dB');
  assert(approx(linearToDb(2.0), 6.02), '2.0 lineare -> +6.02 dB');
  assert(linearToDb(0.0) === NEG_INF_DB, '0.0 lineare -> -100 dB (NEG_INF_DB)');

  assert(formatDb(0.0) === '0.0 dB', 'formatDb(0) -> "0.0 dB"');
  assert(formatDb(-6.5) === '-6.5 dB', 'formatDb(-6.5) -> "-6.5 dB"');
  assert(formatDb(-70.0) === '-INF', 'formatDb(-70) -> "-INF"');

  // Curve di interpolazione
  assert(interpolateCurve(0.5, FadeCurveType.LINEAR) === 0.5, 'Curva Lineare a t=0.5 -> 0.5');
  assert(interpolateCurve(0.5, FadeCurveType.SMOOTHSTEP) === 0.5, 'Curva Smoothstep a t=0.5 -> 0.5');
  assert(interpolateCurve(0.2, FadeCurveType.SMOOTHSTEP) < 0.2, 'Curva Smoothstep Ease-in a t=0.2 < 0.2');
}

// ─────────────────────────────────────────────────────────────────
// [2] Test Inizializzazione Matrice N x M e Routing
// ─────────────────────────────────────────────────────────────────
console.log('\n[2] Test Inizializzazione Matrice N x M, Faders e Guadagni:');
{
  // Matrice Stereo 2 in -> 2 out
  const mixer = new AudioMatrixMixer(2, 2);

  assert(mixer.inputCount === 2 && mixer.outputCount === 2, 'Matrice creata con 2 In e 2 Out');
  assert(mixer.masterLevel === 0.0, 'Master level iniziale a 0.0 dB');

  // Routing di fabbrica (1:1 diretto)
  assert(mixer.getCrosspoint(0, 0) === 0.0, 'Crosspoint [0,0] (In1 -> Out1) a 0.0 dB');
  assert(mixer.getCrosspoint(1, 1) === 0.0, 'Crosspoint [1,1] (In2 -> Out2) a 0.0 dB');
  assert(mixer.getCrosspoint(0, 1) === NEG_INF_DB, 'Crosspoint [0,1] isolato a -INF');
  assert(mixer.getCrosspoint(1, 0) === NEG_INF_DB, 'Crosspoint [1,0] isolato a -INF');

  // Calcolo guadagno lineare effettivo a 0 dB
  const g00 = mixer.getEffectiveLinearGain(0, 0);
  assert(approx(g00, 1.0), 'Guadagno lineare effettivo canale diretto = 1.0');

  // Applicazione Trim e Output Master
  mixer.setInputTrim(0, 6.0);       // +6 dB
  mixer.setOutputMaster(0, -6.0);   // -6 dB
  // +6dB + -6dB = 0dB complessivo -> linear gain 1.0
  const gCompensato = mixer.getEffectiveLinearGain(0, 0);
  assert(approx(gCompensato, 1.0), 'Combinazione InputTrim (+6dB) e OutputMaster (-6dB) = 0 dB (1.0)');

  // Test Mute
  mixer.setInputMute(0, true);
  assert(mixer.getEffectiveLinearGain(0, 0) === 0.0, 'Input Mute attivo -> guadagno lineare = 0.0');
  mixer.setInputMute(0, false);

  mixer.setOutputMute(0, true);
  assert(mixer.getEffectiveLinearGain(0, 0) === 0.0, 'Output Mute attivo -> guadagno lineare = 0.0');
  mixer.setOutputMute(0, false);

  mixer.setMasterMute(true);
  assert(mixer.getEffectiveLinearGain(0, 0) === 0.0, 'Master Mute attivo -> guadagno lineare = 0.0');
  mixer.setMasterMute(false);
}

// ─────────────────────────────────────────────────────────────────
// [3] Test Elaborazione Audio PCM, Sommatoria e Peak Metering
// ─────────────────────────────────────────────────────────────────
console.log('\n[3] Test Processing Audio PCM, Mixaggio e Peak Meters:');
{
  const mixer = new AudioMatrixMixer(2, 2);

  // Prepariamo 2 buffer di test da 256 campioni
  const sampleCount = 256;
  const inBuf0 = new Float32Array(sampleCount).fill(0.4); // In 1 costante a 0.4
  const inBuf1 = new Float32Array(sampleCount).fill(0.2); // In 2 costante a 0.2

  // 3.1 Mix standard 1:1
  const out1 = mixer.process([inBuf0, inBuf1], sampleCount);
  assert(approx(out1[0][0], 0.4), 'Out 1 riceve 0.4 da In 1');
  assert(approx(out1[1][0], 0.2), 'Out 2 riceve 0.2 da In 2');
  assert(approx(mixer.inputPeaks[0], 0.4), 'Peak meter In 1 a 0.4');
  assert(approx(mixer.outputPeaks[0], 0.4), 'Peak meter Out 1 a 0.4');

  // 3.2 Routing sommato: Invia anche In 1 a Out 2 a 0 dB
  mixer.setCrosspoint(0, 1, 0.0);
  const outSum = mixer.process([inBuf0, inBuf1], sampleCount);
  // Out 2 riceve sia In 0 (0.4) che In 1 (0.2) = 0.6
  assert(approx(outSum[1][0], 0.6), 'Out 2 somma correttamente In 1 + In 2 (0.4 + 0.2 = 0.6)');
  assert(approx(mixer.outputPeaks[1], 0.6), 'Peak meter Out 2 riflette la sommatoria a 0.6');

  // 3.3 Decadimento balistico dei peak meters
  mixer.decayPeaks(0.5, 20.0); // Decadimento di 10 dB in 0.5s -> ~0.316x
  assert(mixer.outputPeaks[1] < 0.6, 'Peak meter decade regolarmente con la balistica temporale');
  assert(mixer.outputPeaks[1] > 0.0, 'Peak meter non si azzera bruscamente (decadimento esponenziale)');
}

// ─────────────────────────────────────────────────────────────────
// [4] Test Dissolvenze Temporizzate (AudioFadeController)
// ─────────────────────────────────────────────────────────────────
console.log('\n[4] Test Dissolvenze Temporizzate (AudioFadeController):');
{
  const mixer = new AudioMatrixMixer(2, 2);
  mixer.setMaster(0.0);

  // Dissolvenza del Master da 0.0 dB a -20.0 dB in 1.0s
  let fadeCompleted = false;
  mixer.fadeTo(
    {
      master: -20.0,
      outputMasters: { 0: -6.0 },
      crosspoints: [{ inIdx: 0, outIdx: 1, targetDb: -3.0 }],
    },
    1.0,
    FadeCurveType.SMOOTHSTEP,
    () => {
      fadeCompleted = true;
    }
  );

  assert(mixer.isFading() === true, 'Dissolvenza avviata correttamente');

  // Avanzamento a metà tempo (t = 0.5s)
  mixer.tick(0.5);
  // A metà tempo smoothstep è esattamente a metà: 0 + (-20 - 0)*0.5 = -10.0 dB
  assert(approx(mixer.masterLevel, -10.0), 'Master fader a metà dissolvenza (-10.0 dB)');
  assert(approx(mixer.outputMasters[0], -3.0), 'Output master 0 a metà dissolvenza (-3.0 dB)');

  // Completamento dissolvenza (un altro tick di 0.5s)
  mixer.tick(0.5);
  assert(approx(mixer.masterLevel, -20.0), 'Master fader ha raggiunto il target esatto (-20.0 dB)');
  assert(approx(mixer.outputMasters[0], -6.0), 'Output master 0 ha raggiunto il target (-6.0 dB)');
  assert(approx(mixer.getCrosspoint(0, 1), -3.0), 'Crosspoint [0,1] ha raggiunto il target (-3.0 dB)');
  assert(fadeCompleted === true, 'Callback onComplete eseguito al termine del fade');
  assert(mixer.isFading() === false, 'Stato di dissolvenza terminato');
}

// ─────────────────────────────────────────────────────────────────
// [5] Test Integrazione Target Multicanale & Ridimensionamento
// ─────────────────────────────────────────────────────────────────
console.log('\n[5] Test AudioTarget Multicanale e Ridimensionamento Matrice:');
{
  // Creazione target Surround 5.1 (6 In -> 8 Out)
  const target51 = new AudioTarget({
    name: 'Teatro 5.1 Surround',
    inputChannels: 6,
    profile: SurroundProfile.SURROUND_5_1,
    outputDeviceName: 'Dante Virtual Soundcard 8ch',
    outputDeviceChannels: 8,
  });

  assert(target51.inputChannelNames.length === 6, 'AudioTarget 5.1 ha 6 canali d\'ingresso');
  assert(target51.inputChannelNames[3] === 'Sub / LFE', 'Canale 4 identificato come Sub / LFE');

  const mixerSurround = new AudioMatrixMixer(6, 8, target51);
  assert(mixerSurround.inputCount === 6 && mixerSurround.outputCount === 8, 'Matrice 6x8 inizializzata');

  // Ridimensionamento dinamico a 8 In x 16 Out
  mixerSurround.setCrosspoint(0, 0, -3.0);
  mixerSurround.resize(8, 16);

  assert(mixerSurround.inputCount === 8 && mixerSurround.outputCount === 16, 'Matrice espansa a 8 In x 16 Out');
  assert(mixerSurround.getCrosspoint(0, 0) === -3.0, 'Valori crosspoint preesistenti preservati dopo il resize');
  assert(mixerSurround.getCrosspoint(7, 7) === 0.0, 'Nuovi canali inizializzati con routing diagonale 1:1');
}

// ─────────────────────────────────────────────────────────────────
// Riepilogo
// ─────────────────────────────────────────────────────────────────
console.log('\n' + '='.repeat(58));
if (failed === 0) {
  console.log(` TUTTI I TEST DELL'AUDIO MATRIX MIXER SUPERATI AL 100%! (${passed}/${passed + failed})`);
} else {
  console.log(` ✗ ${failed} TEST FALLITI su ${passed + failed} totali`);
}
console.log('='.repeat(58) + '\n');
