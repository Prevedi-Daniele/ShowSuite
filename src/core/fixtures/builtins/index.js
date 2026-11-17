import FixtureProfile, { FixtureMode } from '../FixtureProfile.js';
import { DmxChannel, ChannelType } from '../DmxChannel.js';

export const genericDimmer = new FixtureProfile({
  id: 'generic_dimmer_1ch',
  manufacturer: 'Generic',
  model: 'Dimmer / Par Can',
  category: 'dimmer',
  modes: [
    new FixtureMode({
      name: '1 Channel',
      channelCount: 1,
      channels: [
        new DmxChannel({ name: 'Dimmer', type: ChannelType.INTENSITY, offset: 0, defaultValue: 0, highlightValue: 255 }),
      ],
    }),
  ],
});

export const genericRgb = new FixtureProfile({
  id: 'generic_rgb_3ch',
  manufacturer: 'Generic',
  model: 'LED Par RGB',
  category: 'par',
  modes: [
    new FixtureMode({
      name: '3 Channel (RGB)',
      channelCount: 3,
      channels: [
        new DmxChannel({ name: 'Red', type: ChannelType.RED, offset: 0, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Green', type: ChannelType.GREEN, offset: 1, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Blue', type: ChannelType.BLUE, offset: 2, defaultValue: 0, highlightValue: 255 }),
      ],
    }),
  ],
});

export const genericRgbw = new FixtureProfile({
  id: 'generic_rgbw_4ch',
  manufacturer: 'Generic',
  model: 'LED Par RGBW',
  category: 'par',
  modes: [
    new FixtureMode({
      name: '4 Channel (RGBW)',
      channelCount: 4,
      channels: [
        new DmxChannel({ name: 'Red', type: ChannelType.RED, offset: 0, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Green', type: ChannelType.GREEN, offset: 1, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Blue', type: ChannelType.BLUE, offset: 2, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'White', type: ChannelType.WHITE, offset: 3, defaultValue: 0, highlightValue: 255 }),
      ],
    }),
  ],
});

export const proMovingHeadSpot = new FixtureProfile({
  id: 'pro_moving_head_spot_16ch',
  manufacturer: 'Pro Lighting',
  model: 'Spot Profile 575',
  category: 'moving_head',
  physical: {
    panMaxAngle: 540,
    tiltMaxAngle: 270,
    beamAngleMin: 12,
    beamAngleMax: 32,
    hasColorWheel: true,
    hasGoboWheel: true,
    hasPrism: true,
    hasZoom: true,
  },
  modes: [
    new FixtureMode({
      name: '16 Channel Standard',
      channelCount: 16,
      channels: [
        new DmxChannel({ name: 'Pan (Coarse)', type: ChannelType.PAN, offset: 0, defaultValue: 128 }),
        new DmxChannel({ name: 'Pan Fine', type: ChannelType.PAN_FINE, offset: 1, defaultValue: 0 }),
        new DmxChannel({ name: 'Tilt (Coarse)', type: ChannelType.TILT, offset: 2, defaultValue: 128 }),
        new DmxChannel({ name: 'Tilt Fine', type: ChannelType.TILT_FINE, offset: 3, defaultValue: 0 }),
        new DmxChannel({ name: 'Pan/Tilt Speed', type: ChannelType.SPEED, offset: 4, defaultValue: 0 }),
        new DmxChannel({ name: 'Dimmer', type: ChannelType.INTENSITY, offset: 5, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Shutter / Strobe', type: ChannelType.SHUTTER, offset: 6, defaultValue: 255 }), // 255 = open
        new DmxChannel({ name: 'Red', type: ChannelType.RED, offset: 7, defaultValue: 255 }),
        new DmxChannel({ name: 'Green', type: ChannelType.GREEN, offset: 8, defaultValue: 255 }),
        new DmxChannel({ name: 'Blue', type: ChannelType.BLUE, offset: 9, defaultValue: 255 }),
        new DmxChannel({ name: 'Color Wheel', type: ChannelType.COLOR_WHEEL, offset: 10, defaultValue: 0 }),
        new DmxChannel({ name: 'Gobo Wheel', type: ChannelType.GOBO_WHEEL, offset: 11, defaultValue: 0 }),
        new DmxChannel({ name: 'Gobo Rotation', type: ChannelType.GOBO_ROTATE, offset: 12, defaultValue: 0 }),
        new DmxChannel({ name: 'Prism', type: ChannelType.PRISM, offset: 13, defaultValue: 0 }),
        new DmxChannel({ name: 'Focus', type: ChannelType.FOCUS, offset: 14, defaultValue: 128 }),
        new DmxChannel({ name: 'Zoom', type: ChannelType.ZOOM, offset: 15, defaultValue: 128 }),
      ],
    }),
  ],
});

export const proWashCmy = new FixtureProfile({
  id: 'pro_wash_cmy_16ch',
  manufacturer: 'Pro Lighting',
  model: 'Wash CMY 700',
  category: 'moving_head',
  physical: {
    panMaxAngle: 540,
    tiltMaxAngle: 270,
    beamAngleMin: 15,
    beamAngleMax: 45,
    hasCmy: true,
    hasFrost: true,
    hasZoom: true,
  },
  modes: [
    new FixtureMode({
      name: '16 Channel CMY',
      channelCount: 16,
      channels: [
        new DmxChannel({ name: 'Pan', type: ChannelType.PAN, offset: 0, defaultValue: 128 }),
        new DmxChannel({ name: 'Pan Fine', type: ChannelType.PAN_FINE, offset: 1, defaultValue: 0 }),
        new DmxChannel({ name: 'Tilt', type: ChannelType.TILT, offset: 2, defaultValue: 128 }),
        new DmxChannel({ name: 'Tilt Fine', type: ChannelType.TILT_FINE, offset: 3, defaultValue: 0 }),
        new DmxChannel({ name: 'Dimmer', type: ChannelType.INTENSITY, offset: 4, defaultValue: 0, highlightValue: 255 }),
        new DmxChannel({ name: 'Shutter', type: ChannelType.SHUTTER, offset: 5, defaultValue: 255 }),
        new DmxChannel({ name: 'Cyan', type: ChannelType.CYAN, offset: 6, defaultValue: 0 }),
        new DmxChannel({ name: 'Magenta', type: ChannelType.MAGENTA, offset: 7, defaultValue: 0 }),
        new DmxChannel({ name: 'Yellow', type: ChannelType.YELLOW, offset: 8, defaultValue: 0 }),
        new DmxChannel({ name: 'CTO Color Temp', type: ChannelType.CTO, offset: 9, defaultValue: 0 }),
        new DmxChannel({ name: 'Zoom', type: ChannelType.ZOOM, offset: 10, defaultValue: 128 }),
        new DmxChannel({ name: 'Frost', type: ChannelType.FROST, offset: 11, defaultValue: 0 }),
      ],
    }),
  ],
});

export const genericFogMachine = new FixtureProfile({
  id: 'generic_fog_machine_2ch',
  manufacturer: 'Generic',
  model: 'Fog & Haze Generator',
  category: 'fog',
  modes: [
    new FixtureMode({
      name: '2 Channel',
      channelCount: 2,
      channels: [
        new DmxChannel({ name: 'Fog Volume', type: ChannelType.FOG, offset: 0, defaultValue: 0 }),
        new DmxChannel({ name: 'Fan Speed', type: ChannelType.FAN, offset: 1, defaultValue: 128 }),
      ],
    }),
  ],
});

export const builtInProfiles = [
  genericDimmer,
  genericRgb,
  genericRgbw,
  proMovingHeadSpot,
  proWashCmy,
  genericFogMachine,
];
