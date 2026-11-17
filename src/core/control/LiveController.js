/**
 * LiveController.js — Modulo Live Performance per Lightkey
 * Gestisce Grand Master, Speed Master, Blind Mode, Freeze,
 * Griglia Trigger (Flash/Latch) e Fader di Gruppo.
 */

/** Modalità di attivazione di una cella trigger. */
export const TriggerMode = {
  FLASH: 'flash',  // Momentaneo: attivo solo durante la pressione
  LATCH: 'latch',  // Toggle: rimane attivo/inattivo al rilascio
};

/** Tipo di azione associata alla cella. */
export const CellType = {
  EMPTY:    'empty',
  CUE:      'cue',
  PALETTE:  'palette',
  SCENE:    'scene',
  BLACKOUT: 'blackout',
};

export default class LiveController {
  constructor() {
    /** Intensità globale applicata a tutta l'uscita DMX (0.0 → 1.0). */
    this.grandMaster  = 1.0;
    /** Moltiplicatore di velocità per tutti gli effetti (0.1 → 4.0). */
    this.speedMaster  = 1.0;
    /** Modifica senza inviare output DMX al palco. */
    this.isBlind      = false;
    /** Congela l'output DMX all'ultimo frame calcolato. */
    this.isFrozen     = false;
    /** Stato globale Blackout. */
    this.isBlackout   = false;

    this.gridCols = 8;
    this.gridRows = 6;

    this.cells  = this._initDefaultGrid();
    this.groups = this._initDefaultGroups();
  }

  // ─── Inizializzazione Griglia ─────────────────────────────────────────────

