/**
 * test_live_controller.js — Test Suite STEP 3.2
 * Verifica LiveController: Grand Master, Speed Master, Blind/Freeze,
 * Trigger Grid (Latch/Flash) e Fader di Gruppo.
 */

import LiveController, { TriggerMode, CellType } from '../src/core/control/LiveController.js';

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

function approx(a, b, eps = 0.001) {
  return Math.abs(a - b) < eps;
}

console.log('=== TEST LIVE CONTROLLER (STEP 3.2) ===\n');

// ─────────────────────────────────────────────────────────────────
// [1] Grand Master
// ─────────────────────────────────────────────────────────────────
console.log('[1] Test Grand Master (intensità globale):');
{
  const lc = new LiveController();
  assert(approx(lc.grandMaster, 1.0), 'Grand Master iniziale = 1.0');

  lc.setGrandMaster(0.5);
  assert(approx(lc.grandMaster, 0.5), 'setGrandMaster(0.5) → 0.5');

  lc.setGrandMaster(-0.5);
  assert(approx(lc.grandMaster, 0.0), 'setGrandMaster(-0.5) → clamp a 0.0');

  lc.setGrandMaster(2.0);
  assert(approx(lc.grandMaster, 1.0), 'setGrandMaster(2.0) → clamp a 1.0');

  // applyGrandMaster: scala intensità, non tocca colore
  lc.setGrandMaster(0.5);
  const fixtures = [
    { id: 'f1', state: { intensity: 1.0, color: { r: 1.0, g: 0.0, b: 0.5 } } },
    { id: 'f2', state: { intensity: 0.8, color: { r: 0.0, g: 1.0, b: 0.0 } } },
  ];
  const result = lc.applyGrandMaster(fixtures);
  assert(approx(result[0].state.intensity, 0.5), 'applyGrandMaster: faro 1 (1.0 × 0.5) = 0.5');
  assert(approx(result[1].state.intensity, 0.4), 'applyGrandMaster: faro 2 (0.8 × 0.5) = 0.4');
  assert(result[0].state.color.r === 1.0,        'applyGrandMaster: colore RGB invariato');

  // Con GM = 1.0, restituisce lo stesso array (ottimizzazione)
  lc.setGrandMaster(1.0);
  const same = lc.applyGrandMaster(fixtures);
  assert(same === fixtures, 'applyGrandMaster: GM=1.0 → array identico (nessuna copia)');
}

// ─────────────────────────────────────────────────────────────────
// [2] Speed Master
// ─────────────────────────────────────────────────────────────────
console.log('\n[2] Test Speed Master (moltiplicatore velocità effetti):');
{
  const lc = new LiveController();
  assert(approx(lc.speedMaster, 1.0), 'Speed Master iniziale = 1.0');

  lc.setSpeedMaster(2.5);
  assert(approx(lc.speedMaster, 2.5), 'setSpeedMaster(2.5) → 2.5');

  lc.setSpeedMaster(0.05);
  assert(approx(lc.speedMaster, 0.1), 'setSpeedMaster(0.05) → clamp minimo a 0.1');

  lc.setSpeedMaster(5.0);
  assert(approx(lc.speedMaster, 4.0), 'setSpeedMaster(5.0) → clamp massimo a 4.0');

  lc.setSpeedMaster(1.0);
  assert(approx(lc.speedMaster, 1.0), 'setSpeedMaster(1.0) → valore nominale');
}

// ─────────────────────────────────────────────────────────────────
// [3] Blind Mode & Freeze
// ─────────────────────────────────────────────────────────────────
console.log('\n[3] Test Modalità Blind e Freeze:');
{
  const lc = new LiveController();
  assert(!lc.isBlind,   'Blind inizialmente inattivo');
  assert(!lc.isFrozen,  'Freeze inizialmente inattivo');

  const b1 = lc.toggleBlind();
  assert(b1 === true && lc.isBlind,   'toggleBlind() 1a volta → true (attivato)');

  const b2 = lc.toggleBlind();
  assert(b2 === false && !lc.isBlind, 'toggleBlind() 2a volta → false (disattivato)');

  const f1 = lc.toggleFreeze();
  assert(f1 === true && lc.isFrozen,  'toggleFreeze() 1a volta → true (attivato)');

  const f2 = lc.toggleFreeze();
  assert(f2 === false && !lc.isFrozen,'toggleFreeze() 2a volta → false (disattivato)');

  // Blind e Freeze sono indipendenti
  lc.toggleBlind();
  lc.toggleFreeze();
  assert(lc.isBlind && lc.isFrozen, 'Blind e Freeze attivabili simultaneamente');
}

