/**
 * test_show_control.js — Test Suite Completa per STEP 7.1: Network & Show Control
 * 
 * Verifica approfondita di:
 * 1. OscPacket — Codifica e decodifica nativa di messaggi OSC e OSC Bundles (#bundle), typetags, padding a 4 byte, parser testuale
 * 2. OSCDictionary — Dizionario completo conforme a QLab 5 (/go, /stop, /cue/{number}/start, /arm, queries) e mapping Lightkey Live (/live/grandMaster, ecc.)
 * 3. OSCController — Ricevitore e trasmettitore OSC integrato
 * 4. NetworkCue — Network Cues per OSC custom, datagrammi UDP, TCP stream e codici RAW HEX
 * 5. MidiCue — MIDI Cues per Note On/Off, CC, Program Change, Pitch Bend e MIDI Show Control (MSC) standard MMA RP-002
 * 6. ShowControlManager — Controller unificato con instradamento automatico di OSC e MSC su CueScheduler e LiveController
 */

import {
  OscPacket,
  OSCDictionary,
  OSCController,
  NetworkCue,
  NetworkProtocol,
  NetworkTransport,
  MidiCue,
  MidiMessageType,
  MSCFormat,
  MSCCommand,
  noteNameToNumber,
  numberToNoteName,
  ShowControlManager,
  LiveController,
} from '../src/core/control/index.js';

