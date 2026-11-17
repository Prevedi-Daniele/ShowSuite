/**
 * test_timecode_engine.js — Test Suite Completa per STEP 7.2: Timecode Engine
 * 
 * Verifica approfondita di:
 * 1. SMPTETimecode — Modello matematico, frame rates (24, 25, 29.97 NDF, 29.97 DF, 30 fps),
 *    conversione bidirezionale toFrames/fromFrames, aritmetica, parsing e drop-frame rules.
 * 2. MTCDecoder & MTCGenerator — Generazione e decodifica Quarter-Frame (0xF1), compensazione
 *    latenza (+2 frames), Full-Frame SysEx seek, e rilevamento automatico rate code.
 * 3. LTCDecoder & LTCGenerator — Struttura 80 bit SMPTE 12M, sync word (0x3FFD), modulazione BMC
 *    (Bi-phase Mark Code), sintesi audio PCM e decodifica zero-crossing su flusso audio.
 * 4. TimecodeChaser — Macchina a stati (OFFLINE, LOCKING, LOCKED, FREEWHEELING),
 *    tolleranza dropout (freewheel N frame) e riarmo automatico su rewind.
 * 5. Trigger Cue su Timecode — Innesco automatico di Cue QLab sincronizzato al timecode in ingresso.
 * 6. TimecodeCue — Modello Cue di output timecode conforme a QLab 5.
 * 7. ShowControlManager Integration — Ricezione MTC e LTC audio integrata con trigger su CueScheduler.
 */

import {
  SMPTETimecode,
  SMPTEFrameRate,
  MTC_RATE_CODES,
  MTCDecoder,
  MTCGenerator,
  LTCDecoder,
  LTCGenerator,
  TimecodeChaser,
  ChaserState,
  TimecodeTriggerAction,
  TimecodeCue,
  TimecodeOutputFormat,
} from '../src/core/timecode/index.js';

import {
  BaseCue,
  CueScheduler,
  CueState,
} from '../src/core/qlab/index.js';

import { ShowControlManager } from '../src/core/control/index.js';

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

console.log('=== TEST TIMECODE ENGINE & CHASING (STEP 7.2) ===\n');

// ═══════════════════════════════════════════════════════════════════════
// 1. SMPTETimecode: Modello Matematico e Frame Rates
// ═══════════════════════════════════════════════════════════════════════
console.log('[1] Test SMPTETimecode (Modello Matematico SMPTE 12M):');

// 1.1 Inizializzazione e normalizzazione base a 25 fps
{
  const tc1 = new SMPTETimecode(1, 2, 3, 15, 0, SMPTEFrameRate.FPS_25, false);
  assert(tc1.hours === 1 && tc1.minutes === 2 && tc1.seconds === 3 && tc1.frames === 15, 'Costruzione timecode 01:02:03:15');
  assert(tc1.toString() === '01:02:03:15', 'toString formatta "01:02:03:15"');
  assert(tc1.nominalFps === 25, 'Nominal FPS = 25');

  // Normalizzazione overflow frame (es. 28 frame a 25 fps -> +1 sec, 3 frame)
  const tcOverflow = new SMPTETimecode(0, 0, 0, 28, 0, SMPTEFrameRate.FPS_25);
  assert(tcOverflow.seconds === 1 && tcOverflow.frames === 3, 'Normalizzazione overflow frame');
}

