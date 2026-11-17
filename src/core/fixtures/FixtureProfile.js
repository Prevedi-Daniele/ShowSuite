import { DmxChannel, ChannelType } from './DmxChannel.js';

/**
 * FixtureMode - Rappresenta una modalità DMX specifica (es. 16ch Standard, 24ch Extended)
 */
export class FixtureMode {
  constructor(data = {}) {
    this.name = data.name || 'Standard';
    this.channelCount = data.channelCount || 1;
    this.channels = (data.channels || []).map((ch, idx) => {
      if (ch instanceof DmxChannel) return ch;
      return new DmxChannel({ ...ch, offset: ch.offset !== undefined ? ch.offset : idx });
    });
  }

  /**
   * Trova il canale associato a un tipo
   */
  getChannelByType(type) {
    return this.channels.find((ch) => ch.type === type);
  }

  /**
   * Trova tutti i canali associati a un tipo (es. RGB multipli per barre LED)
   */
  getChannelsByType(type) {
    return this.channels.filter((ch) => ch.type === type);
  }
}

/**
 * FixtureProfile - Scheda tecnica e definizione completa del proiettore
 */
export default class FixtureProfile {
  constructor(data = {}) {
    this.id = data.id || `profile_${Date.now()}`;
    this.manufacturer = data.manufacturer || 'Generico';
    this.model = data.model || 'Generic Fixture';
    this.category = data.category || 'dimmer'; // 'moving_head', 'scanner', 'par', 'bar', 'strobe', 'fog', 'dimmer'
    
    // Parametri fisici e ottici (utilizzati dal Canvas 2D di Lightkey per il fascio luminoso)
    this.physical = {
      panMaxAngle: data.physical?.panMaxAngle || 540,
      tiltMaxAngle: data.physical?.tiltMaxAngle || 270,
      beamAngleMin: data.physical?.beamAngleMin || 15,
      beamAngleMax: data.physical?.beamAngleMax || 35,
      hasColorWheel: !!data.physical?.hasColorWheel,
      hasGoboWheel: !!data.physical?.hasGoboWheel,
      hasPrism: !!data.physical?.hasPrism,
      hasFrost: !!data.physical?.hasFrost,
      hasZoom: !!data.physical?.hasZoom,
      hasCmy: !!data.physical?.hasCmy,
    };

    // Modalità operative DMX supportate
    this.modes = (data.modes || []).map((m) => (m instanceof FixtureMode ? m : new FixtureMode(m)));

    // Ruote (Color wheel e Gobo wheel se presenti)
    this.colorWheelSlots = data.colorWheelSlots || []; // [{ name: 'White', color: '#ffffff' }, { name: 'Red', color: '#ff0000' }, ...]
    this.goboWheelSlots = data.goboWheelSlots || [];   // [{ name: 'Open' }, { name: 'Dots' }, { name: 'Star' }, ...]
  }

  getMode(modeName) {
    if (!modeName) return this.modes[0] || null;
    return this.modes.find((m) => m.name.toLowerCase() === modeName.toLowerCase()) || this.modes[0];
  }
}
