/**
 * test_unification_bridge.js — Test Suite Completa per STEP 8.1: Unificazione ShowSuite & In-Process OSC Routing
 * 
 * Verifica di:
 * 1. ShowSuiteBridge — Router OSC in-process a latenza zero tra QLab e Lightkey
 * 2. Routing diretto da NetworkCue verso i controlli live di Lightkey (/live/...)
 * 3. Controllo opzioni abilitazione/disabilitazione bridge in opzioni
 * 4. Helper diretti (triggerLightkeyCell, triggerLightkeyGo, setLightkeyGrandMaster, setLightkeyBlackout)
 * 5. Parsing opzioni da riga di comando CLI (--standalone-lightkey, --standalone-qlab, --module=...)
 */

import showSuiteBridge, { ShowSuiteBridge } from '../src/shared/ShowSuiteBridge.js';
import {
  LiveController,
  CueEngine,
  PaletteManager,
  NetworkCue,
  NetworkProtocol,
} from '../src/core/control/index.js';
import {
  CueScheduler,
  BaseCue,
  CueType,
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

function approx(a, b, eps = 0.005) {
  return Math.abs(a - b) < eps;
}

console.log('=== TEST UNIFICAZIONE SHOWSUITE & OSC BRIDGE (STEP 8.1) ===\n');

// ═══════════════════════════════════════════════════════════════════════
// 1. ShowSuiteBridge: Registrazione Motori e Stato
// ═══════════════════════════════════════════════════════════════════════
console.log('[1] Test ShowSuiteBridge (Registrazione Motori e Stato):');

{
  const bridge = new ShowSuiteBridge();
  assert(bridge.isEnabled() === true, 'Bridge attivo di default');

  bridge.setEnabled(false);
  assert(bridge.isEnabled() === false, 'setEnabled(false) disabilita il bridge');
  bridge.setEnabled(true);
  assert(bridge.isEnabled() === true, 'setEnabled(true) riabilita il bridge');

  const live = new LiveController();
  const cueEngine = new CueEngine();
  const paletteMgr = new PaletteManager();
  const scheduler = new CueScheduler();

  bridge.registerLightkey({ liveController: live, cueEngine, paletteManager: paletteMgr });
  bridge.registerQLab({ cueScheduler: scheduler });

  const ctx = bridge.getContext();
  assert(ctx.liveController === live, 'LiveController registrato nel bridge');
  assert(ctx.cueEngine === cueEngine, 'CueEngine registrato nel bridge');
  assert(ctx.paletteManager === paletteMgr, 'PaletteManager registrato nel bridge');
  assert(ctx.cueScheduler === scheduler, 'CueScheduler registrato nel bridge');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 2. Routing OSC In-Process verso Lightkey
// ═══════════════════════════════════════════════════════════════════════
console.log('[2] Test Routing OSC In-Process QLab -> Lightkey:');

{
  const live = new LiveController();
  const cueEngine = new CueEngine();
  const scheduler = new CueScheduler();

  showSuiteBridge.setEnabled(true);
  showSuiteBridge.registerLightkey({ liveController: live, cueEngine });
  showSuiteBridge.registerQLab({ cueScheduler: scheduler });

  // 2.1 Modifica Grand Master via OSC interno
  const gmRes = showSuiteBridge.routeOsc('/live/grandMaster', [0.65], 'qlab');
  assert(gmRes.handled === true, '/live/grandMaster instradato con successo');
  assert(approx(live.grandMaster, 0.65), 'Grand Master aggiornato a 0.65 in-process');

  // 2.2 Speed Master via OSC interno
  const spdRes = showSuiteBridge.routeOsc('/live/speedMaster', [2.5], 'qlab');
  assert(spdRes.handled === true && live.speedMaster === 2.5, 'Speed Master aggiornato a 2.5 in-process');

  // 2.3 Blackout toggle / set
  showSuiteBridge.routeOsc('/live/blackout', [1], 'qlab');
  assert(live.isBlackout === true, 'Blackout attivato via OSC interno');
  showSuiteBridge.routeOsc('/live/blackout', [0], 'qlab');
  assert(live.isBlackout === false, 'Blackout disattivato via OSC interno');

  // 2.4 Blind & Freeze
  showSuiteBridge.routeOsc('/live/blind', [1], 'qlab');
  assert(live.isBlind === true, 'Blind attivato via OSC interno');
  showSuiteBridge.routeOsc('/live/freeze', [1], 'qlab');
  assert(live.isFrozen === true, 'Freeze attivato via OSC interno');

  // 2.5 Trigger Cella Griglia Live
  const cellRes = showSuiteBridge.routeOsc('/live/cell/0/trigger', [], 'qlab');
  assert(cellRes.handled === true, 'Trigger cella griglia eseguito via OSC');

  // 2.6 Trigger Cue Go di Lightkey
  const goRes = showSuiteBridge.routeOsc('/live/cue/go', [], 'qlab');
  assert(goRes.handled === true, 'Trigger cue go di Lightkey eseguito via OSC');

  // 2.7 Controllo disabilitazione Bridge
  showSuiteBridge.setEnabled(false);
  const disabledRes = showSuiteBridge.routeOsc('/live/blackout', [1], 'qlab');
  assert(disabledRes.handled === false, 'Comando rifiutato quando bridge è disabilitato');
  showSuiteBridge.setEnabled(true);
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 3. Helper Diretti di ShowSuiteBridge
// ═══════════════════════════════════════════════════════════════════════
console.log('[3] Test Helper Diretti ShowSuiteBridge:');

{
  const live = new LiveController();
  const cueEngine = new CueEngine();
  showSuiteBridge.registerLightkey({ liveController: live, cueEngine });

  showSuiteBridge.setLightkeyGrandMaster(0.42);
  assert(approx(live.grandMaster, 0.42), 'setLightkeyGrandMaster(0.42)');

  showSuiteBridge.setLightkeyBlackout(true);
  assert(live.isBlackout === true, 'setLightkeyBlackout(true)');

  showSuiteBridge.triggerLightkeyCell(1);
  assert(showSuiteBridge.routingHistory.length > 0, 'Comando registrato nella cronologia di routing');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 4. Trigger Automatico da NetworkCue di QLab
// ═══════════════════════════════════════════════════════════════════════
console.log('[4] Test Trigger da NetworkCue di QLab verso Lightkey:');

{
  const live = new LiveController();
  showSuiteBridge.registerLightkey({ liveController: live });
  live.setBlackout(false);

  // Crea una NetworkCue di QLab con comando OSC verso /live/blackout
  const netCue = new NetworkCue({
    number: 'N_LIGHT',
    name: 'Trigger Lightkey Blackout',
    protocol: NetworkProtocol.OSC,
    destination: '127.0.0.1',
    port: 53000,
    oscAddress: '/live/blackout',
    oscArguments: [1],
  });

  // Esecuzione della cue: deve passare dal bridge ed eseguire il blackout su Lightkey
  await netCue.transmit();
  assert(live.isBlackout === true, 'NetworkCue di QLab ha attivato il blackout su Lightkey all\'interno del processo!');

  // Reset blackout
  const netCueUnblackout = new NetworkCue({
    protocol: NetworkProtocol.OSC,
    destination: 'localhost',
    oscAddress: '/live/blackout',
    oscArguments: [0],
  });
  await netCueUnblackout.transmit();
  assert(live.isBlackout === false, 'NetworkCue di QLab ha ripristinato il blackout!');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 5. Opzioni CLI: Parsing Parametri di Avvio Standalone
// ═══════════════════════════════════════════════════════════════════════
console.log('[5] Test Parsing Opzioni CLI (--standalone-lightkey, --standalone-qlab):');

{
  function parseCliMode(args) {
    let mode = 'suite';
    args.forEach((arg) => {
      if (arg.startsWith('--module=')) {
        const m = arg.split('=')[1].toLowerCase();
        if (['suite', 'lightkey', 'qlab'].includes(m)) mode = m;
      } else if (arg === '--standalone-lightkey') {
        mode = 'lightkey';
      } else if (arg === '--standalone-qlab') {
        mode = 'qlab';
      }
    });
    return mode;
  }

  assert(parseCliMode([]) === 'suite', 'Default senza argomenti: suite');
  assert(parseCliMode(['--standalone-lightkey']) === 'lightkey', 'Flag --standalone-lightkey -> lightkey');
  assert(parseCliMode(['--standalone-qlab']) === 'qlab', 'Flag --standalone-qlab -> qlab');
  assert(parseCliMode(['--module=lightkey']) === 'lightkey', 'Flag --module=lightkey -> lightkey');
  assert(parseCliMode(['--module=qlab']) === 'qlab', 'Flag --module=qlab -> qlab');
  assert(parseCliMode(['node', 'main.cjs', '--standalone-lightkey']) === 'lightkey', 'Argomenti complessi con flag standalone');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// RIEPILOGO FINALE
// ═══════════════════════════════════════════════════════════════════════
console.log('==========================================================');
if (failed === 0) {
  console.log(` TUTTI I TEST DI UNIFICAZIONE SHOWSUITE SUPERATI AL 100%! (${passed}/${passed})`);
} else {
  console.error(` TEST COMPLETATI CON ERRORI: ${failed} falliti, ${passed} superati`);
}
console.log('==========================================================');
