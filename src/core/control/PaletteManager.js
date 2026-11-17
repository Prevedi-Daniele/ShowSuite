/**
 * PaletteManager - Gestione e memorizzazione di Palette (Color, Position, Beam, All-In-One Presets)
 * Consente il richiamo immediato a 1 click su singoli o gruppi di proiettori.
 */

export const PaletteType = {
  COLOR: 'color',
  POSITION: 'position',
  BEAM: 'beam',
  PRESET: 'preset', // All-in-one
};

export default class PaletteManager {
  constructor() {
    this.palettes = [];
    this.initDefaultPalettes();
  }

  initDefaultPalettes() {
    this.palettes = [
      // 1. Color Palettes
      {
        id: 'pal_col_white',
        name: 'Bianco Naturale',
        type: PaletteType.COLOR,
        colorHex: '#ffffff',
        data: { color: { r: 1, g: 1, b: 1 } },
      },
      {
        id: 'pal_col_amber',
        name: 'Ambra Caldo',
        type: PaletteType.COLOR,
        colorHex: '#ff9900',
        data: { color: { r: 1, g: 0.6, b: 0.05 } },
      },
      {
        id: 'pal_col_red',
        name: 'Rosso Fuoco',
        type: PaletteType.COLOR,
        colorHex: '#ff1a1a',
        data: { color: { r: 1, g: 0.1, b: 0.1 } },
      },
      {
        id: 'pal_col_cyan',
        name: 'Ciano Elettrico',
        type: PaletteType.COLOR,
        colorHex: '#00e5ff',
        data: { color: { r: 0, g: 0.9, b: 1 } },
      },
      {
        id: 'pal_col_blue',
        name: 'Blu Notte Profondo',
        type: PaletteType.COLOR,
        colorHex: '#1a44ff',
        data: { color: { r: 0.1, g: 0.25, b: 1 } },
      },
      {
        id: 'pal_col_magenta',
        name: 'Magenta Shock',
        type: PaletteType.COLOR,
        colorHex: '#ff00cc',
        data: { color: { r: 1, g: 0, b: 0.8 } },
      },
      {
        id: 'pal_col_green',
        name: 'Verde Smeraldo',
        type: PaletteType.COLOR,
        colorHex: '#00e64d',
        data: { color: { r: 0.1, g: 0.9, b: 0.3 } },
      },
      {
        id: 'pal_col_uv',
        name: 'UV Viola Dark',
        type: PaletteType.COLOR,
        colorHex: '#7b00ff',
        data: { color: { r: 0.45, g: 0, b: 1 } },
      },

      // 2. Position Palettes
      {
        id: 'pal_pos_center',
        name: 'Centro Palco',
        type: PaletteType.POSITION,
        icon: 'Target',
        data: { pan: 0.5, tilt: 0.5 },
      },
      {
        id: 'pal_pos_down_stage',
        name: 'Pedana Frontale (Giù)',
        type: PaletteType.POSITION,
        icon: 'ArrowDown',
        data: { pan: 0.5, tilt: 0.78 },
      },
      {
        id: 'pal_pos_audience',
        name: 'Pubblico / Sala',
        type: PaletteType.POSITION,
        icon: 'Users',
        data: { pan: 0.5, tilt: 0.22 },
      },
      {
        id: 'pal_pos_left_cross',
        name: 'Incrocio Sinistro',
        type: PaletteType.POSITION,
        icon: 'ArrowUpLeft',
        data: { pan: 0.25, tilt: 0.55 },
      },
      {
        id: 'pal_pos_right_cross',
        name: 'Incrocio Destro',
        type: PaletteType.POSITION,
        icon: 'ArrowUpRight',
        data: { pan: 0.75, tilt: 0.55 },
      },
      {
        id: 'pal_pos_sky_high',
        name: 'Cielo Verticale (Zenith)',
        type: PaletteType.POSITION,
        icon: 'Compass',
        data: { pan: 0.5, tilt: 0.05 },
      },

      // 3. Beam & Gobo Palettes
      {
        id: 'pal_beam_pinspot',
        name: 'Pinspot Stretto',
        type: PaletteType.BEAM,
        icon: 'CircleDot',
        data: { zoom: 0.15, focus: 0.8, frost: 0, gobo: 0, prism: 0 },
      },
      {
        id: 'pal_beam_wide_wash',
        name: 'Wash Flood Aperto',
        type: PaletteType.BEAM,
        icon: 'Sun',
        data: { zoom: 0.85, focus: 0.5, frost: 0.6, gobo: 0, prism: 0 },
      },
      {
        id: 'pal_beam_prism_star',
        name: 'Prisma 3-Facce Star',
        type: PaletteType.BEAM,
        icon: 'Sparkles',
        data: { zoom: 0.45, focus: 0.6, frost: 0, gobo: 0.28, goboRotate: 0.25, prism: 1 },
      },
      {
        id: 'pal_beam_breakup_soft',
        name: 'Texture Breakup',
        type: PaletteType.BEAM,
        icon: 'Cloud',
        data: { zoom: 0.55, focus: 0.3, frost: 0.35, gobo: 0.7, goboRotate: 0, prism: 0 },
      },

      // 4. All-in-One Presets
      {
        id: 'pal_preset_intro_rock',
        name: 'Rock Intro (Blu & Ciano)',
        type: PaletteType.PRESET,
        icon: 'Zap',
        data: {
          intensity: 1.0,
          shutter: 1,
          color: { r: 0.05, g: 0.5, b: 1 },
          pan: 0.5,
          tilt: 0.65,
          zoom: 0.4,
          focus: 0.5,
          gobo: 0.28,
          goboRotate: 0.15,
          prism: 1,
        },
      },
      {
        id: 'pal_preset_amber_glow',
        name: 'Warm Stage Glow (Ambra Caldo)',
        type: PaletteType.PRESET,
        icon: 'SunMedium',
        data: {
          intensity: 0.85,
          shutter: 1,
          color: { r: 1, g: 0.65, b: 0.1 },
          pan: 0.5,
          tilt: 0.7,
          zoom: 0.75,
          focus: 0.5,
          frost: 0.4,
          gobo: 0,
          prism: 0,
        },
      },
      {
        id: 'pal_preset_club_strobe',
        name: 'Club Strobe Rush',
        type: PaletteType.PRESET,
        icon: 'Activity',
        data: {
          intensity: 1.0,
          shutter: 14, // Strobo 14 Hz
          color: { r: 1, g: 1, b: 1 },
          pan: 0.5,
          tilt: 0.35,
          zoom: 0.3,
          gobo: 0,
          prism: 0,
        },
      },
    ];
  }

