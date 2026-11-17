import React, { useState } from 'react';
import {
  PaletteType,
} from '../core/control/index.js';
import {
  Palette,
  Target,
  Disc,
  Layers,
  Plus,
  Trash2,
  Check,
  Sparkles,
  ArrowDown,
  Users,
  Compass,
  CircleDot,
  Sun,
  Cloud,
  Zap,
  SunMedium,
  Activity,
  ArrowUpLeft,
  ArrowUpRight,
} from 'lucide-react';
import MacButton from '../shared/components/MacButton';

// Mappa icone dinamiche
const iconComponents = {
  Target,
  ArrowDown,
  Users,
  Compass,
  CircleDot,
  Sun,
  Sparkles,
  Cloud,
  Zap,
  SunMedium,
  Activity,
  ArrowUpLeft,
  ArrowUpRight,
};

export default function PalettesPanel({
  palettes = [],
  selectedIds = [],
  onApplyPalette,
  onSavePalette,
  onDeletePalette,
}) {
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'color' | 'position' | 'beam' | 'preset'
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newPalName, setNewPalName] = useState('');
  const [newPalType, setNewPalType] = useState(PaletteType.COLOR);

  const filteredPalettes =
    activeTab === 'all' ? palettes : palettes.filter((p) => p.type === activeTab);

  const handleCreatePalette = () => {
    if (!newPalName.trim()) return;
    onSavePalette?.(newPalName.trim(), newPalType);
    setNewPalName('');
    setIsAddModalOpen(false);
  };

  return (
    <div className="flex flex-col h-full bg-[#18181c] text-zinc-300 select-none">
      {/* Top Header & Tabs */}
      <div className="p-2.5 bg-[#1f1f25] border-b border-[#2d2d38] flex items-center justify-between">
        <div className="flex items-center space-x-1 text-xs">
          {[
            { id: 'all', label: 'Tutte' },
            { id: PaletteType.COLOR, label: 'Colore' },
            { id: PaletteType.POSITION, label: 'Posizione' },
            { id: PaletteType.BEAM, label: 'Beam/Gobo' },
            { id: PaletteType.PRESET, label: 'Presets' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-mac-accent text-white font-semibold'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <MacButton
          variant="toolbar"
          size="sm"
          icon={Plus}
          onClick={() => setIsAddModalOpen(true)}
          title="Salva Nuova Palette dai Fari Selezionati"
        >
          Nuova Palette
        </MacButton>
      </div>

      {/* Grid delle Palette */}
      <div className="flex-1 p-3 overflow-y-auto">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
          {filteredPalettes.map((pal) => {
            const Icon = iconComponents[pal.icon] || Layers;

            return (
              <div
                key={pal.id}
                onClick={() => onApplyPalette?.(pal.id)}
                className="group relative p-2.5 bg-black/30 hover:bg-zinc-800/60 border border-[#2d2d38] hover:border-mac-accent rounded-lg cursor-pointer flex flex-col items-center justify-between text-center transition-all hover:scale-[1.02] shadow-sm hover:shadow-mac-accent/10"
              >
                {/* Visual Preview */}
                <div className="w-10 h-10 rounded-full flex items-center justify-center mb-1.5 shadow-md border border-white/10 relative overflow-hidden">
                  {pal.type === PaletteType.COLOR ? (
                    <div
                      className="w-full h-full rounded-full"
                      style={{
                        backgroundColor:
                          pal.colorHex ||
                          `rgb(${(pal.data?.color?.r || 1) * 255}, ${(pal.data?.color?.g || 1) * 255}, ${(pal.data?.color?.b || 1) * 255})`,
                      }}
                    />
                  ) : (
                    <div className="w-full h-full bg-zinc-800 flex items-center justify-center text-mac-accent">
                      <Icon size={18} />
                    </div>
                  )}
                </div>

                {/* Nome Palette */}
                <span className="text-[11px] font-semibold text-zinc-200 truncate w-full">
                  {pal.name}
                </span>

                {/* Badge Tipo */}
                <span className="text-[9px] text-zinc-500 uppercase tracking-wider font-mono mt-0.5">
                  {pal.type}
                </span>

                {/* Pulsante Elimina (solo se custom, ovvero se contiene data custom) */}
                {pal.isCustom && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeletePalette?.(pal.id);
                    }}
                    title="Elimina Palette"
                    className="absolute top-1.5 right-1.5 p-1 text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {filteredPalettes.length === 0 && (
          <div className="h-32 flex flex-col items-center justify-center text-zinc-500 text-xs">
            Nessuna palette trovata in questa categoria.
          </div>
        )}
      </div>

      {/* Mini Modale Salva Nuova Palette */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-[#1e1e24] border border-[#33333f] rounded-xl w-80 p-4 space-y-4 shadow-2xl">
            <h3 className="font-bold text-white text-sm">Registra Nuova Palette</h3>
            <p className="text-[11px] text-zinc-400">
              Cattura gli attributi attuali dei {selectedIds.length > 0 ? selectedIds.length : 'tutti i'} fari in una nuova palette rapida.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] text-zinc-300 block">Nome Palette</label>
              <input
                type="text"
                value={newPalName}
                onChange={(e) => setNewPalName(e.target.value)}
                placeholder="es. Blue Strobo, Spot Cantante..."
                className="w-full bg-black/40 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white outline-none focus:border-mac-accent"
                autoFocus
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-zinc-300 block">Tipo Attributo</label>
              <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                {[
                  { id: PaletteType.COLOR, label: 'Solo Colore' },
                  { id: PaletteType.POSITION, label: 'Solo Posizione' },
                  { id: PaletteType.BEAM, label: 'Solo Beam / Gobo' },
                  { id: PaletteType.PRESET, label: 'All-In-One (Tutto)' },
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setNewPalType(t.id)}
                    className={`p-1.5 rounded border text-left font-medium transition-colors ${
                      newPalType === t.id
                        ? 'bg-mac-accent text-white border-mac-accent'
                        : 'bg-black/30 border-zinc-700 text-zinc-400 hover:text-white'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <MacButton size="sm" variant="secondary" onClick={() => setIsAddModalOpen(false)}>
                Annulla
              </MacButton>
              <MacButton size="sm" variant="primary" onClick={handleCreatePalette}>
                Salva Palette
              </MacButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
