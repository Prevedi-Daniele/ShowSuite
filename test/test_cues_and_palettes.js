import { PaletteManager, PaletteType, CueEngine, Cue } from '../src/core/control/index.js';

async function runCuesAndPalettesTests() {
  console.log('=== TEST PRESETS & PALETTES LIBRARY + CUES ENGINE ===\n');

  // 1. Test PaletteManager
  console.log('[1] Test PaletteManager:');
  const palManager = new PaletteManager();
  const allPals = palManager.getPalettes();
  console.log(`   ✓ Inizializzate ${allPals.length} palette predefinite.`);

  const colorPals = palManager.getPalettes(PaletteType.COLOR);
  const posPals = palManager.getPalettes(PaletteType.POSITION);
  const beamPals = palManager.getPalettes(PaletteType.BEAM);
  const presetPals = palManager.getPalettes(PaletteType.PRESET);

  console.log(`   ✓ Categorie: ${colorPals.length} Colore, ${posPals.length} Posizione, ${beamPals.length} Beam, ${presetPals.length} Presets.`);

  // Test applicazione palette Colore
  const dummyFixtureState = {
    intensity: 0.5,
    pan: 0.5,
    tilt: 0.5,
    color: { r: 0, g: 0, b: 0 },
    zoom: 0.5,
    gobo: 0,
    prism: 0,
  };

  const stateWithColor = palManager.applyToState('pal_col_amber', dummyFixtureState);
  if (stateWithColor.color.r === 1 && stateWithColor.color.b === 0.05 && stateWithColor.pan === 0.5) {
    console.log('   ✓ Applicazione Palette Colore (Ambra Caldo) corretta (pan/tilt inalterati).');
  } else {
    throw new Error('Test applicazione palette colore fallito');
  }

  // Test applicazione palette Posizione
  const stateWithPos = palManager.applyToState('pal_pos_down_stage', stateWithColor);
  if (stateWithPos.tilt === 0.78 && stateWithPos.color.r === 1) {
    console.log('   ✓ Applicazione Palette Posizione (Pedana Frontale) corretta (colore inalterato).');
  } else {
    throw new Error('Test applicazione palette posizione fallito');
  }

  // Test creazione custom palette
  const customPal = palManager.addPalette({
    name: 'Mio Spot Speciale',
    type: PaletteType.PRESET,
    data: { intensity: 1, pan: 0.1, tilt: 0.9, color: { r: 0.5, g: 1, b: 0.5 } },
  });
  const stateFromCustom = palManager.applyToState(customPal.id, dummyFixtureState);
  if (stateFromCustom.pan === 0.1 && stateFromCustom.tilt === 0.9 && stateFromCustom.intensity === 1) {
    console.log(`   ✓ Creazione ed esecuzione Custom Palette "${customPal.name}" superata.`);
  } else {
    throw new Error('Test custom palette fallito');
  }

  // 2. Test CueEngine & Interpolazione
  console.log('\n[2] Test CueEngine (Interpolazione Dissolvenze a 60 FPS):');
  const cueEngine = new CueEngine();
  console.log(`   ✓ CueEngine avviato con ${cueEngine.cues.length} scene standard.`);

  const fromState = {
    intensity: 0.0,
    color: { r: 1, g: 0, b: 0 }, // Rosso
    pan: 0.2,
    tilt: 0.2,
    gobo: 0,
    prism: 0,
  };

  const toState = {
    intensity: 1.0,
    color: { r: 0, g: 0, b: 1 }, // Blu
    pan: 0.8,
    tilt: 0.8,
    gobo: 0.5,
    prism: 1,
  };

  // Interpolazione al 50% (t = 0.5)
  const midState = CueEngine.interpolateState(fromState, toState, 0.5);
  console.log('   Interpolazione al 50%:');
  console.log(`     Dimmer: ${midState.intensity} (atteso 0.5)`);
  console.log(`     Colore R: ${midState.color.r.toFixed(2)}, B: ${midState.color.b.toFixed(2)} (atteso 0.50, 0.50)`);
  console.log(`     Pan: ${midState.pan.toFixed(2)}, Tilt: ${midState.tilt.toFixed(2)} (atteso 0.50, 0.50)`);
  console.log(`     Gobo Snap: ${midState.gobo} (atteso 0.5 a t>=0.5)`);
  console.log(`     Prism Snap: ${midState.prism} (atteso 1 a t>=0.5)`);

  if (
    Math.abs(midState.intensity - 0.5) < 0.001 &&
    Math.abs(midState.color.r - 0.5) < 0.001 &&
    Math.abs(midState.color.b - 0.5) < 0.001 &&
    Math.abs(midState.pan - 0.5) < 0.001 &&
    midState.gobo === 0.5 &&
    midState.prism === 1
  ) {
    console.log('   ✓ Interpolazione continua + Snap Gobo/Prisma a metà transizione corretti al 100%.');
  } else {
    throw new Error('Test interpolazione Cue fallito');
  }

  // 3. Test Tasto GO & Sequenza Scenica
  console.log('\n[3] Test Esecuzione Tasto GO & Transizione Temporizzata:');
  const testFixtures = [
    { id: 'spot_1', state: { intensity: 0, pan: 0.5, tilt: 0.5, color: { r: 1, g: 1, b: 1 } } },
  ];

  // GO alla prima cue
  const ok1 = cueEngine.go(testFixtures);
  if (!ok1 || !cueEngine.fade.isFading || cueEngine.activeCueIndex !== 0) {
    throw new Error('Test GO 1 fallito');
  }
  console.log(`   ✓ GO attivato: Cue Attiva: Q${cueEngine.cues[cueEngine.activeCueIndex].number}, Prossima: Q${cueEngine.cues[cueEngine.nextCueIndex].number}`);

  // Simula tick a metà tempo
  const halfwayTime = cueEngine.fade.startTime + cueEngine.fade.durationMs / 2;
  const tickHalf = cueEngine.tick(testFixtures, halfwayTime);
  console.log(`   ✓ Tick a metà dissolvenza: progresso ${Math.round(tickHalf.progress * 100)}%, isFading = ${tickHalf.isFading}`);

  // Simula tick alla fine
  const endTime = cueEngine.fade.startTime + cueEngine.fade.durationMs + 50;
  const tickEnd = cueEngine.tick(testFixtures, endTime);
  console.log(`   ✓ Tick al termine dissolvenza: progresso ${Math.round(tickEnd.progress * 100)}%, isFading = ${tickEnd.isFading}`);

  if (tickEnd.progress === 1.0 && tickEnd.isFading === false) {
    console.log('   ✓ Completamento dissolvenza e rilascio fader verificati.');
  } else {
    throw new Error('Test termine dissolvenza fallito');
  }

  // 4. Test Tasto Back
  console.log('\n[4] Test Tasto Back (Ritorno a scena precedente):');
  cueEngine.back(testFixtures);
  console.log(`   ✓ Tasto Back eseguito: Cue Attiva: Q${cueEngine.cues[cueEngine.activeCueIndex].number}`);

  // 5. Test Crossfader Manuale A/B
  console.log('\n[5] Test Crossfader Manuale A/B:');
  cueEngine.setManualCrossfade(0.75);
  if (cueEngine.isManualMode && cueEngine.manualCrossfade === 0.75) {
    console.log('   ✓ Crossfader manuale impostato a 75% con successo.');
  } else {
    throw new Error('Test crossfader manuale fallito');
  }

  console.log('\n=============================================================');
  console.log(' TUTTI I TEST DI PRESETS, PALETTES E CUES ENGINE SUPERATI! ');
  console.log('=============================================================\n');
}

runCuesAndPalettesTests().catch((err) => {
  console.error('ERRORE TEST:', err);
  process.exit(1);
});
