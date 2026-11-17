import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Palette, Droplet, SunMedium, Plus } from 'lucide-react';

/**
 * Converte HSB in RGB
 * Hue: 0..360, Saturation: 0..1, Brightness: 0..1
 * Ritorna { r: 0..1, g: 0..1, b: 0..1 }
 */
function hsbToRgb(h, s, b) {
  const c = b * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = b - c;
  let r = 0, g = 0, bl = 0;

  if (h >= 0 && h < 60) { r = c; g = x; bl = 0; }
  else if (h >= 60 && h < 120) { r = x; g = c; bl = 0; }
  else if (h >= 120 && h < 180) { r = 0; g = c; bl = x; }
  else if (h >= 180 && h < 240) { r = 0; g = x; bl = c; }
  else if (h >= 240 && h < 300) { r = x; g = 0; bl = c; }
  else if (h >= 300 && h < 360) { r = c; g = 0; bl = x; }

  return {
    r: Math.max(0, Math.min(1, r + m)),
    g: Math.max(0, Math.min(1, g + m)),
    b: Math.max(0, Math.min(1, bl + m)),
  };
}

/**
 * Converte RGB in HSB
 * R, G, B: 0..1
 * Ritorna { h: 0..360, s: 0..1, b: 0..1 }
 */
function rgbToHsb(r, g, b) {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  let h = 0;
  const s = max === 0 ? 0 : delta / max;
  const br = max;

  if (delta !== 0) {
    if (max === r) h = ((g - b) / delta) % 6;
    else if (max === g) h = (b - r) / delta + 2;
    else h = (r - g) / delta + 4;
    h = Math.round(h * 60);
    if (h < 0) h += 360;
  }

  return { h, s, b: br };
}

/**
 * Converte Temperatura colore Kelvin (2000K - 10000K) in RGB
 */
function kelvinToRgb(kelvin) {
  const temp = kelvin / 100;
  let red, green, blue;

  if (temp <= 66) {
    red = 255;
    green = temp;
    green = 99.4708025861 * Math.log(green) - 161.1195681661;
    if (temp <= 19) {
      blue = 0;
    } else {
      blue = temp - 10;
      blue = 138.5177312231 * Math.log(blue) - 305.0447927307;
    }
  } else {
    red = temp - 60;
    red = 329.698727446 * Math.pow(red, -0.1332047592);
    green = temp - 60;
    green = 288.1221695283 * Math.pow(green, -0.0755148492);
    blue = 255;
  }

  return {
    r: Math.max(0, Math.min(1, red / 255)),
    g: Math.max(0, Math.min(1, green / 255)),
    b: Math.max(0, Math.min(1, blue / 255)),
  };
}

// Gel Color Palette professionale da teatro e concerti
const standardGels = [
  { name: 'Open White', r: 1, g: 1, b: 1 },
  { name: 'Warm White (3200K)', r: 1, g: 0.85, b: 0.65 },
  { name: 'Cool White (6500K)', r: 0.85, g: 0.92, b: 1 },
  { name: 'Amber Gold', r: 1, g: 0.6, b: 0.1 },
  { name: 'Flame Red', r: 1, g: 0.1, b: 0.1 },
  { name: 'Rose Pink', r: 1, g: 0.3, b: 0.6 },
  { name: 'Magenta', r: 1, g: 0, b: 1 },
  { name: 'Dark Violet', r: 0.5, g: 0, b: 1 },
  { name: 'Congo Blue', r: 0.15, g: 0.1, b: 0.9 },
  { name: 'Sky Cyan', r: 0, g: 0.8, b: 1 },
  { name: 'Emerald Green', r: 0.1, g: 0.9, b: 0.2 },
  { name: 'Lime Yellow', r: 0.8, g: 1, b: 0.1 },
];

