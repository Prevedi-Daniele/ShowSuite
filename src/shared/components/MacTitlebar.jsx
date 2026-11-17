import React from 'react';
import { Lightbulb, Layers, Settings } from 'lucide-react';
import MacSegmentedControl from './MacSegmentedControl';

/**
 * MacTitlebar - Barra dei titoli conforme ad Apple HIG (macOS Dark)
 * Traffic lights pixel-perfect con micro-simboli al passaggio del mouse
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
    { id: 'lightkey', label: 'Lightkey DMX', icon: Lightbulb },
    { id: 'qlab', label: 'QLab Workspace', icon: Layers },
  ];

  return (
    <header className="app-drag-region h-9 min-h-[36px] bg-[#1a1a1d] border-b border-white/[0.08] flex items-center justify-between px-3 select-none z-40">
      {/* Controlli finestra macOS (Traffic Lights: Close, Min, Zoom) */}
      <div className="flex items-center space-x-2 app-no-drag w-44">
        <button
          type="button"
          onClick={handleClose}
          className="w-3 h-3 rounded-full bg-[#ff5f56] hover:bg-[#ff3b30] border border-[#e0443e] flex items-center justify-center group transition shadow-sm active:opacity-80"
          title="Chiudi"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[8px] text-[#4d0000] font-black leading-none select-none">×</span>
        </button>
        <button
          type="button"
          onClick={handleMinimize}
          className="w-3 h-3 rounded-full bg-[#ffbd2e] hover:bg-[#ffaa00] border border-[#dea123] flex items-center justify-center group transition shadow-sm active:opacity-80"
          title="Riduci a icona"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[8px] text-[#593d00] font-black leading-none select-none">−</span>
        </button>
        <button
          type="button"
          onClick={handleMaximize}
          className="w-3 h-3 rounded-full bg-[#27c93f] hover:bg-[#1db833] border border-[#1aab29] flex items-center justify-center group transition shadow-sm active:opacity-80"
          title="Schermo intero"
        >
          <span className="opacity-0 group-hover:opacity-100 text-[7px] text-[#004d11] font-black leading-none select-none">+</span>
        </button>
      </div>

      {/* Switcher centrale modalità Suite */}
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
          <div className="text-xs font-semibold tracking-wide text-[#f5f5f7] flex items-center space-x-2">
            {activeMode === 'lightkey' ? (
              <Lightbulb size={13} className="text-[#0a84ff]" />
            ) : (
              <Layers size={13} className="text-[#30d158]" />
            )}
            <span className="font-medium text-zinc-300">
              {activeMode === 'lightkey' ? 'ShowSuite — Lightkey Console' : 'ShowSuite — QLab 5 Workspace'}
            </span>
          </div>
        )}
      </div>

      {/* Pulsante preferenze e badge di sistema */}
      <div className="flex items-center justify-end space-x-2 app-no-drag w-44 text-xs">
        <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-white/[0.05] text-[#86868b] border border-white/[0.06]">
          {systemInfo.platform === 'win32' ? 'Windows' : 'Linux'}
        </span>

        <button
          type="button"
          onClick={onOpenSettings}
          className="p-1 rounded-[5px] text-[#86868b] hover:text-[#f5f5f7] hover:bg-white/[0.08] active:bg-white/[0.14] transition-colors"
          title="Impostazioni ShowSuite (Ctrl+,)"
        >
          <Settings size={14} />
        </button>
      </div>
    </header>
  );
}
