/**
 * test_stage_geometry.js — Suite di test per lo Stage Geometry Engine (STEP 6.2)
 *
 * Verifica:
 * 1. StageGeometry — Costruzione, angoli predefiniti, serializzazione JSON
 * 2. Corner Pinning / Keystone — setKeystone H/V, setCorner, reset
 * 3. Surface Warping — Mesh creazione, ridimensionamento griglia, setMeshPoint, angoli -> corners
 * 4. Edge Blending — Toggle bordi, larghezza, gamma, blackLevel, getEdgeBlendFactor
 * 5. Test Pattern — Selezione tipo, brightness
 * 6. Rendering Canvas 2D — renderTestPattern, renderEdgeBlendMask, renderWarpedSurface (mock ctx)
 * 7. VideoStage con geometria — addScreenMapping porta StageGeometry, toJSON include geometry
 */

import { StageGeometry, TestPatternType, VideoStage } from '../src/core/qlab/index.js';

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

function approxEq(a, b, eps = 1) {
  return Math.abs(a - b) <= eps;
}

// Mock Canvas 2D Context headless
function createMockCtx(w = 1920, h = 1080) {
  const calls = [];
  const gradients = [];
  return {
    calls,
    fillStyle: '#000',
    strokeStyle: '#fff',
    lineWidth: 1,
    font: '10px sans-serif',
    textAlign: 'center',
    textBaseline: 'middle',
    globalAlpha: 1,
    shadowColor: '',
    shadowBlur: 0,
    shadowOffsetX: 0,
    shadowOffsetY: 0,
    _width: w,
    _height: h,

    save() { this.calls.push('save'); },
    restore() { this.calls.push('restore'); },
    fillRect(x, y, w, h) { this.calls.push(`fillRect(${Math.round(x)},${Math.round(y)},${Math.round(w)},${Math.round(h)})`); },
    strokeRect(...a) { this.calls.push(`strokeRect`); },
    beginPath() { this.calls.push('beginPath'); },
    moveTo(x, y) { this.calls.push(`moveTo`); },
    lineTo(x, y) { this.calls.push(`lineTo`); },
    arc(...a) { this.calls.push('arc'); },
    closePath() { this.calls.push('closePath'); },
    clip() { this.calls.push('clip'); },
    stroke() { this.calls.push('stroke'); },
    fill() { this.calls.push('fill'); },
    fillText(t, x, y) { this.calls.push(`fillText("${t}")`); },
    setLineDash(d) {},
    scale(x, y) { this.calls.push(`scale(${x},${y})`); },
    createLinearGradient(x0, y0, x1, y1) {
      const g = { addColorStop() {}, _id: `grad_${gradients.length}` };
      gradients.push(g);
      this.calls.push(`createLinearGradient`);
      return g;
    },
    measureText(t) { return { width: t.length * 10 }; },
    roundRect(x, y, w, h, r) { this.calls.push(`roundRect`); },
  };
}

