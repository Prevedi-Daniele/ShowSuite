/**
 * DmxChannel - Definizione e comportamento di un singolo canale o coppia coarse/fine (16-bit)
 */

export const ChannelType = {
  INTENSITY: 'intensity',
  SHUTTER: 'shutter',
  PAN: 'pan',
  PAN_FINE: 'pan_fine',
  TILT: 'tilt',
  TILT_FINE: 'tilt_fine',
  RED: 'red',
  GREEN: 'green',
  BLUE: 'blue',
  WHITE: 'white',
  AMBER: 'amber',
  UV: 'uv',
  CYAN: 'cyan',
  MAGENTA: 'magenta',
  YELLOW: 'yellow',
  CTO: 'cto',
  COLOR_WHEEL: 'color_wheel',
  GOBO_WHEEL: 'gobo_wheel',
  GOBO_ROTATE: 'gobo_rotate',
  PRISM: 'prism',
  PRISM_ROTATE: 'prism_rotate',
  ZOOM: 'zoom',
  FOCUS: 'focus',
  IRIS: 'iris',
  FROST: 'frost',
  SPEED: 'speed',
  FOG: 'fog',
  FAN: 'fan',
  CUSTOM: 'custom',
};

export class DmxChannel {
  constructor(config = {}) {
    this.name = config.name || 'Canale DMX';
    this.type = config.type || ChannelType.CUSTOM;
    this.offset = config.offset !== undefined ? config.offset : 0; // 0-based offset all'interno della modalità DMX
    this.defaultValue = config.defaultValue !== undefined ? config.defaultValue : 0;
    this.highlightValue = config.highlightValue !== undefined ? config.highlightValue : 255;
    this.is16Bit = !!config.is16Bit;
    this.fineOffset = config.fineOffset !== undefined ? config.fineOffset : null; // Se 16-bit, l'offset del canale Fine
    this.capabilities = config.capabilities || []; // Array di { range: [min, max], name: string, type: string }
  }

  /**
   * Converte un valore normalizzato 0..1 nel byte (o word 16-bit) DMX
   */
  encodeValue(normalizedVal) {
    const clamped = Math.max(0, Math.min(1, normalizedVal));
    if (this.is16Bit) {
      const val16 = Math.round(clamped * 65535);
      return {
        coarse: (val16 >> 8) & 0xff,
        fine: val16 & 0xff,
      };
    }
    return {
      coarse: Math.round(clamped * 255),
      fine: null,
    };
  }

  /**
   * Decodifica un valore DMX in valore normalizzato 0..1
   */
  decodeValue(coarse, fine = 0) {
    if (this.is16Bit && fine !== null) {
      const val16 = ((coarse & 0xff) << 8) | (fine & 0xff);
      return val16 / 65535;
    }
    return (coarse & 0xff) / 255;
  }
}

export default DmxChannel;