// 1.2 Conversione bidirezionale toFrames / fromFrames (24, 25, 30 fps)
{
  // 25 fps: 1 ora = 3600 * 25 = 90000 frame
  const tc25 = new SMPTETimecode(1, 0, 0, 0, 0, SMPTEFrameRate.FPS_25);
  assert(tc25.toFrames() === 90000, '1 ora a 25 fps = 90.000 frame');

  const recon25 = SMPTETimecode.fromFrames(90000, SMPTEFrameRate.FPS_25);
  assert(recon25.toString() === '01:00:00:00', 'fromFrames ricostruisce "01:00:00:00"');

  // 24 fps: 01:10:20:12
  const tc24 = new SMPTETimecode(1, 10, 20, 12, 0, SMPTEFrameRate.FPS_24);
  const frames24 = tc24.toFrames();
  const recon24 = SMPTETimecode.fromFrames(frames24, SMPTEFrameRate.FPS_24);
  assert(recon24.toString() === '01:10:20:12', 'Simmetria toFrames/fromFrames a 24 fps');

  // 30 fps: 00:01:00:00 = 1800 frame
  const tc30 = new SMPTETimecode(0, 1, 0, 0, 0, SMPTEFrameRate.FPS_30);
  assert(tc30.toFrames() === 1800, '1 minuto a 30 fps = 1800 frame');
}

// 1.3 Drop-Frame (29.97 DF) SMPTE standard
{
  // In 29.97 DF: i frame 0 e 1 vengono scartati al minuto 1, 2, 3.. 9, ma NON al minuto 0, 10, 20...
  // 10 minuti in 29.97 DF = 10 * 1800 - 9 * 2 = 17982 frame
  const tc10MinDF = new SMPTETimecode(0, 10, 0, 0, 0, SMPTEFrameRate.FPS_29_97, true);
  assert(tc10MinDF.toFrames() === 17982, '10 minuti in Drop-Frame = 17.982 frame');
  assert(tc10MinDF.toString() === '00:10:00;00', 'Drop-Frame usa il punto e virgola ";" come separatore');

  const recon10Min = SMPTETimecode.fromFrames(17982, SMPTEFrameRate.FPS_29_97, true);
  assert(recon10Min.toString() === '00:10:00;00', 'fromFrames ricostruisce correttamente blocco 10 minuti DF');

  // Salto drop-frame al minuto 1: i frame validi passano da 00:00:59;29 a 00:01:00;02
  const tcPreDrop = new SMPTETimecode(0, 0, 59, 29, 0, SMPTEFrameRate.FPS_29_97, true);
  const tcPostDrop = tcPreDrop.addFrames(1);
  assert(tcPostDrop.toString() === '00:01:00;02', 'Drop-Frame salta i frame 00 e 01 al minuto 1 (00:01:00;02)');
}

