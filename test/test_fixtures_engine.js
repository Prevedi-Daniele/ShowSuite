import {
  PatchManager,
  FixtureInstance,
  DipSwitchCalculator,
  OflParser,
  builtInProfiles,
  ChannelType,
} from '../src/core/fixtures/index.js';
import { DmxEngine } from '../src/core/dmx/index.js';

async function runFixtureEngineTests() {
  console.log('--- AVVIO TEST DEL FIXTURE LIBRARY & PATCHING ENGINE ---');

  // 1. Test Dip Switch Calculator
  console.log('\n[1] Test DipSwitchCalculator:');
  const dip1 = DipSwitchCalculator.addressToDipSwitches(1);
  const addr1 = DipSwitchCalculator.dipSwitchesToAddress(dip1);
  if (dip1[0] === true && dip1[1] === false && addr1 === 1) {
    console.log('✓ Indirizzo DMX 1 -> Dip [ON, OFF, OFF...] -> Riconversione: 1 (OK)');
  } else {
    throw new Error('Test Dip 1 fallito');
  }

  // Indirizzo 17 (16 + 1 = dip 1 e dip 5 ON)
  const dip17 = DipSwitchCalculator.addressToDipSwitches(17);
  const addr17 = DipSwitchCalculator.dipSwitchesToAddress(dip17);
  if (dip17[0] === true && dip17[4] === true && addr17 === 17) {
    console.log('✓ Indirizzo DMX 17 (16+1) -> Dip 1 & Dip 5 ON -> Riconversione: 17 (OK)');
  } else {
    throw new Error('Test Dip 17 fallito');
  }

  // 2. Test Built-in Profiles
  console.log('\n[2] Test Profili Built-In:');
  console.log(`✓ Caricati ${builtInProfiles.length} profili predefiniti (Dimmer, RGB, RGBW, Spot 16ch, Wash CMY 16ch, Fog).`);
  const spotProfile = builtInProfiles.find((p) => p.id === 'pro_moving_head_spot_16ch');
  if (!spotProfile || spotProfile.modes[0].channelCount !== 16) {
    throw new Error('Profilo Spot 16ch non valido');
  }
  console.log(`✓ Profilo Spot: ${spotProfile.manufacturer} ${spotProfile.model} (${spotProfile.modes[0].channelCount} canali DMX).`);

  // 3. Test Parser Open Fixture Library (OFL)
  console.log('\n[3] Test OFL Parser:');
  const oflSample = {
    name: 'Mega Tri Par Profile',
    categories: ['Color Changer', 'Par'],
    physical: { panMax: 0, tiltMax: 0 },
    availableChannels: {
      'Master Dimmer': { type: 'Intensity' },
      'Strobe Rate': { type: 'Shutter' },
      'Red Color': { type: 'Single Color' },
      'Green Color': { type: 'Single Color' },
      'Blue Color': { type: 'Single Color' },
    },
    modes: [
      {
        name: '5-channel',
        channels: ['Master Dimmer', 'Red Color', 'Green Color', 'Blue Color', 'Strobe Rate'],
      },
    ],
  };

  const parsedProfile = OflParser.parse(oflSample, 'American DJ');
  if (parsedProfile.modes[0].channelCount === 5 && parsedProfile.modes[0].channels[0].type === ChannelType.INTENSITY) {
    console.log(`✓ Parser OFL JSON: Profilo "${parsedProfile.model}" convertito con 5 canali (OK).`);
  } else {
    throw new Error('Parsing OFL fallito');
  }

  // 4. Test FixtureInstance: Pan/Tilt 16-bit e HSB Color
  console.log('\n[4] Test FixtureInstance (16-bit Pan/Tilt & HSB):');
  const spotInstance = new FixtureInstance({
    name: 'Moving Head 1',
    profile: spotProfile,
    universe: 1,
    address: 1,
  });

  // Imposta Dimmer al 100%, Pan a 0.5 (centro), Colore HSB (Rosso puro: H=0, S=1, B=1)
  spotInstance.state.intensity = 1.0;
  spotInstance.state.pan = 0.5; // In 16-bit: 0.5 * 65535 = 32767.5 -> Coarse: 128, Fine: 0
  spotInstance.setColorHsb(0, 1.0, 1.0); // Rosso

  const dmxBuffer = new Uint8Array(512);
  spotInstance.renderToDmx(dmxBuffer);

  // Verifica canali dello Spot:
  // Offset 0: Pan Coarse (128)
  // Offset 1: Pan Fine (0)
  // Offset 5: Dimmer (255)
  // Offset 7: Red (255), Offset 8: Green (0), Offset 9: Blue (0)
  if (dmxBuffer[0] === 128 && dmxBuffer[5] === 255 && dmxBuffer[7] === 255 && dmxBuffer[8] === 0) {
    console.log('✓ Rendering DMX Spot 16-bit: Pan Coarse (128), Dimmer (255), Rosso (255), Verde (0) (OK).');
  } else {
    throw new Error(`Rendering DMX inatteso: Pan=${dmxBuffer[0]}, Dim=${dmxBuffer[5]}, R=${dmxBuffer[7]}`);
  }

  // 5. Test PatchManager & Collision Detection
  console.log('\n[5] Test PatchManager & Collision Detection:');
  const patchManager = new PatchManager({ universeCount: 4 });
  patchManager.addFixture(spotInstance); // Canali 1-16 Universo 1

  // Tento di aggiungere un faro che collide (es. canale 10)
  const collidingPar = new FixtureInstance({
    name: 'Par Conflitto',
    profile: builtInProfiles.find((p) => p.id === 'generic_rgb_3ch'),
    universe: 1,
    address: 10, // Conflitto: 10..12 è dentro 1..16!
  });

  let collisionDetected = false;
  try {
    patchManager.addFixture(collidingPar);
  } catch (err) {
    collisionDetected = true;
    console.log(`✓ Collisione rilevata correttamente: ${err.message}`);
  }

  if (!collisionDetected) {
    throw new Error('La collisione non è stata rilevata!');
  }

  // Test Auto-Patch (trova prossimo indirizzo libero)
  const nextAddr = patchManager.findNextAvailableAddress(1, 3);
  if (nextAddr === 17) {
    console.log(`✓ Auto-Patching: Prossimo indirizzo libero per 3 canali calcolato correttamente a: ${nextAddr} (OK).`);
  } else {
    throw new Error(`Prossimo indirizzo errato: atteso 17, ottenuto ${nextAddr}`);
  }

  // Aggiungi faro a indirizzo 17
  collidingPar.address = nextAddr;
  patchManager.addFixture(collidingPar);
  console.log(`✓ Faro aggiunto con successo all'indirizzo ${nextAddr} (Nessuna collisione).`);

  // 6. Test Rendering su DmxEngine completo
  console.log('\n[6] Test Integrazione PatchManager -> DmxEngine:');
  const dmxEngine = new DmxEngine({ universeCount: 4 });
  patchManager.renderAllToDmx(dmxEngine);
  const u1Data = dmxEngine.getUniverseData(1);
  if (u1Data[0] === 128 && u1Data[5] === 255) {
    console.log('✓ DmxEngine universi popolati simultaneamente da tutti i proiettori patchati (OK).');
  }

  console.log('\n--- TUTTI I TEST DEL FIXTURE LIBRARY & PATCHING ENGINE SUPERATI AL 100%! ---');
}

runFixtureEngineTests().catch((err) => {
  console.error('Errore durante i test:', err);
  process.exit(1);
});
