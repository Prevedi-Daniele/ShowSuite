import { FanEngine, FanMode, FanAttribute } from '../src/core/control/index.js';
import { FixtureInstance, builtInProfiles, ChannelType } from '../src/core/fixtures/index.js';

async function runFanAndHudTests() {
  console.log('=== TEST FANNING ENGINE & HUD CONTEXTUAL PROPERTIES ===\n');

  // 1. Test FanEngine - Linear Pan
  console.log('[1] Test FanEngine (Linear Pan su 5 fari, base 0.5, amount 0.4):');
  const linearPan = FanEngine.calculateFan(5, 0.5, 0.4, FanMode.LINEAR, FanAttribute.PAN);
  console.log('   Valori Pan generati:', linearPan.map((v) => v.toFixed(3)));
  // Per 5 fari con base 0.5 e amount 0.4:
  // delta = 0.4 * 0.5 = 0.2
  // Faro 0: 0.5 - 0.2 = 0.3
  // Faro 2 (centro): 0.5
  // Faro 4: 0.5 + 0.2 = 0.7
  if (Math.abs(linearPan[0] - 0.3) < 0.001 && Math.abs(linearPan[2] - 0.5) < 0.001 && Math.abs(linearPan[4] - 0.7) < 0.001) {
    console.log('   ✓ Distribuzione lineare perfetta (da 0.30 a 0.70 con centro a 0.50).');
  } else {
    throw new Error(`Test Linear Pan fallito: ${JSON.stringify(linearPan)}`);
  }

  // 2. Test FanEngine - Symmetric (Center-Out / V-Shape)
  console.log('\n[2] Test FanEngine (Symmetric Center-Out su 5 fari, base 0.5, amount 0.5):');
  const symPan = FanEngine.calculateFan(5, 0.5, 0.5, FanMode.SYMMETRIC, FanAttribute.PAN);
  console.log('   Valori Pan generati:', symPan.map((v) => v.toFixed(3)));
  // Faro centro (idx 2) deve essere 0.5
  // Fari esterni (idx 0 e idx 4) devono essere speculari (0.5 - 0.25 = 0.25 e 0.5 + 0.25 = 0.75)
  if (Math.abs(symPan[2] - 0.5) < 0.001 && Math.abs(symPan[0] - 0.25) < 0.001 && Math.abs(symPan[4] - 0.75) < 0.001) {
    console.log('   ✓ Distribuzione simmetrica a V perfetta (centro fisso, lati specchiati).');
  } else {
    throw new Error(`Test Symmetric Pan fallito: ${JSON.stringify(symPan)}`);
  }

  // 3. Test FanEngine - Color Hue Rainbow
  console.log('\n[3] Test FanEngine (Hue Rainbow su 4 fari, base 180°, amount 0.5):');
  const hueValues = FanEngine.calculateFan(4, 180, 0.5, FanMode.LINEAR, FanAttribute.HUE);
  console.log('   Valori Hue generati:', hueValues.map((v) => `${Math.round(v)}°`));
  // delta = 0.5 * 180 = 90
  // Faro 0: 180 - 90 = 90°
  // Faro 3: 180 + 90 = 270°
  if (Math.abs(hueValues[0] - 90) < 0.001 && Math.abs(hueValues[3] - 270) < 0.001) {
    console.log('   ✓ Distribuzione arcobaleno Hue calcolata correttamente (da 90° a 270°).');
  } else {
    throw new Error(`Test Hue Rainbow fallito: ${JSON.stringify(hueValues)}`);
  }

  // 4. Test Calibrazione & Inversione Assi Hardware in FixtureInstance
  console.log('\n[4] Test Calibrazione & Inversione Assi Hardware in FixtureInstance:');
  const spotProfile = builtInProfiles.find((p) => p.id === 'pro_moving_head_spot_16ch');
  const fixtureNormal = new FixtureInstance({
    profile: spotProfile,
    universe: 1,
    address: 1,
  });
  fixtureNormal.state.pan = 0.8;
  fixtureNormal.state.tilt = 0.2;

  const bufNormal = new Uint8Array(512);
  fixtureNormal.renderToDmx(bufNormal);
  const panCoarseNormal = bufNormal[0];
  const tiltCoarseNormal = bufNormal[2];

  const fixtureInverted = new FixtureInstance({
    profile: spotProfile,
    universe: 1,
    address: 1,
    invertPan: true,
    invertTilt: true,
  });
  fixtureInverted.state.pan = 0.8;
  fixtureInverted.state.tilt = 0.2;

  const bufInverted = new Uint8Array(512);
  fixtureInverted.renderToDmx(bufInverted);
  const panCoarseInverted = bufInverted[0];
  const tiltCoarseInverted = bufInverted[2];

  console.log(`   Pan Normale (0.8): ${panCoarseNormal} DMX | Pan Invertito (0.2 effettivo): ${panCoarseInverted} DMX`);
  console.log(`   Tilt Normale (0.2): ${tiltCoarseNormal} DMX | Tilt Invertito (0.8 effettivo): ${tiltCoarseInverted} DMX`);

  if (panCoarseNormal > 200 && panCoarseInverted < 60 && tiltCoarseNormal < 60 && tiltCoarseInverted > 200) {
    console.log('   ✓ Inversione assi DMX hardware verificata con successo.');
  } else {
    throw new Error('Test inversione assi fallito');
  }

  // 5. Test Rendering DMX Gobo & Shutter
  console.log('\n[5] Test Gobo Wheel & Shutter DMX Output:');
  fixtureNormal.state.gobo = 0.5; // ~128 DMX
  fixtureNormal.state.shutter = 1; // Aperto = 255
  fixtureNormal.renderToDmx(bufNormal);

  const goboChannel = spotProfile.modes[0].channels.find((c) => c.type === ChannelType.GOBO_WHEEL);
  const shutterChannel = spotProfile.modes[0].channels.find((c) => c.type === ChannelType.SHUTTER);

  const goboDmxVal = bufNormal[goboChannel.offset];
  const shutterDmxVal = bufNormal[shutterChannel.offset];

  console.log(`   Canale Gobo Wheel (offset ${goboChannel.offset}): DMX = ${goboDmxVal}`);
  console.log(`   Canale Shutter (offset ${shutterChannel.offset}): DMX = ${shutterDmxVal}`);

  if (goboDmxVal === 128 && shutterDmxVal === 255) {
    console.log('   ✓ Scrittura canali Gobo e Shutter nel buffer DMX corretta.');
  } else {
    throw new Error('Test Gobo/Shutter DMX fallito');
  }

  console.log('\n======================================================');
  console.log(' TUTTI I TEST DEL FANNING & HUD PROPERTIES SUPERATI! ');
  console.log('======================================================\n');
}

runFanAndHudTests().catch((err) => {
  console.error('ERRORE TEST:', err);
  process.exit(1);
});
