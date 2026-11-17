const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('showsuite', {
  // Controlli della finestra (macOS Traffic Lights)
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
    onStateChange: (callback) => {
      ipcRenderer.on('window-state-change', (_event, state) => callback(state));
    },
  },
  // Info di sistema e modalità iniziale
  app: {
    getInitialMode: () => ipcRenderer.invoke('app:getInitialMode'),
    getSystemInfo: () => ipcRenderer.invoke('app:getSystemInfo'),
  },
  // Canali IPC Motore DMX Hardware
  dmx: {
    setDriver: (type, options) => ipcRenderer.invoke('dmx:setDriver', type, options),
    setRefreshRate: (fps) => ipcRenderer.invoke('dmx:setRefreshRate', fps),
    setChannel: (universe, channel, value) => ipcRenderer.invoke('dmx:setChannel', universe, channel, value),
    setChannels: (universe, values) => ipcRenderer.invoke('dmx:setChannels', universe, values),
    toggleBlackout: () => ipcRenderer.invoke('dmx:toggleBlackout'),
    getUniverseData: (universe) => ipcRenderer.invoke('dmx:getUniverseData', universe),
    listPorts: () => ipcRenderer.invoke('dmx:listPorts'),
    onStats: (callback) => {
      ipcRenderer.on('dmx:stats', (_event, stats) => callback(stats));
    },
    onDriverStatus: (callback) => {
      ipcRenderer.on('dmx:driverStatus', (_event, status) => callback(status));
    },
  },
  // Canali IPC Patching & Fixture Library
  patch: {
    getProfiles: () => ipcRenderer.invoke('patch:getProfiles'),
    getFixtures: () => ipcRenderer.invoke('patch:getFixtures'),
    addFixture: (config) => ipcRenderer.invoke('patch:addFixture', config),
    removeFixture: (id) => ipcRenderer.invoke('patch:removeFixture', id),
    updateFixtureState: (id, state) => ipcRenderer.invoke('patch:updateFixtureState', id, state),
    calculateDip: (address) => ipcRenderer.invoke('patch:calculateDip', address),
  },
  qlab: {
    triggerCue: (cueId) => ipcRenderer.invoke('qlab:triggerCue', cueId),
  }
});
