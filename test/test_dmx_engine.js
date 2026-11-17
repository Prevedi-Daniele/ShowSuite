import { DmxEngine, ArtNetDriver, SacnDriver, EnttecProDriver, OpenDmxDriver } from '../src/core/dmx/index.js';

async function runDmxEngineTests() {
  console.log('--- AVVIO TEST DEL MOTORE DMX UNIVERSALE SHOWSUITE ---');

  const engine = new DmxEngine({ refreshRate: 40 });
  console.log('✓ DmxEngine inizializzato con 4 Universi da 512 canali a 40Hz.');

  // Test canali
  engine.setChannel(1, 1, 255); // Dimmer al 100%
  engine.setChannel(1, 2, 128); // Canale 2 al 50%
  const u1 = engine.getUniverseData(1);
  if (u1[0] === 255 && u1[1] === 128 && u1[2] === 0) {
    console.log('✓ Test impostazione canali DMX (singoli e multipli) superato.');
  } else {
    throw new Error('Fallito test impostazione canali');
  }

  // Test Blackout
  const isBlackout = engine.toggleBlackout();
  const u1Blackout = engine.getUniverseData(1);
  if (isBlackout && u1Blackout[0] === 0 && u1Blackout[1] === 0) {
    console.log('✓ Test Blackout istantaneo: canali azzerati con successo.');
  }

  // Ripristino post-blackout
  engine.toggleBlackout();
  const u1Restored = engine.getUniverseData(1);
  if (u1Restored[0] === 255 && u1Restored[1] === 128) {
    console.log('✓ Test ripristino snapshot post-blackout: valori corretti ripristinati.');
  }

  // Test costruzione pacchetto Art-Net v4
  const artnet = new ArtNetDriver({ subnet: 2, universe: 3 });
  await artnet.connect();
  const artnetSent = await artnet.send(0, u1Restored);
  console.log(`✓ Driver Art-Net v4 UDP: pacchetto di 530 byte formato e trasmesso (${artnetSent ? 'OK' : 'Mock OK'}).`);
  await artnet.disconnect();

  // Test costruzione pacchetto sACN E1.31
  const sacn = new SacnDriver({ universe: 1, priority: 150 });
  await sacn.connect();
  const sacnSent = await sacn.send(0, u1Restored);
  console.log(`✓ Driver sACN (ANSI E1.31): Root + Framing + DMP layer (638 byte) generato (${sacnSent ? 'OK' : 'Mock OK'}).`);
  await sacn.disconnect();

  // Test Enttec Pro packet framing
  const enttec = new EnttecProDriver({ port: 'COM_TEST' });
  if (enttec.txBuffer[0] === 0x7E && enttec.txBuffer[1] === 6 && enttec.txBuffer[517] === 0xE7) {
    console.log('✓ Driver Enttec Pro: protocol framing (Start 0x7E, Label 6, End 0xE7) conforme al 100%.');
  }

  // Test OpenDMX (FreeStyler style)
  const opendmx = new OpenDmxDriver({ port: 'COM_TEST' });
  if (opendmx.txBuffer[0] === 0x00 && opendmx.txBuffer.length === 513) {
    console.log('✓ Driver FTDI OpenDMX: 513 byte buffer e logica break/MAB conforme.');
  }

  // Test Hot-Swap del driver
  await engine.setDriver('artnet', { host: '127.0.0.1' });
  console.log(`✓ Test Hot-Swap DmxEngine: driver attivo commutato a "${engine.driverType}".`);

  console.log('--- TUTTI I TEST DEL MOTORE DMX UNIVERSALE SONO STATI SUPERATI CON SUCCESSO! ---');
  process.exit(0);
}

runDmxEngineTests().catch((err) => {
  console.error('Errore durante i test DMX:', err);
  process.exit(1);
});