// 1.4 Aritmetica, differenze e comparazione
{
  const tcA = SMPTETimecode.fromString('01:00:00:00', SMPTEFrameRate.FPS_25);
  const tcB = tcA.addFrames(50); // +2 secondi
  assert(tcB.toString() === '01:00:02:00', 'addFrames(+50) = 01:00:02:00');

  const diff = tcB.diffFrames(tcA);
  assert(diff === 50, 'diffFrames restituisce 50');
  assert(tcB.compare(tcA) === 1, 'compare(B, A) = 1 (B > A)');
  assert(tcA.compare(tcB) === -1, 'compare(A, B) = -1 (A < B)');
  assert(tcA.compare(tcA) === 0, 'compare(A, A) = 0 (A == A)');

  // Parsing da stringa con punto e virgola
  const tcParsedDF = SMPTETimecode.fromString('02:15:30;12', SMPTEFrameRate.FPS_29_97);
  assert(tcParsedDF.isDropFrame === true, 'Punto e virgola ";" attiva automaticamente isDropFrame');
  assert(tcParsedDF.hours === 2 && tcParsedDF.minutes === 15 && tcParsedDF.seconds === 30 && tcParsedDF.frames === 12, 'Campi parsati correttamente');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 2. MTCDecoder & MTCGenerator: MIDI Timecode
// ═══════════════════════════════════════════════════════════════════════
console.log('[2] Test MTCDecoder & MTCGenerator (MIDI Timecode):');

// 2.1 Generazione e decodifica di 8 Quarter-Frame MTC
{
  const sourceTc = new SMPTETimecode(1, 23, 45, 10, 0, SMPTEFrameRate.FPS_25);
  // Genera gli 8 messaggi Quarter-Frame
  const qfMessages = MTCGenerator.createQuarterFrames(sourceTc);
  assert(qfMessages.length === 8, 'MTCGenerator genera esattamente 8 messaggi Quarter-Frame');
  assert(qfMessages.every(m => m[0] === 0xF1), 'Tutti i messaggi Quarter-Frame hanno status byte 0xF1');

  // Decodifica con MTCDecoder
  const decoder = new MTCDecoder({ compensateLatency: false });
  let decodedResult = null;

  for (let i = 0; i < 8; i++) {
    const res = decoder.processMidi(qfMessages[i]);
    if (i < 7) {
      assert(res === null, `Pezzo ${i} elaborato senza emissione premature`);
    } else {
      decodedResult = res;
    }
  }

  assert(decodedResult !== null, 'Timecode emesso alla ricezione dell\'ottavo pezzo (pezzo 7)');
  assert(decodedResult.toString() === '01:23:45:10', 'Timecode decodificato identico all\'originale (01:23:45:10)');
}

// 2.2 Compensazione Latenza Standard MTC (+2 Frame)
{
  const sourceTc = new SMPTETimecode(0, 0, 10, 0, 0, SMPTEFrameRate.FPS_25);
  const qfMessages = MTCGenerator.createQuarterFrames(sourceTc);

  const decoderWithComp = new MTCDecoder({ compensateLatency: true });
  let decodedWithComp = null;
  for (const msg of qfMessages) {
    const res = decoderWithComp.processMidi(msg);
    if (res) decodedWithComp = res;
  }

  // Con compensateLatency = true, aggiunge +2 frame per il tempo impiegato dagli 8 QF a trasmettere
  assert(decodedWithComp.frames === 2, 'Compensazione latenza MTC standard: 0 frame + 2 frame = 2 frame');
  assert(decodedWithComp.toString() === '00:00:10:02', 'Risultato con compensazione: 00:00:10:02');
}

// 2.3 MTC Full-Frame SysEx (Riposizionamento istantaneo)
{
  const targetTc = new SMPTETimecode(2, 30, 0, 12, 0, SMPTEFrameRate.FPS_24);
  const sysEx = MTCGenerator.createFullFrameSysEx(targetTc);

  assert(sysEx[0] === 0xF0 && sysEx[sysEx.length - 1] === 0xF7, 'Pacchetto SysEx delimitato da F0 e F7');
  assert(sysEx[1] === 0x7F && sysEx[3] === 0x01 && sysEx[4] === 0x01, 'Sub-ID MTC Full Frame (0x01, 0x01)');

  const decoder = new MTCDecoder();
  const res = decoder.processMidi(sysEx);
  assert(res !== null, 'Full Frame SysEx elaborato istantaneamente');
  assert(res.toString() === '02:30:00:12', 'Timecode impostato esattamente a 02:30:00:12');
  assert(res.fps === 24, 'Frame rate cinema 24 fps rilevato dai flag MTC');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 3. LTCDecoder & LTCGenerator: Linear Timecode Audio (SMPTE 12M)
// ═══════════════════════════════════════════════════════════════════════
console.log('[3] Test LTCDecoder & LTCGenerator (Audio LTC SMPTE 12M):');

// 3.1 Codifica Frame 80 bit e Sync Word
{
  const sourceTc = new SMPTETimecode(1, 15, 30, 20, 0, SMPTEFrameRate.FPS_25);
  const bits = LTCGenerator.encodeBits(sourceTc);

  assert(bits.length === 80, 'Frame LTC ha esattamente 80 bit');
  // Verifica Sync Word standard (bit 64..79: 0011 1111 1111 1101)
  const syncWord = Array.from(bits.slice(64, 80)).join('');
  assert(syncWord === '0011111111111101', 'Sync Word standard SMPTE presente sui bit 64..79');
}

// 3.2 Sintesi Audio PCM BMC e Decodifica Zero-Crossing
{
  const sampleRate = 48000;
  const startTc = new SMPTETimecode(0, 1, 0, 5, 0, SMPTEFrameRate.FPS_25);
  // Genera 3 frame di segnale audio PCM modulato BMC
  const audioBuffer = LTCGenerator.generateAudio(startTc, sampleRate, 3);

  assert(audioBuffer instanceof Float32Array, 'Audio LTC sintetizzato come Float32Array');
  assert(audioBuffer.length > 0, 'Buffer audio generato con successo');

  // Decodifica il flusso audio
  const ltcDecoder = new LTCDecoder({ sampleRate, expectedFps: SMPTEFrameRate.FPS_25 });
  const decodedList = ltcDecoder.processAudio(audioBuffer);

  assert(decodedList.length >= 2, `Decodificati ${decodedList.length} frame completi dal flusso audio PCM`);
  assert(decodedList[0].toString() === '00:01:00:05', 'Frame 1 decodificato correttamente: 00:01:00:05');
  assert(decodedList[1].toString() === '00:01:00:06', 'Frame 2 progressivo: 00:01:00:06');
}

// 3.3 Audio LTC con Drop-Frame a 29.97 fps
{
  const sampleRate = 48000;
  const tcDF = new SMPTETimecode(0, 5, 0, 10, 0, SMPTEFrameRate.FPS_29_97, true);
  const audioBufferDF = LTCGenerator.generateAudio(tcDF, sampleRate, 2);

  const ltcDecoderDF = new LTCDecoder({ sampleRate, expectedFps: SMPTEFrameRate.FPS_29_97 });
  const decodedDF = ltcDecoderDF.processAudio(audioBufferDF);

  assert(decodedDF.length >= 1, 'Frame LTC Drop-Frame decodificato con successo');
  assert(decodedDF[0].isDropFrame === true, 'Flag Drop-Frame rilevato nel bit 10');
  assert(decodedDF[0].toString() === '00:05:00;10', 'Timecode formattato con punto e virgola: 00:05:00;10');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 4. TimecodeChaser: Sincronizzazione, Freewheeling e Dropout
// ═══════════════════════════════════════════════════════════════════════
console.log('[4] Test TimecodeChaser (Macchina a Stati, Chasing & Freewheeling):');

{
  const chaser = new TimecodeChaser({
    fps: SMPTEFrameRate.FPS_25,
    lockThreshold: 3,
    freewheelFrames: 5,
  });

  assert(chaser.state === ChaserState.OFFLINE, 'Stato iniziale: OFFLINE');

  // Invia 1° frame -> passa a LOCKING
  const tc1 = new SMPTETimecode(1, 0, 0, 0, 0, SMPTEFrameRate.FPS_25);
  chaser.updateIncomingTimecode(tc1);
  assert(chaser.state === ChaserState.LOCKING, '1° frame: stato transita in LOCKING');

  // Invia 2° e 3° frame consecutivi -> raggiunge la soglia lockThreshold (3) e diventa LOCKED
  const tc2 = new SMPTETimecode(1, 0, 0, 1, 0, SMPTEFrameRate.FPS_25);
  const tc3 = new SMPTETimecode(1, 0, 0, 2, 0, SMPTEFrameRate.FPS_25);
  chaser.updateIncomingTimecode(tc2);
  chaser.updateIncomingTimecode(tc3);
  assert(chaser.state === ChaserState.LOCKED, '3 frame consecutivi: stato transita in LOCKED (sincronizzato)');
  assert(chaser.currentTimecode.toString() === '01:00:00:02', 'Timecode corrente agganciato: 01:00:00:02');

  // Test Freewheeling: simula una perdita temporanea di pacchetti (dropout)
  // Simula trascorso del tempo senza nuovi frame in arrivo
  chaser.lastReceivedTimestamp = Date.now() - 100; // 100ms fa (> tempo frame di 40ms)
  chaser.tick(0.04);
  assert(chaser.state === ChaserState.FREEWHEELING, 'Dropout segnale: entra in FREEWHEELING');
  assert(chaser.currentTimecode.toString() === '01:00:00:03', 'Timecode avanza autonomamente di 1 frame (+1)');

  // Ripristino del segnale: arriva frame 4 -> torna subito in LOCKED
  const tc4 = new SMPTETimecode(1, 0, 0, 4, 0, SMPTEFrameRate.FPS_25);
  chaser.updateIncomingTimecode(tc4);
  assert(chaser.state === ChaserState.LOCKED, 'Segnale ripristinato: torna immediatamente in LOCKED');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 5. Trigger Cue su Timecode: Avvio Sincronizzato di Cue QLab
// ═══════════════════════════════════════════════════════════════════════
console.log('[5] Test Trigger Cue Sincronizzato al Timecode:');

{
  const scheduler = new CueScheduler();
  const cueIntro = new BaseCue({ id: 'cue_intro', number: '1.0', name: 'Intro Concerto', duration: 5.0 });
  const cueChorus = new BaseCue({ id: 'cue_chorus', number: '2.0', name: 'Ritornello Laser', duration: 5.0 });
  scheduler.addCue(cueIntro);
  scheduler.addCue(cueChorus);

  const chaser = new TimecodeChaser({
    cueScheduler: scheduler,
    fps: SMPTEFrameRate.FPS_25,
  });

  // Registra i trigger timecode:
  // Intro scatta a 01:00:01:00
  // Chorus scatta a 01:00:02:10
  chaser.registerCueTrigger('cue_intro', '01:00:01:00', TimecodeTriggerAction.START);
  chaser.registerCueTrigger('cue_chorus', '01:00:02:10', TimecodeTriggerAction.START);

  // Timecode iniziale: 01:00:00:20 (prima di cue_intro)
  chaser.updateIncomingTimecode(new SMPTETimecode(1, 0, 0, 20, 0, SMPTEFrameRate.FPS_25));
  assert(cueIntro.state === CueState.IDLE, 'A 01:00:00:20 la cueIntro non è ancora scattata');

  // Timecode attraversa il punto 01:00:01:00 (es. arriva 01:00:01:00)
  chaser.updateIncomingTimecode(new SMPTETimecode(1, 0, 1, 0, 0, SMPTEFrameRate.FPS_25));
  assert(cueIntro.state === CueState.RUNNING, 'A 01:00:01:00 cueIntro si avvia automaticamente (RUNNING)');
  assert(scheduler.runningCues.has(cueIntro), 'cueIntro presente nelle runningCues dello scheduler');

  // Timecode avanza a 01:00:02:00 (prima di chorus)
  chaser.updateIncomingTimecode(new SMPTETimecode(1, 0, 2, 0, 0, SMPTEFrameRate.FPS_25));
  assert(cueChorus.state === CueState.IDLE, 'cueChorus ancora IDLE');

  // Timecode attraversa 01:00:02:10
  chaser.updateIncomingTimecode(new SMPTETimecode(1, 0, 2, 10, 0, SMPTEFrameRate.FPS_25));
  assert(cueChorus.state === CueState.RUNNING, 'A 01:00:02:10 cueChorus si avvia automaticamente');

  // Test Riarmo: se il timecode viene riavvolto a 01:00:00:00, i trigger devono riarmarsi
  scheduler.stop();
  chaser.updateIncomingTimecode(new SMPTETimecode(1, 0, 0, 0, 0, SMPTEFrameRate.FPS_25));
  const triggers = chaser.registeredTriggers.get('cue_intro');
  assert(triggers[0].fired === false, 'Riavvolgimento timecode: trigger riarmato con successo (fired = false)');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 6. TimecodeCue: Generatore e Output Cue QLab 5
// ═══════════════════════════════════════════════════════════════════════
console.log('[6] Test TimecodeCue (Output Timecode QLab 5):');

{
  let lastEmittedTc = null;
  let lastPayload = null;

  const tcCue = new TimecodeCue({
    number: 'TC1',
    name: 'SMPTE Out Broadcast',
    startTimecode: '01:00:00:00',
    fps: SMPTEFrameRate.FPS_25,
    duration: 10.0,
    outputFormat: TimecodeOutputFormat.MTC,
    onTimecodeOutput: (cue, tc, payload) => {
      lastEmittedTc = tc;
      lastPayload = payload;
    },
  });

  assert(tcCue.startTimecode.toString() === '01:00:00:00', 'Start timecode impostato a 01:00:00:00');
  assert(tcCue.duration === 10.0, 'Durata 10 secondi');

  // Start della cue
  tcCue.start();
  assert(tcCue.state === CueState.RUNNING, 'TimecodeCue in stato RUNNING');
  assert(lastPayload instanceof Uint8Array, 'Full-Frame SysEx inviato all\'avvio');

  // Tick di 1 secondo (25 frame)
  tcCue.tick(1.0);
  const curTc = tcCue.getCurrentTimecode();
  assert(curTc.seconds === 1 && curTc.frames === 0, 'Dopo 1.0s il timecode avanza a 01:00:01:00');
  assert(Array.isArray(lastPayload) && lastPayload.length === 8, '8 Quarter-Frame MTC emessi nel tick');

  // Serializzazione toJSON
  const json = tcCue.toJSON();
  assert(json.type === 'timecode', 'JSON type = "timecode"');
  assert(json.startTimecode === '01:00:00:00', 'JSON startTimecode serializzato');
  assert(json.fps === 25, 'JSON fps serializzato');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 7. ShowControlManager: Integrazione MTC, LTC e Cue Triggering
// ═══════════════════════════════════════════════════════════════════════
console.log('[7] Test ShowControlManager (Integrazione Timecode End-to-End):');

{
  const scheduler = new CueScheduler();
  const qTarget = new BaseCue({ id: 'target_q', number: '10.0', name: 'Effetto Pirotecnico', duration: 5.0 });
  scheduler.addCue(qTarget);

  const manager = new ShowControlManager({
    cueScheduler: scheduler,
    timecodeFps: SMPTEFrameRate.FPS_25,
  });

  // Mappa trigger timecode tramite l'hub
  manager.mapTimecodeTrigger('target_q', '01:00:00:02', TimecodeTriggerAction.START);

  // Invia pacchetti MTC Quarter-Frame verso ShowControlManager
  const incomingTc = new SMPTETimecode(1, 0, 0, 0, 0, SMPTEFrameRate.FPS_25);
  const qfMessages = MTCGenerator.createQuarterFrames(incomingTc);

  for (const qf of qfMessages) {
    manager.processIncomingMidi(qf);
  }

  // Il decoder con compensazione MTC genera 01:00:00:02, che attiva target_q!
  assert(qTarget.state === CueState.RUNNING, 'Target cue avviata dalla ricezione di MTC Quarter-Frame!');

  // Test ricezione LTC audio
  scheduler.stop();
  const sampleRate = 48000;
  const ltcAudio = LTCGenerator.generateAudio(new SMPTETimecode(2, 0, 0, 0, 0, SMPTEFrameRate.FPS_25), sampleRate, 2);
  const decodedFromAudio = manager.processIncomingLtcAudio(ltcAudio);

  assert(decodedFromAudio.length >= 1, 'Audio LTC elaborato con successo dal manager');
  assert(manager.timecodeChaser.currentTimecode.hours === 2, 'TimecodeChaser sincronizzato dal flusso audio LTC');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// RIEPILOGO FINALE
// ═══════════════════════════════════════════════════════════════════════
console.log('==========================================================');
if (failed === 0) {
  console.log(` TUTTI I TEST DEL TIMECODE ENGINE SUPERATI AL 100%! (${passed}/${passed})`);
} else {
  console.error(` TEST COMPLETATI CON ERRORI: ${failed} falliti, ${passed} superati`);
}
console.log('==========================================================');
