import FixtureProfile, { FixtureMode } from './FixtureProfile.js';
import { DmxChannel, ChannelType } from './DmxChannel.js';

/**
 * OflParser - Converte i profili JSON standard di Open Fixture Library (OFL) in FixtureProfile di ShowSuite
 */
export default class OflParser {
  /**
   * Mappa il tipo di canale OFL nei ChannelType di ShowSuite
   */
  static mapOflTypeToChannelType(oflType, channelName = '') {
    const lowerType = (oflType || '').toLowerCase();
    const lowerName = (channelName || '').toLowerCase();

    if (lowerName.includes('fine') || lowerName.includes('16-bit')) {
      if (lowerType === 'pan' || lowerName.includes('pan')) return ChannelType.PAN_FINE;
      if (lowerType === 'tilt' || lowerName.includes('tilt')) return ChannelType.TILT_FINE;
    }

    switch (lowerType) {
      case 'intensity':
        return ChannelType.INTENSITY;
      case 'shutter':
      case 'strobe':
        return ChannelType.SHUTTER;
      case 'pan':
        return ChannelType.PAN;
      case 'tilt':
        return ChannelType.TILT;
      case 'single color':
        if (lowerName.includes('red')) return ChannelType.RED;
        if (lowerName.includes('green')) return ChannelType.GREEN;
        if (lowerName.includes('blue')) return ChannelType.BLUE;
        if (lowerName.includes('white')) return ChannelType.WHITE;
        if (lowerName.includes('amber')) return ChannelType.AMBER;
        if (lowerName.includes('uv')) return ChannelType.UV;
        if (lowerName.includes('cyan')) return ChannelType.CYAN;
        if (lowerName.includes('magenta')) return ChannelType.MAGENTA;
        if (lowerName.includes('yellow')) return ChannelType.YELLOW;
        return ChannelType.CUSTOM;
      case 'color intensity':
        if (lowerName.includes('red')) return ChannelType.RED;
        if (lowerName.includes('green')) return ChannelType.GREEN;
        if (lowerName.includes('blue')) return ChannelType.BLUE;
        return ChannelType.CUSTOM;
      case 'color wheel':
        return ChannelType.COLOR_WHEEL;
      case 'gobo':
        return ChannelType.GOBO_WHEEL;
      case 'prism':
        return ChannelType.PRISM;
      case 'zoom':
        return ChannelType.ZOOM;
      case 'focus':
        return ChannelType.FOCUS;
      case 'iris':
        return ChannelType.IRIS;
      case 'frost':
        return ChannelType.FROST;
      case 'speed':
        return ChannelType.SPEED;
      case 'fog':
        return ChannelType.FOG;
      default:
        return ChannelType.CUSTOM;
    }
  }

  /**
   * Esegue il parsing di un oggetto o stringa JSON OFL
   * @param {string|Object} oflJson
   * @param {string} manufacturer
   * @returns {FixtureProfile}
   */
  static parse(oflJson, manufacturer = 'Generico') {
    const data = typeof oflJson === 'string' ? JSON.parse(oflJson) : oflJson;

    // Normalizza categoria
    let category = 'par';
    if (data.categories && data.categories.length > 0) {
      const primaryCat = data.categories[0].toLowerCase();
      if (primaryCat.includes('moving head')) category = 'moving_head';
      else if (primaryCat.includes('scanner')) category = 'scanner';
      else if (primaryCat.includes('bar')) category = 'bar';
      else if (primaryCat.includes('strobe')) category = 'strobe';
      else if (primaryCat.includes('fog') || primaryCat.includes('smoke')) category = 'fog';
      else if (primaryCat.includes('dimmer')) category = 'dimmer';
    }

    const availableChannels = data.availableChannels || {};

    // Crea le modalità
    const modes = (data.modes || []).map((m) => {
      const modeChannels = [];
      const channelNames = m.channels || [];

      channelNames.forEach((chRef, index) => {
        if (!chRef || chRef === null) {
          // Canale nullo o non assegnato
          modeChannels.push(
            new DmxChannel({
              name: `Canale ${index + 1}`,
              type: ChannelType.CUSTOM,
              offset: index,
            })
          );
          return;
        }

        const chDef = availableChannels[chRef] || { name: chRef, type: 'custom' };
        const chType = OflParser.mapOflTypeToChannelType(chDef.type, chRef);

        const dmxChannel = new DmxChannel({
          name: chRef,
          type: chType,
          offset: index,
          defaultValue: chDef.defaultValue || 0,
          highlightValue: chDef.highlightValue || 255,
          capabilities: chDef.capabilities || [],
        });

        modeChannels.push(dmxChannel);
      });

      return new FixtureMode({
        name: m.name || 'Standard',
        channelCount: modeChannels.length,
        channels: modeChannels,
      });
    });

    return new FixtureProfile({
      id: `${manufacturer}_${data.name || 'fixture'}`.toLowerCase().replace(/[^a-z0-9]/g, '_'),
      manufacturer: manufacturer || data.fixtureManufacturer || 'Generico',
      model: data.name || 'Custom Fixture',
      category,
      physical: {
        panMaxAngle: data.physical?.panMax || 540,
        tiltMaxAngle: data.physical?.tiltMax || 270,
        beamAngleMin: data.physical?.lens?.degreesMinMax?.[0] || 15,
        beamAngleMax: data.physical?.lens?.degreesMinMax?.[1] || 35,
      },
      modes,
    });
  }
}
