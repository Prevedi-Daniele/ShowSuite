import React, { useState, useEffect } from 'react';
import MacModal from '../shared/components/MacModal';
import MacButton from '../shared/components/MacButton';
import { Plus, Check, Sliders, Layers } from 'lucide-react';

export default function AddFixtureModal({
  isOpen,
  onClose,
  profiles = [],
  onAdd,
}) {
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [universe, setUniverse] = useState(1);
  const [address, setAddress] = useState(1);
  const [name, setName] = useState('');
  const [count, setCount] = useState(1);
  const [dipSwitches, setDipSwitches] = useState([]);

  useEffect(() => {
    if (profiles.length > 0 && !selectedProfileId) {
      setSelectedProfileId(profiles[0].id);
      setName(profiles[0].model);
    }
  }, [profiles, selectedProfileId]);

  useEffect(() => {
    // Calcola i dip-switch per l'indirizzo selezionato
    if (window.showsuite?.patch) {
      window.showsuite.patch.calculateDip(address).then((dips) => {
        if (dips) setDipSwitches(dips);
      });
    } else {
      // Fallback calcolo dip-switch locale
      const dips = [];
      for (let i = 0; i < 9; i++) {
        dips.push((address & (1 << i)) !== 0);
      }
      dips.push(true); // dip 10
      setDipSwitches(dips);
    }
  }, [address]);

  const handleProfileChange = (pId) => {
    setSelectedProfileId(pId);
    const prof = profiles.find((p) => p.id === pId);
    if (prof) setName(prof.model);
  };

  const handleAddSubmit = () => {
    if (!selectedProfileId) return;

    for (let i = 0; i < count; i++) {
      const fixName = count > 1 ? `${name} ${i + 1}` : name;
      onAdd({
        profileId: selectedProfileId,
        universe,
        address: address + i * 16, // offset canali approssimato
        name: fixName,
        x: 200 + i * 80,
        y: universe === 1 ? 120 : universe === 2 ? 300 : 480,
      });
    }

    onClose();
  };

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) || profiles[0];

  return (
    <MacModal
      isOpen={isOpen}
      onClose={onClose}
      title="Aggiungi Proiettore al Patch (Lightkey)"
      width="max-w-lg"
      footer={
        <>
          <MacButton variant="default" onClick={onClose}>
            Annulla
          </MacButton>
          <MacButton variant="primary" icon={Check} onClick={handleAddSubmit}>
            Aggiungi al Palco
          </MacButton>
        </>
      }
    >
      <div className="space-y-4 text-xs">
        {/* Scelta Profilo */}
        <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-2">
          <label className="block font-semibold text-zinc-200">Profilo Proiettore</label>
          <select
            value={selectedProfileId}
            onChange={(e) => handleProfileChange(e.target.value)}
            className="w-full bg-[#161619] border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white"
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.manufacturer} - {p.model} ({p.modes?.[0]?.channelCount || 1} canali)
              </option>
            ))}
          </select>

          <div>
            <label className="block text-[11px] text-zinc-400 mb-1">Nome sul Palco</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
            />
          </div>
        </div>

        {/* Assegnazione DMX */}
        <div className="p-3 bg-zinc-900/60 rounded-lg border border-zinc-800 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Universo DMX</label>
              <select
                value={universe}
                onChange={(e) => setUniverse(parseInt(e.target.value) || 1)}
                className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
              >
                <option value="1">Universo 1</option>
                <option value="2">Universo 2</option>
                <option value="3">Universo 3</option>
                <option value="4">Universo 4</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Indirizzo DMX Iniziale (1-512)</label>
              <input
                type="number"
                min="1"
                max="512"
                value={address}
                onChange={(e) => setAddress(parseInt(e.target.value) || 1)}
                className="w-full bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-zinc-400 mb-1">Numero di Fari da aggiungere in serie</label>
            <input
              type="number"
              min="1"
              max="24"
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value) || 1)}
              className="w-24 bg-[#161619] border border-zinc-700 rounded px-2 py-1 text-xs text-white"
            />
          </div>
        </div>

        {/* Calcolatore Dip-Switch Grafico (Lightkey Style) */}
        <div className="p-3 bg-zinc-900/40 rounded-lg border border-zinc-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-zinc-300">Configurazione Dip-Switch Hardware</span>
            <span className="text-[10px] text-zinc-500 font-mono">DMX {address}</span>
          </div>

          <div className="flex items-center justify-between bg-black/60 p-2.5 rounded-lg border border-zinc-800">
            {dipSwitches.map((isOn, idx) => (
              <div key={idx} className="flex flex-col items-center space-y-1">
                <span className="text-[9px] text-zinc-500 font-mono">{idx + 1}</span>
                <div
                  className={`w-3.5 h-7 rounded-sm border flex items-center justify-center transition-colors ${
                    isOn ? 'bg-mac-accent border-blue-400' : 'bg-zinc-800 border-zinc-700'
                  }`}
                >
                  <div
                    className={`w-2.5 h-3 bg-white rounded-xs transition-transform ${
                      isOn ? '-translate-y-1.5' : 'translate-y-1.5'
                    }`}
                  />
                </div>
                <span className="text-[8px] font-mono font-bold text-zinc-400">
                  {isOn ? 'ON' : '0'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </MacModal>
  );
}