export default function ColorPickerHUD({
  color = { r: 1, g: 1, b: 1 },
  onChange,
}) {
  const satValPadRef = useRef(null);
  const [isDraggingSatVal, setIsDraggingSatVal] = useState(false);
  const [colorMode, setColorMode] = useState('hsb'); // 'hsb' | 'rgb' | 'kelvin'
  const [kelvin, setKelvin] = useState(4000);
  const [customSwatches, setCustomSwatches] = useState([]);

  // Calcola HSB interno
  const hsb = rgbToHsb(color.r || 0, color.g || 0, color.b || 0);

  // Aggiornamento Saturation & Value dal pad
  const updateSatValFromPointer = useCallback(
    (clientX, clientY) => {
      const pad = satValPadRef.current;
      if (!pad) return;
      const rect = pad.getBoundingClientRect();
      const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
      const y = Math.max(0, Math.min(rect.height, clientY - rect.top));

      const newSat = x / rect.width;
      const newBright = 1 - y / rect.height;

      const newRgb = hsbToRgb(hsb.h, newSat, newBright);
      onChange?.(newRgb);
    },
    [hsb.h, onChange]
  );

  const handlePointerDown = (e) => {
    setIsDraggingSatVal(true);
    updateSatValFromPointer(e.clientX, e.clientY);
  };

  useEffect(() => {
    const handlePointerMove = (e) => {
      if (isDraggingSatVal) updateSatValFromPointer(e.clientX, e.clientY);
    };
    const handlePointerUp = () => setIsDraggingSatVal(false);

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDraggingSatVal, updateSatValFromPointer]);

  // Gestione slider Hue
  const handleHueChange = (newHue) => {
    const newRgb = hsbToRgb(newHue, hsb.s, hsb.b);
    onChange?.(newRgb);
  };

  // Gestione slider Kelvin
  const handleKelvinChange = (k) => {
    setKelvin(k);
    const newRgb = kelvinToRgb(k);
    onChange?.(newRgb);
  };

  // Gestione slider singoli RGB
  const handleRgbChannel = (channel, val01) => {
    onChange?.({
      ...color,
      [channel]: Math.max(0, Math.min(1, val01)),
    });
  };

  // Aggiungi swatch custom
  const handleAddCustomSwatch = () => {
    if (customSwatches.length < 8) {
      setCustomSwatches((prev) => [...prev, { ...color }]);
    }
  };

  // Colore puro Hue per il pad Saturation/Brightness
  const pureHueRgb = hsbToRgb(hsb.h, 1, 1);
  const pureHueCss = `rgb(${Math.round(pureHueRgb.r * 255)}, ${Math.round(pureHueRgb.g * 255)}, ${Math.round(pureHueRgb.b * 255)})`;

  return (
    <div className="space-y-3 select-none text-xs">
      {/* Tab Switcher: HSB / RGB / Kelvin */}
      <div className="flex bg-black/40 p-0.5 rounded border border-[#2d2d38] text-[10px]">
        <button
          onClick={() => setColorMode('hsb')}
          className={`flex-1 py-1 rounded transition-colors ${
            colorMode === 'hsb' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
        >
          HSB Spettro
        </button>
        <button
          onClick={() => setColorMode('rgb')}
          className={`flex-1 py-1 rounded transition-colors ${
            colorMode === 'rgb' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
        >
          RGB Sliders
        </button>
        <button
          onClick={() => setColorMode('kelvin')}
          className={`flex-1 py-1 rounded transition-colors ${
            colorMode === 'kelvin' ? 'bg-mac-accent text-white font-semibold' : 'text-zinc-400 hover:text-white'
          }`}
        >
          Kelvin (White)
        </button>
      </div>

      {colorMode === 'hsb' && (
        <div className="space-y-3">
          {/* 2D Pad Saturazione & Luminosità con sfumatura */}
          <div
            ref={satValPadRef}
            onPointerDown={handlePointerDown}
            className="w-full h-32 rounded-lg relative overflow-hidden cursor-crosshair border border-[#2d2d38] shadow-inner"
            style={{
              backgroundColor: pureHueCss,
              touchAction: 'none',
            }}
          >
            {/* Gradiente Saturazione (bianco da sinistra a trasparente a destra) */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'linear-gradient(to right, #ffffff, transparent)',
              }}
            />
            {/* Gradiente Luminosità (nero dal basso a trasparente in alto) */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'linear-gradient(to top, #000000, transparent)',
              }}
            />

            {/* Cursore del Colore Selezionato */}
            <div
              className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow pointer-events-none"
              style={{
                left: `${hsb.s * 100}%`,
                top: `${(1 - hsb.b) * 100}%`,
                backgroundColor: `rgb(${Math.round(color.r * 255)}, ${Math.round(color.g * 255)}, ${Math.round(color.b * 255)})`,
              }}
            />
          </div>

          {/* Rainbow Hue Slider (0 - 360°) */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-zinc-400">
              <span>Tonalità (Hue)</span>
              <span className="font-mono text-white">{hsb.h}°</span>
            </div>
            <div className="relative flex items-center">
              <input
                type="range"
                min="0"
                max="359"
                value={hsb.h}
                onChange={(e) => handleHueChange(parseInt(e.target.value))}
                className="w-full h-3 rounded-full appearance-none cursor-pointer outline-none"
                style={{
                  background:
                    'linear-gradient(to right, #ff0000 0%, #ffff00 17%, #00ff00 33%, #00ffff 50%, #0000ff 67%, #ff00ff 83%, #ff0000 100%)',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {colorMode === 'rgb' && (
        <div className="space-y-2.5 bg-black/30 p-2.5 rounded-lg border border-[#2d2d38]">
          {/* Red Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-red-400 font-semibold">Rosso (R)</span>
              <span className="font-mono text-white">{Math.round((color.r || 0) * 255)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="255"
              value={Math.round((color.r || 0) * 255)}
              onChange={(e) => handleRgbChannel('r', parseInt(e.target.value) / 255)}
              className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-red-500"
            />
          </div>

          {/* Green Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-emerald-400 font-semibold">Verde (G)</span>
              <span className="font-mono text-white">{Math.round((color.g || 0) * 255)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="255"
              value={Math.round((color.g || 0) * 255)}
              onChange={(e) => handleRgbChannel('g', parseInt(e.target.value) / 255)}
              className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-emerald-500"
            />
          </div>

          {/* Blue Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-blue-400 font-semibold">Blu (B)</span>
              <span className="font-mono text-white">{Math.round((color.b || 0) * 255)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="255"
              value={Math.round((color.b || 0) * 255)}
              onChange={(e) => handleRgbChannel('b', parseInt(e.target.value) / 255)}
              className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-blue-500"
            />
          </div>
        </div>
      )}

      {colorMode === 'kelvin' && (
        <div className="space-y-3 bg-black/30 p-2.5 rounded-lg border border-[#2d2d38]">
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-zinc-400">
              <span className="flex items-center gap-1">
                <SunMedium size={11} className="text-amber-400" /> Temperatura Kelvin
              </span>
              <span className="font-mono text-white font-bold">{kelvin} K</span>
            </div>
            <input
              type="range"
              min="2400"
              max="8000"
              step="50"
              value={kelvin}
              onChange={(e) => handleKelvinChange(parseInt(e.target.value))}
              className="w-full h-2.5 rounded appearance-none cursor-pointer"
              style={{
                background: 'linear-gradient(to right, #ff8912 0%, #ffe4b5 40%, #ffffff 70%, #cae4ff 100%)',
              }}
            />
            <div className="flex justify-between text-[9px] text-zinc-500 pt-0.5">
              <span>2400K (Caldo)</span>
              <span>4000K (Neutro)</span>
              <span>8000K (Freddo)</span>
            </div>
          </div>
        </div>
      )}

      {/* Palette Gelatin / Swatch Rapidi */}
      <div className="space-y-1.5 pt-1">
        <div className="flex justify-between items-center text-[10px] text-zinc-400">
          <span>Palette Predefinita</span>
          <button
            onClick={handleAddCustomSwatch}
            title="Salva colore attuale nei preferiti"
            className="flex items-center gap-1 text-[9px] text-mac-accent hover:underline"
          >
            <Plus size={10} /> Salva
          </button>
        </div>

        {/* Griglia Colori Standard */}
        <div className="grid grid-cols-6 gap-1.5">
          {standardGels.map((gel, idx) => {
            const isCurrent =
              Math.abs(color.r - gel.r) < 0.05 &&
              Math.abs(color.g - gel.g) < 0.05 &&
              Math.abs(color.b - gel.b) < 0.05;

            return (
              <button
                key={idx}
                onClick={() => onChange?.({ r: gel.r, g: gel.g, b: gel.b })}
                title={gel.name}
                className={`h-6 rounded border transition-all ${
                  isCurrent
                    ? 'ring-2 ring-white scale-105 z-10 border-transparent'
                    : 'border-white/10 hover:scale-105'
                }`}
                style={{
                  backgroundColor: `rgb(${Math.round(gel.r * 255)}, ${Math.round(gel.g * 255)}, ${Math.round(gel.b * 255)})`,
                }}
              />
            );
          })}
        </div>

        {/* Swatch Personalizzati Salvati dall'utente */}
        {customSwatches.length > 0 && (
          <div className="pt-2 border-t border-[#2d2d38] space-y-1">
            <span className="text-[10px] text-zinc-500 block">Personalizzati</span>
            <div className="flex gap-1.5">
              {customSwatches.map((sw, idx) => (
                <button
                  key={idx}
                  onClick={() => onChange?.(sw)}
                  className="w-6 h-6 rounded border border-white/20 hover:scale-110 transition-transform"
                  style={{
                    backgroundColor: `rgb(${Math.round(sw.r * 255)}, ${Math.round(sw.g * 255)}, ${Math.round(sw.b * 255)})`,
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
