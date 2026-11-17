/**
 * test_video_engine.js — Suite di test per il Video & Text Engine (STEP 6.1)
 * 
 * Verifica:
 * 1. VideoStage: dimensioni, screen mappings fisici, ordinamento layer, rendering composito
 * 2. VideoCue: trasformazioni 2D (traslazione, scala, rotazione, opacità, blendMode), aspect ratio, timing
 * 3. TextCue: tipografia (font, size, weight, allineamento, drop shadow, background box), multiriga
 * 4. CameraCue: acquisizione live, supporto driver WebRTC / DirectShow / v4l2, formati e mirror
 * 5. VideoEngine: gestione stages, enumerazione display fisici e telecamere, pipeline renderStage
 */

import {
  VideoStage,
  VideoCue,
  TextCue,
  CameraCue,
  VideoEngine,
  CueState,
  CueType,
} from '../src/core/qlab/index.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

// Mock Canvas 2D Context per test headless
function createMockCanvasContext() {
  const calls = [];
  return {
    calls,
    fillStyle: '#000000',
    strokeStyle: '#ffffff',
    lineWidth: 1,
    font: '10px sans-serif',
    textAlign: 'center',
    textBaseline: 'middle',
    globalAlpha: 1.0,
    globalCompositeOperation: 'source-over',
    shadowColor: '',
    shadowBlur: 0,
    shadowOffsetX: 0,
    shadowOffsetY: 0,

    save() { this.calls.push('save'); },
    restore() { this.calls.push('restore'); },
    translate(x, y) { this.calls.push(`translate(${x},${y})`); },
    rotate(angle) { this.calls.push(`rotate(${angle.toFixed(2)})`); },
    scale(x, y) { this.calls.push(`scale(${x},${y})`); },
    fillRect(x, y, w, h) { this.calls.push(`fillRect(${x},${y},${w},${h})`); },
    strokeRect(x, y, w, h) { this.calls.push(`strokeRect(${x},${y},${w},${h})`); },
    fillText(text, x, y) { this.calls.push(`fillText("${text}",${x},${y})`); },
    beginPath() { this.calls.push('beginPath'); },
    moveTo(x, y) { this.calls.push(`moveTo(${x},${y})`); },
    lineTo(x, y) { this.calls.push(`lineTo(${x},${y})`); },
    arc(x, y, r, sa, ea) { this.calls.push(`arc(${x},${y},${r})`); },
    stroke() { this.calls.push('stroke'); },
    fill() { this.calls.push('fill'); },
    roundRect(x, y, w, h, r) { this.calls.push(`roundRect(${x},${y},${w},${h},${r})`); },
    measureText(text) { return { width: (text || '').length * 10 }; },
  };
}

