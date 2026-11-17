import React, { useState } from 'react';
import {
  Play,
  RotateCcw,
  Pause,
  Square,
  Plus,
  Trash2,
  Sliders,
  Check,
  Radio,
  Clock,
  Sparkles,
  ZapOff,
} from 'lucide-react';
import MacButton from '../shared/components/MacButton';

export default function CueListPanel({
  cues = [],
  activeCueIndex = -1,
  nextCueIndex = 0,
  fadeState = { isFading: false, progress: 0, isPaused: false },
  manualCrossfade = 0,
  onGo,
  onBack,
  onPause,
  onStop,
  onManualCrossfadeChange,
  onAddCue,
  onUpdateCue,
  onDeleteCue,
  onSelectCue,
  onToggleBlackout,
  isBlackout = false,
}) {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newCueName, setNewCueName] = useState('');
  const [newCueNumber, setNewCueNumber] = useState('');
  const [newCueFade, setNewCueFade] = useState(2.0);

  // Calcola numero suggerito per la nuova Cue
  const suggestedNumber =
    cues.length > 0
      ? (Math.max(...cues.map((c) => c.number || 1)) + 1).toFixed(1)
      : '1.0';

  const handleOpenAddModal = () => {
    setNewCueNumber(suggestedNumber);
    setNewCueName(`Scena ${suggestedNumber}`);
    setNewCueFade(2.0);
    setIsAddModalOpen(true);
  };

  const handleCreateCue = () => {
    if (!newCueName.trim()) return;
    onAddCue?.({
      number: parseFloat(newCueNumber) || parseFloat(suggestedNumber),
      name: newCueName.trim(),
      fadeIn: parseFloat(newCueFade) || 2.0,
      fadeOut: parseFloat(newCueFade) || 2.0,
    });
    setIsAddModalOpen(false);
  };

  const activeCue = activeCueIndex >= 0 ? cues[activeCueIndex] : null;
  const nextCue = nextCueIndex >= 0 ? cues[nextCueIndex] : null;

  return (
    <div className="flex flex-col h-full bg-[#161619] text-zinc-300 select-none">
      {/* Top Playback Transport Bar (The Console GO HUD) */}
      <div className="h-14 bg-[#1e1e24] border-b border-[#2d2d38] px-4 flex items-center justify-between shadow-md">
        {/* Sinistra: GO & Transport Controls */}
        <div className="flex items-center space-x-3">
          {/* Big Tactile GO Button */}
          <button
            onClick={onGo}
            disabled={cues.length === 0}
            className={`h-10 px-6 rounded-lg font-bold text-sm flex items-center gap-2 shadow-lg transition-all transform active:scale-95 ${
              fadeState.isFading
                ? 'bg-amber-500 hover:bg-amber-400 text-black shadow-amber-500/20 animate-pulse'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30 ring-2 ring-emerald-400/40'
            }`}
          >
            <Play size={16} fill="currentColor" />
            <span>{fadeState.isFading ? 'FADING...' : 'GO'}</span>
          </button>

          {/* Back / Pause / Stop Buttons */}
          <div className="flex items-center space-x-1 bg-black/40 p-1 rounded-lg border border-zinc-800">
            <button
              onClick={onBack}
              title="Cue Precedente (Back)"
              className="p-1.5 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded transition-colors"
            >
              <RotateCcw size={15} />
            </button>
            <button
              onClick={onPause}
              title={fadeState.isPaused ? 'Riprendi' : 'Pausa Dissolvenza'}
              className="p-1.5 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded transition-colors"
            >
              <Pause size={15} />
            </button>
            <button
              onClick={onStop}
              title="Ferma / Completa Immediatamente"
              className="p-1.5 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded transition-colors"
            >
              <Square size={15} />
            </button>
          </div>

          {/* Blackout Button */}
          <button
            onClick={onToggleBlackout}
            className={`h-8 px-2.5 rounded text-xs font-semibold flex items-center gap-1.5 border transition-colors ${
              isBlackout
                ? 'bg-red-600 border-red-500 text-white animate-pulse'
                : 'bg-black/40 border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-600'
            }`}
          >
            <ZapOff size={13} />
            <span>BLACKOUT</span>
          </button>
        </div>

        {/* Centro: Info Stato Dissolvenza Attiva */}
        <div className="flex-1 max-w-xs mx-4">
          <div className="flex justify-between text-[10px] text-zinc-400 mb-1 font-mono">
            <span>
              LIVE:{' '}
              <strong className="text-emerald-400">
                {activeCue ? `Q${activeCue.number} - ${activeCue.name}` : 'Nessuna'}
              </strong>
            </span>
            <span>
              NEXT:{' '}
              <strong className="text-amber-400">
                {nextCue ? `Q${nextCue.number}` : '--'}
              </strong>
            </span>
          </div>

          {/* Barra progresso fade */}
          <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden border border-zinc-700/60 relative">
            <div
              className={`h-full transition-all duration-75 ${
                fadeState.isFading ? 'bg-gradient-to-r from-emerald-500 to-amber-400' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.round(fadeState.progress * 100)}%` }}
            />
          </div>
        </div>

        {/* Destra: Manual Crossfader Slider A/B */}
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-[10px] font-mono text-zinc-500">Crossfader:</span>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(manualCrossfade * 100)}
            onChange={(e) => onManualCrossfadeChange?.(parseInt(e.target.value) / 100)}
            className="w-28 h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
          />
          <span className="text-[10px] font-mono text-white w-8">
            {Math.round(manualCrossfade * 100)}%
          </span>
          <MacButton
            variant="toolbar"
            size="sm"
            icon={Plus}
            onClick={handleOpenAddModal}
            title="Registra Scena Attuale in Nuova Cue"
          >
            Nuova Cue
          </MacButton>
        </div>
      </div>

      {/* Tabella Cue List */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#1b1b20] border-b border-[#2d2d38] text-[10px] text-zinc-400 uppercase font-mono tracking-wider">
              <th className="py-2 px-3 w-12 text-center">Stato</th>
              <th className="py-2 px-3 w-16">Cue #</th>
              <th className="py-2 px-4">Nome Scena / Descrizione</th>
              <th className="py-2 px-3 w-28">Fade In</th>
              <th className="py-2 px-3 w-28">Fade Out</th>
              <th className="py-2 px-3 w-16 text-center">Azioni</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#24242d]">
            {cues.map((cue, idx) => {
              const isLive = idx === activeCueIndex;
              const isNext = idx === nextCueIndex;

              return (
                <tr
                  key={cue.id}
                  onClick={() => onSelectCue?.(idx)}
                  className={`cursor-pointer transition-colors ${
                    isLive
                      ? 'bg-emerald-950/30 text-white font-medium border-l-4 border-l-emerald-500'
                      : isNext
                      ? 'bg-amber-950/20 text-zinc-200 border-l-4 border-l-amber-500'
                      : 'hover:bg-zinc-800/40 text-zinc-400'
                  }`}
                >
                  {/* Badge Stato */}
                  <td className="py-2.5 px-3 text-center">
                    {isLive ? (
                      <span className="inline-block px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/20 text-emerald-400 font-mono font-bold">
                        LIVE
                      </span>
                    ) : isNext ? (
                      <span className="inline-block px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-400 font-mono font-bold">
                        NEXT
                      </span>
                    ) : (
                      <span className="inline-block w-2 h-2 rounded-full bg-zinc-700" />
                    )}
                  </td>

                  {/* Numero Cue */}
                  <td className="py-2.5 px-3 font-mono font-bold text-white">
                    {cue.number.toFixed(1)}
                  </td>

                  {/* Nome Scena */}
                  <td className="py-2.5 px-4 font-medium text-zinc-200">
                    {cue.name}
                  </td>

                  {/* Fade In */}
                  <td className="py-2.5 px-3 font-mono text-[11px] text-zinc-400">
                    <span className="inline-flex items-center gap-1">
                      <Clock size={11} className="text-zinc-500" /> {cue.fadeIn}s
                    </span>
                  </td>

                  {/* Fade Out */}
                  <td className="py-2.5 px-3 font-mono text-[11px] text-zinc-400">
                    <span className="inline-flex items-center gap-1">
                      <Clock size={11} className="text-zinc-500" /> {cue.fadeOut}s
                    </span>
                  </td>

                  {/* Azioni */}
                  <td className="py-2.5 px-3 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCue?.(cue.id);
                      }}
                      title="Elimina Cue"
                      className="text-zinc-500 hover:text-red-400 p-1 rounded hover:bg-zinc-800 transition-colors"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {cues.length === 0 && (
          <div className="p-8 text-center text-zinc-500 text-xs">
            Nessuna scena registrata. Clicca su "Nuova Cue" per catturare lo stato attuale del palco.
          </div>
        )}
      </div>

      {/* Modale Registra Nuova Cue */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-[#1e1e24] border border-[#33333f] rounded-xl w-84 p-4 space-y-4 shadow-2xl">
            <h3 className="font-bold text-white text-sm">Registra Nuova Scena (Cue)</h3>
            <p className="text-[11px] text-zinc-400">
              Salva istantaneamente le posizioni, i colori, i gobo e le intensità di tutti i proiettori attivi.
            </p>

            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label className="text-[11px] text-zinc-300 block">Numero Cue</label>
                <input
                  type="number"
                  step="0.5"
                  value={newCueNumber}
                  onChange={(e) => setNewCueNumber(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white outline-none focus:border-mac-accent font-mono"
                />
              </div>

              <div className="col-span-2 space-y-1">
                <label className="text-[11px] text-zinc-300 block">Nome Scena</label>
                <input
                  type="text"
                  value={newCueName}
                  onChange={(e) => setNewCueName(e.target.value)}
                  placeholder="es. Strofa 2, Solo Chitarra..."
                  className="w-full bg-black/40 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white outline-none focus:border-mac-accent"
                  autoFocus
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-zinc-300 block">Tempo di Dissolvenza (Fade In)</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.5"
                  value={newCueFade}
                  onChange={(e) => setNewCueFade(parseFloat(e.target.value))}
                  className="flex-1 h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                />
                <span className="font-mono text-white text-xs w-12">{newCueFade}s</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <MacButton size="sm" variant="secondary" onClick={() => setIsAddModalOpen(false)}>
                Annulla
              </MacButton>
              <MacButton size="sm" variant="primary" onClick={handleCreateCue}>
                Registra Cue
              </MacButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