import {
  BaseCue,
  CueScheduler,
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

function approx(a, b, eps = 0.005) {
  return Math.abs(a - b) < eps;
}

console.log('=== TEST NETWORK & SHOW CONTROL (STEP 7.1) ===\n');

// ═══════════════════════════════════════════════════════════════════════
// 1. OscPacket: Codec OSC, Typetags, Padding, Bundles e Parser
// ═══════════════════════════════════════════════════════════════════════
console.log('[1] Test OscPacket (Open Sound Control Codec):');

// 1.1 Messaggio semplice senza argomenti
{
  const encoded = OscPacket.encodeMessage('/go');
  assert(encoded.length % 4 === 0, 'Il buffer codificato è allineato a 4 byte');
  const decoded = OscPacket.decode(encoded);
  assert(decoded.address === '/go', 'Indirizzo "/go" decodificato correttamente');
  assert(decoded.args.length === 0, 'Nessun argomento presente');
}

// 1.2 Messaggio con argomenti misti (int, float, stringa, booleani, null)
{
  const encoded = OscPacket.encodeMessage('/cue/10/params', [42, 3.1415, 'ShowSuite', true, false, null]);
  assert(encoded.length % 4 === 0, 'Buffer con argomenti multipli allineato a 4 byte');
  const decoded = OscPacket.decode(encoded);
  assert(decoded.address === '/cue/10/params', 'Indirizzo decodificato con successo');
  assert(decoded.args.length === 6, '6 argomenti decodificati');
  assert(decoded.args[0] === 42, 'Argomento 0 (int32) = 42');
  assert(approx(decoded.args[1], 3.1415), 'Argomento 1 (float32) ≈ 3.1415');
  assert(decoded.args[2] === 'ShowSuite', 'Argomento 2 (string) = "ShowSuite"');
  assert(decoded.args[3] === true, 'Argomento 3 (boolean True) = true');
  assert(decoded.args[4] === false, 'Argomento 4 (boolean False) = false');
  assert(decoded.args[5] === null, 'Argomento 5 (Null) = null');
}

// 1.3 Messaggio con Blob binario ('b')
{
  const rawBytes = new Uint8Array([0x01, 0x02, 0x03, 0x04, 0x05]);
  const encoded = OscPacket.encodeMessage('/data/blob', [rawBytes]);
  const decoded = OscPacket.decode(encoded);
  assert(decoded.args[0] instanceof Uint8Array, 'Argomento Blob decodificato come Uint8Array');
  assert(decoded.args[0].length === 5, 'Lunghezza blob corretta (5 byte)');
  assert(decoded.args[0][0] === 0x01 && decoded.args[0][4] === 0x05, 'Contenuto del blob integro');
}

// 1.4 OSC Bundle (#bundle)
{
  const msg1 = { address: '/cue/1/start', args: [] };
  const msg2 = { address: '/live/grandMaster', args: [0.85] };
  const bundleBytes = OscPacket.encodeBundle(12345678n, [msg1, msg2]);

  assert(bundleBytes.length % 4 === 0, 'Buffer Bundle allineato a 4 byte');
  const decodedBundle = OscPacket.decode(bundleBytes);
  assert(decodedBundle.isBundle === true, 'Riconosciuto come OSC Bundle');
  assert(decodedBundle.timetag === 12345678n, 'Timetag a 64 bit corrispondente');
  assert(decodedBundle.elements.length === 2, 'Bundle contiene 2 messaggi');
  assert(decodedBundle.elements[0].address === '/cue/1/start', 'Messaggio 1 indirizzo corretto');
  assert(decodedBundle.elements[1].address === '/live/grandMaster', 'Messaggio 2 indirizzo corretto');
  assert(approx(decodedBundle.elements[1].args[0], 0.85), 'Messaggio 2 argomento corretto');
}

// 1.5 Parser di comandi testuali
{
  const parsed1 = OscPacket.parseOscString('/go');
  assert(parsed1.address === '/go' && parsed1.args.length === 0, 'parseOscString("/go")');

  const parsed2 = OscPacket.parseOscString('/cue/2.5/start 10.5');
  assert(parsed2.address === '/cue/2.5/start' && parsed2.args[0] === 10.5, 'parseOscString con float');

  const parsed3 = OscPacket.parseOscString('/network/send "Regia Audio" true 100');
  assert(parsed3.address === '/network/send', 'Indirizzo estratto correttamente');
  assert(parsed3.args[0] === 'Regia Audio', 'Stringa con virgolette preservata');
  assert(parsed3.args[1] === true, 'Booleano true riconosciuto');
  assert(parsed3.args[2] === 100, 'Intero riconosciuto');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 2. OSCDictionary: Dizionario QLab 5 & Lightkey
// ═══════════════════════════════════════════════════════════════════════
console.log('[2] Test OSCDictionary (Dizionario QLab 5 & Lightkey):');

{
  const scheduler = new CueScheduler();
  const q1 = new BaseCue({ id: 'c1', number: '1.0', name: 'Intro', duration: 5.0 });
  const q2 = new BaseCue({ id: 'c2', number: '2.0', name: 'Scena 1', preWait: 1.0 });
  scheduler.addCue(q1);
  scheduler.addCue(q2);

  const live = new LiveController();
  const dict = new OSCDictionary();
  const context = { cueScheduler: scheduler, liveController: live };

  // 2.1 Workspace Transport: /go
  const goRes = dict.dispatch('/go', [], context);
  assert(goRes.handled === true, '/go gestito');
  assert(scheduler.runningCues.has(q1), 'Q1 avviata dal comando /go');
  assert(scheduler.standbyIndex === 1, 'Playhead avanzato su Q2');

  // 2.2 Workspace Transport: /pause e /resume
  const pauseRes = dict.dispatch('/pause', [], context);
  assert(pauseRes.handled === true && q1.state === CueState.PAUSED, '/pause mette la cue in PAUSED');
  const resumeRes = dict.dispatch('/resume', [], context);
  assert(resumeRes.handled === true && q1.state === CueState.RUNNING, '/resume ripristina lo stato RUNNING');

  // 2.3 Workspace Transport: /panic
  const panicRes = dict.dispatch('/panic', [0.5], context);
  assert(panicRes.handled === true && scheduler.isPanicking === true, '/panic attiva la dissolvenza di emergenza');
  assert(scheduler.panicFadeTime === 0.5, 'Panic fadeTime impostato a 0.5s');

  // 2.4 Workspace Transport: /stop
  const stopRes = dict.dispatch('/stop', [], context);
  assert(stopRes.handled === true && scheduler.runningCues.size === 0, '/stop ferma tutte le cue attive');

  // 2.5 Targeting Cue per Numero: /cue/{number}/start
  const cueStartRes = dict.dispatch('/cue/2.0/start', [], context);
  assert(cueStartRes.handled === true, '/cue/2.0/start gestito con successo');
  assert(scheduler.runningCues.has(q2), 'Q2 avviata');

  // 2.6 Modifica Proprietà Cue tramite OSC: arm, preWait, name, flagged
  dict.dispatch('/cue/2.0/disarm', [], context);
  assert(q2.armed === false, '/cue/2.0/disarm imposta armed = false');
  dict.dispatch('/cue/2.0/arm', [1], context);
  assert(q2.armed === true, '/cue/2.0/arm con 1 riarma la cue');

  dict.dispatch('/cue/2.0/preWait', [3.5], context);
  assert(q2.preWait === 3.5, '/cue/2.0/preWait aggiorna il pre-wait a 3.5s');

  dict.dispatch('/cue/2.0/name', ['Nuovo Titolo'], context);
  assert(q2.name === 'Nuovo Titolo', '/cue/2.0/name aggiorna il nome');

  dict.dispatch('/cue/2.0/flagged', [1], context);
  assert(q2.flagged === true, '/cue/2.0/flagged imposta flagged a true');

  // 2.7 Targeting Cue per ID: /cue_id/{id}/stop
  const cueIdRes = dict.dispatch('/cue_id/c2/stop', [], context);
  assert(cueIdRes.handled === true && q2.state === CueState.IDLE, '/cue_id/c2/stop ferma la cue tramite ID univoco');

  // 2.8 Selected Cue: /cue/selected/start
  scheduler.setStandbyIndex(0); // Standby su Q1
  const selRes = dict.dispatch('/cue/selected/start', [], context);
  assert(selRes.handled === true && scheduler.runningCues.has(q1), '/cue/selected/start avvia la cue in Standby');
  scheduler.stop();

  // 2.9 Query di stato: /runningOrPausedCues e /standbyCue
  scheduler.startCue(q2);
  const runningRes = dict.dispatch('/runningOrPausedCues', [], context);
  assert(runningRes.handled === true && runningRes.data.length === 1, '/runningOrPausedCues restituisce le cue attive');
  assert(runningRes.data[0].number === '2.0', 'Dati della cue attiva coerenti');

  const standbyRes = dict.dispatch('/standbyCue', [], context);
  assert(standbyRes.handled === true && standbyRes.data.number === '1.0', '/standbyCue restituisce la cue corrente');
  scheduler.stop();

  // 2.10 Mapping Lightkey Live: Grand Master, Speed Master, Blackout, Blind, Freeze, Cell Trigger
  dict.dispatch('/live/grandMaster', [0.75], context);
  assert(live.grandMaster === 0.75, '/live/grandMaster imposta Grand Master a 0.75');

  dict.dispatch('/live/speedMaster', [2.0], context);
  assert(live.speedMaster === 2.0, '/live/speedMaster imposta Speed Master a 2.0');

  dict.dispatch('/live/blackout', [1], context);
  assert(live.isBlackout === true, '/live/blackout imposta Blackout a true');

  dict.dispatch('/live/blind', [1], context);
  assert(live.isBlind === true, '/live/blind imposta Blind a true');

  dict.dispatch('/live/freeze', [1], context);
  assert(live.isFrozen === true, '/live/freeze imposta Freeze a true');

  const cellRes = dict.dispatch('/live/cell/0/trigger', [], context);
  assert(cellRes.handled === true, '/live/cell/0/trigger attiva la cella 0 della Live Grid');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 3. OSCController: Ricevitore & Trasmettitore integrato
// ═══════════════════════════════════════════════════════════════════════
console.log('[3] Test OSCController (Ricevitore & Trasmettitore):');

{
  const scheduler = new CueScheduler();
  const cue = new BaseCue({ number: '1', name: 'Test Cue' });
  scheduler.addCue(cue);

  const oscCtrl = new OSCController({ context: { cueScheduler: scheduler } });

  // 3.1 Elaborazione pacchetto binario ricevuto in ingresso
  const packetBytes = OscPacket.encodeMessage('/cue/1/start');
  const res = oscCtrl.processPacket(packetBytes);
  assert(res.handled === true, 'Pacchetto binario OSC ricevuto e processato con successo');
  assert(scheduler.runningCues.has(cue), 'Cue avviata dal pacchetto OSC binario');

  // 3.2 Esecuzione da stringa testuale
  const textRes = oscCtrl.executeText('/stop');
  assert(textRes.handled === true && scheduler.runningCues.size === 0, 'executeText("/stop") ha fermato la cue');

  // 3.3 Route personalizzata registrata
  let customCalled = false;
  oscCtrl.registerRoute('/show/curtain/open', () => {
    customCalled = true;
    return 'curtain_opened';
  });

  const customBytes = OscPacket.encodeMessage('/show/curtain/open');
  const customRes = oscCtrl.processPacket(customBytes);
  assert(customRes.handled === true && customCalled === true, 'Route personalizzata eseguita con successo');

  // 3.4 Trasmissione simulata
  oscCtrl.send('192.168.1.50', 8000, '/eos/cue/1/fire', [10]);
  assert(oscCtrl.transmitter.sentPackets.length === 1, 'Messaggio registrato nei pacchetti inviati');
  assert(oscCtrl.transmitter.sentPackets[0].host === '192.168.1.50', 'Target host registrato');
  assert(oscCtrl.transmitter.sentPackets[0].port === 8000, 'Target port registrata');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 4. NetworkCue: OSC, UDP, TCP e codici RAW HEX
// ═══════════════════════════════════════════════════════════════════════
console.log('[4] Test Network Cues (OSC, UDP, TCP, HEX):');

// 4.1 NetworkCue modalità OSC
{
  const netCueOsc = new NetworkCue({
    number: 'N1',
    name: 'Trigger EOS Console',
    protocol: NetworkProtocol.OSC,
    destination: '192.168.1.100',
    port: 8000,
    oscAddress: '/eos/cue/10/fire',
    oscArguments: [1],
  });

  const payload = netCueOsc.compilePayload();
  assert(payload.protocol === 'osc', 'Protocollo compilato: osc');
  assert(payload.destination === '192.168.1.100' && payload.port === 8000, 'Destinazione e porta corrette');
  const decoded = OscPacket.decode(payload.bytes);
  assert(decoded.address === '/eos/cue/10/fire', 'Payload binario OSC contiene l\'indirizzo specificato');
  assert(decoded.args[0] === 1, 'Payload binario OSC contiene l\'argomento specificato');
}

// 4.2 NetworkCue modalità UDP Plain Text
{
  const netCueUdp = new NetworkCue({
    number: 'N2',
    name: 'UDP Projector Shutter Open',
    protocol: NetworkProtocol.UDP,
    destination: '192.168.1.200',
    port: 4352,
    messageText: '%1POWR 1\r',
  });

  const payload = netCueUdp.compilePayload();
  assert(payload.protocol === 'udp', 'Protocollo compilato: udp');
  assert(payload.transport === 'udp', 'Transport: udp');
  const decodedText = new TextDecoder('utf-8').decode(payload.bytes);
  assert(decodedText === '%1POWR 1\r', 'Testo UTF-8 del comando UDP corrispondente');
}

// 4.3 NetworkCue modalità TCP Stream
{
  const netCueTcp = new NetworkCue({
    number: 'N3',
    name: 'TCP Video Server Trigger',
    protocol: NetworkProtocol.TCP,
    destination: '10.0.0.5',
    port: 9999,
    messageText: 'PLAY CLIP_01\n',
  });

  const payload = netCueTcp.compilePayload();
  assert(payload.protocol === 'tcp', 'Protocollo compilato: tcp');
  assert(payload.transport === 'tcp', 'Transport: tcp');
  const decodedText = new TextDecoder('utf-8').decode(payload.bytes);
  assert(decodedText === 'PLAY CLIP_01\n', 'Testo UTF-8 del comando TCP corrispondente');
}

// 4.4 NetworkCue modalità RAW HEX
{
  // Test con formati flessibili di stringhe HEX: spazi, prefissi 0x, virgole
  const hex1 = NetworkCue.hexStringToBytes('01 03 00 00 00 02 C4 0B');
  assert(hex1.length === 8, '8 byte estratti dalla stringa hex con spazi');
  assert(hex1[0] === 0x01 && hex1[1] === 0x03 && hex1[6] === 0xC4 && hex1[7] === 0x0B, 'Byte hex esatti');

  const hex2 = NetworkCue.hexStringToBytes('0xAA, 0xBB, 0xCC, 0xDD');
  assert(hex2.length === 4 && hex2[0] === 0xAA && hex2[3] === 0xDD, 'Formato con prefisso 0x e virgole gestito');

  const hex3 = NetworkCue.hexStringToBytes('AABB1122');
  assert(hex3.length === 4 && hex3[1] === 0xBB && hex3[2] === 0x11, 'Formato esadecimale continuo gestito');

  const formattedStr = NetworkCue.bytesToHexString(hex1);
  assert(formattedStr === '01 03 00 00 00 02 C4 0B', 'bytesToHexString formatta correttamente in maiuscolo');

  const netCueHex = new NetworkCue({
    number: 'N4',
    name: 'RS-232 over IP Raw Hex',
    protocol: NetworkProtocol.HEX,
    hexString: '02 30 30 30 31 03', // STX '0001' ETX
    destination: '192.168.1.150',
    port: 5000,
    transport: NetworkTransport.TCP,
  });

  const payload = netCueHex.compilePayload();
  assert(payload.protocol === 'hex', 'Protocollo compilato: hex');
  assert(payload.transport === 'tcp', 'Transport per Hex configurato come tcp');
  assert(payload.bytes.length === 6, '6 byte compilati');
  assert(payload.bytes[0] === 0x02 && payload.bytes[5] === 0x03, 'Byte iniziale STX e finale ETX corretti');
}

// 4.5 Esecuzione NetworkCue nel ciclo di vita (start e onTransmit)
{
  let transmittedData = null;
  const netCue = new NetworkCue({
    number: 'N5',
    name: 'Live Show Trigger',
    protocol: NetworkProtocol.OSC,
    oscAddress: '/action/go',
    onTransmit: (cue, payload) => {
      transmittedData = payload;
    },
  });

  netCue.start();
  assert(netCue.state === CueState.COMPLETED, 'NetworkCue a durata 0 completa immediatamente l\'azione');
  assert(transmittedData !== null, 'Callback onTransmit invocato');
  assert(transmittedData.protocol === 'osc', 'Payload trasmesso registrato');

  // Test disarm: cue disarmata non trasmette
  let disarmedTransmitted = false;
  const disarmedCue = new NetworkCue({
    armed: false,
    onTransmit: () => { disarmedTransmitted = true; },
  });
  disarmedCue.start();
  assert(disarmedTransmitted === false, 'Cue disarmata non effettua la trasmissione materiale');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 5. MidiCue: Note On/Off, CC, PC, Pitch Bend e MSC (MIDI Show Control)
// ═══════════════════════════════════════════════════════════════════════
console.log('[5] Test MIDI Cues & MIDI Show Control (MSC):');

// 5.1 Note Name translation
{
  assert(noteNameToNumber('C4') === 60, 'C4 (Middle C) = 60');
  assert(noteNameToNumber('A4') === 69, 'A4 (Concert Pitch) = 69');
  assert(noteNameToNumber('C#4') === 61, 'C#4 = 61');
  assert(noteNameToNumber('Bb3') === 58, 'Bb3 = 58');
  assert(numberToNoteName(60) === 'C4', '60 -> C4');
  assert(numberToNoteName(69) === 'A4', '69 -> A4');
}

// 5.2 Note On / Note Off
{
  const noteOnCue = new MidiCue({
    number: 'M1',
    midiMessageType: MidiMessageType.NOTE_ON,
    channel: 1,
    note: 'C4', // 60
    velocity: 100,
  });

  const bytesOn = noteOnCue.compileBytes();
  assert(bytesOn.length === 3, '3 byte per Note On');
  assert(bytesOn[0] === 0x90, 'Status byte Note On canale 1 = 0x90');
  assert(bytesOn[1] === 60, 'Note number = 60');
  assert(bytesOn[2] === 100, 'Velocity = 100');

  const parsedOn = MidiCue.parseBytes(bytesOn);
  assert(parsedOn.type === MidiMessageType.NOTE_ON, 'Decodificato come NOTE_ON');
  assert(parsedOn.channel === 1 && parsedOn.note === 60 && parsedOn.velocity === 100, 'Campi Note On corrispondenti');

  const noteOffCue = new MidiCue({
    midiMessageType: MidiMessageType.NOTE_OFF,
    channel: 2,
    note: 64, // E4
    velocity: 64,
  });
  const bytesOff = noteOffCue.compileBytes();
  assert(bytesOff[0] === 0x81, 'Status byte Note Off canale 2 = 0x81');
  assert(bytesOff[1] === 64 && bytesOff[2] === 64, 'Nota e velocity off corrette');
}

// 5.3 Control Change (CC)
{
  const ccCue = new MidiCue({
    number: 'M2',
    midiMessageType: MidiMessageType.CONTROL_CHANGE,
    channel: 5,
    controlNumber: 7, // Volume Master
    controlValue: 120,
  });

  const bytesCC = ccCue.compileBytes();
  assert(bytesCC[0] === 0xB4, 'Status byte CC canale 5 = 0xB4');
  assert(bytesCC[1] === 7, 'Control Number = 7');
  assert(bytesCC[2] === 120, 'Control Value = 120');

  const parsedCC = MidiCue.parseBytes(bytesCC);
  assert(parsedCC.type === MidiMessageType.CONTROL_CHANGE, 'Decodificato come CONTROL_CHANGE');
  assert(parsedCC.channel === 5 && parsedCC.controlNumber === 7 && parsedCC.controlValue === 120, 'Campi CC corrispondenti');
}

// 5.4 Program Change (PC) con Bank Select
{
  const pcCue = new MidiCue({
    number: 'M3',
    midiMessageType: MidiMessageType.PROGRAM_CHANGE,
    channel: 1,
    program: 42,
    bankMSB: 0,
    bankLSB: 2,
  });

  const bytesPC = pcCue.compileBytes();
  // Deve contenere CC 0 (MSB: 3 byte), CC 32 (LSB: 3 byte) e PC (2 byte: status + program) = 8 byte
  assert(bytesPC.length === 8, '8 byte totali per Program Change con Bank Select MSB/LSB');
  assert(bytesPC[0] === 0xB0 && bytesPC[1] === 0 && bytesPC[2] === 0, 'Bank MSB (CC 0, val 0)');
  assert(bytesPC[3] === 0xB0 && bytesPC[4] === 32 && bytesPC[5] === 2, 'Bank LSB (CC 32, val 2)');
  assert(bytesPC[6] === 0xC0 && bytesPC[7] === 42, 'Status PC = 0xC0 e program = 42');
}

// 5.5 Pitch Bend
{
  const pbCue = new MidiCue({
    midiMessageType: MidiMessageType.PITCH_BEND,
    channel: 1,
    pitchBend: 0, // Centro
  });
  const bytesPB = pbCue.compileBytes();
  assert(bytesPB[0] === 0xE0, 'Status Pitch Bend canale 1 = 0xE0');
  const parsedPB = MidiCue.parseBytes(bytesPB);
  assert(parsedPB.type === MidiMessageType.PITCH_BEND, 'Decodificato come PITCH_BEND');
  assert(parsedPB.value === 8192, 'Valore centrale = 8192');
}

// 5.6 MIDI Show Control (MSC) SysEx standard RP-002
{
  const mscCue = new MidiCue({
    number: 'M4',
    name: 'MSC Audio Cue Go',
    midiMessageType: MidiMessageType.MSC,
    mscDevice: 0x7F,               // All-Call broadcast
    mscFormat: MSCFormat.SOUND,    // Sound 0x10
    mscCommand: MSCCommand.GO,     // GO 0x01
    mscCue: '2.5',                 // Cue number '2.5'
    mscCueList: '1',               // Cue list '1'
  });

  const mscBytes = mscCue.compileBytes();
  assert(mscBytes[0] === 0xF0, 'Byte iniziale SysEx = 0xF0');
  assert(mscBytes[1] === 0x7F, 'Universal Real-Time ID = 0x7F');
  assert(mscBytes[2] === 0x7F, 'Device ID All-Call = 0x7F');
  assert(mscBytes[3] === 0x02, 'Sub-ID #1 (MSC) = 0x02');
  assert(mscBytes[4] === 0x10, 'Command Format (Sound) = 0x10');
  assert(mscBytes[5] === 0x01, 'Command (GO) = 0x01');
  assert(mscBytes[mscBytes.length - 1] === 0xF7, 'Byte finale EOX = 0xF7');

  // Verifica decodifica del pacchetto MSC
  const parsedMsc = MidiCue.parseBytes(mscBytes);
  assert(parsedMsc.type === MidiMessageType.MSC, 'Riconosciuto come MSC');
  assert(parsedMsc.deviceId === 0x7F, 'Device ID = 0x7F');
  assert(parsedMsc.commandFormat === MSCFormat.SOUND, 'Command Format = Sound (0x10)');
  assert(parsedMsc.command === MSCCommand.GO, 'Command = GO (0x01)');
  assert(parsedMsc.cueNumber === '2.5', 'Cue Number = "2.5"');
  assert(parsedMsc.cueList === '1', 'Cue List = "1"');
}

// 5.7 MSC STOP e RESET
{
  const stopBytes = MidiCue.encodeMscSysEx({
    deviceId: 1,
    commandFormat: MSCFormat.LIGHTING,
    command: MSCCommand.STOP,
    cueNumber: '10',
  });
  const parsedStop = MidiCue.parseBytes(stopBytes);
  assert(parsedStop.deviceId === 1, 'Device ID specifico = 1');
  assert(parsedStop.commandFormat === MSCFormat.LIGHTING, 'Lighting format = 0x01');
  assert(parsedStop.command === MSCCommand.STOP, 'Command = STOP (0x02)');
  assert(parsedStop.cueNumber === '10', 'Cue number = "10"');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// 6. ShowControlManager: Hub Centrale, Trigger MIDI e Instradamento MSC
// ═══════════════════════════════════════════════════════════════════════
console.log('[6] Test ShowControlManager (Hub Show Control Integrato):');

{
  const scheduler = new CueScheduler();
  const c1 = new BaseCue({ id: 'c1', number: '1.0', name: 'Scena 1' });
  const c2 = new BaseCue({ id: 'c2', number: '2.0', name: 'Scena 2' });
  scheduler.addCue(c1);
  scheduler.addCue(c2);

  const live = new LiveController();
  const manager = new ShowControlManager({
    cueScheduler: scheduler,
    liveController: live,
    mscDeviceId: 1,
    mscFormat: MSCFormat.ALL,
  });

  // 6.1 Ricezione pacchetto MSC GO su specifica Cue (Scena 2)
  const mscGoBytes = MidiCue.encodeMscSysEx({
    deviceId: 1,
    commandFormat: MSCFormat.ALL,
    command: MSCCommand.GO,
    cueNumber: '2.0',
  });

  const mscGoRes = manager.processIncomingMidi(mscGoBytes);
  assert(mscGoRes.handled === true, 'MSC GO elaborato con successo dall\'hub');
  assert(scheduler.runningCues.has(c2), 'Scena 2 avviata via comando MSC');

  // 6.2 Ricezione pacchetto MSC STOP su Scena 2
  const mscStopBytes = MidiCue.encodeMscSysEx({
    deviceId: 0x7F, // Broadcast All-Call
    commandFormat: MSCFormat.ALL,
    command: MSCCommand.STOP,
    cueNumber: '2.0',
  });

  const mscStopRes = manager.processIncomingMidi(mscStopBytes);
  assert(mscStopRes.handled === true, 'MSC STOP elaborato con successo');
  assert(c2.state === CueState.IDLE, 'Scena 2 arrestata via comando MSC');

  // 6.3 Ricezione pacchetto MSC ALL_OFF (spegne show e attiva blackout lighting)
  scheduler.startCue(c1);
  const mscAllOffBytes = MidiCue.encodeMscSysEx({
    deviceId: 1,
    commandFormat: MSCFormat.ALL,
    command: MSCCommand.ALL_OFF,
  });

  manager.processIncomingMidi(mscAllOffBytes);
  assert(scheduler.runningCues.size === 0, 'Tutte le cue QLab fermate da MSC ALL_OFF');
  assert(live.isBlackout === true, 'Blackout Lightkey attivato da MSC ALL_OFF');

  // 6.4 Mappatura Trigger MIDI Note (es. tastiera o launchpad: Ch 1, C4 -> GO)
  let customTriggerExecuted = false;
  manager.mapMidiNote(1, 'C4', (midiEvent, mgr) => {
    customTriggerExecuted = true;
    mgr.cueScheduler.go();
  });

  const incomingNoteOn = new Uint8Array([0x90, 60, 127]); // Note On Ch.1, C4, Vel 127
  const triggerRes = manager.processIncomingMidi(incomingNoteOn);
  assert(triggerRes.handled === true, 'Trigger MIDI Note On intercettato');
  assert(customTriggerExecuted === true, 'Callback del trigger MIDI eseguito');
  assert(scheduler.runningCues.has(c1), 'Tasto GO scattato dal trigger MIDI');
  scheduler.stop();

  // 6.5 Mappatura Trigger MIDI Control Change (es. Fader BCF2000: Ch 1, CC 7 -> Grand Master)
  manager.mapMidiCC(1, 7, (midiEvent, mgr) => {
    const normalized = midiEvent.controlValue / 127.0;
    mgr.liveController.setGrandMaster(normalized);
  });

  const incomingCC = new Uint8Array([0xB0, 7, 64]); // CC 7, valore 64 (~50%)
  manager.processIncomingMidi(incomingCC);
  assert(approx(live.grandMaster, 64 / 127.0, 0.01), 'Grand Master aggiornato via fader MIDI CC');

  // 6.6 Invio messaggi di rete e MIDI tramite l'hub
  await manager.sendOsc('127.0.0.1', 53000, '/ping', ['test']);
  assert(manager.networkHistory.length > 0, 'Trasmissione OSC registrata nella cronologia di rete');

  await manager.sendHex('127.0.0.1', 8000, '01 02 03');
  assert(manager.networkHistory.some(h => h.type === 'udp_tx'), 'Trasmissione HEX registrata nella cronologia di rete');

  await manager.sendMidi(new Uint8Array([0x90, 60, 100]));
  assert(manager.midiHistory.length > 0, 'Trasmissione MIDI registrata nella cronologia MIDI');
}

console.log();

// ═══════════════════════════════════════════════════════════════════════
// RIEPILOGO FINALE
// ═══════════════════════════════════════════════════════════════════════
console.log('==========================================================');
if (failed === 0) {
  console.log(` TUTTI I TEST DI NETWORK & SHOW CONTROL SUPERATI AL 100%! (${passed}/${passed})`);
} else {
  console.error(` TEST COMPLETATI CON ERRORI: ${failed} falliti, ${passed} superati`);
}
console.log('==========================================================');
