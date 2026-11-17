/**
 * StageGeometryEditor.jsx — Editor di Stage e Geometria per ShowSuite / QLab 5 (STEP 6.2)
 * 
 * Funzionalità:
 * 1. Corner Pinning / Keystone — Correzione prospettica a 4 punti con drag interattivo sui vertici
 * 2. Surface Warping — Griglia Bézier NxM di punti di controllo deformabili via drag & drop
 * 3. Edge Blending — Maschere di dissolvenza per proiezioni continue affiancate con gamma curve
 * 4. Test Pattern — Grid, Cerchi, SMPTE Color Bars, Checkerboard, Crosshair, White Uniformity
 * 5. Screen Mappings — Gestione visiva dei mapping su display fisici multipli
 * 
 * Layout: 2 pannelli
 *   Sinistra: Canvas preview interattivo dello Stage con overlay geometria
 *   Destra:  Pannello di controllo a tab (Correzione | Surface Warp | Edge Blend | Test Pattern | Display)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { VideoStage, VideoEngine, StageGeometry, TestPatternType } from '../core/qlab/index.js';
import {
  Move,
  Grid3x3,
  Layers,
  Monitor,
  Sliders,
  RefreshCw,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronRight,
  Maximize2,
  RotateCcw,
  Copy,
  CheckSquare,
  Square,
} from 'lucide-react';

// ====================================================================================
// Costanti
// ====================================================================================

const CORNER_LABELS = ['TL', 'TR', 'BR', 'BL'];
const CORNER_COLORS = ['#ff453a', '#ffd60a', '#30d158', '#0a84ff'];

const TABS = [
  { id: 'keystone', label: 'Corner Pin', icon: Move },
  { id: 'warp', label: 'Surface Warp', icon: Grid3x3 },
  { id: 'blend', label: 'Edge Blend', icon: Layers },
  { id: 'pattern', label: 'Test Pattern', icon: Monitor },
  { id: 'display', label: 'Display', icon: Sliders },
];

const TEST_PATTERNS = [
  { id: TestPatternType.NONE, label: 'Nessuno', desc: 'Output live normale' },
  { id: TestPatternType.GRID, label: 'Griglia Allineamento', desc: 'Linee guida e assi ortogonali' },
  { id: TestPatternType.CIRCLES, label: 'Cerchi & Convergenza', desc: 'Cerchi concentrici per aspect ratio' },
  { id: TestPatternType.COLOR_BARS, label: 'SMPTE Color Bars', desc: 'Barre colore standard broadcast' },
  { id: TestPatternType.CHECKERBOARD, label: 'Scacchiera', desc: 'Pattern 64px per uniformità' },
  { id: TestPatternType.CROSSHAIR, label: 'Crosshair', desc: 'Mirino centrale per allineamento' },
  { id: TestPatternType.WHITE_UNIFORMITY, label: 'Bianco Uniforme', desc: 'Verifica uniformità luminosità' },
];

// ====================================================================================
// Componenti UI Helper
// ====================================================================================

function MacSlider({ label, value, min, max, step = 0.01, unit = '', onChange, disabled = false }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span className="font-mono text-zinc-200">{typeof value === 'number' ? value.toFixed(step < 0.1 ? 2 : 0) : value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-zinc-700 rounded-full appearance-none accent-blue-500 disabled:opacity-40 cursor-pointer"
      />
    </div>
  );
}

function ToggleSwitch({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        className={`relative w-9 h-5 rounded-full transition-colors ${checked ? 'bg-blue-500' : 'bg-zinc-600'}`}
        onClick={() => onChange(!checked)}
      >
        <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-4' : ''}`} />
      </div>
      {label && <span className="text-xs text-zinc-300">{label}</span>}
    </label>
  );
}

function SectionHeader({ label, icon: Icon }) {
  return (
    <div className="flex items-center gap-2 pb-2 border-b border-zinc-700/60 mb-3">
      {Icon && <Icon size={13} className="text-blue-400" />}
      <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">{label}</span>
    </div>
  );
}

// ====================================================================================
// Canvas Interattivo — Overlay Corner Pin + Mesh Warp
// ====================================================================================

function GeometryCanvas({ stage, geometry, selectedMapping, activeTab, onDragCorner, onDragMeshPoint }) {
  const canvasRef = useRef(null);
  const [dragging, setDragging] = useState(null); // { type: 'corner'|'mesh', idx, r, c }
  const [hovered, setHovered] = useState(null);

  const CANVAS_W = 640;
  const CANVAS_H = 360;

  const stageW = stage?.width || 1920;
  const stageH = stage?.height || 1080;
  const scaleX = CANVAS_W / stageW;
  const scaleY = CANVAS_H / stageH;

  // Coordinate Stage -> Canvas
  const toCanvas = useCallback((x, y) => ({
    cx: x * scaleX,
    cy: y * scaleY,
  }), [scaleX, scaleY]);

  // Coordinate Canvas -> Stage
  const fromCanvas = useCallback((cx, cy) => ({
    x: Math.round(cx / scaleX),
    y: Math.round(cy / scaleY),
  }), [scaleX, scaleY]);

  // Rendering del canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !geometry) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    // Sfondo stage
    ctx.fillStyle = stage?.backgroundColor || '#000000';
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    // Test pattern (mini-render)
    if (geometry.activeTestPattern !== TestPatternType.NONE) {
      ctx.save();
      ctx.scale(scaleX, scaleY);
      geometry.renderTestPattern(ctx, geometry.activeTestPattern);
      ctx.restore();
    } else {
      // Griglia tenue di sfondo
      ctx.strokeStyle = '#1e1e26';
      ctx.lineWidth = 1;
      for (let x = 0; x <= CANVAS_W; x += 80 * scaleX) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, CANVAS_H); ctx.stroke();
      }
      for (let y = 0; y <= CANVAS_H; y += 45 * scaleY) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(CANVAS_W, y); ctx.stroke();
      }
    }

    // Edge Blend Mask
    if (['blend', 'pattern'].includes(activeTab)) {
      ctx.save();
      ctx.scale(scaleX, scaleY);
      geometry.renderEdgeBlendMask(ctx);
      ctx.restore();
    }

    // ---- CORNER PIN Overlay ----
    if (activeTab === 'keystone' || activeTab === 'warp') {
      const corners = geometry.corners;

      // Poligono di proiezione
      ctx.save();
      ctx.beginPath();
      const c0 = toCanvas(corners[0].x, corners[0].y);
      ctx.moveTo(c0.cx, c0.cy);
      corners.forEach((c, i) => {
        if (i > 0) {
          const p = toCanvas(c.x, c.y);
          ctx.lineTo(p.cx, p.cy);
        }
      });
      ctx.closePath();
      ctx.strokeStyle = '#ffffff44';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    // ---- WARP MESH Overlay ----
    if (activeTab === 'warp') {
      ctx.save();
      const mesh = geometry.mesh;
      ctx.lineWidth = 1.5;

      // Linee orizzontali
      for (let r = 0; r < geometry.gridRows; r++) {
        ctx.strokeStyle = r === 0 || r === geometry.gridRows - 1 ? '#ffd60a88' : '#0a84ff66';
        ctx.beginPath();
        const p0 = toCanvas(mesh[r][0].x, mesh[r][0].y);
        ctx.moveTo(p0.cx, p0.cy);
        for (let c = 1; c < geometry.gridCols; c++) {
          const p = toCanvas(mesh[r][c].x, mesh[r][c].y);
          ctx.lineTo(p.cx, p.cy);
        }
        ctx.stroke();
      }

      // Linee verticali
      for (let c = 0; c < geometry.gridCols; c++) {
        ctx.strokeStyle = c === 0 || c === geometry.gridCols - 1 ? '#ffd60a88' : '#0a84ff66';
        ctx.beginPath();
        const p0 = toCanvas(mesh[0][c].x, mesh[0][c].y);
        ctx.moveTo(p0.cx, p0.cy);
        for (let r = 1; r < geometry.gridRows; r++) {
          const p = toCanvas(mesh[r][c].x, mesh[r][c].y);
          ctx.lineTo(p.cx, p.cy);
        }
        ctx.stroke();
      }

      // Punti di controllo mesh
      for (let r = 0; r < geometry.gridRows; r++) {
        for (let c = 0; c < geometry.gridCols; c++) {
          const p = toCanvas(mesh[r][c].x, mesh[r][c].y);
          const isCorner = (r === 0 || r === geometry.gridRows - 1) && (c === 0 || c === geometry.gridCols - 1);
          const isHovered = hovered?.type === 'mesh' && hovered.r === r && hovered.c === c;
          const isDragging = dragging?.type === 'mesh' && dragging.r === r && dragging.c === c;

          ctx.beginPath();
          ctx.arc(p.cx, p.cy, isDragging ? 7 : isHovered ? 6 : isCorner ? 5 : 4, 0, Math.PI * 2);
          ctx.fillStyle = isCorner ? '#ffd60a' : isDragging ? '#30d158' : isHovered ? '#0a84ff' : '#ffffff88';
          ctx.fill();
          ctx.strokeStyle = '#000000aa';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      ctx.restore();
    }

    // ---- CORNER PIN handles (tutti i tab tranne warp, che usa la mesh) ----
    if (activeTab === 'keystone') {
      const corners = geometry.corners;
      corners.forEach((c, idx) => {
        const p = toCanvas(c.x, c.y);
        const isHov = hovered?.type === 'corner' && hovered.idx === idx;
        const isDrag = dragging?.type === 'corner' && dragging.idx === idx;

        // Ombra
        ctx.shadowColor = CORNER_COLORS[idx];
        ctx.shadowBlur = 12;

        // Punto handle
        ctx.beginPath();
        ctx.arc(p.cx, p.cy, isDrag ? 11 : isHov ? 9 : 7, 0, Math.PI * 2);
        ctx.fillStyle = CORNER_COLORS[idx];
        ctx.fill();

        ctx.shadowBlur = 0;

        // Etichetta
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(CORNER_LABELS[idx], p.cx, p.cy);
      });
    }

    // Cornice esterna canvas
    ctx.strokeStyle = '#3f3f4a';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, CANVAS_W - 2, CANVAS_H - 2);

    // Risoluzione stage
    ctx.fillStyle = '#ffffff44';
    ctx.font = '10px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText(`${stageW}×${stageH}`, 6, CANVAS_H - 4);

  }, [stage, geometry, activeTab, dragging, hovered, scaleX, scaleY, toCanvas, stageW, stageH]);

  // HIT TEST per corner pin
  const hitTestCorner = useCallback((cx, cy) => {
    if (!geometry) return null;
    for (let idx = 0; idx < 4; idx++) {
      const p = toCanvas(geometry.corners[idx].x, geometry.corners[idx].y);
      const dist = Math.sqrt((cx - p.cx) ** 2 + (cy - p.cy) ** 2);
      if (dist < 14) return { type: 'corner', idx };
    }
    return null;
  }, [geometry, toCanvas]);

  // HIT TEST per mesh warp
  const hitTestMesh = useCallback((cx, cy) => {
    if (!geometry) return null;
    for (let r = 0; r < geometry.gridRows; r++) {
      for (let c = 0; c < geometry.gridCols; c++) {
        const p = toCanvas(geometry.mesh[r][c].x, geometry.mesh[r][c].y);
        const dist = Math.sqrt((cx - p.cx) ** 2 + (cy - p.cy) ** 2);
        if (dist < 10) return { type: 'mesh', r, c };
      }
    }
    return null;
  }, [geometry, toCanvas]);

  const getCanvasPos = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      cx: (e.clientX - rect.left) * (CANVAS_W / rect.width),
      cy: (e.clientY - rect.top) * (CANVAS_H / rect.height),
    };
  }, []);

  const handleMouseDown = useCallback((e) => {
    const { cx, cy } = getCanvasPos(e);
    let hit = null;
    if (activeTab === 'keystone') hit = hitTestCorner(cx, cy);
    if (activeTab === 'warp') hit = hitTestMesh(cx, cy);
    if (hit) {
      setDragging(hit);
      e.preventDefault();
    }
  }, [activeTab, getCanvasPos, hitTestCorner, hitTestMesh]);

  const handleMouseMove = useCallback((e) => {
    const { cx, cy } = getCanvasPos(e);
    if (dragging) {
      const { x, y } = fromCanvas(cx, cy);
      if (dragging.type === 'corner') onDragCorner(dragging.idx, x, y);
      if (dragging.type === 'mesh') onDragMeshPoint(dragging.r, dragging.c, x, y);
    } else {
      let hit = null;
      if (activeTab === 'keystone') hit = hitTestCorner(cx, cy);
      if (activeTab === 'warp') hit = hitTestMesh(cx, cy);
      setHovered(hit);
    }
  }, [dragging, fromCanvas, getCanvasPos, hitTestCorner, hitTestMesh, onDragCorner, onDragMeshPoint, activeTab]);

  const handleMouseUp = useCallback(() => { setDragging(null); }, []);

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        className="w-full rounded-lg border border-zinc-700/80 cursor-crosshair select-none"
        style={{ background: '#0a0a0c' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
      {/* Legenda Tab */}
      {activeTab === 'keystone' && (
        <div className="absolute bottom-2 right-2 flex gap-1.5">
          {CORNER_LABELS.map((lbl, idx) => (
            <span key={idx} className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: CORNER_COLORS[idx] + '33', color: CORNER_COLORS[idx], border: `1px solid ${CORNER_COLORS[idx]}55` }}>
              {lbl}
            </span>
          ))}
        </div>
      )}
      {activeTab === 'warp' && (
        <div className="absolute bottom-2 right-2 text-[9px] text-zinc-500 font-mono">
          Trascina i punti di controllo mesh
        </div>
      )}
    </div>
  );
}

