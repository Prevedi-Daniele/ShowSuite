/**
 * CueTypes.js — Tipi, enumeratori e costanti per il motore QLab 5 di ShowSuite
 */

/**
 * Stati operativi di una Cue (conforme a QLab 5)
 */
export const CueState = {
  IDLE: 'idle',           // Ferma, pronta all'esecuzione
  LOADED: 'loaded',       // Pre-caricata in memoria (pronta per instant-start)
  RUNNING: 'running',     // In esecuzione attiva
  PAUSED: 'paused',       // In pausa (tempo congelato)
  COMPLETED: 'completed', // Esecuzione terminata con successo
  BROKEN: 'broken',       // Errore: file mancante, target non valido o errore hardware
};

/**
 * Fasi interne del ciclo di vita temporale di una Cue
 */
export const CuePhase = {
  NONE: 'none',
  PRE_WAIT: 'pre_wait',
  ACTION: 'action',
  POST_WAIT: 'post_wait',
  COMPLETED: 'completed',
};

/**
 * Azione di avanzamento / continuità (Follow Action)
 */
export const ContinueMode = {
  DO_NOT_CONTINUE: 'do_not_continue', // Attende il prossimo tasto GO per avanzare
  AUTO_CONTINUE: 'auto_continue',     // Avvia la cue successiva al termine di (preWait + postWait), anche se l'azione è ancora in corso
  AUTO_FOLLOW: 'auto_follow',         // Avvia la cue successiva solo dopo che l'azione ha terminato (preWait + duration + postWait)
};

/**
 * Modalità operative per Group Cue (Gruppi gerarchici QLab 5)
 */
export const GroupMode = {
  TIMELINE: 'timeline',                               // "Timeline: Start all children simultaneously"
  PLAYLIST: 'playlist',                               // "Playlist: Start first child and go to next upon completion"
  START_FIRST_AND_GO_TO_NEXT: 'start_first_advance',  // "Start first child and advance playhead"
  RANDOM: 'random',                                   // "Random: Start one child randomly"
};

/**
 * Tipi di Cue supportati nel sistema
 */
export const CueType = {
  BASE: 'base',
  GROUP: 'group',
  AUDIO: 'audio',
  MIC: 'mic',
  VIDEO: 'video',
  CAMERA: 'camera',
  TEXT: 'text',
  LIGHT: 'light',
  FADE: 'fade',
  NETWORK: 'network',
  MIDI: 'midi',
  TIMECODE: 'timecode',
  WAIT: 'wait',
  SCRIPT: 'script',
};
