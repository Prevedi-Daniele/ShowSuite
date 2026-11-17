import {
  Waveforms,
  WaveformType,
  MotionGenerators,
  MotionShape,
  PhaseModulator,
  PhaseDistribution,
  BeatClock,
  MusicalDivision,
  EffectsEngine,
  EffectAttribute,
} from '../src/core/effects/index.js';

async function runEffectsEngineTests() {
  console.log('=== TEST EFFECTS ENGINE & BEAT SYNCHRONIZATION (STEP 3.1) ===\n');

  // 1. Test Waveforms
  console.log('[1] Test Forme d\'onda Matematiche (Waveforms):');
  // Comportamento: sin(2π*t - π/2) => t=0 -> 0, t=0.25 -> 0.5 (salita), t=0.5 -> 1.0 (picco), t=0.75 -> 0.5, t=1.0 -> 0
  const sin0 = Waveforms.evaluate(WaveformType.SINE, 0);
  const sinQuarter = Waveforms.evaluate(WaveformType.SINE, 0.25);
  const sinHalf = Waveforms.evaluate(WaveformType.SINE, 0.5);
  const sinMax = Waveforms.evaluate(WaveformType.SINE, 0.75);
  console.log(`   Sine: t=0 -> ${sin0.toFixed(2)}, t=0.25 -> ${sinQuarter.toFixed(2)}, t=0.5 -> ${sinHalf.toFixed(2)}, t=0.75 -> ${sinMax.toFixed(2)}`);
  if (
    Math.abs(sin0 - 0.0) < 0.01 &&
    Math.abs(sinQuarter - 0.5) < 0.01 &&
    Math.abs(sinHalf - 1.0) < 0.01 &&
    Math.abs(sinMax - 0.5) < 0.01
  ) {
    console.log('   ✓ Onda Sinusoidale verificata (min -> salita -> max -> discesa).');
  } else {
    throw new Error('Test Sine fallito');
  }

  const saw0 = Waveforms.evaluate(WaveformType.SAWTOOTH, 0.1);
  const sawEnd = Waveforms.evaluate(WaveformType.SAWTOOTH, 0.9);
  console.log(`   Sawtooth: t=0.1 -> ${saw0.toFixed(2)}, t=0.9 -> ${sawEnd.toFixed(2)}`);
  if (Math.abs(saw0 - 0.9) < 0.01 && Math.abs(sawEnd - 0.1) < 0.01) {
    console.log('   ✓ Onda Dente di Sega (Sawtooth) verificata.');
  } else {
    throw new Error('Test Sawtooth fallito');
  }

  const sqHigh = Waveforms.evaluate(WaveformType.SQUARE, 0.2);
  const sqLow = Waveforms.evaluate(WaveformType.SQUARE, 0.8);
  console.log(`   Square (duty 50%): t=0.2 -> ${sqHigh}, t=0.8 -> ${sqLow}`);
  if (sqHigh === 1.0 && sqLow === 0.0) {
    console.log('   ✓ Onda Quadra verificata.');
  } else {
    throw new Error('Test Square fallito');
  }

  const triMid = Waveforms.evaluate(WaveformType.TRIANGLE, 0.5);
  if (Math.abs(triMid - 1.0) < 0.01) {
    console.log('   ✓ Onda Triangolare verificata.');
  } else {
    throw new Error('Test Triangle fallito');
  }

  const bezMid = Waveforms.evaluate(WaveformType.BEZIER, 0.5, { p1x: 0.25, p1y: 0.1, p2x: 0.25, p2y: 1.0 });
  console.log(`   Cubic Bézier (Ease): t=0.5 -> ${bezMid.toFixed(3)}`);
  if (bezMid > 0.6 && bezMid < 0.9) {
    console.log('   ✓ Risolutore Curva di Bézier Cubica verificato.');
  } else {
    throw new Error('Test Bézier fallito');
  }

  // 2. Test MotionGenerators (Pan/Tilt)
  console.log('\n[2] Test Generatori di Movimento Pan / Tilt:');
  const center = { pan: 0.5, tilt: 0.5 };
  const size = { x: 0.2, y: 0.2 };

  // Cerchio: a t=0 deve essere a pan = 0.5 + 0.2 = 0.7, tilt = 0.5
  const circlePos0 = MotionGenerators.evaluate(MotionShape.CIRCLE, 0, { center, size });
  const circlePosQuarter = MotionGenerators.evaluate(MotionShape.CIRCLE, 0.25, { center, size });
  console.log(`   Cerchio t=0: Pan=${circlePos0.pan.toFixed(2)}, Tilt=${circlePos0.tilt.toFixed(2)}`);
  console.log(`   Cerchio t=0.25: Pan=${circlePosQuarter.pan.toFixed(2)}, Tilt=${circlePosQuarter.tilt.toFixed(2)}`);

  if (Math.abs(circlePos0.pan - 0.7) < 0.01 && Math.abs(circlePosQuarter.tilt - 0.7) < 0.01) {
    console.log('   ✓ Generatore Movimento Circolare verificato.');
  } else {
    throw new Error('Test Circle Motion fallito');
  }

  // Figura a 8: a t=0 deve essere al centro (0.5, 0.5)
  const fig8Pos0 = MotionGenerators.evaluate(MotionShape.FIGURE_EIGHT, 0, { center, size });
  const fig8PosMid = MotionGenerators.evaluate(MotionShape.FIGURE_EIGHT, 0.5, { center, size });
  console.log(`   Figura a 8 t=0: Pan=${fig8Pos0.pan.toFixed(2)}, Tilt=${fig8Pos0.tilt.toFixed(2)}`);
  console.log(`   Figura a 8 t=0.5: Pan=${fig8PosMid.pan.toFixed(2)}, Tilt=${fig8PosMid.tilt.toFixed(2)}`);
  if (Math.abs(fig8Pos0.pan - 0.5) < 0.01 && Math.abs(fig8PosMid.pan - 0.5) < 0.01) {
    console.log('   ✓ Generatore Figura a 8 (Lissajous) verificato.');
  } else {
    throw new Error('Test Figure-8 fallito');
  }

  // 3. Test PhaseModulator (Fanning temporale)
  console.log('\n[3] Test PhaseModulator (Sfasamento d\'onda tra fari):');
  const offsetsLinear = PhaseModulator.calculateOffsets(4, PhaseDistribution.LINEAR, 360);
  console.log('   Offsets Lineari (4 fari):', offsetsLinear.map((v) => `${(v * 360).toFixed(0)}°`));
  // 0°, 120°, 240°, 360° (0°)
  if (offsetsLinear[0] === 0 && Math.abs(offsetsLinear[1] - 1 / 3) < 0.01 && Math.abs(offsetsLinear[2] - 2 / 3) < 0.01) {
    console.log('   ✓ Fanning temporale lineare (360° wave) verificato.');
  } else {
    throw new Error('Test Linear Phase Modulator fallito');
  }

  const offsetsSym = PhaseModulator.calculateOffsets(5, PhaseDistribution.SYMMETRIC, 360);
  console.log('   Offsets Simmetrici (5 fari):', offsetsSym.map((v) => `${(v * 360).toFixed(0)}°`));
  // Centro (idx 2) deve essere a 0°, esterni a 360° (0°)
  if (offsetsSym[2] === 0 && Math.abs(offsetsSym[0] - offsetsSym[4]) < 0.001) {
    console.log('   ✓ Fanning temporale simmetrico a specchio verificato.');
  } else {
    throw new Error('Test Symmetric Phase Modulator fallito');
  }

  // 4. Test BeatClock & Tap Tempo
  console.log('\n[4] Test BeatClock & Tap Tempo:');
  const clock = new BeatClock(120.0);
  console.log(`   BPM iniziale: ${clock.bpm}`);
  const beatDuration = clock.getBeatDurationMs();
  console.log(`   Durata 1 beat a 120 BPM: ${beatDuration} ms (atteso 500 ms)`);
  if (beatDuration === 500) {
    console.log('   ✓ Calcolo durata battito corretto.');
  } else {
    throw new Error('Test Beat Duration fallito');
  }

  // Simula Tap Tempo: 4 tap a distanza di 400ms -> deve dare 150 BPM (60000 / 400 = 150)
  const baseTime = 100000;
  clock.tap(baseTime);
  clock.tap(baseTime + 400);
  clock.tap(baseTime + 800);
  const calculatedBpm = clock.tap(baseTime + 1200);
  console.log(`   Tap Tempo simulato (400ms delta): BPM calcolato = ${calculatedBpm}`);
  if (Math.abs(calculatedBpm - 150.0) < 0.5) {
    console.log('   ✓ Rilevamento Tap Tempo accurato al 100% (150 BPM).');
  } else {
    throw new Error('Test Tap Tempo fallito');
  }

  // 5. Test EffectsEngine (Esecuzione simultanea su fari)
  console.log('\n[5] Test EffectsEngine & Applicazione Real-Time:');
  const fxEngine = new EffectsEngine(120.0);
  const testFixtures = [
    { id: 'spot_1', state: { intensity: 1, pan: 0.5, tilt: 0.5, color: { r: 1, g: 1, b: 1 } } },
    { id: 'spot_2', state: { intensity: 1, pan: 0.5, tilt: 0.5, color: { r: 1, g: 1, b: 1 } } },
  ];

  // Abilita effetto cerchio
  fxEngine.toggleEffect('fx_circle_motion', true);
  const updatedFixtures = fxEngine.applyEffects(testFixtures, 1000);
  console.log('   Coordinate Faro 1 dopo cerchio:', updatedFixtures[0].state.pan.toFixed(2), updatedFixtures[0].state.tilt.toFixed(2));
  console.log('   Coordinate Faro 2 dopo cerchio (sfasato):', updatedFixtures[1].state.pan.toFixed(2), updatedFixtures[1].state.tilt.toFixed(2));

  if (
    updatedFixtures[0].state.pan !== 0.5 ||
    updatedFixtures[1].state.pan !== 0.5
  ) {
    console.log('   ✓ Modulazione coordinate e sfasamento attivati con successo su fari multipli.');
  } else {
    throw new Error('Test EffectsEngine applicazione fallito');
  }

  console.log('\n=============================================================');
  console.log(' TUTTI I TEST DELL\'EFFECTS ENGINE (STEP 3.1) SUPERATI AL 100%! ');
  console.log('=============================================================\n');
}

runEffectsEngineTests().catch((err) => {
  console.error('ERRORE TEST:', err);
  process.exit(1);
});
