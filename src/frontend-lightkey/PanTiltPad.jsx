import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Target, RefreshCw, Compass, ArrowUpDown, ArrowLeftRight, Sliders, Check } from 'lucide-react';
import MacButton from '../shared/components/MacButton';
import MacToggle from '../shared/components/MacToggle';

/**
 * PanTiltPad - Trackpad 2D interattivo per controllo Pan & Tilt in stile Lightkey
 * Include:
 * - Pad XY interattivo con crosshair fluido
 * - Tasti di posizionamento rapido (Centro, Palco, Pubblico, Fronte, Incrocio)
 * - Slider di precisione numerica Pan & Tilt
 * - Calibrazione hardware (Invert Pan, Invert Tilt, Swap Pan/Tilt)
 * - Limiti angolari regolabili
 */
export default function PanTiltPad({
  pan = 0.5,
  tilt = 0.5,
  calibration = { invertPan: false, invertTilt: false, swapPanTilt: false },
  limits = { panMin: 0, panMax: 1, tiltMin: 0, tiltMax: 1 },
  onChange,
  onCalibrationChange,
  onLimitsChange,
}) {
  const padRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showCalibration, setShowCalibration] = useState(false);

  // Calcola coordinate relative al pad e notifica
  const updateFromPointer = useCallback(
    (clientX, clientY) => {
      const pad = padRef.current;
      if (!pad) return;

      const rect = pad.getBoundingClientRect();
      const x = Math.max(0, Math.min(rect.width, clientX - rect.width / 2 - rect.left + rect.width / 2));
      const y = Math.max(0, Math.min(rect.height, clientY - rect.height / 2 - rect.top + rect.height / 2));

      // Normalizza 0..1 (X = Pan, Y = Tilt; Y invertito dove top = 1 o top = 0: in lighting 0 = front/down, 1 = up/back)
      // Mappiamo X: 0 (sinistra) .. 1 (destra); Y: 0 (in alto) .. 1 (in basso)
      let normPan = x / rect.width;
      let normTilt = y / rect.height;

      // Applica limiti se definiti
      if (limits) {
        normPan = Math.max(limits.panMin || 0, Math.min(limits.panMax || 1, normPan));
        normTilt = Math.max(limits.tiltMin || 0, Math.min(limits.tiltMax || 1, normTilt));
      }

      onChange?.({ pan: Number(normPan.toFixed(3)), tilt: Number(normTilt.toFixed(3)) });
    },
    [onChange, limits]
  );

  const handlePointerDown = (e) => {
    setIsDragging(true);
    updateFromPointer(e.clientX, e.clientY);
  };

  useEffect(() => {
    const handlePointerMove = (e) => {
      if (isDragging) {
        updateFromPointer(e.clientX, e.clientY);
      }
    };

    const handlePointerUp = () => {
      if (isDragging) {
        setIsDragging(false);
      }
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, updateFromPointer]);

  // Posizioni Sceniche Rapide di Lightkey
  const presets = [
    { label: 'Centro', pan: 0.5, tilt: 0.5 },
    { label: 'Palco (Giù)', pan: 0.5, tilt: 0.8 },
    { label: 'Pubblico', pan: 0.5, tilt: 0.2 },
    { label: 'Sinistra', pan: 0.2, tilt: 0.5 },
    { label: 'Destra', pan: 0.8, tilt: 0.5 },
  ];

  // Gradi Pan & Tilt reali (es. 540° Pan: -270°..+270°, 270° Tilt: -135°..+135°)
  const panDegrees = Math.round((pan - 0.5) * 540);
  const tiltDegrees = Math.round((tilt - 0.5) * 270);

  return (
    <div className="space-y-3 select-none">
      {/* 2D XY Pad */}
      <div className="relative">
        <div
          ref={padRef}
          onPointerDown={handlePointerDown}
          className="w-full h-44 bg-[#121215] rounded-lg border border-[#2d2d38] relative overflow-hidden cursor-crosshair shadow-inner"
          style={{ touchAction: 'none' }}
        >
          {/* Griglia coordinate stile radar */}
          <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 pointer-events-none opacity-20">
            {Array.from({ length: 16 }).map((_, i) => (
              <div key={i} className="border-r border-b border-zinc-500" />
            ))}
          </div>

          {/* Assi centrali tratteggiati */}
          <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-mac-accent/40 pointer-events-none" />
          <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-mac-accent/40 pointer-events-none" />

          {/* Cerchio centrale di riferimento */}
          <div className="absolute left-1/2 top-1/2 w-8 h-8 -translate-x-1/2 -translate-y-1/2 rounded-full border border-zinc-700/60 pointer-events-none" />

          {/* Cursore Crosshair Pan & Tilt */}
          <div
            className="absolute w-6 h-6 -translate-x-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center transition-transform duration-75"
            style={{
              left: `${pan * 100}%`,
              top: `${tilt * 100}%`,
            }}
          >
            {/* Alone luminoso */}
            <div className="absolute inset-0 rounded-full bg-mac-accent/30 animate-pulse" />
            {/* Mirino esterno */}
            <div className="w-5 h-5 rounded-full border-2 border-white shadow-lg bg-mac-accent/80 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-white" />
            </div>
          </div>

          {/* Etichette degli angoli nel pad */}
          <span className="absolute top-1 left-2 text-[9px] font-mono text-zinc-600 pointer-events-none">Tilt 0°</span>
          <span className="absolute bottom-1 left-2 text-[9px] font-mono text-zinc-600 pointer-events-none">Tilt 100%</span>
          <span className="absolute bottom-1 right-2 text-[9px] font-mono text-zinc-600 pointer-events-none">Pan +270°</span>
        </div>

        {/* Display Digitale Coordinate Correnti */}
        <div className="flex justify-between items-center mt-1.5 px-1 text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <span className="text-zinc-500">Pan:</span>
            <span className="text-white font-bold">{Math.round(pan * 100)}%</span>
            <span className="text-zinc-500 text-[10px]">({panDegrees > 0 ? `+${panDegrees}` : panDegrees}°)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-zinc-500">Tilt:</span>
            <span className="text-white font-bold">{Math.round(tilt * 100)}%</span>
            <span className="text-zinc-500 text-[10px]">({tiltDegrees > 0 ? `+${tiltDegrees}` : tiltDegrees}°)</span>
          </div>
        </div>
      </div>

      {/* Preset Rapidi */}
      <div className="flex items-center gap-1.5">
        {presets.map((preset) => (
          <button
            key={preset.label}
            onClick={() => onChange?.({ pan: preset.pan, tilt: preset.tilt })}
            className={`flex-1 py-1 px-1.5 text-[10px] font-medium rounded border transition-colors ${
              Math.abs(pan - preset.pan) < 0.05 && Math.abs(tilt - preset.tilt) < 0.05
                ? 'bg-mac-accent/25 border-mac-accent text-white font-semibold'
                : 'bg-black/30 border-[#2d2d38] text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Slider Fine Tuning Pan & Tilt */}
      <div className="space-y-2 bg-black/20 p-2.5 rounded-lg border border-[#2d2d34]">
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-zinc-400">
            <span className="flex items-center gap-1">
              <ArrowLeftRight size={10} className="text-mac-accent" /> Pan Fine
            </span>
            <span className="font-mono text-white">{Math.round(pan * 100)}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(pan * 100)}
            onChange={(e) => onChange?.({ pan: parseInt(e.target.value) / 100, tilt })}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-mac-accent"
          />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-zinc-400">
            <span className="flex items-center gap-1">
              <ArrowUpDown size={10} className="text-mac-accent" /> Tilt Fine
            </span>
            <span className="font-mono text-white">{Math.round(tilt * 100)}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(tilt * 100)}
            onChange={(e) => onChange?.({ pan, tilt: parseInt(e.target.value) / 100 })}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-mac-accent"
          />
        </div>
      </div>

      {/* Accordion Calibrazione & Inversione Assi Hardware */}
      <div className="border border-[#2d2d34] rounded-lg overflow-hidden bg-black/20">
        <button
          onClick={() => setShowCalibration(!showCalibration)}
          className="w-full px-2.5 py-1.5 flex items-center justify-between text-[11px] font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/40 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Sliders size={12} className="text-zinc-500" /> Calibrazione Assi & Limiti
          </span>
          <span className="text-[10px] text-zinc-500">{showCalibration ? '▲ Chiudi' : '▼ Apri'}</span>
        </button>

        {showCalibration && (
          <div className="p-2.5 border-t border-[#2d2d34] space-y-2.5 text-[11px] text-zinc-300">
            {/* Toggles Inversione */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span>Inverti Asse Pan</span>
                <MacToggle
                  checked={calibration.invertPan || false}
                  onChange={(val) => onCalibrationChange?.({ ...calibration, invertPan: val })}
                />
              </div>
              <div className="flex items-center justify-between">
                <span>Inverti Asse Tilt</span>
                <MacToggle
                  checked={calibration.invertTilt || false}
                  onChange={(val) => onCalibrationChange?.({ ...calibration, invertTilt: val })}
                />
              </div>
              <div className="flex items-center justify-between">
                <span>Inverti Pan / Tilt (Swap)</span>
                <MacToggle
                  checked={calibration.swapPanTilt || false}
                  onChange={(val) => onCalibrationChange?.({ ...calibration, swapPanTilt: val })}
                />
              </div>
            </div>

            {/* Limiti Pan & Tilt */}
            <div className="pt-2 border-t border-zinc-800/80 space-y-2">
              <div className="text-[10px] font-semibold text-zinc-400">Limiti Escursione (Range)</div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <span className="text-zinc-500">Pan Min/Max:</span>
                  <div className="flex items-center gap-1 font-mono">
                    <span>{Math.round((limits?.panMin || 0) * 100)}%</span>
                    <span>-</span>
                    <span>{Math.round((limits?.panMax || 1) * 100)}%</span>
                  </div>
                </div>
                <div>
                  <span className="text-zinc-500">Tilt Min/Max:</span>
                  <div className="flex items-center gap-1 font-mono">
                    <span>{Math.round((limits?.tiltMin || 0) * 100)}%</span>
                    <span>-</span>
                    <span>{Math.round((limits?.tiltMax || 1) * 100)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
