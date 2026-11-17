import { ChannelType } from './DmxChannel.js';
import DipSwitchCalculator from './DipSwitchCalculator.js';

/**
 * FixtureInstance - Singolo proiettore patchato nel workspace con proprietà fisiche, spaziali e DMX
 */
export default class FixtureInstance {
  constructor(config = {}) {
    this.id = config.id || `fixture_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    this.name = config.name || 'Proiettore';
    this.profile = config.profile;
    this.mode = config.mode || (this.profile ? this.profile.modes[0] : null);
    
    // Assegnazione DMX
    this.universe = config.universe || 1; // 1-4
    this.address = config.address || 1;   // 1-512

    // Coordinate spaziali per 2D Stage Canvas di Lightkey
    this.position = {
      x: config.x !== undefined ? config.x : 200,
      y: config.y !== undefined ? config.y : 200,
      z: config.z !== undefined ? config.z : 0,
      rotation: config.rotation !== undefined ? config.rotation : 0, // In gradi
    };

    // Calibrazione (da capitolo Calibration di Lightkey)
    this.calibration = {
      invertPan: !!config.invertPan,
      invertTilt: !!config.invertTilt,
      swapPanTilt: !!config.swapPanTilt,
      panOffset: config.panOffset || 0,
      tiltOffset: config.tiltOffset || 0,
    };

    // Stato logico corrente delle proprietà fixture
    this.state = {
      intensity: 0, // 0..1 (Dimmer)
      shutter: 1,   // 1 = aperto, 0 = chiuso, >1 = strobo
      color: {
        r: 1, g: 1, b: 1, w: 0, a: 0, uv: 0,
        c: 0, m: 0, y: 0,
      },
      pan: 0.5,    // 0..1 (0.5 = centro 50%)
      tilt: 0.5,   // 0..1
      gobo: 0,     // Slot gobo 0 = open
      goboRotate: 0,
      prism: 0,    // 0 = off, 1 = on
      zoom: 0.5,
      focus: 0.5,
      frost: 0,
      fog: 0,
      fan: 0.5,
    };
  }

  /**
   * Restituisce la configurazione dei dip switch per questo faro
   */
  getDipSwitches() {
    return DipSwitchCalculator.addressToDipSwitches(this.address);
  }

  /**
   * Restituisce il range di canali occupati [startAddress, endAddress]
   */
  getChannelRange() {
    const count = this.mode ? this.mode.channelCount : 1;
    return {
      start: this.address,
      end: this.address + count - 1,
      count,
    };
  }

  /**
   * Converte lo stato logico nei byte DMX fisici e li scrive nel buffer dell'universo
   * @param {Uint8Array} universeBuffer - Buffer da 512 byte dell'universo corrispondente
   */
  renderToDmx(universeBuffer) {
    if (!this.mode || !universeBuffer) return;

    const baseAddress = this.address - 1; // 0-based
    const channels = this.mode.channels;

    // Gestione Pan e Tilt calibrati (inversione e swap)
    let effPan = this.state.pan;
    let effTilt = this.state.tilt;

    if (this.calibration.invertPan) effPan = 1 - effPan;
    if (this.calibration.invertTilt) effTilt = 1 - effTilt;
    if (this.calibration.swapPanTilt) {
      const temp = effPan;
      effPan = effTilt;
      effTilt = temp;
    }

    channels.forEach((ch) => {
      const dmxIndex = baseAddress + ch.offset;
      if (dmxIndex < 0 || dmxIndex >= 512) return;

      switch (ch.type) {
        case ChannelType.INTENSITY: {
          universeBuffer[dmxIndex] = Math.round(this.state.intensity * 255);
          break;
        }

        case ChannelType.SHUTTER: {
          // Se shutter è aperto (>0), imposta valore aperto (solitamente 255)
          universeBuffer[dmxIndex] = this.state.shutter > 0 ? 255 : 0;
          break;
        }

        case ChannelType.PAN: {
          const enc = ch.encodeValue(effPan);
          universeBuffer[dmxIndex] = enc.coarse;
          break;
        }

        case ChannelType.PAN_FINE: {
          const val16 = Math.round(effPan * 65535);
          universeBuffer[dmxIndex] = val16 & 0xff;
          break;
        }

        case ChannelType.TILT: {
          const enc = ch.encodeValue(effTilt);
          universeBuffer[dmxIndex] = enc.coarse;
          break;
        }

        case ChannelType.TILT_FINE: {
          const val16 = Math.round(effTilt * 65535);
          universeBuffer[dmxIndex] = val16 & 0xff;
          break;
        }

        case ChannelType.RED: {
          universeBuffer[dmxIndex] = Math.round(this.state.color.r * 255);
          break;
        }

        case ChannelType.GREEN: {
          universeBuffer[dmxIndex] = Math.round(this.state.color.g * 255);
          break;
        }

        case ChannelType.BLUE: {
          universeBuffer[dmxIndex] = Math.round(this.state.color.b * 255);
          break;
        }

        case ChannelType.WHITE: {
          universeBuffer[dmxIndex] = Math.round((this.state.color.w || 0) * 255);
          break;
        }

        case ChannelType.CYAN: {
          universeBuffer[dmxIndex] = Math.round((this.state.color.c || 0) * 255);
          break;
        }

        case ChannelType.MAGENTA: {
          universeBuffer[dmxIndex] = Math.round((this.state.color.m || 0) * 255);
          break;
        }

        case ChannelType.YELLOW: {
          universeBuffer[dmxIndex] = Math.round((this.state.color.y || 0) * 255);
          break;
        }

        case ChannelType.GOBO_WHEEL: {
          universeBuffer[dmxIndex] = Math.round(this.state.gobo * 255);
          break;
        }

        case ChannelType.PRISM: {
          universeBuffer[dmxIndex] = this.state.prism > 0 ? 255 : 0;
          break;
        }

        case ChannelType.ZOOM: {
          universeBuffer[dmxIndex] = Math.round(this.state.zoom * 255);
          break;
        }

        case ChannelType.FOCUS: {
          universeBuffer[dmxIndex] = Math.round(this.state.focus * 255);
          break;
        }

        case ChannelType.FROST: {
          universeBuffer[dmxIndex] = Math.round(this.state.frost * 255);
          break;
        }

        case ChannelType.FOG: {
          universeBuffer[dmxIndex] = Math.round(this.state.fog * 255);
          break;
        }

        case ChannelType.FAN: {
          universeBuffer[dmxIndex] = Math.round(this.state.fan * 255);
          break;
        }

        default:
          break;
      }
    });
  }

  /**
   * Helper per impostare il colore via HSB (Hue, Saturation, Brightness) tipico di Lightkey
   */
  setColorHsb(hue, saturation, brightness) {
    const h = (hue % 360) / 360;
    const s = Math.max(0, Math.min(1, saturation));
    const v = Math.max(0, Math.min(1, brightness));

    let r, g, b;
    const i = Math.floor(h * 6);
    const f = h * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - f * s);
    const t = v * (1 - (1 - f) * s);

    switch (i % 6) {
      case 0: r = v; g = t; b = p; break;
      case 1: r = q; g = v; b = p; break;
      case 2: r = p; g = v; b = t; break;
      case 3: r = p; g = q; b = v; break;
      case 4: r = t; g = p; b = v; break;
      case 5: r = v; g = p; b = q; break;
    }

    this.state.color.r = r;
    this.state.color.g = g;
    this.state.color.b = b;

    // Se il profilo ha miscelazione CMY, calcola i complementari sottrattivi
    this.state.color.c = 1 - r;
    this.state.color.m = 1 - g;
    this.state.color.y = 1 - b;
  }
}
