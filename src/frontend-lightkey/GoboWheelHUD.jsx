import React from 'react';
import { RotateCw, RotateCcw, Pause, Sparkles, Circle } from 'lucide-react';

// Catalogo Gobo con rendering SVG vettoriale stile Lightkey
export const goboCatalog = [
  {
    id: 0,
    name: 'Open (Aperto)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <circle cx="20" cy="20" r="14" fill="#ffffff" />
      </svg>
    ),
  },
  {
    id: 1,
    name: 'Punti (Dots Matrix)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <circle cx="20" cy="12" r="3" fill="#ffffff" />
        <circle cx="12" cy="20" r="3" fill="#ffffff" />
        <circle cx="28" cy="20" r="3" fill="#ffffff" />
        <circle cx="20" cy="28" r="3" fill="#ffffff" />
        <circle cx="20" cy="20" r="4" fill="#ffffff" />
      </svg>
    ),
  },
  {
    id: 2,
    name: 'Starburst (Raggi)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <circle cx="20" cy="20" r="3" fill="#ffffff" />
        {Array.from({ length: 8 }).map((_, i) => (
          <line
            key={i}
            x1="20"
            y1="20"
            x2={20 + Math.cos((i * Math.PI) / 4) * 14}
            y2={20 + Math.sin((i * Math.PI) / 4) * 14}
            stroke="#ffffff"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        ))}
      </svg>
    ),
  },
  {
    id: 3,
    name: 'Barre Lineari (Bars)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <line x1="12" y1="10" x2="12" y2="30" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" />
        <line x1="20" y1="8" x2="20" y2="32" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" />
        <line x1="28" y1="10" x2="28" y2="30" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 4,
    name: 'Triangolo (Prism Ray)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <polygon points="20,8 32,30 8,30" fill="none" stroke="#ffffff" strokeWidth="3" strokeLinejoin="round" />
        <circle cx="20" cy="22" r="3" fill="#ffffff" />
      </svg>
    ),
  },
  {
    id: 5,
    name: 'Breakup (Fogliame / Nuvoloso)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <circle cx="15" cy="15" r="4" fill="#ffffff" />
        <circle cx="25" cy="14" r="5" fill="#ffffff" />
        <circle cx="26" cy="25" r="4.5" fill="#ffffff" />
        <circle cx="16" cy="26" r="3.5" fill="#ffffff" />
        <circle cx="20" cy="20" r="3" fill="#ffffff" />
      </svg>
    ),
  },
  {
    id: 6,
    name: 'Spirale (Vortex)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <path
          d="M 20 20 m -10 0 a 10 10 0 1 0 20 0 a 7 7 0 1 0 -14 0 a 4 4 0 1 0 8 0"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    id: 7,
    name: 'Finestre (Cathedral)',
    svg: (
      <svg viewBox="0 0 40 40" className="w-full h-full">
        <rect x="10" y="10" width="8" height="8" rx="2" fill="#ffffff" />
        <rect x="22" y="10" width="8" height="8" rx="2" fill="#ffffff" />
        <rect x="10" y="22" width="8" height="8" rx="2" fill="#ffffff" />
        <rect x="22" y="22" width="8" height="8" rx="2" fill="#ffffff" />
      </svg>
    ),
  },
];