async function runTests() {
  console.log('=== TEST SUITE: STAGE GEOMETRY ENGINE (STEP 6.2) ===\n');

  // ----------------------------------------------------------------
  // GRUPPO 1: StageGeometry — Costruzione e angoli predefiniti
  // ----------------------------------------------------------------
  console.log('--- 1. StageGeometry — Costruzione Base ---');

  const geo = new StageGeometry({ width: 1920, height: 1080 });

  assert(geo.width === 1920 && geo.height === 1080, 'Dimensioni 1920×1080 impostate correttamente');
  assert(geo.corners.length === 4, 'Quattro angoli inizializzati (TL, TR, BR, BL)');
  assert(geo.corners[0].x === 0 && geo.corners[0].y === 0, 'TL angolo a (0, 0)');
  assert(geo.corners[1].x === 1920 && geo.corners[1].y === 0, 'TR angolo a (1920, 0)');
  assert(geo.corners[2].x === 1920 && geo.corners[2].y === 1080, 'BR angolo a (1920, 1080)');
  assert(geo.corners[3].x === 0 && geo.corners[3].y === 1080, 'BL angolo a (0, 1080)');
  assert(geo.keystone.horizontal === 0 && geo.keystone.vertical === 0, 'Keystone iniziale a 0');
  assert(geo.activeTestPattern === TestPatternType.NONE, 'Test Pattern iniziale: NONE');

  // ----------------------------------------------------------------
  // GRUPPO 2: Corner Pin e Keystone
  // ----------------------------------------------------------------
  console.log('\n--- 2. Corner Pinning e Keystone ---');

  // setCorner manuale
  geo.setCorner(0, 50, 30);
  assert(geo.corners[0].x === 50 && geo.corners[0].y === 30, 'setCorner(0) → TL spostato a (50, 30)');

  // reset
  geo.resetCorners();
  assert(geo.corners[0].x === 0 && geo.corners[0].y === 0, 'resetCorners() riporta TL a (0, 0)');
  assert(geo.keystone.horizontal === 0 && geo.keystone.vertical === 0, 'resetCorners() azzera keystone');

  // Keystone orizzontale positivo → sposta TL e TR verso il centro orizzontalmente
  const geo2 = new StageGeometry({ width: 1920, height: 1080 });
  geo2.setKeystone(0.5, 0);
  assert(Math.abs(geo2.keystone.horizontal - 0.5) < 0.001, 'Keystone H impostato a 0.5');
  assert(geo2.corners[0].x > 0, 'TL spostato verso destra con Keystone H > 0');
  assert(geo2.corners[1].x < 1920, 'TR spostato verso sinistra con Keystone H > 0');
  assert(geo2.corners[0].x + geo2.corners[1].x === 1920, 'Simmetria TL+TR su asse verticale');

  // Keystone verticale positivo → sposta TL e BL verso il centro verticalmente
  const geo3 = new StageGeometry({ width: 1920, height: 1080 });
  geo3.setKeystone(0, 0.5);
  assert(geo3.corners[0].y > 0, 'TL spostato verso il basso con Keystone V > 0');
  assert(geo3.corners[3].y < 1080, 'BL spostato verso l\'alto con Keystone V > 0');

  // Keystone clampato a [-1, 1]
  const geo4 = new StageGeometry({ width: 1920, height: 1080 });
  geo4.setKeystone(99, -99);
  assert(geo4.keystone.horizontal === 1 && geo4.keystone.vertical === -1, 'Keystone H e V clampati a [-1, 1]');

  // ----------------------------------------------------------------
  // GRUPPO 3: Surface Warping - Mesh
  // ----------------------------------------------------------------
  console.log('\n--- 3. Surface Warping — Mesh di Controllo ---');

  const geoW = new StageGeometry({ width: 1920, height: 1080, gridRows: 3, gridCols: 4 });
  assert(geoW.gridRows === 3 && geoW.gridCols === 4, 'Griglia creata con 3 righe × 4 colonne');
  assert(geoW.mesh.length === 3, 'Mesh ha 3 righe');
  assert(geoW.mesh[0].length === 4, 'Ogni riga ha 4 colonne');

  // Angoli della mesh devono coincidere con gli angoli di default
  assert(geoW.mesh[0][0].x === 0 && geoW.mesh[0][0].y === 0, 'Punto mesh [0][0] = (0,0) = TL');
  assert(geoW.mesh[0][3].x === 1920 && geoW.mesh[0][3].y === 0, 'Punto mesh [0][3] = (1920,0) = TR');
  assert(geoW.mesh[2][3].x === 1920 && geoW.mesh[2][3].y === 1080, 'Punto mesh [2][3] = (1920,1080) = BR');

  // Punto centrale (interpolato bilinearmente)
  const centerPt = geoW.mesh[1][2]; // r=1 v=0.5, c=2 u=2/3
  assert(approxEq(centerPt.u, 2 / 3), `Coordinata U centro mesh ~ 0.667 (ottenuto ${centerPt.u.toFixed(3)})`);
  assert(approxEq(centerPt.x, Math.round(2 / 3 * 1920), 2), `X centro mesh ~ ${Math.round(2/3*1920)} (ottenuto ${centerPt.x})`);

  // setMeshPoint
  geoW.setMeshPoint(1, 2, 700, 400);
  assert(geoW.mesh[1][2].x === 700 && geoW.mesh[1][2].y === 400, 'setMeshPoint(1,2) → (700,400)');

  // setMeshPoint su angolo aggiorna anche this.corners
  geoW.setMeshPoint(0, 0, 25, 15);
  assert(geoW.corners[0].x === 25 && geoW.corners[0].y === 15, 'setMeshPoint angolo TL aggiorna corners[0]');

  // setGridDensity con reset
  geoW.setGridDensity(5, 5);
  assert(geoW.gridRows === 5 && geoW.gridCols === 5, 'Griglia ridimensionata a 5×5');
  assert(geoW.mesh.length === 5 && geoW.mesh[0].length === 5, 'Mesh 5×5 ricostruita correttamente');

  // resetMesh
  const geoW2 = new StageGeometry({ width: 1920, height: 1080 });
  geoW2.setMeshPoint(1, 1, 999, 999);
  geoW2.resetMesh();
  const ptAfterReset = geoW2.mesh[1][1];
  assert(ptAfterReset.x !== 999, 'resetMesh() reimposta il punto di controllo deformato');

  // ----------------------------------------------------------------
  // GRUPPO 4: Edge Blending
  // ----------------------------------------------------------------
  console.log('\n--- 4. Edge Blending ---');

  const geoB = new StageGeometry({
    width: 1920, height: 1080,
    edgeBlend: {
      left:   { enabled: true, width: 300, gamma: 2.2, blackLevel: 0.02 },
      right:  { enabled: false, width: 200, gamma: 2.2, blackLevel: 0 },
      top:    { enabled: false, width: 100, gamma: 2.2, blackLevel: 0 },
      bottom: { enabled: false, width: 100, gamma: 2.2, blackLevel: 0 },
    }
  });

  assert(geoB.edgeBlend.left.enabled === true, 'Bordo sinistro abilitato');
  assert(geoB.edgeBlend.left.width === 300, 'Larghezza overlap bordo sinistro: 300px');
  assert(geoB.edgeBlend.right.enabled === false, 'Bordo destro disabilitato');

  // getEdgeBlendFactor: punto al bordo sinistro
  const factorAtEdge = geoB.getEdgeBlendFactor(0, 540); // x=0 → t=0 → factor=blackLevel
  assert(approxEq(factorAtEdge, 0.02, 0.01), `Factor al bordo estremo sinistro ≈ blackLevel (0.02), ottenuto ${factorAtEdge.toFixed(4)}`);

  const factorMiddleBlend = geoB.getEdgeBlendFactor(150, 540); // x=150 → t=0.5 → within blend zone
  const factorOutside = geoB.getEdgeBlendFactor(1900, 540); // x=1900 → bordo destro disabilitato
  assert(factorMiddleBlend > factorAtEdge, `Factor a metà zona blend (${factorMiddleBlend.toFixed(4)}) > factor al bordo (${factorAtEdge.toFixed(4)})`);
  assert(factorOutside === 1.0, `Factor fuori dalle zone blend = 1.0 (nessuna attenuazione)`);

  // setEdgeBlend patch
  geoB.setEdgeBlend('right', { enabled: true, width: 400, gamma: 3.0 });
  assert(geoB.edgeBlend.right.enabled === true, 'setEdgeBlend patch abilitato bordo destro');
  assert(geoB.edgeBlend.right.width === 400, 'setEdgeBlend larghezza bordo destro → 400px');
  assert(geoB.edgeBlend.right.gamma === 3.0, 'setEdgeBlend gamma bordo destro → 3.0');

  // Factor punto al bordo destro
  const factorRightEdge = geoB.getEdgeBlendFactor(1919, 540);
  assert(factorRightEdge < 1.0, `Factor al bordo destro < 1.0 (attenuazione attiva: ${factorRightEdge.toFixed(4)})`);

  // ----------------------------------------------------------------
  // GRUPPO 5: Test Pattern
  // ----------------------------------------------------------------
  console.log('\n--- 5. Test Pattern ---');

  const geoP = new StageGeometry({ width: 1920, height: 1080 });
  assert(geoP.activeTestPattern === TestPatternType.NONE, 'Test Pattern iniziale: NONE');

  geoP.activeTestPattern = TestPatternType.GRID;
  geoP.testPatternBrightness = 0.8;
  assert(geoP.activeTestPattern === TestPatternType.GRID, 'Test Pattern impostato su GRID');
  assert(geoP.testPatternBrightness === 0.8, 'Luminosità Test Pattern impostata a 0.8');

  const allPatterns = [
    TestPatternType.GRID,
    TestPatternType.CIRCLES,
    TestPatternType.COLOR_BARS,
    TestPatternType.CHECKERBOARD,
    TestPatternType.CROSSHAIR,
    TestPatternType.WHITE_UNIFORMITY,
  ];
  assert(allPatterns.length === 6, '6 tipi di Test Pattern disponibili');

  // ----------------------------------------------------------------
  // GRUPPO 6: Rendering Canvas 2D (mock headless)
  // ----------------------------------------------------------------
  console.log('\n--- 6. Rendering Canvas 2D (mock headless) ---');

  // renderTestPattern GRID
  const ctxGrid = createMockCtx();
  const geoRender = new StageGeometry({ width: 1920, height: 1080 });
  geoRender.renderTestPattern(ctxGrid, TestPatternType.GRID);
  assert(ctxGrid.calls.includes('save') && ctxGrid.calls.includes('restore'), 'renderTestPattern salva e ripristina stato canvas');
  assert(ctxGrid.calls.some((c) => c.includes('fillRect')), 'renderTestPattern GRID esegue fillRect per sfondo');
  assert(ctxGrid.calls.includes('stroke'), 'renderTestPattern GRID esegue stroke per griglia');
  assert(ctxGrid.calls.some((c) => c.includes('fillText')), 'renderTestPattern GRID renderizza testo risoluzione');

  // renderTestPattern COLOR_BARS
  const ctxBars = createMockCtx();
  geoRender.renderTestPattern(ctxBars, TestPatternType.COLOR_BARS);
  const fillRectCalls = ctxBars.calls.filter((c) => c.includes('fillRect'));
  assert(fillRectCalls.length >= 8, `renderTestPattern COLOR_BARS disegna ≥8 barre colore (${fillRectCalls.length} fillRect)`);

  // renderTestPattern CHECKERBOARD
  const ctxCheck = createMockCtx();
  geoRender.renderTestPattern(ctxCheck, TestPatternType.CHECKERBOARD);
  const checkCalls = ctxCheck.calls.filter((c) => c.includes('fillRect'));
  assert(checkCalls.length > 100, `renderTestPattern CHECKERBOARD disegna molti quadrati (${checkCalls.length})`);

  // renderEdgeBlendMask
  const ctxBlend = createMockCtx();
  const geoBlendMask = new StageGeometry({
    width: 1920, height: 1080,
    edgeBlend: {
      left:   { enabled: true, width: 200, gamma: 2.2, blackLevel: 0 },
      right:  { enabled: true, width: 200, gamma: 2.2, blackLevel: 0 },
      top:    { enabled: false, width: 100, gamma: 2.2, blackLevel: 0 },
      bottom: { enabled: false, width: 100, gamma: 2.2, blackLevel: 0 },
    }
  });
  geoBlendMask.renderEdgeBlendMask(ctxBlend);
  const gradCount = ctxBlend.calls.filter((c) => c === 'createLinearGradient').length;
  assert(gradCount === 2, `renderEdgeBlendMask crea 2 gradienti lineari (sinistra + destra), ottenuto ${gradCount}`);

  // renderWarpedSurface — solo wireframe senza sorgente immagine
  const ctxWarp = createMockCtx();
  const geoWarpRender = new StageGeometry({ width: 1920, height: 1080, gridRows: 3, gridCols: 3 });
  geoWarpRender.renderWarpedSurface(ctxWarp, null, true);
  assert(ctxWarp.calls.includes('stroke'), 'renderWarpedSurface esegue stroke per wireframe mesh');

  // ----------------------------------------------------------------
  // GRUPPO 7: VideoStage integrazione con StageGeometry
  // ----------------------------------------------------------------
  console.log('\n--- 7. VideoStage con StageGeometry ---');

  const vs = new VideoStage({ id: 'vs_geo_test', name: 'Main Stage', width: 1920, height: 1080 });
  assert(vs.screenMappings.length === 1, 'VideoStage ha 1 mapping di default');
  assert(vs.screenMappings[0].geometry instanceof StageGeometry, 'screenMappings[0] porta istanza StageGeometry');

  // addScreenMapping crea StageGeometry per il nuovo display
  const newMapping = vs.addScreenMapping({
    screenId: 'display_led_wall',
    screenName: 'LED Wall Laterale',
    stageX: 0, stageY: 0,
    stageWidth: 1920, stageHeight: 1080,
  });
  assert(newMapping.geometry instanceof StageGeometry, 'addScreenMapping crea StageGeometry per il nuovo display');

  // Applica Keystone al secondo mapping
  newMapping.geometry.setKeystone(0.3, 0);
  assert(Math.abs(newMapping.geometry.keystone.horizontal - 0.3) < 0.001, 'Keystone applicato allo stage mapping isolato');

  // toJSON include geometry serializzata
  const json = vs.toJSON();
  assert(Array.isArray(json.screenMappings), 'toJSON include screenMappings');
  assert(json.screenMappings[0].geometry !== undefined, 'toJSON serializza geometry per ogni mapping');
  assert(typeof json.screenMappings[0].geometry === 'object', 'geometry serializzata è oggetto JSON');
  assert(json.screenMappings[0].geometry.corners?.length === 4, 'geometry.corners ha 4 angoli nel JSON');

  // ----------------------------------------------------------------
  // RIEPILOGO FINALE
  // ----------------------------------------------------------------
  console.log(`\n========================================`);
  console.log(`Totale Test Superati: ${passed}`);
  console.log(`Totale Test Falliti:  ${failed}`);
  console.log(`========================================`);

  if (failed > 0) process.exit(1);
}

runTests().catch((err) => {
  console.error('Errore imprevisto durante i test:', err);
  process.exit(1);
});