  _initDefaultGrid() {
    const presets = [
      // Riga 0: 8 Palettes Colore
      { label: 'Full Open',    type: CellType.SCENE,    mode: TriggerMode.LATCH, color: '#d8d8d8', linkedId: null },
      { label: 'Ambra Caldo',  type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#ff8800', linkedId: 'pal_amber_warm' },
      { label: 'Blu Profondo', type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#0a5cff', linkedId: 'pal_blue_deep' },
      { label: 'Rosso Rock',   type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#ff1133', linkedId: 'pal_red_rock' },
      { label: 'UV',           type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#7700ff', linkedId: 'pal_uv' },
      { label: 'Verde Neon',   type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#00ff44', linkedId: 'pal_green_neon' },
      { label: 'Cyano Ice',    type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#00d4ff', linkedId: 'pal_cyan_ice' },
      { label: 'Bianco Puro',  type: CellType.PALETTE,  mode: TriggerMode.LATCH, color: '#ffffff', linkedId: 'pal_white_pure' },
      // Riga 1: 8 Trigger immediati (Flash/Latch)
      { label: 'STROBE',       type: CellType.SCENE,    mode: TriggerMode.FLASH, color: '#ffffff', linkedId: null },
      { label: 'BUMP!',        type: CellType.SCENE,    mode: TriggerMode.FLASH, color: '#ff6600', linkedId: null },
      { label: 'BLACKOUT',     type: CellType.BLACKOUT, mode: TriggerMode.FLASH, color: '#ff0000', linkedId: null },
      { label: 'Cue 1',        type: CellType.CUE,      mode: TriggerMode.LATCH, color: '#22aaff', linkedId: null },
      { label: 'Cue 2',        type: CellType.CUE,      mode: TriggerMode.LATCH, color: '#22aaff', linkedId: null },
      { label: 'Cue 3',        type: CellType.CUE,      mode: TriggerMode.LATCH, color: '#22aaff', linkedId: null },
    ];

    const total = this.gridCols * this.gridRows;
    return Array.from({ length: total }, (_, i) => {
      const p = presets[i] ?? null;
      return {
        id:       i,
        active:   false,
        label:    p?.label    ?? '',
        type:     p?.type     ?? CellType.EMPTY,
        mode:     p?.mode     ?? TriggerMode.LATCH,
        color:    p?.color    ?? '#252530',
        linkedId: p?.linkedId ?? null,
      };
    });
  }

  _initDefaultGroups() {
    return [
      { id: 'grp_spots', name: 'Spot Post.',  fixtureIds: ['spot_1', 'spot_2', 'spot_3', 'spot_4'], faderLevel: 1.0 },
      { id: 'grp_wash',  name: 'Wash Front.', fixtureIds: ['par_1', 'par_2'],                        faderLevel: 1.0 },
      { id: 'grp_all',   name: 'All',         fixtureIds: [],                                         faderLevel: 1.0 }, // vuoto = tutti
    ];
  }

  // ─── Override Modifiers ───────────────────────────────────────────────────

  /** Imposta l'intensità globale (0.0–1.0). */
  setGrandMaster(val) {
    this.grandMaster = Math.max(0.0, Math.min(1.0, val));
  }

  /** Imposta il moltiplicatore velocità effetti (0.1–4.0). */
  setSpeedMaster(val) {
    this.speedMaster = Math.max(0.1, Math.min(4.0, val));
  }

  toggleBlind()  { this.isBlind  = !this.isBlind;  return this.isBlind;  }
  toggleFreeze() { this.isFrozen = !this.isFrozen; return this.isFrozen; }
  toggleBlackout() { this.isBlackout = !this.isBlackout; return this.isBlackout; }

  setBlind(val)    { this.isBlind    = val !== undefined ? Boolean(val) : !this.isBlind;    return this.isBlind; }
  setFreeze(val)   { this.isFrozen   = val !== undefined ? Boolean(val) : !this.isFrozen;   return this.isFrozen; }
  setBlackout(val) { this.isBlackout = val !== undefined ? Boolean(val) : !this.isBlackout; return this.isBlackout; }

  triggerCell(idx) { return this.activateCell(idx); }

  // ─── Applicazione all'output DMX ─────────────────────────────────────────

  /**
   * Scala l'intensità di tutti i fari per il Grand Master.
   * NON modifica lo stato React (sola lettura per l'output DMX).
   */
  applyGrandMaster(fixtures) {
    if (this.grandMaster >= 1.0) return fixtures;
    return fixtures.map((f) => ({
      ...f,
      state: { ...f.state, intensity: f.state.intensity * this.grandMaster },
    }));
  }

  /**
   * Scala l'intensità di ogni faro per il fader del gruppo corrispondente.
   * Vince il fader più basso tra tutti i gruppi che contengono il faro.
   * Un gruppo con `fixtureIds` vuoto si applica a TUTTI i fari.
   */
  applyGroupFaders(fixtures) {
    return fixtures.map((f) => {
      let minLevel = 1.0;
      for (const grp of this.groups) {
        const inGroup = grp.fixtureIds.length === 0 || grp.fixtureIds.includes(f.id);
        if (inGroup && grp.faderLevel < minLevel) {
          minLevel = grp.faderLevel;
        }
      }
      if (minLevel >= 1.0) return f;
      return { ...f, state: { ...f.state, intensity: f.state.intensity * minLevel } };
    });
  }

  // ─── Trigger Grid ────────────────────────────────────────────────────────

  /**
   * Attiva / toggling la cella.
   * Modalità LATCH: inverte `active`.
   * Modalità FLASH: imposta `active = true` (desattivare con releaseCell).
   * @returns {Object|null} Copia della cella aggiornata, o null se vuota.
   */
  activateCell(idx) {
    const cell = this.cells[idx];
    if (!cell || cell.type === CellType.EMPTY) return null;

    if (cell.mode === TriggerMode.LATCH) {
      cell.active = !cell.active;
    } else {
      cell.active = true;
    }
    return { ...cell };
  }

  /** Desattiva una cella in modalità FLASH (rilascio del tasto). */
  releaseCell(idx) {
    const cell = this.cells[idx];
    if (!cell || cell.mode !== TriggerMode.FLASH) return;
    cell.active = false;
  }

  /** Aggiorna le proprietà di una cella. */
  updateCell(idx, patch) {
    if (idx < 0 || idx >= this.cells.length) return;
    Object.assign(this.cells[idx], patch);
  }

  // ─── Gestione Gruppi ─────────────────────────────────────────────────────

  setGroupFader(groupId, level) {
    const grp = this.groups.find((g) => g.id === groupId);
    if (grp) grp.faderLevel = Math.max(0, Math.min(1, level));
  }

  addGroup(name, fixtureIds = []) {
    const id = `grp_${Date.now()}`;
    this.groups.push({ id, name, fixtureIds, faderLevel: 1.0 });
    return id;
  }

  removeGroup(groupId) {
    this.groups = this.groups.filter((g) => g.id !== groupId);
  }
}
