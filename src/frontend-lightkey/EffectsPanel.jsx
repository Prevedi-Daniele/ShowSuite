import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  WaveformType,
  MotionShape,
  PhaseDistribution,
  MusicalDivision,
  EffectAttribute,
} from '../core/effects/index.js';
import {
  Zap, Play, Pause, Circle, RotateCw, Infinity, ArrowLeftRight,
  Music, Clock, Layers, Plus, Trash2, SlidersHorizontal, Radio, Wand2,
} from 'lucide-react';
import MacButton from '../shared/components/MacButton';

// Miniatura canvas della forma d'onda
function WaveformPreview({ type, options = {}, width = 80, height = 32, color = '#0a84ff' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;

    const steps = width;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const phase = t;
      let val = 0;

      switch (type) {
        case WaveformType.SINE:
          val = 0.5 + 0.5 * Math.sin(2 * Math.PI * phase - Math.PI / 2);
          break;
        case WaveformType.SAWTOOTH:
          val = 1 - phase;
          break;
        case WaveformType.RAMP:
          val = phase;
          break;
        case WaveformType.SQUARE:
          val = phase < (options.dutyCycle || 0.5) ? 1.0 : 0.0;
          break;
        case WaveformType.TRIANGLE:
          val = phase < 0.5 ? phase * 2 : 2 - phase * 2;
          break;
        default:
          val = phase;
      }

      const x = i;
      const y = (1 - val) * (height - 4) + 2;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }, [type, options, width, height, color]);

  return <canvas ref={canvasRef} width={width} height={height} className="rounded" />;
}

// Miniatura canvas della traiettoria di movimento
function MotionPreview({ shape, size = { x: 0.3, y: 0.3 }, width = 48, height = 48, color = '#0a84ff' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    // Sfondo cerchio palco
    ctx.fillStyle = '#111115';
    ctx.fillRect(0, 0, width, height);

    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;

    const cx = width / 2;
    const cy = height / 2;
    const sx = size.x * width * 0.9;
    const sy = size.y * height * 0.9;
    const steps = 80;

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const angle = t * 2 * Math.PI;
      let lx = 0, ly = 0;

      switch (shape) {
        case MotionShape.CIRCLE:
          lx = Math.cos(angle) * sx;
          ly = Math.sin(angle) * sy;
          break;
        case MotionShape.FIGURE_EIGHT:
          lx = Math.sin(angle) * sx;
          ly = Math.sin(2 * angle) * 0.5 * sy;
          break;
        case MotionShape.SPIRAL: {
          const r = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(angle * 0.5));
          lx = Math.cos(angle) * sx * r;
          ly = Math.sin(angle) * sy * r;
          break;
        }
        case MotionShape.LINEAR:
          lx = Math.sin(angle) * sx;
          ly = 0;
          break;
        default:
          lx = Math.cos(angle) * sx;
          ly = Math.sin(angle) * sy;
      }

      const px = cx + lx;
      const py = cy + ly;
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.stroke();
  }, [shape, size, width, height, color]);

  return <canvas ref={canvasRef} width={width} height={height} className="rounded border border-zinc-800/60" />;
}

const DIVISION_LABELS = {
  [MusicalDivision.DIV_1_16]: '1/16',
  [MusicalDivision.DIV_1_8]: '1/8',
  [MusicalDivision.DIV_1_4]: '1/4',
  [MusicalDivision.DIV_1_2]: '1/2',
  [MusicalDivision.DIV_1_1]: '1 Bar',
  [MusicalDivision.DIV_2_1]: '2 Bar',
  [MusicalDivision.DIV_4_1]: '4 Bar',
};

const WAVEFORM_LABELS = {
  [WaveformType.SINE]: 'Sinusoide',
  [WaveformType.SAWTOOTH]: 'Sawtooth',
  [WaveformType.RAMP]: 'Rampa',
  [WaveformType.SQUARE]: 'Quadra',
  [WaveformType.TRIANGLE]: 'Triangolare',
  [WaveformType.BEZIER]: 'Bézier Custom',
};

