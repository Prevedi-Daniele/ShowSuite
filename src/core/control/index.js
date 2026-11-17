/**
 * src/core/control/index.js — Barrel exports per il modulo Control & Show Control di ShowSuite
 */

export { default as FanEngine, FanMode, FanAttribute } from './FanEngine.js';
export { default as PaletteManager, PaletteType } from './PaletteManager.js';
export { default as CueEngine, Cue } from './CueEngine.js';
export { default as LiveController, TriggerMode, CellType } from './LiveController.js';

// ─── Network & Show Control (STEP 7.1) ───────────────────────────
export { default as OscPacket, getPaddedStringLength, writePaddedString, readPaddedString } from './OscPacket.js';
export { OSCDictionary } from './OSCDictionary.js';
export { default as OSCController, OSCReceiver, OSCTransmitter } from './OSCController.js';
export { default as NetworkCue, NetworkProtocol, NetworkTransport } from './NetworkCue.js';
export {
  default as MidiCue,
  MidiMessageType,
  MSCFormat,
  MSCCommand,
  noteNameToNumber,
  numberToNoteName,
} from './MidiCue.js';
export { default as ShowControlManager } from './ShowControlManager.js';

// ─── Timecode Engine & Chasing (STEP 7.2) ────────────────────────
export {
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
} from '../timecode/index.js';
