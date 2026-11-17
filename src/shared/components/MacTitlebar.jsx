import React from 'react';
import { Lightbulb, Layers, Settings } from 'lucide-react';
import MacSegmentedControl from './MacSegmentedControl';

/**
 * MacTitlebar - Barra dei titoli personalizzata macOS con controlli di finestra e switch di modalità
 */
export default function MacTitlebar({
  activeMode,
  onModeChange,
  isSuiteMode = true,
  systemInfo = { platform: 'win32' },
  onOpenSettings,
}) {
  const handleMinimize = () => window.showsuite?.window?.minimize();
  const handleMaximize = () => window.showsuite?.window?.maximize();
  const handleClose = () => window.showsuite?.window?.close();

  const modeOptions = [
    { id: 'lightkey', label: 'Lightkey', icon: Lightbulb },
    { id: 'qlab', label: 'QLab', icon: Layers },
  ];

  return (
    <header className="app-drag-region h-10 min-h-[40px] bg-[#1e1e22] border-b border-[#303038] flex items-center justify-between px-3 select-none z-40">
      {/* Controlli finestra macOS (Traffic Lights) */}
      <div className="flex items-center space-x-2 app-no-drag w-44">
        <button
          onClick={handleClose}
          className="w-3 h-3 rounded-full bg-[#ff5f56] hover:bg-[#ff3b30] border border-[#e0443e] flex items-center justify-center group transition shadow-sm"
          title="Chiudi"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[8px] text-[#4d0000] font-bold leading-none">×</span>
        </button>
        <button
          onClick={handleMinimize}
          className="w-3 h-3 rounded-full bg-[#ffbd2e] hover:bg-[#ffaa00] border border-[#dea123] flex items-center justify-center group transition shadow-sm"
          title="Minimizza"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[8px] text-[#593d00] font-bold leading-none">−</span>
        </button>
        <button
          onClick={handleMaximize}
          className="w-3 h-3 rounded-full bg-[#27c93f] hover:bg-[#1db833] border border-[#1aab29] flex items-center justify-center group transition shadow-sm"
          title="Espandi"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[7px] text-[#004d11] font-bold leading-none">+</span>
        </button>
      </div>

      {/* Switcher centrale di modalità */}
      <div className="flex items-center justify-center flex-1">
        {isSuiteMode ? (
          <div className="app-no-drag">
            <MacSegmentedControl
              options={modeOptions}
              value={activeMode}
              onChange={onModeChange}
              size="sm"
            />
          </div>
        ) : (
          <div className="text-xs font-semibold tracking-wide text-zinc-300 flex items-center space-x-2">
            {activeMode === 'lightkey' ? (
              <Lightbulb size={14} className="text-mac-accent" />
            ) : (
              <Layers size={14} className="text-qlab-accent" />
            )}
            <span>
              {activeMode === 'lightkey' ? 'ShowSuite - Lightkey Console' : 'ShowSuite - QLab Workspace'}
            </span>
          </div>
        )}
      </div>

      {/* Pulsante preferenze e badge di sistema */}
      <div className="flex items-center justify-end space-x-2.5 app-no-drag w-44 text-xs text-mac-muted">
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
          {systemInfo.platform === 'win32' ? 'Windows' : 'Linux'}
        </span>
        <button
          onClick={onOpenSettings}
          className="p-1 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition focus:outline-none"
          title="Preferenze Globali"
        >
          <Settings size={15} />
        </button>
      </div>
    </header>
  );
}
