import React, { useState, useEffect } from 'react';
import MacTitlebar from './shared/components/MacTitlebar';
import GlobalSettingsModal from './shared/components/GlobalSettingsModal';
import LightkeyMainView from './frontend-lightkey/LightkeyMainView';
import QLabMainView from './frontend-qlab/QLabMainView';

export default function App() {
  const [activeMode, setActiveMode] = useState('lightkey'); // 'lightkey' o 'qlab'
  const [isSuiteMode, setIsSuiteMode] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [systemInfo, setSystemInfo] = useState({ platform: 'win32', version: '1.0.0' });

  useEffect(() => {
    // Rileva la modalità iniziale da Electron se presente
    if (window.showsuite?.app) {
      window.showsuite.app.getInitialMode().then((mode) => {
        if (mode === 'lightkey' || mode === 'qlab') {
          setActiveMode(mode);
          setIsSuiteMode(false);
        } else {
          setIsSuiteMode(true);
        }
      });

      window.showsuite.app.getSystemInfo().then((info) => {
        if (info) setSystemInfo(info);
      });
    }

    // Shortcut da tastiera rapida: F1 per Lightkey, F2 per QLab (se in Suite Mode)
    const handleKeyDown = (e) => {
      if (e.key === 'F1' && isSuiteMode) {
        setActiveMode('lightkey');
      } else if (e.key === 'F2' && isSuiteMode) {
        setActiveMode('qlab');
      } else if (e.key === ',' && (e.metaKey || e.ctrlKey)) {
        // Cmd+, o Ctrl+, apre le preferenze (standard macOS / Win)
        setIsSettingsOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSuiteMode]);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#141416] text-mac-text select-none overflow-hidden">
      {/* Titlebar macOS personalizzata con Traffic Lights e Switcher */}
      <MacTitlebar
        activeMode={activeMode}
        onModeChange={setActiveMode}
        isSuiteMode={isSuiteMode}
        systemInfo={systemInfo}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Contenuto Dinamico del Workspace */}
      <main className="flex-1 flex overflow-hidden">
        {activeMode === 'lightkey' ? <LightkeyMainView /> : <QLabMainView />}
      </main>

      {/* Pannello Impostazioni Globali ShowSuite */}
      <GlobalSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