const MOTION_LABELS = {
  [MotionShape.CIRCLE]: 'Cerchio / Ellisse',
  [MotionShape.FIGURE_EIGHT]: 'Figura a 8',
  [MotionShape.SPIRAL]: 'Spirale',
  [MotionShape.LINEAR]: 'Lineare',
};

const ATTRIBUTE_LABELS = {
  [EffectAttribute.PAN_TILT]: 'Pan / Tilt',
  [EffectAttribute.INTENSITY]: 'Dimmer',
  [EffectAttribute.COLOR_HUE]: 'Colore (Hue)',
  [EffectAttribute.ZOOM]: 'Zoom',
};

export default function EffectsPanel({
  effectsEngine,
  bpm = 120,
  onBpmChange,
  onTapTempo,
  onToggleEffect,
  onAddEffect,
  onRemoveEffect,
  onUpdateEffect,
}) {
  const [effects, setEffects] = useState(() => effectsEngine?.effects || []);
  const [selectedEffectId, setSelectedEffectId] = useState(null);
  const [isBeatPulse, setIsBeatPulse] = useState(false);

  // Aggiorna lista effetti dal motore
  const refreshEffects = useCallback(() => {
    if (effectsEngine) setEffects([...effectsEngine.effects]);
  }, [effectsEngine]);

  // Animazione pulse sul beat
  useEffect(() => {
    if (!effectsEngine) return;
    let frameId;
    const checkBeat = () => {
      if (effectsEngine.clock.checkBeatPulse()) {
        setIsBeatPulse(true);
        setTimeout(() => setIsBeatPulse(false), 90);
      }
      frameId = requestAnimationFrame(checkBeat);
    };
    frameId = requestAnimationFrame(checkBeat);
    return () => cancelAnimationFrame(frameId);
  }, [effectsEngine]);

  const selectedEffect = effects.find((e) => e.id === selectedEffectId) || null;

  const handleToggle = (id) => {
    onToggleEffect?.(id);
    refreshEffects();
  };

  const handleUpdateField = (field, value) => {
    if (!selectedEffect) return;
    onUpdateEffect?.(selectedEffect.id, { [field]: value });
    refreshEffects();
  };

  return (
    <div className="flex flex-col h-full bg-[#17171b] text-zinc-300 select-none overflow-hidden">

      {/* Top: BPM Master + Tap Tempo */}
      <div className="h-14 bg-[#1e1e24] border-b border-[#2d2d38] px-4 flex items-center gap-6 flex-shrink-0">
        {/* Beat Pulse Indicator */}
        <div className="flex items-center gap-3">
          <div
            className={`w-4 h-4 rounded-full border-2 transition-all duration-75 ${
              isBeatPulse
                ? 'bg-mac-accent border-mac-accent scale-110 shadow-lg shadow-mac-accent/60'
                : 'bg-transparent border-zinc-600'
            }`}
          />
          <div className="flex flex-col">
            <span className="text-[9px] text-zinc-500 uppercase font-mono tracking-widest">Master BPM</span>
            <span className={`font-mono font-black text-xl leading-none ${isBeatPulse ? 'text-mac-accent' : 'text-white'}`}>
              {bpm.toFixed(1)}
            </span>
          </div>
        </div>

        {/* BPM Slider */}
        <div className="flex-1 max-w-48">
          <input
            type="range"
            min="40"
            max="300"
            step="0.5"
            value={bpm}
            onChange={(e) => onBpmChange?.(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
          />
        </div>

        {/* Tap Tempo Button */}
        <button
          onClick={() => { onTapTempo?.(); refreshEffects(); }}
          className="h-10 px-5 rounded-lg bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 hover:border-mac-accent text-white font-bold text-sm active:scale-95 transition-all"
        >
          TAP
        </button>

        {/* BPM Preset Buttons */}
        <div className="flex gap-1">
          {[90, 120, 128, 140].map((preset) => (
            <button
              key={preset}
              onClick={() => onBpmChange?.(preset)}
              className={`px-2 py-1 rounded text-[10px] font-mono border transition-colors ${
                Math.abs(bpm - preset) < 0.5
                  ? 'bg-mac-accent/30 border-mac-accent text-mac-accent font-bold'
                  : 'bg-black/30 border-zinc-800 text-zinc-400 hover:text-white'
              }`}
            >
              {preset}
            </button>
          ))}
        </div>

        {/* Add Effect Button */}
        <MacButton
          variant="toolbar"
          size="sm"
          icon={Plus}
          onClick={() => { onAddEffect?.(); refreshEffects(); }}
        >
          Nuovo Effetto
        </MacButton>
      </div>

      {/* Main Area: Effect List (left) + Editor (right) */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left: Effect List */}
        <div className="w-56 bg-[#15151a] border-r border-[#2d2d38] flex flex-col overflow-y-auto flex-shrink-0">
          {effects.length === 0 && (
            <div className="p-4 text-[11px] text-zinc-500 text-center mt-4">
              Nessun effetto programmato. Usa "+ Nuovo Effetto" per iniziare.
            </div>
          )}
          {effects.map((fx) => {
            const isSelected = fx.id === selectedEffectId;
            const isPanTilt = fx.attribute === EffectAttribute.PAN_TILT;

            return (
              <div
                key={fx.id}
                onClick={() => setSelectedEffectId(fx.id)}
                className={`group px-3 py-2.5 flex items-center gap-2.5 cursor-pointer border-b border-[#22222a] transition-colors ${
                  isSelected ? 'bg-mac-accent/15 border-l-2 border-l-mac-accent' : 'hover:bg-zinc-800/40'
                }`}
              >
                {/* Enable/Disable Toggle Dot */}
                <button
                  onClick={(e) => { e.stopPropagation(); handleToggle(fx.id); }}
                  className={`w-3 h-3 rounded-full border flex-shrink-0 transition-colors ${
                    fx.enabled
                      ? 'bg-mac-accent border-mac-accent shadow-sm shadow-mac-accent/50'
                      : 'bg-transparent border-zinc-600 hover:border-zinc-400'
                  }`}
                />

                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-semibold text-zinc-200 truncate">{fx.name}</div>
                  <div className="text-[9px] text-zinc-500 font-mono">
                    {ATTRIBUTE_LABELS[fx.attribute]} · {DIVISION_LABELS[fx.division]}
                  </div>
                </div>

                {/* Mini Preview */}
                {isPanTilt ? (
                  <MotionPreview shape={fx.motionShape} size={fx.motionSize} width={28} height={28}
                    color={fx.enabled ? '#0a84ff' : '#3f3f4a'} />
                ) : (
                  <WaveformPreview type={fx.waveform} width={36} height={22}
                    color={fx.enabled ? '#0a84ff' : '#3f3f4a'} />
                )}
              </div>
            );
          })}
        </div>

        {/* Right: Effect Editor */}
        {selectedEffect ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-5">

            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <div className="font-bold text-white text-sm">{selectedEffect.name}</div>
                <div className="text-[11px] text-zinc-500">
                  {ATTRIBUTE_LABELS[selectedEffect.attribute]}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggle(selectedEffect.id)}
                  className={`px-3 py-1 rounded text-[11px] font-semibold border transition-colors ${
                    selectedEffect.enabled
                      ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
                      : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-white'
                  }`}
                >
                  {selectedEffect.enabled ? '● Attivo' : '○ Disattivo'}
                </button>
                <button
                  onClick={() => { onRemoveEffect?.(selectedEffect.id); setSelectedEffectId(null); refreshEffects(); }}
                  className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>

            {/* 1. Attribute Target */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
                Attributo Target
              </label>
              <div className="grid grid-cols-4 gap-1 text-[11px]">
                {Object.entries(ATTRIBUTE_LABELS).map(([attr, label]) => (
                  <button
                    key={attr}
                    onClick={() => handleUpdateField('attribute', attr)}
                    className={`py-1.5 rounded border transition-colors ${
                      selectedEffect.attribute === attr
                        ? 'bg-mac-accent text-white font-semibold border-mac-accent'
                        : 'bg-black/30 text-zinc-400 border-zinc-800 hover:text-white'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Motion Shape (solo se PAN_TILT) */}
            {selectedEffect.attribute === EffectAttribute.PAN_TILT && (
              <div className="space-y-3 bg-black/25 p-3 rounded-lg border border-[#2d2d38]">
                <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
                  Forma Traiettoria
                </label>

                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(MOTION_LABELS).map(([shape, label]) => (
                    <button
                      key={shape}
                      onClick={() => handleUpdateField('motionShape', shape)}
                      className={`flex flex-col items-center gap-1 p-2 rounded border transition-colors ${
                        selectedEffect.motionShape === shape
                          ? 'bg-mac-accent/20 border-mac-accent'
                          : 'bg-black/30 border-zinc-800 hover:border-zinc-600'
                      }`}
                    >
                      <MotionPreview shape={shape} width={42} height={42}
                        color={selectedEffect.motionShape === shape ? '#0a84ff' : '#4a4a5a'} />
                      <span className="text-[9px] text-zinc-400 text-center leading-tight">{label}</span>
                    </button>
                  ))}
                </div>

                {/* Dimensioni e rotazione */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Ampiezza X (Pan)', field: 'motionSize', sub: 'x', value: selectedEffect.motionSize?.x || 0.25, min: 0.01, max: 0.5 },
                    { label: 'Ampiezza Y (Tilt)', field: 'motionSize', sub: 'y', value: selectedEffect.motionSize?.y || 0.25, min: 0.01, max: 0.5 },
                    { label: 'Rotazione Piano', field: 'motionRotation', value: selectedEffect.motionRotation || 0, min: -180, max: 180 },
                  ].map((ctrl) => (
                    <div key={ctrl.label} className="space-y-1">
                      <div className="flex justify-between text-[10px] text-zinc-400">
                        <span>{ctrl.label}</span>
                        <span className="font-mono text-white">
                          {ctrl.field === 'motionRotation'
                            ? `${ctrl.value}°`
                            : `${Math.round(ctrl.value * 100)}%`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={ctrl.min * (ctrl.sub ? 100 : 1)}
                        max={ctrl.max * (ctrl.sub ? 100 : 1)}
                        value={ctrl.value * (ctrl.sub ? 100 : 1)}
                        onChange={(e) => {
                          const v = parseFloat(e.target.value) / (ctrl.sub ? 100 : 1);
                          if (ctrl.sub) {
                            handleUpdateField(ctrl.field, {
                              ...selectedEffect.motionSize,
                              [ctrl.sub]: v,
                            });
                          } else {
                            handleUpdateField(ctrl.field, v);
                          }
                        }}
                        className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. Waveform (canali scalari) */}
            {selectedEffect.attribute !== EffectAttribute.PAN_TILT && (
              <div className="space-y-3 bg-black/25 p-3 rounded-lg border border-[#2d2d38]">
                <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
                  Forma d'Onda
                </label>

                <div className="grid grid-cols-3 gap-1.5">
                  {Object.entries(WAVEFORM_LABELS).map(([wave, label]) => (
                    <button
                      key={wave}
                      onClick={() => handleUpdateField('waveform', wave)}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded border text-[10px] transition-colors ${
                        selectedEffect.waveform === wave
                          ? 'bg-mac-accent/20 border-mac-accent text-white font-semibold'
                          : 'bg-black/30 border-zinc-800 text-zinc-400 hover:text-white'
                      }`}
                    >
                      <WaveformPreview type={wave} width={36} height={18}
                        color={selectedEffect.waveform === wave ? '#0a84ff' : '#4a4a5a'} />
                      <span className="truncate">{label}</span>
                    </button>
                  ))}
                </div>

                {/* Profondità e Offset */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] text-zinc-400">
                      <span>Profondità (Depth)</span>
                      <span className="font-mono text-white">{Math.round((selectedEffect.depth || 1) * 100)}%</span>
                    </div>
                    <input
                      type="range" min="0" max="100"
                      value={Math.round((selectedEffect.depth || 1) * 100)}
                      onChange={(e) => handleUpdateField('depth', parseInt(e.target.value) / 100)}
                      className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                    />
                  </div>
                  {selectedEffect.waveform === WaveformType.SQUARE && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-zinc-400">
                        <span>Duty Cycle</span>
                        <span className="font-mono text-white">
                          {Math.round(((selectedEffect.waveformOptions?.dutyCycle) || 0.5) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range" min="5" max="95"
                        value={Math.round(((selectedEffect.waveformOptions?.dutyCycle) || 0.5) * 100)}
                        onChange={(e) => handleUpdateField('waveformOptions', {
                          ...selectedEffect.waveformOptions,
                          dutyCycle: parseInt(e.target.value) / 100,
                        })}
                        className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-amber-400"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 4. Timing & Fanning Temporale */}
            <div className="space-y-3 bg-black/25 p-3 rounded-lg border border-[#2d2d38]">
              <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
                Timing Musicale & Fanning d'Onda
              </label>

              {/* Divisione musicale */}
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500">Durata Ciclo (Suddivisione Musicale)</span>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(DIVISION_LABELS).map(([div, label]) => (
                    <button
                      key={div}
                      onClick={() => handleUpdateField('division', div)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-colors ${
                        selectedEffect.division === div
                          ? 'bg-mac-accent text-white font-bold border-mac-accent'
                          : 'bg-black/40 text-zinc-400 border-zinc-800 hover:text-white'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Phase Spread */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-400">
                  <span>Sfasamento tra Fari (Phase Spread)</span>
                  <span className="font-mono text-white">{selectedEffect.phaseSpread}°</span>
                </div>
                <input
                  type="range" min="0" max="360"
                  value={selectedEffect.phaseSpread}
                  onChange={(e) => handleUpdateField('phaseSpread', parseInt(e.target.value))}
                  className="w-full h-1.5 bg-zinc-800 rounded appearance-none cursor-pointer accent-mac-accent"
                />
                <div className="flex justify-between text-[9px] text-zinc-600 font-mono">
                  <span>0° (Sync)</span><span>90°</span><span>180° (Opposti)</span><span>360° (Onda)</span>
                </div>
              </div>

              {/* Distribuzione fasi */}
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500">Distribuzione Fase tra Fari</span>
                <div className="grid grid-cols-4 gap-1 text-[10px]">
                  {[
                    { id: PhaseDistribution.LINEAR, label: 'Lineare' },
                    { id: PhaseDistribution.SYMMETRIC, label: 'Simmetrico' },
                    { id: PhaseDistribution.ODD_EVEN, label: 'Pari/Dispari' },
                    { id: PhaseDistribution.RANDOM, label: 'Casuale' },
                  ].map((d) => (
                    <button
                      key={d.id}
                      onClick={() => handleUpdateField('distribution', d.id)}
                      className={`py-1 rounded border transition-colors ${
                        selectedEffect.distribution === d.id
                          ? 'bg-mac-accent/30 border-mac-accent text-mac-accent font-semibold'
                          : 'bg-black/30 text-zinc-400 border-zinc-800 hover:text-white'
                      }`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 p-8 text-center gap-3">
            <Wand2 size={30} className="text-zinc-700" />
            <p className="text-xs font-medium text-zinc-400">Nessun effetto selezionato</p>
            <p className="text-[11px] text-zinc-600">
              Seleziona un effetto dalla lista o usa "+ Nuovo Effetto" per aggiungerne uno. Tutti gli effetti sono sincronizzati al clock BPM master.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
