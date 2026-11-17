/**
 * test_qlab_engine.js — Test Suite STEP 4.1
 * Verifica approfondita del motore gerarchico delle Cue di QLab 5 per ShowSuite:
 * - BaseCue & stati (Armed, Disarmed, Loaded, Running, Paused, Broken, Completed)
 * - Timing: Pre-wait, Duration, Post-wait
 * - Follow Actions: Auto-continue, Auto-follow, Do not continue
 * - GroupCue: Timeline, Playlist, Start first and go to next, Random
 * - CueScheduler: GO, Stop, Pause, Resume, Panic, Playhead e nidificazione gerarchica
 */

import {
  BaseCue,
  GroupCue,
  CueScheduler,
  CueState,
  CuePhase,
  ContinueMode,
  GroupMode,
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

console.log('=== TEST MOTORE CUES QLAB 5 (STEP 4.1) ===\n');

// ─────────────────────────────────────────────────────────────────
// [1] Test BaseCue & Stati Operativi
// ─────────────────────────────────────────────────────────────────
console.log('[1] Test BaseCue, Ciclo di Vita e Stati:');
{
  const cue = new BaseCue({
    number: '1',
    name: 'Intro Audio',
    preWait: 1.0,
    duration: 3.0,
    postWait: 0.5,
  });

  assert(cue.state === CueState.IDLE, 'Stato iniziale: IDLE');
  assert(cue.armed === true, 'Armed di default: true');
  assert(cue.preWait === 1.0 && cue.duration === 3.0 && cue.postWait === 0.5, 'Parametri temporali memorizzati correttamente');

  // Test Load
  const loaded = cue.load();
  assert(loaded && cue.state === CueState.LOADED, 'load() imposta lo stato a LOADED');

  // Test Broken state
  cue.setBroken('File audio mancante su disco');
  assert(cue.state === CueState.BROKEN && cue.isBroken(), 'setBroken() imposta lo stato a BROKEN');
  const cantStart = cue.start();
  assert(cantStart === false, 'start() su cue BROKEN restituisce false');

  cue.clearBroken();
  assert(!cue.isBroken() && cue.state === CueState.IDLE, 'clearBroken() ripristina lo stato a IDLE');

  // Test Start -> Pre-wait -> Pause -> Resume
  cue.start();
  assert(cue.state === CueState.RUNNING, 'start() avvia la cue in RUNNING');
  assert(cue.currentPhase === CuePhase.PRE_WAIT, 'Fase iniziale con preWait > 0 è PRE_WAIT');

  cue.pause();
  assert(cue.state === CueState.PAUSED, 'pause() congela la cue in PAUSED');
  cue.tick(0.5); // Con la cue in pausa il tempo non deve avanzare
  assert(cue.elapsedTime === 0, 'Il tempo non avanza mentre la cue è in pausa');

  cue.resume();
  assert(cue.state === CueState.RUNNING, 'resume() ripristina lo stato a RUNNING');

  cue.stop();
  assert(cue.state === CueState.IDLE && cue.currentPhase === CuePhase.NONE, 'stop() ferma e resetta i timer a IDLE');
}

// ─────────────────────────────────────────────────────────────────
// [2] Test Timing e Fasi: Pre-Wait -> Action -> Post-Wait -> Completed
// ─────────────────────────────────────────────────────────────────
console.log('\n[2] Test Fasi Temporali e Avanzamento Preciso (tick):');
{
  const cue = new BaseCue({
    number: '2',
    name: 'Sequenza Temporizzata',
    preWait: 1.0,
    duration: 2.0,
    postWait: 1.0,
  });

  cue.start();

  // Tick 0.5s -> ancora in preWait
  cue.tick(0.5);
  assert(cue.currentPhase === CuePhase.PRE_WAIT && approx(cue.preWaitElapsed, 0.5), 'A t=0.5s è in PRE_WAIT (0.5s trascorsi)');

  // Tick 0.6s -> supera 1.0s di preWait ed entra in ACTION (con 0.1s traslato in azione)
  cue.tick(0.6);
  assert(cue.currentPhase === CuePhase.ACTION, 'A t=1.1s transita correttamente in ACTION');
  assert(approx(cue.actionElapsed, 0.1), 'Tempo in eccesso (0.1s) riversato nell\'azione');

  // Tick 1.5s -> azione a 1.6s / 2.0s
  cue.tick(1.5);
  assert(cue.currentPhase === CuePhase.ACTION && approx(cue.actionElapsed, 1.6), 'Azione in corso (1.6s su 2.0s)');

  // Tick 0.5s -> azione completata (1.6 + 0.5 = 2.1s -> 0.1s in postWait)
  cue.tick(0.5);
  assert(cue.currentPhase === CuePhase.POST_WAIT, 'Azione completata, transita in POST_WAIT');
  assert(approx(cue.postWaitElapsed, 0.1), 'Tempo in eccesso (0.1s) riversato nella post-wait');

  // Tick 1.0s -> post-wait completata
  cue.tick(1.0);
  assert(cue.state === CueState.COMPLETED && cue.currentPhase === CuePhase.COMPLETED, 'Post-wait terminata, cue in stato COMPLETED');
  assert(approx(cue.getProgress(), 1.0), 'Progresso totale = 100% (1.0)');
}

// ─────────────────────────────────────────────────────────────────
// [3] Test Follow Actions: Auto-continue vs Auto-follow
// ─────────────────────────────────────────────────────────────────
console.log('\n[3] Test Follow Actions (Auto-continue vs Auto-follow):');
{
  // 3.1 Auto-continue: scatta a preWait + postWait indipendentemente dalla durata
  const autoContinueCue = new BaseCue({
    number: 'AC',
    preWait: 0.5,
    duration: 5.0,  // Azione lunga 5 secondi!
    postWait: 0.5,
    continueMode: ContinueMode.AUTO_CONTINUE,
  });

  autoContinueCue.start();
  // A t=0.4s non deve ancora scattare
  let r = autoContinueCue.tick(0.4);
  assert(!r.shouldTriggerNext, 'Auto-continue: a t=0.4s non scatta ancora (attende pre+post = 1.0s)');

  // A t=1.0s (0.4 + 0.65 = 1.05s) deve scattare, ANCHE SE l'azione è appena iniziata!
  r = autoContinueCue.tick(0.65);
  assert(r.shouldTriggerNext === true, 'Auto-continue: scatta esattamente a preWait + postWait (1.0s), con azione ancora in corso');

  // Al tick successivo non deve rescattare
  r = autoContinueCue.tick(0.5);
  assert(r.shouldTriggerNext === false, 'Auto-continue: non rescatta al tick successivo (evento emesso una sola volta)');

  // 3.2 Auto-follow: scatta solo dopo che l'azione ha FINITO + postWait
  const autoFollowCue = new BaseCue({
    number: 'AF',
    preWait: 0.5,
    duration: 2.0,
    postWait: 0.5,
    continueMode: ContinueMode.AUTO_FOLLOW,
  });

  autoFollowCue.start();
  // Trigger time atteso = 0.5 + 2.0 + 0.5 = 3.0s
  autoFollowCue.tick(1.5);
  assert(autoFollowCue.followTriggered === false, 'Auto-follow: a t=1.5s non scatta (azione ancora in corso)');

  autoFollowCue.tick(1.6); // t=3.1s
  assert(autoFollowCue.followTriggered === true, 'Auto-follow: scatta correttamente solo a durata finita + post-wait (3.0s)');
}

// ─────────────────────────────────────────────────────────────────
// [4] Test Cue Disarmata (Disarmed)
// ─────────────────────────────────────────────────────────────────
console.log('\n[4] Test Cue Disarmata (Disarmed Behavior):');
{
  const disarmedCue = new BaseCue({
    number: 'DIS',
    name: 'Cue Disarmata',
    armed: false,
    preWait: 0.2,
    duration: 4.0, // Durata che deve essere saltata!
    postWait: 0.2,
    continueMode: ContinueMode.AUTO_FOLLOW,
  });

  disarmedCue.start();
  assert(disarmedCue.state === CueState.RUNNING, 'Cue disarmata può essere avviata');

  // Al tick di 0.25s supera il preWait e l'azione (essendo disarmata) salta istantaneamente a durata 0
  disarmedCue.tick(0.25);
  assert(disarmedCue.currentPhase === CuePhase.POST_WAIT, 'Azione saltata istantaneamente senza attendere 4 secondi');

  // Supera anche il post-wait (0.2s)
  const res = disarmedCue.tick(0.2);
  assert(disarmedCue.state === CueState.COMPLETED, 'Cue disarmata completa l\'esecuzione rispettando solo preWait e postWait');
  assert(res.shouldTriggerNext === true, 'Cue disarmata propaga comunque il Follow Action');
}

// ─────────────────────────────────────────────────────────────────
// [5] Test GroupCue (Le 4 Modalità Native QLab 5)
// ─────────────────────────────────────────────────────────────────
console.log('\n[5] Test GroupCue (Timeline, Playlist, Start-First, Random):');
{
  // 5.1 Modalità TIMELINE: avvia tutti i figli simultaneamente
  const groupTimeline = new GroupCue({
    number: 'GRP_TL',
    name: 'Gruppo Timeline',
    mode: GroupMode.TIMELINE,
  });

  const childA = new BaseCue({ number: 'A', duration: 1.0 });
  const childB = new BaseCue({ number: 'B', duration: 2.0 });
  groupTimeline.addChild(childA);
  groupTimeline.addChild(childB);

  assert(groupTimeline.duration === 2.0, 'Modalità Timeline: durata calcolata dinamicamente dal figlio più lungo (2.0s)');

  groupTimeline.start();
  assert(childA.state === CueState.RUNNING && childB.state === CueState.RUNNING, 'Timeline: tutti i figli si avviano simultaneamente');

  // Dopo 1.1s childA finisce, childB è ancora attivo
  groupTimeline.tick(1.1);
  assert(childA.state === CueState.COMPLETED, 'Timeline: childA completato a 1.1s');
  assert(childB.state === CueState.RUNNING, 'Timeline: childB ancora in esecuzione');

  // Dopo un altro 1.0s (totale 2.1s) anche childB finisce e il gruppo completa
  groupTimeline.tick(1.0);
  assert(childB.state === CueState.COMPLETED, 'Timeline: childB completato');
  assert(groupTimeline.state === CueState.COMPLETED, 'Timeline: Gruppo completato dopo la fine di tutti i figli');

  // 5.2 Modalità PLAYLIST: sequenziale da uno all'altro
  const groupPlaylist = new GroupCue({
    number: 'GRP_PL',
    name: 'Gruppo Playlist',
    mode: GroupMode.PLAYLIST,
  });

  const pl1 = new BaseCue({ number: 'P1', duration: 0.5 });
  const pl2 = new BaseCue({ number: 'P2', duration: 0.5 });
  groupPlaylist.addChild(pl1);
  groupPlaylist.addChild(pl2);

  groupPlaylist.start();
  assert(pl1.state === CueState.RUNNING && pl2.state === CueState.IDLE, 'Playlist: solo il primo figlio è attivo all\'avvio');

  // Al tick di 0.55s P1 finisce e P2 deve partire automaticamente
  groupPlaylist.tick(0.55);
  assert(pl1.state === CueState.COMPLETED, 'Playlist: P1 completato');
  assert(pl2.state === CueState.RUNNING, 'Playlist: P2 avviato automaticamente al termine di P1');

  // Un altro tick di 0.55s -> P2 finisce e il gruppo completa
  groupPlaylist.tick(0.55);
  assert(pl2.state === CueState.COMPLETED, 'Playlist: P2 completato');
  assert(groupPlaylist.state === CueState.COMPLETED, 'Playlist: Gruppo completato dopo l\'ultimo figlio');

  // 5.3 Modalità START_FIRST_AND_GO_TO_NEXT
  const groupStep = new GroupCue({
    number: 'GRP_STEP',
    mode: GroupMode.START_FIRST_AND_GO_TO_NEXT,
  });
  const step1 = new BaseCue({ number: 'S1', duration: 1.0 });
  const step2 = new BaseCue({ number: 'S2', duration: 1.0 });
  groupStep.addChild(step1);
  groupStep.addChild(step2);

  groupStep.start();
  assert(step1.state === CueState.RUNNING && step2.state === CueState.IDLE, 'Start-First: avvia il primo figlio (S1)');

  step1.stop();
  groupStep.start(); // Secondo trigger del gruppo
  assert(step2.state === CueState.RUNNING, 'Start-First: il secondo trigger del gruppo avvia il figlio successivo (S2)');

  // 5.4 Modalità RANDOM: estrae un figlio a sorte
  const groupRandom = new GroupCue({
    number: 'GRP_RND',
    mode: GroupMode.RANDOM,
  });
  const r1 = new BaseCue({ number: 'R1', duration: 1.0 });
  const r2 = new BaseCue({ number: 'R2', duration: 1.0 });
  groupRandom.addChild(r1);
  groupRandom.addChild(r2);

  groupRandom.start();
  const oneRunning = (r1.state === CueState.RUNNING && r2.state === CueState.IDLE) ||
                     (r2.state === CueState.RUNNING && r1.state === CueState.IDLE);
  assert(oneRunning, 'Random: esattamente un figlio estratto e avviato casualmente');
}

// ─────────────────────────────────────────────────────────────────
// [6] Test CueScheduler: GO, Playhead, Auto-continue & Panic
// ─────────────────────────────────────────────────────────────────
console.log('\n[6] Test CueScheduler (GO, Sequenziamento, Auto-continue e Panic):');
{
  const scheduler = new CueScheduler();

  const q1 = new BaseCue({ number: '1.0', name: 'Scena 1', duration: 1.0, continueMode: ContinueMode.AUTO_CONTINUE });
  const q2 = new BaseCue({ number: '2.0', name: 'Scena 2', duration: 1.0 });
  const q3 = new BaseCue({ number: '3.0', name: 'Scena 3', duration: 1.0 });

  scheduler.addCue(q1);
  scheduler.addCue(q2);
  scheduler.addCue(q3);

  assert(scheduler.cues.length === 3, 'Scheduler inizializzato con 3 Cue');
  assert(scheduler.standbyIndex === 0, 'Playhead iniziale su Cue 1.0');

  // Test GO standard: avvia Q1 e sposta il playhead su Q2
  const goResult = scheduler.go();
  assert(goResult === true, 'Tasto GO eseguito con successo');
  assert(q1.state === CueState.RUNNING, 'Q1 in esecuzione');
  assert(scheduler.standbyIndex === 1, 'Playhead avanzato automaticamente su Q2 (indice 1)');

  // Poiché Q1 ha continueMode AUTO_CONTINUE (con postWait=0), al tick() Q2 deve avviarsi automaticamente!
  scheduler.tick(0.02);
  assert(q2.state === CueState.RUNNING, 'Auto-continue eseguito: Q2 avviato automaticamente dallo scheduler!');
  assert(scheduler.standbyIndex === 2, 'Playhead aggiornato alla successiva Q3');

  // Test Panic con dissolvenza di 0.5s
  scheduler.panic(0.5);
  assert(scheduler.isPanicking === true, 'Panic attivato: isPanicking = true');

  // Tick 0.3s -> panic ancora attivo
  scheduler.tick(0.3);
  assert(scheduler.isPanicking === true && scheduler.runningCues.size > 0, 'Panic in dissolvenza (0.3s su 0.5s)');

  // Tick 0.3s -> panic termina e ferma tutte le cue
  scheduler.tick(0.3);
  assert(scheduler.isPanicking === false, 'Dissolvenza Panic completata');
  assert(scheduler.runningCues.size === 0, 'Tutte le cue arrestate dal Panic');
  assert(q1.state === CueState.IDLE && q2.state === CueState.IDLE, 'Stato di Q1 e Q2 resettato a IDLE');

  // Test Flattened Cues con annidamento
  const group = new GroupCue({ number: '4.0', name: 'Gruppo Speciale' });
  group.addChild(new BaseCue({ number: '4.1', name: 'Sub Cue 1' }));
  group.addChild(new BaseCue({ number: '4.2', name: 'Sub Cue 2' }));
  scheduler.addCue(group);

  const flat = scheduler.getFlattenedCues();
  assert(flat.length === 6, `getFlattenedCues() restituisce tutte le 6 cue (4 radice + 2 figlie)`);
  assert(flat[3].depth === 0 && flat[4].depth === 1 && flat[5].depth === 1, 'Gerarchia e profondità (depth 0 e 1) calcolate correttamente');

  // Ricerca per ID e per Numero
  const foundByNum = scheduler.findCueByNumber('4.2');
  assert(foundByNum && foundByNum.name === 'Sub Cue 2', 'findCueByNumber() trova correttamente cue annidate');
}

// ─────────────────────────────────────────────────────────────────
// Riepilogo
// ─────────────────────────────────────────────────────────────────
console.log('\n' + '='.repeat(58));
if (failed === 0) {
  console.log(` TUTTI I TEST DEL MOTORE CUE QLAB 5 SUPERATI AL 100%! (${passed}/${passed + failed})`);
} else {
  console.log(` ✗ ${failed} TEST FALLITI su ${passed + failed} totali`);
}
console.log('='.repeat(58) + '\n');