// ====================================================================================
// Pannello Tab: Corner Pin / Keystone
// ====================================================================================

function CornerPinPanel({ geometry, onUpdateGeometry }) {
  if (!geometry) return null;

  const handleKeystoneH = (v) => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setKeystone(v, geometry.keystone.vertical);
    onUpdateGeometry(g);
  };

  const handleKeystoneV = (v) => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setKeystone(geometry.keystone.horizontal, v);
    onUpdateGeometry(g);
  };

  const handleReset = () => {
    const g = new StageGeometry({ width: geometry.width, height: geometry.height });
    onUpdateGeometry(g);
  };

  return (
    <div className="flex flex-col gap-5 p-4">
      <SectionHeader label="Correzione Prospettica Keystone" icon={Move} />

      <div className="flex flex-col gap-4">
        <MacSlider
          label="Keystone Orizzontale"
          value={geometry.keystone.horizontal}
          min={-1} max={1} step={0.01}
          onChange={handleKeystoneH}
        />
        <MacSlider
          label="Keystone Verticale"
          value={geometry.keystone.vertical}
          min={-1} max={1} step={0.01}
          onChange={handleKeystoneV}
        />
      </div>

      <SectionHeader label="Posizione Angoli (Pixel)" icon={Move} />

      <div className="grid grid-cols-2 gap-3">
        {geometry.corners.map((c, idx) => (
          <div key={idx} className="rounded-lg border p-3 flex flex-col gap-2"
            style={{ borderColor: CORNER_COLORS[idx] + '55', background: CORNER_COLORS[idx] + '0d' }}>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full" style={{ background: CORNER_COLORS[idx] }} />
              <span className="text-xs font-semibold text-zinc-300">{CORNER_LABELS[idx]}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {['x', 'y'].map((axis) => (
                <div key={axis} className="flex flex-col gap-0.5">
                  <label className="text-[10px] text-zinc-500 uppercase font-mono">{axis.toUpperCase()}</label>
                  <input
                    type="number"
                    value={c[axis]}
                    onChange={(e) => {
                      const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
                      const newCorner = { ...g.corners[idx], [axis]: parseInt(e.target.value, 10) || 0 };
                      g.setCorner(idx, newCorner.x, newCorner.y);
                      onUpdateGeometry(g);
                    }}
                    className="bg-zinc-800/80 border border-zinc-600/60 rounded px-2 py-1 text-xs text-zinc-200 font-mono w-full focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleReset}
        className="flex items-center justify-center gap-2 py-2 rounded-lg border border-zinc-600/60 text-xs text-zinc-400 hover:text-white hover:border-zinc-500 transition-colors"
      >
        <RotateCcw size={12} /> Ripristina Correzione
      </button>
    </div>
  );
}

// ====================================================================================
// Pannello Tab: Surface Warp
// ====================================================================================

function SurfaceWarpPanel({ geometry, onUpdateGeometry }) {
  if (!geometry) return null;

  const handleGridChange = (key, val) => {
    const rows = key === 'rows' ? val : geometry.gridRows;
    const cols = key === 'cols' ? val : geometry.gridCols;
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setGridDensity(rows, cols);
    onUpdateGeometry(g);
  };

  const handleResetMesh = () => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.resetMesh();
    onUpdateGeometry(g);
  };

  return (
    <div className="flex flex-col gap-5 p-4">
      <SectionHeader label="Densità Griglia di Controllo" icon={Grid3x3} />

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-400">Righe Verticali</label>
          <div className="flex items-center gap-2">
            <input
              type="range" min={2} max={10} value={geometry.gridRows}
              onChange={(e) => handleGridChange('rows', parseInt(e.target.value, 10))}
              className="flex-1 h-1.5 bg-zinc-700 rounded-full appearance-none accent-blue-500 cursor-pointer"
            />
            <span className="text-xs font-mono text-zinc-200 w-4 text-right">{geometry.gridRows}</span>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-400">Colonne Orizzontali</label>
          <div className="flex items-center gap-2">
            <input
              type="range" min={2} max={10} value={geometry.gridCols}
              onChange={(e) => handleGridChange('cols', parseInt(e.target.value, 10))}
              className="flex-1 h-1.5 bg-zinc-700 rounded-full appearance-none accent-blue-500 cursor-pointer"
            />
            <span className="text-xs font-mono text-zinc-200 w-4 text-right">{geometry.gridCols}</span>
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-zinc-800/50 border border-zinc-700/40 p-3 text-xs text-zinc-400">
        <p className="mb-1 text-zinc-300 font-medium">Griglia {geometry.gridRows} × {geometry.gridCols} = {geometry.gridRows * geometry.gridCols} punti di controllo</p>
        <p>Trascina i punti di controllo sull'anteprima per deformare la superficie di proiezione. I punti agli angoli aggiornano automaticamente il Corner Pinning.</p>
      </div>

      {/* Tabella coordinate mesh per editing numerico */}
      <SectionHeader label="Punti di Controllo Mesh" icon={Grid3x3} />

      <div className="max-h-52 overflow-y-auto rounded-lg border border-zinc-700/40">
        <table className="w-full text-[10px] font-mono">
          <thead>
            <tr className="bg-zinc-800 text-zinc-400 sticky top-0">
              <th className="px-2 py-1.5 text-left">R</th>
              <th className="px-2 py-1.5 text-left">C</th>
              <th className="px-2 py-1.5 text-left">X (px)</th>
              <th className="px-2 py-1.5 text-left">Y (px)</th>
            </tr>
          </thead>
          <tbody>
            {geometry.mesh.map((row, r) =>
              row.map((pt, c) => (
                <tr key={`${r}-${c}`} className="border-t border-zinc-700/30 hover:bg-zinc-700/20">
                  <td className="px-2 py-1 text-zinc-500">{r}</td>
                  <td className="px-2 py-1 text-zinc-500">{c}</td>
                  <td className="px-1 py-0.5">
                    <input
                      type="number"
                      value={pt.x}
                      onChange={(e) => {
                        const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
                        g.setMeshPoint(r, c, parseInt(e.target.value, 10) || 0, pt.y);
                        onUpdateGeometry(g);
                      }}
                      className="w-16 bg-zinc-800 border border-zinc-700/40 rounded px-1 py-0.5 text-zinc-200 focus:outline-none focus:border-blue-500"
                    />
                  </td>
                  <td className="px-1 py-0.5">
                    <input
                      type="number"
                      value={pt.y}
                      onChange={(e) => {
                        const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
                        g.setMeshPoint(r, c, pt.x, parseInt(e.target.value, 10) || 0);
                        onUpdateGeometry(g);
                      }}
                      className="w-16 bg-zinc-800 border border-zinc-700/40 rounded px-1 py-0.5 text-zinc-200 focus:outline-none focus:border-blue-500"
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <button
        onClick={handleResetMesh}
        className="flex items-center justify-center gap-2 py-2 rounded-lg border border-zinc-600/60 text-xs text-zinc-400 hover:text-white hover:border-zinc-500 transition-colors"
      >
        <RotateCcw size={12} /> Ripristina Mesh
      </button>
    </div>
  );
}

// ====================================================================================
// Pannello Tab: Edge Blending
// ====================================================================================

function EdgeBlendPanel({ geometry, onUpdateGeometry }) {
  if (!geometry) return null;

  const edges = [
    { key: 'left', label: 'Bordo Sinistro', desc: 'Overlap proiettore adiacente ←' },
    { key: 'right', label: 'Bordo Destro', desc: 'Overlap proiettore adiacente →' },
    { key: 'top', label: 'Bordo Superiore', desc: 'Overlap proiettore sovrastante ↑' },
    { key: 'bottom', label: 'Bordo Inferiore', desc: 'Overlap proiettore sottostante ↓' },
  ];

  const handleEdgePatch = (edge, patch) => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setEdgeBlend(edge, patch);
    onUpdateGeometry(g);
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <SectionHeader label="Edge Blending per Proiezioni Multiple" icon={Layers} />

      <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 p-3 text-xs text-blue-300">
        Configura le maschere di dissolvenza per fondere proiezioni adiacenti su una superficie continua. Ogni bordo può avere larghezza di overlap, curva gamma e compensazione del black level indipendenti.
      </div>

      {edges.map(({ key, label, desc }) => {
        const e = geometry.edgeBlend[key];
        return (
          <div key={key} className={`rounded-lg border p-3 flex flex-col gap-3 transition-colors ${e.enabled ? 'border-blue-500/40 bg-blue-500/5' : 'border-zinc-700/40 bg-zinc-800/30'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-zinc-200">{label}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5">{desc}</p>
              </div>
              <ToggleSwitch
                checked={e.enabled}
                onChange={(v) => handleEdgePatch(key, { enabled: v })}
              />
            </div>

            {e.enabled && (
              <div className="flex flex-col gap-3 pt-1 border-t border-zinc-700/40">
                <MacSlider
                  label="Larghezza Overlap"
                  value={e.width}
                  min={0} max={800} step={1} unit=" px"
                  onChange={(v) => handleEdgePatch(key, { width: v })}
                />
                <MacSlider
                  label="Curva Gamma"
                  value={e.gamma}
                  min={0.5} max={5.0} step={0.1}
                  onChange={(v) => handleEdgePatch(key, { gamma: v })}
                />
                <MacSlider
                  label="Black Level Compensation"
                  value={e.blackLevel}
                  min={0} max={0.2} step={0.001}
                  onChange={(v) => handleEdgePatch(key, { blackLevel: v })}
                />
                {/* Anteprima grafica della curva */}
                <EdgeBlendCurvePreview gamma={e.gamma} blackLevel={e.blackLevel} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function EdgeBlendCurvePreview({ gamma, blackLevel }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#1c1c20';
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = '#0a84ff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i <= W; i++) {
      const t = i / W;
      const f = blackLevel + (1 - blackLevel) * Math.pow(t, gamma);
      const y = H - f * H;
      if (i === 0) ctx.moveTo(i, y);
      else ctx.lineTo(i, y);
    }
    ctx.stroke();

    ctx.strokeStyle = '#3f3f4a';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 2]);
    for (let i = 1; i < 4; i++) {
      ctx.beginPath();
      ctx.moveTo((i / 4) * W, 0);
      ctx.lineTo((i / 4) * W, H);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, (i / 4) * H);
      ctx.lineTo(W, (i / 4) * H);
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }, [gamma, blackLevel]);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] text-zinc-500">Curva di dissolvenza (Gamma: {gamma.toFixed(1)} | Black: {(blackLevel * 100).toFixed(1)}%)</span>
      <canvas ref={canvasRef} width={240} height={60} className="rounded w-full border border-zinc-700/40" />
    </div>
  );
}

// ====================================================================================
// Pannello Tab: Test Pattern
// ====================================================================================

function TestPatternPanel({ geometry, onUpdateGeometry }) {
  if (!geometry) return null;

  const handlePattern = (id) => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.activeTestPattern = id;
    onUpdateGeometry(g);
  };

  const handleBrightness = (v) => {
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.testPatternBrightness = v;
    onUpdateGeometry(g);
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <SectionHeader label="Test Pattern di Calibrazione" icon={Monitor} />

      <MacSlider
        label="Luminosità Test Pattern"
        value={geometry.testPatternBrightness}
        min={0} max={1} step={0.01}
        onChange={handleBrightness}
        disabled={geometry.activeTestPattern === TestPatternType.NONE}
      />

      <div className="flex flex-col gap-2">
        {TEST_PATTERNS.map(({ id, label, desc }) => {
          const active = geometry.activeTestPattern === id;
          return (
            <button
              key={id}
              onClick={() => handlePattern(id)}
              className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
                active
                  ? 'border-blue-500 bg-blue-500/15 text-white'
                  : 'border-zinc-700/50 bg-zinc-800/30 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'
              }`}
            >
              <div className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${active ? 'border-blue-500 bg-blue-500' : 'border-zinc-600'}`} />
              <div>
                <p className="text-xs font-semibold">{label}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5">{desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ====================================================================================
// Pannello Tab: Display Mapping
// ====================================================================================

function DisplayMappingPanel({ stage, selectedMappingIdx, onSelectMapping, onUpdateStage }) {
  if (!stage) return null;

  const mapping = stage.screenMappings[selectedMappingIdx];

  return (
    <div className="flex flex-col gap-4 p-4">
      <SectionHeader label="Mapping Display Fisici" icon={Sliders} />

      <div className="flex flex-col gap-2">
        {stage.screenMappings.map((m, idx) => (
          <button
            key={m.screenId}
            onClick={() => onSelectMapping(idx)}
            className={`flex items-center justify-between p-3 rounded-lg border transition-all text-left ${
              idx === selectedMappingIdx
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-zinc-700/50 bg-zinc-800/30 hover:border-zinc-600'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Monitor size={14} className={idx === selectedMappingIdx ? 'text-blue-400' : 'text-zinc-500'} />
              <div>
                <p className="text-xs font-semibold text-zinc-200">{m.screenName}</p>
                <p className="text-[10px] text-zinc-500 font-mono">{m.stageWidth}×{m.stageHeight} @ {m.stageX},{m.stageY}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {m.enabled
                ? <Eye size={12} className="text-green-400" />
                : <EyeOff size={12} className="text-zinc-600" />}
            </div>
          </button>
        ))}
      </div>

      {mapping && (
        <>
          <SectionHeader label={`Configurazione: ${mapping.screenName}`} icon={Monitor} />
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-zinc-400">Nome Display</label>
              <input
                type="text"
                value={mapping.screenName}
                onChange={(e) => {
                  const updated = stage.screenMappings.map((m, i) =>
                    i === selectedMappingIdx ? { ...m, screenName: e.target.value } : m
                  );
                  onUpdateStage({ ...stage, screenMappings: updated });
                }}
                className="bg-zinc-800 border border-zinc-600/60 rounded px-2 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              {[['Offset X', 'stageX'], ['Offset Y', 'stageY'], ['Larghezza', 'stageWidth'], ['Altezza', 'stageHeight']].map(([lbl, field]) => (
                <div key={field} className="flex flex-col gap-1">
                  <label className="text-xs text-zinc-400">{lbl}</label>
                  <input
                    type="number"
                    value={mapping[field]}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10) || 0;
                      const updated = stage.screenMappings.map((m, i) =>
                        i === selectedMappingIdx ? { ...m, [field]: val } : m
                      );
                      onUpdateStage({ ...stage, screenMappings: updated });
                    }}
                    className="bg-zinc-800 border border-zinc-600/60 rounded px-2 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between">
              <ToggleSwitch
                checked={mapping.enabled}
                onChange={(v) => {
                  const updated = stage.screenMappings.map((m, i) =>
                    i === selectedMappingIdx ? { ...m, enabled: v } : m
                  );
                  onUpdateStage({ ...stage, screenMappings: updated });
                }}
                label="Schermo abilitato"
              />
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span>Rotazione</span>
                <select
                  value={mapping.rotation}
                  onChange={(e) => {
                    const updated = stage.screenMappings.map((m, i) =>
                      i === selectedMappingIdx ? { ...m, rotation: parseInt(e.target.value, 10) } : m
                    );
                    onUpdateStage({ ...stage, screenMappings: updated });
                  }}
                  className="bg-zinc-800 border border-zinc-600/60 rounded px-1.5 py-1 text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
                >
                  {[0, 90, 180, 270].map((r) => (
                    <option key={r} value={r}>{r}°</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ====================================================================================
// Componente Principale: StageGeometryEditor
// ====================================================================================

export default function StageGeometryEditor() {
  const [engine] = useState(() => new VideoEngine());
  const [stages, setStages] = useState(() => engine.getAllStages());
  const [selectedStageId, setSelectedStageId] = useState(() => engine.defaultStageId);
  const [selectedMappingIdx, setSelectedMappingIdx] = useState(0);
  const [activeTab, setActiveTab] = useState('keystone');
  const [geometries, setGeometries] = useState(() => {
    const map = {};
    engine.getAllStages().forEach((st) => {
      st.screenMappings.forEach((m, idx) => {
        const key = `${st.id}::${idx}`;
        map[key] = m.geometry instanceof StageGeometry
          ? m.geometry
          : new StageGeometry({ width: m.stageWidth || st.width, height: m.stageHeight || st.height });
      });
    });
    return map;
  });

  const selectedStage = stages.find((s) => s.id === selectedStageId) || stages[0];
  const geoKey = selectedStage ? `${selectedStage.id}::${selectedMappingIdx}` : null;
  const geometry = geoKey ? geometries[geoKey] : null;

  const handleUpdateGeometry = useCallback((newGeo) => {
    setGeometries((prev) => ({ ...prev, [geoKey]: newGeo }));
  }, [geoKey]);

  const handleDragCorner = useCallback((idx, x, y) => {
    if (!geometry) return;
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setCorner(idx, x, y);
    handleUpdateGeometry(g);
  }, [geometry, handleUpdateGeometry]);

  const handleDragMeshPoint = useCallback((r, c, x, y) => {
    if (!geometry) return;
    const g = new StageGeometry({ ...geometry.toJSON(), width: geometry.width, height: geometry.height });
    g.setMeshPoint(r, c, x, y);
    handleUpdateGeometry(g);
  }, [geometry, handleUpdateGeometry]);

  const handleAddStage = () => {
    const newStage = engine.addStage({
      name: `Stage ${stages.length + 1}`,
      width: 1920, height: 1080,
    });
    setStages(engine.getAllStages());
    setSelectedStageId(newStage.id);
    const key = `${newStage.id}::0`;
    setGeometries((prev) => ({
      ...prev,
      [key]: new StageGeometry({ width: 1920, height: 1080 }),
    }));
    setSelectedMappingIdx(0);
  };

  const handleUpdateStage = (patchedStage) => {
    const updatedStages = stages.map((s) => s.id === patchedStage.id ? { ...s, ...patchedStage } : s);
    setStages(updatedStages);
  };

  return (
    <div className="flex flex-col h-full bg-[#141416] text-white overflow-hidden">
      {/* Toolbar superiore */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-[#1c1c20] border-b border-zinc-700/60 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Maximize2 size={14} className="text-blue-400" />
          <span className="text-sm font-semibold text-zinc-200">Stage Geometry Editor</span>
        </div>

        {/* Stage selector */}
        <div className="flex items-center gap-2 ml-4">
          {stages.map((st) => (
            <button
              key={st.id}
              onClick={() => { setSelectedStageId(st.id); setSelectedMappingIdx(0); }}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                st.id === selectedStageId
                  ? 'bg-blue-500 text-white'
                  : 'bg-zinc-700/60 text-zinc-400 hover:text-white hover:bg-zinc-600/60'
              }`}
            >
              {st.name}
            </button>
          ))}
          <button
            onClick={handleAddStage}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-zinc-400 hover:text-white border border-zinc-700/50 hover:border-zinc-500 transition-colors"
          >
            <Plus size={11} /> Stage
          </button>
        </div>

        <div className="ml-auto flex items-center gap-2 text-xs text-zinc-500">
          {selectedStage && (
            <span className="font-mono">{selectedStage.width}×{selectedStage.height}</span>
          )}
        </div>
      </div>

      {/* Layout principale */}
      <div className="flex flex-1 overflow-hidden">

        {/* Colonna sinistra: canvas preview */}
        <div className="flex flex-col gap-3 p-4 flex-1 min-w-0 overflow-auto">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400 uppercase tracking-wider font-semibold">Anteprima Stage</span>
            {selectedStage && (
              <span className="text-[10px] font-mono text-zinc-500">
                Mapping {selectedMappingIdx + 1} / {selectedStage.screenMappings.length}
                {selectedStage.screenMappings[selectedMappingIdx] && ` — ${selectedStage.screenMappings[selectedMappingIdx].screenName}`}
              </span>
            )}
          </div>

          <GeometryCanvas
            stage={selectedStage}
            geometry={geometry}
            selectedMapping={selectedStage?.screenMappings[selectedMappingIdx]}
            activeTab={activeTab}
            onDragCorner={handleDragCorner}
            onDragMeshPoint={handleDragMeshPoint}
          />

          {/* Info riepilogative geometria */}
          {geometry && (
            <div className="grid grid-cols-4 gap-2">
              {[
                ['Corner TL', `${geometry.corners[0].x}, ${geometry.corners[0].y}`],
                ['Corner TR', `${geometry.corners[1].x}, ${geometry.corners[1].y}`],
                ['Keystone H', geometry.keystone.horizontal.toFixed(2)],
                ['Keystone V', geometry.keystone.vertical.toFixed(2)],
              ].map(([lbl, val]) => (
                <div key={lbl} className="bg-zinc-800/60 rounded-lg p-2.5 border border-zinc-700/40">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">{lbl}</p>
                  <p className="text-xs font-mono text-zinc-200 mt-0.5">{val}</p>
                </div>
              ))}
            </div>
          )}

          {/* Grid density info */}
          {geometry && activeTab === 'warp' && (
            <div className="bg-zinc-800/60 rounded-lg p-3 border border-zinc-700/40 flex items-center gap-6">
              <div>
                <p className="text-[10px] text-zinc-500">Mesh</p>
                <p className="text-sm font-mono text-zinc-200">{geometry.gridRows}×{geometry.gridCols}</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-500">Punti totali</p>
                <p className="text-sm font-mono text-zinc-200">{geometry.gridRows * geometry.gridCols}</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-500">Quad</p>
                <p className="text-sm font-mono text-zinc-200">{(geometry.gridRows - 1) * (geometry.gridCols - 1)}</p>
              </div>
            </div>
          )}
        </div>

        {/* Colonna destra: pannello di controllo */}
        <div className="w-80 flex-shrink-0 border-l border-zinc-700/60 flex flex-col overflow-hidden bg-[#18181c]">
          {/* Tab bar */}
          <div className="flex flex-col border-b border-zinc-700/60">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium transition-colors border-l-2 ${
                  activeTab === id
                    ? 'border-blue-500 bg-blue-500/10 text-white'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/20'
                }`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>

          {/* Contenuto Tab */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'keystone' && (
              <CornerPinPanel
                geometry={geometry}
                onUpdateGeometry={handleUpdateGeometry}
              />
            )}
            {activeTab === 'warp' && (
              <SurfaceWarpPanel
                geometry={geometry}
                onUpdateGeometry={handleUpdateGeometry}
              />
            )}
            {activeTab === 'blend' && (
              <EdgeBlendPanel
                geometry={geometry}
                onUpdateGeometry={handleUpdateGeometry}
              />
            )}
            {activeTab === 'pattern' && (
              <TestPatternPanel
                geometry={geometry}
                onUpdateGeometry={handleUpdateGeometry}
              />
            )}
            {activeTab === 'display' && (
              <DisplayMappingPanel
                stage={selectedStage}
                selectedMappingIdx={selectedMappingIdx}
                onSelectMapping={setSelectedMappingIdx}
                onUpdateStage={handleUpdateStage}
              />
            )}
          </div>

          {/* Footer azioni */}
          <div className="border-t border-zinc-700/60 p-3 flex gap-2">
            <button
              onClick={() => {
                if (!geometry) return;
                const g = new StageGeometry({ width: geometry.width, height: geometry.height });
                handleUpdateGeometry(g);
              }}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md border border-zinc-600/60 text-xs text-zinc-400 hover:text-white hover:border-zinc-500 transition-colors"
            >
              <RotateCcw size={11} /> Reset
            </button>
            <button
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md bg-blue-500 text-white text-xs font-semibold hover:bg-blue-400 transition-colors"
              onClick={() => {
                if (geometry) {
                  console.log('[StageGeometryEditor] Configurazione applicata:', geometry.toJSON());
                }
              }}
            >
              <CheckSquare size={11} /> Applica
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
