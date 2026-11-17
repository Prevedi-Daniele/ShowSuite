const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');

// Modalità modulo: 'suite' (entrambi), 'lightkey' (standalone), 'qlab' (standalone)
let initialModuleMode = 'suite';

// Analizza i flag della riga di comando
process.argv.forEach((arg) => {
  if (arg.startsWith('--module=')) {
    const mode = arg.split('=')[1].toLowerCase();
    if (['suite', 'lightkey', 'qlab'].includes(mode)) {
      initialModuleMode = mode;
    }
  } else if (arg === '--standalone-lightkey') {
    initialModuleMode = 'lightkey';
  } else if (arg === '--standalone-qlab') {
    initialModuleMode = 'qlab';
  }
});

let mainWindow = null;
let dmxEngine = null;
let patchManager = null;

async function initDmxEngine() {
  try {
    const { default: DmxEngine, EnttecProDriver } = await import('../core/dmx/index.js');
    const {
      default: PatchManager,
      FixtureInstance,
      builtInProfiles,
      DipSwitchCalculator,
    } = await import('../core/fixtures/index.js');

    dmxEngine = new DmxEngine({ refreshRate: 33 });
    patchManager = new PatchManager({ universeCount: 4 });
    dmxEngine.start();

    // Loop sincronizzato: aggiorna i buffer DMX da PatchManager
    dmxEngine.on('stats', (stats) => {
      if (patchManager && dmxEngine) {
        patchManager.renderAllToDmx(dmxEngine);
      }
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('dmx:stats', stats);
      }
    });

    dmxEngine.on('driver-status', (status) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('dmx:driverStatus', status);
      }
    });

    // Registra IPC handlers DMX
    ipcMain.handle('dmx:setDriver', async (_event, type, options) => {
      if (!dmxEngine) return false;
      return await dmxEngine.setDriver(type, options);
    });

    ipcMain.handle('dmx:setRefreshRate', (_event, fps) => {
      if (dmxEngine) dmxEngine.setRefreshRate(fps);
      return true;
    });

    ipcMain.handle('dmx:setChannel', (_event, universe, channel, value) => {
      if (dmxEngine) dmxEngine.setChannel(universe, channel, value);
      return true;
    });

    ipcMain.handle('dmx:setChannels', (_event, universe, values) => {
      if (dmxEngine) dmxEngine.setChannels(universe, values);
      return true;
    });

    ipcMain.handle('dmx:toggleBlackout', () => {
      if (!dmxEngine) return false;
      return dmxEngine.toggleBlackout();
    });

    ipcMain.handle('dmx:getUniverseData', (_event, universe) => {
      if (!dmxEngine) return [];
      const data = dmxEngine.getUniverseData(universe);
      return data ? Array.from(data) : [];
    });

    ipcMain.handle('dmx:listPorts', async () => {
      return await EnttecProDriver.listAvailablePorts();
    });

    // Registra IPC handlers Patch & Fixtures
    ipcMain.handle('patch:getProfiles', () => {
      return builtInProfiles.map((p) => ({
        id: p.id,
        manufacturer: p.manufacturer,
        model: p.model,
        category: p.category,
        modes: p.modes.map((m) => ({ name: m.name, channelCount: m.channelCount })),
      }));
    });

    ipcMain.handle('patch:getFixtures', () => {
      if (!patchManager) return [];
      return patchManager.fixtures.map((f) => ({
        id: f.id,
        name: f.name,
        profileId: f.profile?.id,
        modeName: f.mode?.name,
        universe: f.universe,
        address: f.address,
        channelCount: f.mode?.channelCount || 1,
        position: f.position,
        calibration: f.calibration,
        state: f.state,
        dipSwitches: f.getDipSwitches(),
      }));
    });

    ipcMain.handle('patch:addFixture', (_event, fixtureConfig) => {
      if (!patchManager) return null;
      const profile = builtInProfiles.find((p) => p.id === fixtureConfig.profileId) || builtInProfiles[0];
      const fixture = new FixtureInstance({
        name: fixtureConfig.name || profile.model,
        profile,
        universe: fixtureConfig.universe || 1,
        address: fixtureConfig.address || patchManager.findNextAvailableAddress(fixtureConfig.universe || 1, profile.modes[0].channelCount) || 1,
        x: fixtureConfig.x || 200,
        y: fixtureConfig.y || 200,
      });

      patchManager.addFixture(fixture);
      return { success: true, id: fixture.id, address: fixture.address };
    });

    ipcMain.handle('patch:removeFixture', (_event, fixtureId) => {
      if (!patchManager) return false;
      return patchManager.removeFixture(fixtureId);
    });

    ipcMain.handle('patch:updateFixtureState', (_event, fixtureId, newState) => {
      if (!patchManager) return false;
      const fixture = patchManager.getFixtureById(fixtureId);
      if (fixture) {
        Object.assign(fixture.state, newState);
        return true;
      }
      return false;
    });

    ipcMain.handle('patch:calculateDip', (_event, address) => {
      return DipSwitchCalculator.addressToDipSwitches(address);
    });
  } catch (err) {
    console.error('Errore inizializzazione DmxEngine:', err);
  }
}

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1500, width),
    height: Math.min(950, height),
    minWidth: 1024,
    minHeight: 700,
    frame: false, // Frameless per replicare fedelmente la barra dei controlli macOS
    titleBarStyle: 'hidden',
    backgroundColor: '#18181b',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    icon: path.join(__dirname, '../../public/icon.png'),
    show: false,
  });

  // Mostra quando è pronta per evitare sfarfallio
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const devUrl = 'http://localhost:5173';

  if (isDev) {
    mainWindow.loadURL(devUrl).catch(() => {
      // Se il dev server non risponde subito, carica il fallback o riprova
      setTimeout(() => mainWindow.loadURL(devUrl), 1000);
    });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'));
  }

  // Gestione stato massimizzato
  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window-state-change', { isMaximized: true });
  });

  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window-state-change', { isMaximized: false });
  });
}

// IPC Handlers per la barra dei titoli personalizzata macOS style
ipcMain.handle('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.handle('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
    return mainWindow.isMaximized();
  }
  return false;
});

ipcMain.handle('window:close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.handle('window:isMaximized', () => {
  return mainWindow ? mainWindow.isMaximized() : false;
});

ipcMain.handle('app:getInitialMode', () => {
  return initialModuleMode;
});

ipcMain.handle('app:getSystemInfo', () => {
  return {
    platform: process.platform, // 'win32' o 'linux' (o 'darwin')
    version: app.getVersion(),
    arch: process.arch,
  };
});

app.whenReady().then(async () => {
  createWindow();
  await initDmxEngine();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
