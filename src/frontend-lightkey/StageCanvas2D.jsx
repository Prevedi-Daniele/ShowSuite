import React, { useRef, useEffect, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, Maximize, Plus, Move, Sparkles } from 'lucide-react';
import MacButton from '../shared/components/MacButton';

/**
 * StageCanvas2D - Canvas 2D interattivo ad alte prestazioni per Lightkey
 * Gestisce:
 * - Griglia e oggetti scenici (Truss lineari)
 * - Posizionamento e drag-and-drop dei fari
 * - Rendering in tempo reale dei fasci luminosi (Beam, dimmer, colore RGB, pan/tilt e strobo)
 * - Zoom, Pan, selezione singola e selezione multipla a rettangolo (Rubberband)
 */
export default function StageCanvas2D({
  fixtures = [],
  selectedIds = [],
  onSelectionChange,
  onFixtureMove,
  onAddFixture,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Stato navigazione vista (Pan & Zoom)
  const [viewTransform, setViewTransform] = useState({ x: 100, y: 80, scale: 1.0 });

  // Oggetti scenici (Truss / Americane)
  const [trusses, setTrusses] = useState([
    { id: 'truss_back', x1: 150, y1: 120, x2: 850, y2: 120, label: 'Truss Posteriore' },
    { id: 'truss_mid', x1: 200, y1: 300, x2: 800, y2: 300, label: 'Truss Centrale' },
    { id: 'truss_front', x1: 100, y1: 480, x2: 900, y2: 480, label: 'Truss Frontale' },
  ]);

  // Stato interazioni mouse
  const interactionRef = useRef({
    isPanning: false,
    panStart: { x: 0, y: 0 },
    isDraggingFixture: false,
    dragStartPos: { x: 0, y: 0 },
    draggedFixtureId: null,
    isBoxSelecting: false,
    boxStart: { x: 0, y: 0 },
    boxCurrent: { x: 0, y: 0 },
    spacePressed: false,
  });

  // Tasti Spazio per abilitare il Pan con drag del mouse
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && !interactionRef.current.spacePressed) {
        interactionRef.current.spacePressed = true;
        if (canvasRef.current) canvasRef.current.style.cursor = 'grab';
      }
    };
    const handleKeyUp = (e) => {
      if (e.code === 'Space') {
        interactionRef.current.spacePressed = false;
        if (canvasRef.current) canvasRef.current.style.cursor = 'default';
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Coordinate mondo <-> Coordinate schermo
  const screenToWorld = useCallback(
    (screenX, screenY) => {
      return {
        x: (screenX - viewTransform.x) / viewTransform.scale,
        y: (screenY - viewTransform.y) / viewTransform.scale,
      };
    },
    [viewTransform]
  );

  // Loop di disegno canvas a 60 FPS
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const render = () => {
      const width = (canvas.width = canvas.parentElement.clientWidth);
      const height = (canvas.height = canvas.parentElement.clientHeight);

      // Sfondo stage scuro con vignettatura morbida
      ctx.fillStyle = '#0f0f12';
      ctx.fillRect(0, 0, width, height);

      ctx.save();
      // Applica Pan & Zoom
      ctx.translate(viewTransform.x, viewTransform.y);
      ctx.scale(viewTransform.scale, viewTransform.scale);

      // 1. Disegna Griglia Palco (griglia metrica a quadretti)
      const gridSize = 40;
      const worldLeft = -viewTransform.x / viewTransform.scale - 200;
      const worldTop = -viewTransform.y / viewTransform.scale - 200;
      const worldRight = worldLeft + width / viewTransform.scale + 400;
      const worldBottom = worldTop + height / viewTransform.scale + 400;

      ctx.strokeStyle = '#1e1e24';
      ctx.lineWidth = 1 / viewTransform.scale;
      ctx.beginPath();
      for (let x = Math.floor(worldLeft / gridSize) * gridSize; x <= worldRight; x += gridSize) {
        ctx.moveTo(x, worldTop);
        ctx.lineTo(x, worldBottom);
      }
      for (let y = Math.floor(worldTop / gridSize) * gridSize; y <= worldBottom; y += gridSize) {
        ctx.moveTo(worldLeft, y);
        ctx.lineTo(worldRight, y);
      }
      ctx.stroke();

      // Centro palco / pedana
      ctx.strokeStyle = '#272732';
      ctx.lineWidth = 2 / viewTransform.scale;
      ctx.strokeRect(100, 80, 800, 440);

      // 2. Disegna Truss (Americane in alluminio a doppio tubo con diagonali)
      trusses.forEach((truss) => {
        ctx.save();
        ctx.strokeStyle = '#383844';
        ctx.lineWidth = 6 / viewTransform.scale;
        ctx.lineCap = 'round';
        // Tubi principali
        ctx.beginPath();
        ctx.moveTo(truss.x1, truss.y1);
        ctx.lineTo(truss.x2, truss.y2);
        ctx.stroke();

        // Tramezzi diagonali truss
        ctx.strokeStyle = '#282832';
        ctx.lineWidth = 1.5 / viewTransform.scale;
        const dx = truss.x2 - truss.x1;
        const dy = truss.y2 - truss.y1;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const steps = Math.floor(dist / 25);
        ctx.beginPath();
        for (let i = 0; i <= steps; i++) {
          const t = i / steps;
          const px = truss.x1 + dx * t;
          const py = truss.y1 + dy * t;
          ctx.moveTo(px, py - 4);
          ctx.lineTo(px + (i % 2 === 0 ? 12 : -12), py + 4);
        }
        ctx.stroke();

        // Label del Truss
        ctx.fillStyle = '#636370';
        ctx.font = `${10 / viewTransform.scale}px "SF Mono", monospace`;
        ctx.fillText(truss.label, truss.x1, truss.y1 - 10);
        ctx.restore();
      });

      // 3. Disegna i Fasci Luminosi (Beams) - Renderizzati sotto ai corpi dei fari
      const now = Date.now();
      fixtures.forEach((fix) => {
        let intensity = fix.state?.intensity !== undefined ? fix.state.intensity : 1;
        const shutter = fix.state?.shutter !== undefined ? fix.state.shutter : 1;

        // Gestione Shutter & Strobo
        if (shutter === 0) return; // Shutter chiuso
        if (shutter > 1) {
          // Strobo: intervallo di lampeggio basato su Hz (shutter = 2..25 Hz)
          const strobePeriodMs = 1000 / shutter;
          const strobePhase = (now % strobePeriodMs) / strobePeriodMs;
          if (strobePhase > 0.45) return; // Flash rapido
        }

        if (intensity <= 0.01) return; // Fascio spento

        const fx = fix.position.x;
        const fy = fix.position.y;
        const color = fix.state?.color || { r: 1, g: 1, b: 1 };
        let pan = fix.state?.pan !== undefined ? fix.state.pan : 0.5;
        let tilt = fix.state?.tilt !== undefined ? fix.state.tilt : 0.5;
        const zoom = fix.state?.zoom !== undefined ? fix.state.zoom : 0.5;
        const gobo = fix.state?.gobo || 0;
        const goboRotate = fix.state?.goboRotate || 0;
        const prism = fix.state?.prism || 0;

        // Calibrazione hardware
        if (fix.calibration?.invertPan) pan = 1 - pan;
        if (fix.calibration?.invertTilt) tilt = 1 - tilt;
        if (fix.calibration?.swapPanTilt) {
          const tmp = pan;
          pan = tilt;
          tilt = tmp;
        }

        // Calcolo proiezione fascio a terra in base a Pan e Tilt
        const panAngle = (pan - 0.5) * Math.PI * 1.5; // -135° .. +135°
        const tiltAngle = (tilt - 0.5) * Math.PI * 0.8; // Angolo inclinazione
        const beamLength = 120 + tilt * 80;
        const beamAngle = 0.25 + zoom * 0.35; // Ampiezza cono

        const targetX = fx + Math.sin(panAngle) * beamLength;
        const targetY = fy + Math.cos(tiltAngle) * beamLength;
        const beamRadius = 25 + zoom * 45;

        ctx.save();
        // Cono di luce volumetrico con gradiente
        const r255 = Math.round(color.r * 255);
        const g255 = Math.round(color.g * 255);
        const b255 = Math.round(color.b * 255);
        const alpha = Math.min(0.85, intensity * 0.6);

        // Disegna cono
        const coneGrad = ctx.createRadialGradient(fx, fy, 4, targetX, targetY, beamRadius * 1.8);
        coneGrad.addColorStop(0, `rgba(${r255}, ${g255}, ${b255}, ${alpha})`);
        coneGrad.addColorStop(0.7, `rgba(${r255}, ${g255}, ${b255}, ${alpha * 0.3})`);
        coneGrad.addColorStop(1, `rgba(${r255}, ${g255}, ${b255}, 0)`);

        ctx.fillStyle = coneGrad;
        ctx.beginPath();
        ctx.moveTo(fx, fy);
        ctx.arc(targetX, targetY, beamRadius, panAngle - beamAngle, panAngle + beamAngle);
        ctx.closePath();
        ctx.fill();

        // Macchia luminosa a terra (Hotspot / Ellisse di atterraggio)
        // Se prisma attivo (1 = 3 facce, 2 = 8 facce, 3 = lineare), disegna macchie multiple
        const prismFacets = prism === 1 ? 3 : prism === 2 ? 8 : prism === 3 ? 5 : 1;
        const prismSpread = prismFacets > 1 ? beamRadius * 0.65 : 0;

        for (let p = 0; p < prismFacets; p++) {
          const pAngle = (p * Math.PI * 2) / prismFacets + (now * 0.001 * (goboRotate || 1));
          const px = prismFacets > 1 ? targetX + Math.cos(pAngle) * prismSpread : targetX;
          const py = prismFacets > 1 ? targetY + Math.sin(pAngle) * (prismSpread * 0.6) : targetY;
          const pRadius = prismFacets > 1 ? beamRadius * 0.55 : beamRadius;

          const spotGrad = ctx.createRadialGradient(px, py, 0, px, py, pRadius);
          spotGrad.addColorStop(0, `rgba(${r255}, ${g255}, ${b255}, ${intensity * 0.9})`);
          spotGrad.addColorStop(0.5, `rgba(${r255}, ${g255}, ${b255}, ${intensity * 0.4})`);
          spotGrad.addColorStop(1, `rgba(${r255}, ${g255}, ${b255}, 0)`);

          ctx.fillStyle = spotGrad;
          ctx.beginPath();
          ctx.ellipse(px, py, pRadius, pRadius * 0.6, panAngle, 0, Math.PI * 2);
          ctx.fill();

          // Se gobo attivo (>0), disegna il pattern gobo proiettato
          if (gobo > 0.05) {
            ctx.save();
            ctx.translate(px, py);
            const rotAngle = (now * 0.002 * goboRotate) % (Math.PI * 2);
            ctx.rotate(rotAngle);

            ctx.strokeStyle = `rgba(${r255}, ${g255}, ${b255}, ${intensity * 0.7})`;
            ctx.lineWidth = 1.5;

            // Pattern gobo dinamico (raggi o anelli concentrici o dots)
            const goboType = Math.round(gobo * 7);
            if (goboType === 1) {
              // Dots
              ctx.fillStyle = `rgba(${r255}, ${g255}, ${b255}, ${intensity * 0.8})`;
              for (let d = 0; d < 5; d++) {
                const da = (d * Math.PI * 2) / 5;
                ctx.beginPath();
                ctx.arc(Math.cos(da) * (pRadius * 0.4), Math.sin(da) * (pRadius * 0.3), 3, 0, Math.PI * 2);
                ctx.fill();
              }
            } else if (goboType === 2 || goboType === 6) {
              // Starburst / Raggi
              for (let r = 0; r < 8; r++) {
                const ra = (r * Math.PI) / 4;
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(Math.cos(ra) * (pRadius * 0.7), Math.sin(ra) * (pRadius * 0.5));
                ctx.stroke();
              }
            } else {
              // Cerchio interno e barrette
              ctx.beginPath();
              ctx.arc(0, 0, pRadius * 0.35, 0, Math.PI * 2);
              ctx.stroke();
            }
            ctx.restore();
          }
        }

        ctx.restore();
      });

      // 4. Disegna i Proiettori (Fixtures Body)
      fixtures.forEach((fix) => {
        const isSelected = selectedIds.includes(fix.id);
        const fx = fix.position.x;
        const fy = fix.position.y;
        const intensity = fix.state?.intensity !== undefined ? fix.state.intensity : 0;
        const color = fix.state?.color || { r: 1, g: 1, b: 1 };
        const category = fix.category || fix.profile?.category || 'moving_head';

        ctx.save();
        ctx.translate(fx, fy);

        // Cerchio/Alone di selezione
        if (isSelected) {
          ctx.strokeStyle = '#0a84ff';
          ctx.lineWidth = 2.5 / viewTransform.scale;
          ctx.beginPath();
          ctx.arc(0, 0, 22, 0, Math.PI * 2);
          ctx.stroke();

          ctx.fillStyle = 'rgba(10, 132, 255, 0.15)';
          ctx.fill();
        }

        // Corpo del faro (Hardware Head)
        ctx.shadowColor = '#000000';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 3;

        ctx.fillStyle = '#222228';
        ctx.strokeStyle = isSelected ? '#52a5ff' : '#3e3e48';
        ctx.lineWidth = 1.5 / viewTransform.scale;

        if (category === 'moving_head') {
          // Icona Testa Mobile: cerchio base + testa orientata
          ctx.beginPath();
          ctx.arc(0, 0, 16, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();

          // Lente luminosa
          const lr = Math.round(color.r * 255);
          const lg = Math.round(color.g * 255);
          const lb = Math.round(color.b * 255);
          ctx.fillStyle = intensity > 0.05 ? `rgba(${lr}, ${lg}, ${lb}, ${intensity})` : '#161619';
          ctx.beginPath();
          ctx.arc(0, 0, 9, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = intensity > 0.05 ? `rgb(${lr}, ${lg}, ${lb})` : '#33333b';
          ctx.stroke();
        } else if (category === 'par' || category === 'dimmer') {
          // Par Can circolare
          ctx.beginPath();
          ctx.arc(0, 0, 14, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();

          const lr = Math.round(color.r * 255);
          const lg = Math.round(color.g * 255);
          const lb = Math.round(color.b * 255);
          ctx.fillStyle = intensity > 0.05 ? `rgba(${lr}, ${lg}, ${lb}, ${intensity})` : '#141418';
          ctx.beginPath();
          ctx.arc(0, 0, 7, 0, Math.PI * 2);
          ctx.fill();
        } else {
          // Barra o Rettangolo generico
          ctx.beginPath();
          ctx.roundRect(-16, -10, 32, 20, 4);
          ctx.fill();
          ctx.stroke();
        }

        // ID / Indirizzo DMX sotto l'icona
        ctx.shadowBlur = 0;
        ctx.fillStyle = isSelected ? '#ffffff' : '#a1a1aa';
        ctx.font = `bold ${10 / viewTransform.scale}px -apple-system, BlinkMacSystemFont, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(fix.name || `U${fix.universe}:${fix.address}`, 0, 30);

        ctx.restore();
      });

      // 5. Disegna Rettangolo di selezione elastica (Rubberband selection)
      const inter = interactionRef.current;
      if (inter.isBoxSelecting) {
        const start = inter.boxStart;
        const current = inter.boxCurrent;
        const boxX = Math.min(start.x, current.x);
        const boxY = Math.min(start.y, current.y);
        const boxW = Math.abs(current.x - start.x);
        const boxH = Math.abs(current.y - start.y);

        ctx.save();
        ctx.strokeStyle = '#0a84ff';
        ctx.lineWidth = 1 / viewTransform.scale;
        ctx.setLineDash([4, 4]);
        ctx.fillStyle = 'rgba(10, 132, 255, 0.12)';
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);
        ctx.restore();
      }

      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationFrameId);
  }, [fixtures, selectedIds, viewTransform, trusses]);

  // Gestione eventi Mouse
  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const worldPos = screenToWorld(mouseX, mouseY);
    const inter = interactionRef.current;

    // Tasto centrale o Spazio premuto -> Pan
    if (e.button === 1 || inter.spacePressed || e.button === 2) {
      inter.isPanning = true;
      inter.panStart = { x: e.clientX - viewTransform.x, y: e.clientY - viewTransform.y };
      return;
    }

    if (e.button === 0) {
      // Controlla se abbiamo cliccato sopra un faro (hit testing)
      const clickedFix = fixtures.find((f) => {
        const dist = Math.hypot(f.position.x - worldPos.x, f.position.y - worldPos.y);
        return dist <= 24;
      });

      if (clickedFix) {
        inter.isDraggingFixture = true;
        inter.draggedFixtureId = clickedFix.id;
        inter.dragStartPos = { x: worldPos.x - clickedFix.position.x, y: worldPos.y - clickedFix.position.y };

        if (e.shiftKey || e.metaKey || e.ctrlKey) {
          // Selezione additiva
          const newSelected = selectedIds.includes(clickedFix.id)
            ? selectedIds.filter((id) => id !== clickedFix.id)
            : [...selectedIds, clickedFix.id];
          onSelectionChange && onSelectionChange(newSelected);
        } else {
          // Selezione singola
          if (!selectedIds.includes(clickedFix.id)) {
            onSelectionChange && onSelectionChange([clickedFix.id]);
          }
        }
      } else {
        // Cliccato sul vuoto -> Avvia Selezione Rettangolare (Rubberband)
        inter.isBoxSelecting = true;
        inter.boxStart = worldPos;
        inter.boxCurrent = worldPos;

        if (!e.shiftKey && !e.metaKey && !e.ctrlKey) {
          onSelectionChange && onSelectionChange([]);
        }
      }
    }
  };

  const handleMouseMove = (e) => {
    const inter = interactionRef.current;
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const worldPos = screenToWorld(mouseX, mouseY);

    // Pan in corso
    if (inter.isPanning) {
      setViewTransform((prev) => ({
        ...prev,
        x: e.clientX - inter.panStart.x,
        y: e.clientY - inter.panStart.y,
      }));
      return;
    }

    // Drag proiettore
    if (inter.isDraggingFixture && inter.draggedFixtureId) {
      const newX = Math.round(worldPos.x - inter.dragStartPos.x);
      const newY = Math.round(worldPos.y - inter.dragStartPos.y);

      onFixtureMove && onFixtureMove(inter.draggedFixtureId, newX, newY);
      return;
    }

    // Selezione elastica rettangolare
    if (inter.isBoxSelecting) {
      inter.boxCurrent = worldPos;
      const x1 = Math.min(inter.boxStart.x, worldPos.x);
      const y1 = Math.min(inter.boxStart.y, worldPos.y);
      const x2 = Math.max(inter.boxStart.x, worldPos.x);
      const y2 = Math.max(inter.boxStart.y, worldPos.y);

      const insideIds = fixtures
        .filter((f) => f.position.x >= x1 && f.position.x <= x2 && f.position.y >= y1 && f.position.y <= y2)
        .map((f) => f.id);

      onSelectionChange && onSelectionChange(insideIds);
    }
  };

  const handleMouseUp = () => {
    const inter = interactionRef.current;
    inter.isPanning = false;
    inter.isDraggingFixture = false;
    inter.draggedFixtureId = null;
    inter.isBoxSelecting = false;
  };

  // Zoom tramite rotella mouse centrata sul cursore
  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    const newScale = Math.min(3.0, Math.max(0.3, viewTransform.scale * zoomFactor));

    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    setViewTransform((prev) => ({
      scale: newScale,
      x: mouseX - (mouseX - prev.x) * (newScale / prev.scale),
      y: mouseY - (mouseY - prev.y) * (newScale / prev.scale),
    }));
  };

  return (
    <div ref={containerRef} className="relative flex-1 h-full w-full overflow-hidden select-none bg-[#0f0f12]">
      {/* Canvas Element */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onContextMenu={(e) => e.preventDefault()}
        className="w-full h-full block"
      />

      {/* Toolbar Inferiore: Zoom & View Reset HUD (Lightkey Style) */}
      <div className="absolute bottom-4 right-4 flex items-center space-x-1.5 p-1 bg-[#1a1a20]/90 border border-[#33333e] rounded-lg shadow-xl backdrop-blur-md">
        <MacButton
          variant="toolbar"
          size="sm"
          icon={ZoomOut}
          title="Zoom Out"
          onClick={() =>
            setViewTransform((prev) => ({
              ...prev,
              scale: Math.max(0.3, prev.scale * 0.85),
            }))
          }
        />
        <span className="font-mono text-[11px] text-zinc-300 px-1 w-12 text-center">
          {Math.round(viewTransform.scale * 100)}%
        </span>
        <MacButton
          variant="toolbar"
          size="sm"
          icon={ZoomIn}
          title="Zoom In"
          onClick={() =>
            setViewTransform((prev) => ({
              ...prev,
              scale: Math.min(3.0, prev.scale * 1.15),
            }))
          }
        />
        <div className="h-4 w-[1px] bg-zinc-700" />
        <MacButton
          variant="toolbar"
          size="sm"
          icon={Maximize}
          title="Centra Palco"
          onClick={() => setViewTransform({ x: 80, y: 60, scale: 1.0 })}
        />
      </div>

      {/* Floating Add Truss & Fixtures Toolbar in alto a sinistra */}
      <div className="absolute top-4 left-4 flex items-center space-x-2">
        <MacButton
          variant="default"
          size="sm"
          icon={Plus}
          onClick={onAddFixture}
          title="Aggiungi Proiettore al Palco"
        >
          Aggiungi Faro
        </MacButton>
        <span className="text-[11px] text-zinc-400 bg-black/50 px-2 py-1 rounded border border-zinc-800">
          {fixtures.length} fari ({selectedIds.length} selezionati)
        </span>
      </div>
    </div>
  );
}