async function runTests() {
  console.log('=== TEST SUITE: VIDEO & TEXT ENGINE (STEP 6.1) ===\n');

  // --- GRUPPO 1: VideoStage ---
  console.log('--- 1. Test VideoStage ---');
  const stage = new VideoStage({
    id: 'stage_test',
    name: 'Proscenium Projectors',
    width: 3840,
    height: 1080,
  });

  assert(stage.id === 'stage_test', 'ID dello Stage impostato correttamente');
  assert(stage.width === 3840 && stage.height === 1080, 'Dimensioni panoramiche 3840x1080 configurate');
  assert(stage.screenMappings.length === 1, 'Screen mapping predefinito presente');

  // Aggiunta secondo schermo (Edge blending / mapping proiettore 2)
  const mapping2 = stage.addScreenMapping({
    screenId: 'display_projector_2',
    screenName: 'Projector Right Edge Blend',
    stageX: 1920,
    stageY: 0,
    stageWidth: 1920,
    stageHeight: 1080,
  });
  assert(stage.screenMappings.length === 2, 'Secondo mapping di output aggiunto con successo');
  assert(mapping2.stageX === 1920, 'Offset orizzontale del mapping configurato');

  // Layer sorting test
  const cueA = { id: 'c1', stageId: 'stage_test', layer: 3, state: 'running' };
  const cueB = { id: 'c2', stageId: 'stage_test', layer: 1, state: 'running' };
  const cueC = { id: 'c3', stageId: 'other_stage', layer: 2, state: 'running' };
  const cueD = { id: 'c4', stageId: 'stage_test', layer: 2, state: 'idle' }; // non running

  const sorted = stage.getSortedLayers([cueA, cueB, cueC, cueD]);
  assert(sorted.length === 2, 'Filtra solo le cue attive assegnate a questo stage');
  assert(sorted[0].id === 'c2' && sorted[1].id === 'c1', 'Ordina i layer in senso crescente (layer 1 prima di layer 3)');

  // Rendering composito
  const ctx = createMockCanvasContext();
  stage.render(ctx, [cueA, cueB]);
  assert(ctx.calls.includes('fillRect(0,0,3840,1080)'), 'Rendering sfondo dello Stage eseguito');
  assert(ctx.calls.filter((c) => c === 'save').length >= 2, 'Salvataggio stato canvas eseguito per ciascun layer');

  // --- GRUPPO 2: VideoCue ---
  console.log('\n--- 2. Test VideoCue ---');
  const videoCue = new VideoCue({
    name: 'Background Loop.mp4',
    filePath: '/media/video/background.mp4',
    stageId: 'stage_test',
    layer: 2,
    videoWidth: 1920,
    videoHeight: 1080,
    inPoint: 2.0,
    outPoint: 12.0,
    playbackRate: 2.0,
    playCount: 3,
    translation: { x: 100, y: -50 },
    scale: { x: 1.5, y: 1.5 },
    rotation: 45,
    opacity: 0.85,
    blendMode: 'screen',
  });

  assert(videoCue.type === CueType.VIDEO, 'Tipo cue impostato su CueType.VIDEO');
  assert(videoCue.stageId === 'stage_test', 'Target stage assegnato');
  assert(videoCue.layer === 2, 'Layer stack order impostato a 2');
  assert(videoCue.translation.x === 100 && videoCue.translation.y === -50, 'Traslazione 2D {x: 100, y: -50} corretta');
  assert(videoCue.scale.x === 1.5 && videoCue.scale.y === 1.5, 'Scala 2D impostata a 1.5x');
  assert(videoCue.rotation === 45, 'Rotazione impostata a 45 gradi');
  assert(videoCue.opacity === 0.85, 'Opacità impostata a 0.85');
  assert(videoCue.blendMode === 'screen', 'Blend Mode impostato su "screen"');
  
  // Durata effettiva: (12 - 2) / 2.0 * 3 = 15.0 s
  assert(Math.abs(videoCue.duration - 15.0) < 0.001, `Durata calcolata corretta: ${videoCue.duration}s (atteso 15s)`);

  // VideoCue renderLayer
  const vCtx = createMockCanvasContext();
  videoCue.renderLayer(vCtx, 1920, 1080);
  assert(vCtx.calls.some((c) => c.includes('fillText("Background Loop.mp4"')), 'VideoCue renderLayer disegna titolo layer');
  assert(vCtx.calls.some((c) => c.includes('strokeRect(')), 'VideoCue renderLayer disegna riquadro video');

  // --- GRUPPO 3: TextCue ---
  console.log('\n--- 3. Test TextCue ---');
  const textCue = new TextCue({
    name: 'Titolo Opera',
    text: 'ATTO PRIMO\nScena Seconda',
    fontSize: 60,
    fontFamily: 'Helvetica Neue',
    fontWeight: 'bold',
    color: '#ffcc00',
    alignment: 'center',
    dropShadow: { enabled: true, color: 'rgba(0,0,0,0.8)', blur: 12, offsetX: 3, offsetY: 5 },
    background: { enabled: true, color: 'rgba(0,0,0,0.5)', padding: 20, borderRadius: 10 },
    layer: 5,
  });

  assert(textCue.type === CueType.TEXT, 'Tipo cue impostato su CueType.TEXT');
  assert(textCue.fontSize === 60, 'Dimensione font configurata a 60px');
  assert(textCue.color === '#ffcc00', 'Colore testo configurato (#ffcc00)');
  assert(textCue.dropShadow.enabled === true, 'Drop Shadow abilitata');
  assert(textCue.background.enabled === true, 'Background box abilitato');

  // TextCue renderLayer
  const tCtx = createMockCanvasContext();
  textCue.renderLayer(tCtx, 1920, 1080);
  assert(tCtx.shadowColor === 'rgba(0,0,0,0.8)', 'Ombreggiatura testo applicata al context');
  assert(tCtx.shadowBlur === 12, 'Blur raggio ombreggiatura applicato');
  assert(tCtx.calls.some((c) => c.includes('fillText("ATTO PRIMO"')), 'Testo riga 1 renderizzato');
  assert(tCtx.calls.some((c) => c.includes('fillText("Scena Seconda"')), 'Testo riga 2 renderizzato');

  // --- GRUPPO 4: CameraCue ---
  console.log('\n--- 4. Test CameraCue ---');
  const camCue = new CameraCue({
    name: 'Camera Attore Principale',
    deviceId: 'decklink_input_1',
    deviceName: 'Blackmagic DeckLink SDI',
    driver: 'directshow',
    format: { width: 1920, height: 1080, frameRate: 60 },
    mirror: true,
    layer: 3,
  });

  assert(camCue.type === CueType.CAMERA, 'Tipo cue impostato su CueType.CAMERA');
  assert(camCue.driver === 'directshow', 'Driver impostato su DirectShow (Windows)');
  assert(camCue.format.frameRate === 60, 'Frame rate impostato a 60 FPS');
  assert(camCue.mirror === true, 'Mirror speculare abilitato');

  // CameraCue renderLayer
  const cCtx = createMockCanvasContext();
  camCue.renderLayer(cCtx, 1920, 1080);
  assert(cCtx.calls.some((c) => c.includes('scale(-1,1)')), 'Applicato flip orizzontale mirror');
  assert(cCtx.calls.some((c) => c.includes('fillText("● LIVE CAM"')), 'Disegnato badge "LIVE CAM"');
  assert(cCtx.calls.some((c) => c.includes('DIRECTSHOW')), 'Driver hardware visualizzato nel banner');

  // --- GRUPPO 5: VideoEngine ---
  console.log('\n--- 5. Test VideoEngine ---');
  const engine = new VideoEngine();

  const mainSt = engine.getStage('stage_main');
  assert(mainSt !== null, 'Stage principale predefinito inizializzato');
  assert(mainSt.name === 'Main Stage', 'Nome stage principale corretto');

  // Aggiunta stage personalizzato
  const customSt = engine.addStage({
    id: 'stage_foyer',
    name: 'Foyer Screens',
    width: 1920,
    height: 1080,
  });
  assert(engine.getAllStages().length === 2, 'Elenco stage contiene 2 stage registrati');
  assert(engine.getStage('stage_foyer').id === 'stage_foyer', 'Recupero stage per ID funzionante');

  // Enumerazione display fisici
  const displays = await engine.getDisplayOutputs();
  assert(Array.isArray(displays) && displays.length >= 2, 'Rilevati display fisici multipli (primario + secondario/proiettore)');
  assert(displays[0].isPrimary === true, 'Display 1 designato come Primary');

  // Enumerazione telecamere hardware
  const cameras = await engine.getCameraDevices();
  assert(Array.isArray(cameras) && cameras.length >= 3, 'Rilevati dispositivi di cattura telecamera');
  const hasDirectShow = cameras.some((c) => c.driver === 'directshow');
  const hasV4L2 = cameras.some((c) => c.driver === 'v4l2');
  const hasWebRTC = cameras.some((c) => c.driver === 'webrtc');
  assert(hasDirectShow, 'Supporto driver Windows DirectShow presente');
  assert(hasV4L2, 'Supporto driver Linux v4l2 presente');
  assert(hasWebRTC, 'Supporto driver WebRTC / browser presente');

  // Pipeline di rendering composito su stage
  engine.addStage(stage);
  videoCue.state = CueState.RUNNING;
  textCue.state = CueState.RUNNING;
  const stageRenderCtx = createMockCanvasContext();
  engine.renderStage('stage_test', stageRenderCtx, [videoCue, textCue]);
  assert(stageRenderCtx.calls.length > 5, 'renderStage() ha eseguito la pipeline completa dei layer');

  // Serializzazione e ripristino JSON
  const serialized = engine.toJSON();
  assert(serialized.defaultStageId === 'stage_main', 'Serializzazione toJSON completata');
  const restoredEngine = new VideoEngine();
  restoredEngine.loadFromJSON(serialized);
  assert(restoredEngine.getStage('stage_foyer') !== null, 'loadFromJSON ha ripristinato tutti gli stages');

  // --- RISULTATI ---
  console.log(`\n========================================`);
  console.log(`Totale Test Superati: ${passed}`);
  console.log(`Totale Test Falliti:  ${failed}`);
  console.log(`========================================`);

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch((err) => {
  console.error('Errore durante i test:', err);
  process.exit(1);
});