  getPalettes(type = null) {
    if (!type) return this.palettes;
    return this.palettes.filter((p) => p.type === type);
  }

  getPaletteById(id) {
    return this.palettes.find((p) => p.id === id) || null;
  }

  addPalette(paletteConfig) {
    const id = paletteConfig.id || `pal_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    const newPal = {
      ...paletteConfig,
      id,
    };
    this.palettes.push(newPal);
    return newPal;
  }

  removePalette(id) {
    const index = this.palettes.findIndex((p) => p.id === id);
    if (index !== -1) {
      this.palettes.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * Applica una palette allo stato di una fixture
   * @param {string} paletteId 
   * @param {Object} fixtureState 
   * @returns {Object} Nuovo stato fuso
   */
  applyToState(paletteId, fixtureState) {
    const pal = this.getPaletteById(paletteId);
    if (!pal || !pal.data) return fixtureState;

    const merged = { ...fixtureState };

    if (pal.type === PaletteType.COLOR) {
      merged.color = { ...merged.color, ...pal.data.color };
    } else if (pal.type === PaletteType.POSITION) {
      if (pal.data.pan !== undefined) merged.pan = pal.data.pan;
      if (pal.data.tilt !== undefined) merged.tilt = pal.data.tilt;
    } else if (pal.type === PaletteType.BEAM) {
      if (pal.data.zoom !== undefined) merged.zoom = pal.data.zoom;
      if (pal.data.focus !== undefined) merged.focus = pal.data.focus;
      if (pal.data.frost !== undefined) merged.frost = pal.data.frost;
      if (pal.data.gobo !== undefined) merged.gobo = pal.data.gobo;
      if (pal.data.goboRotate !== undefined) merged.goboRotate = pal.data.goboRotate;
      if (pal.data.prism !== undefined) merged.prism = pal.data.prism;
    } else if (pal.type === PaletteType.PRESET) {
      Object.assign(merged, pal.data);
    }

    return merged;
  }
}