export default function GoboWheelHUD({
  gobo = 0,
  goboRotate = 0, // -100..+100 (negativo = CCW, 0 = fermo, positivo = CW)
  prism = 0,      // 0 = Off, 1 = 3-Facet, 2 = 8-Facet, 3 = Linear
  prismRotate = 0,
  onChange,
}) {
  const currentGoboIndex = Math.min(goboCatalog.length - 1, Math.max(0, Math.round(gobo * (goboCatalog.length - 1))));

  const handleSelectGobo = (index) => {
    // Normalizza a 0..1 per il canale DMX
    const val = index / (goboCatalog.length - 1);
    onChange?.({ gobo: Number(val.toFixed(3)) });
  };

  const handleRotateMode = (direction) => {
    // direction: 'stop' (0) | 'cw' (0.5) | 'ccw' (-0.5)
    let speed = 0;
    if (direction === 'cw') speed = 0.5;
    if (direction === 'ccw') speed = -0.5;
    onChange?.({ goboRotate: speed });
  };

  const handlePrismToggle = (prismIndex) => {
    onChange?.({ prism: prismIndex });
  };

  return (
    <div className="space-y-4 select-none text-xs">
      {/* 1. Ruota Gobo Grafica */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-[10px] text-zinc-400">
          <span className="font-semibold text-zinc-300">Ruota Gobo Vettoriale</span>
          <span className="font-mono text-mac-accent">{goboCatalog[currentGoboIndex].name}</span>
        </div>

        {/* Carousel orizzontale dei gobo */}
        <div className="grid grid-cols-4 gap-2 bg-black/30 p-2 rounded-lg border border-[#2d2d38]">
          {goboCatalog.map((item, idx) => {
            const isSelected = idx === currentGoboIndex;
            return (
              <button
                key={item.id}
                onClick={() => handleSelectGobo(idx)}
                title={item.name}
                className={`p-1.5 rounded-lg flex flex-col items-center justify-center transition-all ${
                  isSelected
                    ? 'bg-mac-accent/30 border-2 border-mac-accent shadow-md scale-105'
                    : 'bg-black/40 border border-zinc-800 hover:border-zinc-600 hover:bg-zinc-800/40'
                }`}
              >
                <div className="w-8 h-8 rounded-full bg-black/80 p-1 flex items-center justify-center border border-zinc-700">
                  {item.svg}
                </div>
                <span className="text-[9px] mt-1 text-zinc-400 truncate max-w-full">
                  {idx === 0 ? 'Aperto' : `Gobo ${idx}`}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Rotazione Gobo (Direzione e Velocità) */}
      <div className="space-y-2 bg-black/20 p-2.5 rounded-lg border border-[#2d2d38]">
        <div className="flex justify-between text-[10px] text-zinc-400">
          <span className="flex items-center gap-1 font-semibold text-zinc-300">
            <RotateCw size={11} className="text-mac-accent" /> Rotazione Gobo
          </span>
          <span className="font-mono text-white">
            {goboRotate === 0
              ? 'Fermo'
              : goboRotate > 0
              ? `Orario +${Math.round(goboRotate * 100)}%`
              : `Antiorario ${Math.round(goboRotate * 100)}%`}
          </span>
        </div>

        {/* Tasti Rapidi Direzione */}
        <div className="flex gap-1 text-[10px]">
          <button
            onClick={() => handleRotateMode('ccw')}
            className={`flex-1 py-1 rounded border flex items-center justify-center gap-1 ${
              goboRotate < 0
                ? 'bg-mac-accent text-white font-semibold border-mac-accent'
                : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
            }`}
          >
            <RotateCcw size={11} /> CCW
          </button>
          <button
            onClick={() => handleRotateMode('stop')}
            className={`flex-1 py-1 rounded border flex items-center justify-center gap-1 ${
              goboRotate === 0
                ? 'bg-zinc-700 text-white font-semibold border-zinc-600'
                : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
            }`}
          >
            <Pause size={11} /> Stop
          </button>
          <button
            onClick={() => handleRotateMode('cw')}
            className={`flex-1 py-1 rounded border flex items-center justify-center gap-1 ${
              goboRotate > 0
                ? 'bg-mac-accent text-white font-semibold border-mac-accent'
                : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
            }`}
          >
            <RotateCw size={11} /> CW
          </button>
        </div>

        {/* Slider Velocità Rotazione */}
        <input
          type="range"
          min="-100"
          max="100"
          value={Math.round((goboRotate || 0) * 100)}
          onChange={(e) => onChange?.({ goboRotate: parseInt(e.target.value) / 100 })}
          className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
        />
      </div>

      {/* 3. Controllo Prisma Ottico */}
      <div className="space-y-2 bg-black/20 p-2.5 rounded-lg border border-[#2d2d38]">
        <div className="flex justify-between text-[10px] text-zinc-400">
          <span className="flex items-center gap-1 font-semibold text-zinc-300">
            <Sparkles size={11} className="text-amber-400" /> Prisma Ottico
          </span>
          <span className="font-mono text-white">
            {prism === 0 ? 'Disattivato' : prism === 1 ? '3 Facce' : prism === 2 ? '8 Facce' : 'Lineare'}
          </span>
        </div>

        {/* Opzioni Prisma */}
        <div className="grid grid-cols-4 gap-1 text-[10px]">
          {[
            { id: 0, label: 'Off' },
            { id: 1, label: '3 Facce' },
            { id: 2, label: '8 Facce' },
            { id: 3, label: 'Lineare' },
          ].map((opt) => (
            <button
              key={opt.id}
              onClick={() => handlePrismToggle(opt.id)}
              className={`py-1 rounded border transition-colors ${
                prism === opt.id
                  ? 'bg-amber-500/30 border-amber-500 text-amber-200 font-semibold'
                  : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