// ─────────────────────────────────────────────────────────────────
// [4] Trigger Grid — Inizializzazione, Latch e Flash
// ─────────────────────────────────────────────────────────────────
console.log('\n[4] Test Trigger Grid (6×8 celle, Latch / Flash):');
{
  const lc = new LiveController();
  const total = lc.gridCols * lc.gridRows;
  assert(total === 48, `Griglia inizializzata con ${total} celle (${lc.gridRows}×${lc.gridCols}=48)`);

  // Cella 0 = Full Open — tipo SCENE, modalità LATCH
  const c0 = lc.cells[0];
  assert(c0.type !== CellType.EMPTY, 'Cella 0: non vuota (preset "Full Open")');
  assert(c0.mode === TriggerMode.LATCH, 'Cella 0: modalità LATCH');
  assert(!c0.active, 'Cella 0: inattiva all\'avvio');

  // activateCell → LATCH toggle
  const r1 = lc.activateCell(0);
  assert(r1.active === true,          'activateCell(0): attivato al 1° click');
  const r2 = lc.activateCell(0);
  assert(r2.active === false,         'activateCell(0): disattivato al 2° click (toggle)');

  // Cella FLASH (cella 8 = STROBE)
  const c8 = lc.cells[8];
  assert(c8.mode === TriggerMode.FLASH, 'Cella 8: modalità FLASH (strobe)');
  const rf = lc.activateCell(8);
  assert(rf.active === true,            'activateCell(8) FLASH: attivato alla pressione');
  lc.releaseCell(8);
  assert(!lc.cells[8].active,           'releaseCell(8): disattivato al rilascio del tasto');

  // updateCell modifica arbitrariamente una cella
  lc.updateCell(20, { label: 'Mia Scena Live', type: CellType.SCENE, color: '#00cc66' });
  assert(lc.cells[20].label === 'Mia Scena Live', 'updateCell: label aggiornata correttamente');
  assert(lc.cells[20].color === '#00cc66',         'updateCell: colore aggiornato correttamente');

  // Cella vuota: activateCell ritorna null
  const emptyIdx = lc.cells.findIndex((c) => c.type === CellType.EMPTY);
  if (emptyIdx >= 0) {
    const res = lc.activateCell(emptyIdx);
    assert(res === null, `activateCell(${emptyIdx}) su cella vuota → null`);
  }

  // releaseCell su LATCH non fa nulla (solo FLASH)
  lc.activateCell(0); // attiva
  lc.releaseCell(0);  // dovrebbe essere no-op
  assert(lc.cells[0].active === true, 'releaseCell su LATCH: stato invariato (no-op)');
}

// ─────────────────────────────────────────────────────────────────
// [5] Group Faders — applyGroupFaders + addGroup/removeGroup
// ─────────────────────────────────────────────────────────────────
console.log('\n[5] Test Fader di Gruppo:');
{
  const lc = new LiveController();
  assert(lc.groups.length === 3, `Inizializzati ${lc.groups.length} gruppi predefiniti (atteso 3)`);

  // setGroupFader + clamp
  lc.setGroupFader('grp_spots', 0.5);
  const spotsGrp = lc.groups.find((g) => g.id === 'grp_spots');
  assert(approx(spotsGrp.faderLevel, 0.5), 'setGroupFader grp_spots → 0.5');

  lc.setGroupFader('grp_spots', -0.3);
  assert(approx(spotsGrp.faderLevel, 0.0), 'setGroupFader(-0.3) → clamp a 0.0');

  lc.setGroupFader('grp_spots', 1.5);
  assert(approx(spotsGrp.faderLevel, 1.0), 'setGroupFader(1.5) → clamp a 1.0');

  // applyGroupFaders: spot scalati da grp_spots, par inalterati
  // Reset: spots=0.5, wash=1.0, all=1.0
  lc.setGroupFader('grp_spots', 0.5);
  lc.setGroupFader('grp_wash',  1.0);
  lc.setGroupFader('grp_all',   1.0);

  const fixtures = [
    { id: 'spot_1', state: { intensity: 1.0 } },
    { id: 'par_1',  state: { intensity: 1.0 } },
  ];

  // spot_1 → in grp_spots (0.5) + grp_all (1.0) → minimo = 0.5
  // par_1  → in grp_wash  (1.0) + grp_all (1.0) → minimo = 1.0 (invariato)
  const out = lc.applyGroupFaders(fixtures);
  assert(approx(out[0].state.intensity, 0.5), 'applyGroupFaders: spot_1 scalato a 0.5');
  assert(approx(out[1].state.intensity, 1.0), 'applyGroupFaders: par_1 invariato (1.0)');

  // Gruppo "All" (fixtureIds vuoto) → si applica a tutti
  lc.setGroupFader('grp_all', 0.6);
  const out2 = lc.applyGroupFaders(fixtures);
  // spot_1 → min(0.5, 0.6) = 0.5; par_1 → min(1.0, 0.6) = 0.6
  assert(approx(out2[0].state.intensity, 0.5), 'applyGroupFaders: spot_1 limitato dal grp_spots (0.5 < 0.6)');
  assert(approx(out2[1].state.intensity, 0.6), 'applyGroupFaders: par_1 limitato dal grp_all (0.6)');

  // addGroup / removeGroup
  const newId = lc.addGroup('Front Fill', ['par_1', 'par_2']);
  assert(lc.groups.some((g) => g.id === newId && g.name === 'Front Fill'), 'addGroup: gruppo creato correttamente');

  lc.removeGroup(newId);
  assert(!lc.groups.some((g) => g.id === newId), 'removeGroup: gruppo eliminato correttamente');

  // ID inesistente: setGroupFader non deve crashare
  lc.setGroupFader('grp_nonexistent', 0.5);
  assert(true, 'setGroupFader su ID inesistente: nessuna eccezione (OK)');
}

// ─────────────────────────────────────────────────────────────────
// Riepilogo
// ─────────────────────────────────────────────────────────────────
console.log('\n' + '='.repeat(58));
if (failed === 0) {
  console.log(` TUTTI I TEST DEL LIVE CONTROLLER SUPERATI AL 100%! (${passed}/${passed + failed})`);
} else {
  console.log(` ✗ ${failed} TEST FALLITI su ${passed + failed} totali`);
}
console.log('='.repeat(58) + '\n');
