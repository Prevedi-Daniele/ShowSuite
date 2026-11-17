/**
 * StageGeometry.js — Modello matematico e di calibrazione geometrica per Video Stages (QLab 5)
 * 
 * Gestisce:
 * 1. Corner Pinning / Keystone (4 punti di controllo prospettico per correggere proiezioni inclinate)
 * 2. Surface Warping (Griglia Bézier NxM di vertici deformabili per superfici curve, cilindri o schermi sagomati)
 * 3. Edge Blending (Maschere di dissolvenza con correzione gamma e black level compensation per proiettori sovrapposti)
 * 4. Calibrazione e generazione di Test Pattern professionali (Grid, Cerchi, Barre colore SMPTE, Checkerboard)
 */

export const TestPatternType = {
  NONE: 'none',
  GRID: 'grid',
  CIRCLES: 'circles',
  COLOR_BARS: 'color_bars',
  CHECKERBOARD: 'checkerboard',
  CROSSHAIR: 'crosshair',
  WHITE_UNIFORMITY: 'white_uniformity',
};

export class StageGeometry {
  constructor(options = {}) {
    this.width = Math.max(100, parseInt(options.width, 10) || 1920);
    this.height = Math.max(100, parseInt(options.height, 10) || 1080);

    // 1. CORNER PINNING (4 Angoli: TL, TR, BR, BL)
    // Coordinate assolute dei 4 vertici nello spazio di proiezione
    this.corners = Array.isArray(options.corners) && options.corners.length === 4
      ? options.corners.map((c) => ({ x: Number(c.x), y: Number(c.y) }))
      : this.getDefaultCorners();

    // Valori rapidi Keystone (-1.0 .. +1.0)
    this.keystone = {
      horizontal: Number(options.keystone?.horizontal) || 0,
      vertical: Number(options.keystone?.vertical) || 0,
    };

    // 2. SURFACE WARPING (Griglia di controllo NxM)
    this.gridRows = Math.max(2, Math.min(10, parseInt(options.gridRows, 10) || 4));
    this.gridCols = Math.max(2, Math.min(10, parseInt(options.gridCols, 10) || 4));
    this.mesh = Array.isArray(options.mesh) ? options.mesh : this.createDefaultMesh(this.gridRows, this.gridCols);

    // 3. EDGE BLENDING (4 Bordi: Left, Right, Top, Bottom)
    this.edgeBlend = {
      left: {
        enabled: Boolean(options.edgeBlend?.left?.enabled),
        width: Math.max(0, parseInt(options.edgeBlend?.left?.width, 10) || 200), // pixel di overlap
        gamma: Math.max(0.1, Number(options.edgeBlend?.left?.gamma) || 2.2),
        blackLevel: Math.max(0, Math.min(0.2, Number(options.edgeBlend?.left?.blackLevel) || 0.0)),
      },
      right: {
        enabled: Boolean(options.edgeBlend?.right?.enabled),
        width: Math.max(0, parseInt(options.edgeBlend?.right?.width, 10) || 200),
        gamma: Math.max(0.1, Number(options.edgeBlend?.right?.gamma) || 2.2),
        blackLevel: Math.max(0, Math.min(0.2, Number(options.edgeBlend?.right?.blackLevel) || 0.0)),
      },
      top: {
        enabled: Boolean(options.edgeBlend?.top?.enabled),
        width: Math.max(0, parseInt(options.edgeBlend?.top?.width, 10) || 150),
        gamma: Math.max(0.1, Number(options.edgeBlend?.top?.gamma) || 2.2),
        blackLevel: Math.max(0, Math.min(0.2, Number(options.edgeBlend?.top?.blackLevel) || 0.0)),
      },
      bottom: {
        enabled: Boolean(options.edgeBlend?.bottom?.enabled),
        width: Math.max(0, parseInt(options.edgeBlend?.bottom?.width, 10) || 150),
        gamma: Math.max(0.1, Number(options.edgeBlend?.bottom?.gamma) || 2.2),
        blackLevel: Math.max(0, Math.min(0.2, Number(options.edgeBlend?.bottom?.blackLevel) || 0.0)),
      },
    };

    // Test Pattern attivo
    this.activeTestPattern = options.activeTestPattern || TestPatternType.NONE;
    this.testPatternBrightness = options.testPatternBrightness !== undefined ? Number(options.testPatternBrightness) : 1.0;
  }

  getDefaultCorners() {
    return [
      { x: 0, y: 0 },                        // Top-Left (TL)
      { x: this.width, y: 0 },               // Top-Right (TR)
      { x: this.width, y: this.height },     // Bottom-Right (BR)
      { x: 0, y: this.height },              // Bottom-Left (BL)
    ];
  }

  resetCorners() {
    this.corners = this.getDefaultCorners();
    this.keystone = { horizontal: 0, vertical: 0 };
    this.rebuildMeshFromCorners();
  }

  setCorner(index, x, y) {
    if (index >= 0 && index < 4) {
      this.corners[index] = {
        x: Math.round(Number(x)),
        y: Math.round(Number(y)),
      };
      this.rebuildMeshFromCorners();
    }
  }

  /**
   * Applica correzione Keystone orizzontale o verticale calcolando gli offset dei 4 angoli
   * 
   * @param {number} h Keystone orizzontale (-1.0 .. +1.0)
   * @param {number} v Keystone verticale (-1.0 .. +1.0)
   */
  setKeystone(h, v) {
    this.keystone.horizontal = Math.max(-1, Math.min(1, Number(h) || 0));
    this.keystone.vertical = Math.max(-1, Math.min(1, Number(v) || 0));

    const maxShiftX = this.width * 0.25;
    const maxShiftY = this.height * 0.25;

    const baseCorners = this.getDefaultCorners();
    const shiftH = this.keystone.horizontal * maxShiftX;
    const shiftV = this.keystone.vertical * maxShiftY;

    // Keystone orizzontale: stringe/allarga i lati superiore o inferiore
    // Keystone verticale: stringe/allarga i lati sinistro o destro
    this.corners = [
      { x: baseCorners[0].x + (shiftH > 0 ? shiftH : 0), y: baseCorners[0].y + (shiftV > 0 ? shiftV : 0) },
      { x: baseCorners[1].x - (shiftH > 0 ? shiftH : 0), y: baseCorners[1].y + (shiftV < 0 ? -shiftV : 0) },
      { x: baseCorners[2].x - (shiftH < 0 ? -shiftH : 0), y: baseCorners[2].y - (shiftV < 0 ? -shiftV : 0) },
      { x: baseCorners[3].x + (shiftH < 0 ? -shiftH : 0), y: baseCorners[3].y - (shiftV > 0 ? shiftV : 0) },
    ];

    this.rebuildMeshFromCorners();
  }

  /**
   * Inizializza o ridimensiona la mesh di warping a griglia (NxM)
   * 
   * @param {number} rows Numero di righe vertici (min 2, max 10)
   * @param {number} cols Numero di colonne vertici (min 2, max 10)
   */
  createDefaultMesh(rows, cols) {
    const mesh = [];
    for (let r = 0; r < rows; r++) {
      const row = [];
      const vNorm = r / (rows - 1);
      for (let c = 0; c < cols; c++) {
        const uNorm = c / (cols - 1);
        row.push({
          u: uNorm, // coordinate normalizzate UV di sorgente (0..1)
          v: vNorm,
          x: uNorm * this.width, // coordinate di output deformate
          y: vNorm * this.height,
        });
      }
      mesh.push(row);
    }
    return mesh;
  }

  setGridDensity(rows, cols) {
    this.gridRows = Math.max(2, Math.min(10, parseInt(rows, 10) || 4));
    this.gridCols = Math.max(2, Math.min(10, parseInt(cols, 10) || 4));
    this.rebuildMeshFromCorners();
  }

  /**
   * Ricalcola i punti interni della mesh interpolando bilinearemente i 4 angoli attivi
   */
  rebuildMeshFromCorners() {
    const [tl, tr, br, bl] = this.corners;
    const mesh = [];
    for (let r = 0; r < this.gridRows; r++) {
      const v = r / (this.gridRows - 1);
      const row = [];
      for (let c = 0; c < this.gridCols; c++) {
        const u = c / (this.gridCols - 1);

        // Interpolazione bilineare dai 4 vertici
        const topX = tl.x + u * (tr.x - tl.x);
        const topY = tl.y + u * (tr.y - tl.y);
        const btmX = bl.x + u * (br.x - bl.x);
        const btmY = bl.y + u * (br.y - bl.y);

        const x = topX + v * (btmX - topX);
        const y = topY + v * (btmY - topY);

        row.push({ u, v, x: Math.round(x), y: Math.round(y) });
      }
      mesh.push(row);
    }
    this.mesh = mesh;
  }

  setMeshPoint(r, c, x, y) {
    if (r >= 0 && r < this.gridRows && c >= 0 && c < this.gridCols) {
      this.mesh[r][c].x = Math.round(Number(x));
      this.mesh[r][c].y = Math.round(Number(y));

      // Se il punto modificato è un angolo, aggiorna anche this.corners
      if (r === 0 && c === 0) this.corners[0] = { x, y };
      if (r === 0 && c === this.gridCols - 1) this.corners[1] = { x, y };
      if (r === this.gridRows - 1 && c === this.gridCols - 1) this.corners[2] = { x, y };
      if (r === this.gridRows - 1 && c === 0) this.corners[3] = { x, y };
    }
  }

  resetMesh() {
    this.rebuildMeshFromCorners();
  }

  // --- EDGE BLENDING ---

  setEdgeBlend(edge, patch) {
    if (this.edgeBlend[edge]) {
      Object.assign(this.edgeBlend[edge], patch);
    }
  }

  /**
   * Calcola il fattore di attenuazione Edge Blend (0.0 .. 1.0)
   * applicando la curva di gamma e il black level compensation
   * 
   * @param {number} x Coordinata X (pixel)
   * @param {number} y Coordinata Y (pixel)
   * @returns {number} Luminanza moltiplicativa (0.0 .. 1.0)
   */
  getEdgeBlendFactor(x, y) {
    let factor = 1.0;

    // Bordo Sinistro
    const left = this.edgeBlend.left;
    if (left.enabled && left.width > 0 && x < left.width) {
      const t = x / left.width; // 0 (bordo esterno) -> 1 (fine overlap)
      const f = left.blackLevel + (1 - left.blackLevel) * Math.pow(t, left.gamma);
      factor = Math.min(factor, f);
    }

    // Bordo Destro
    const right = this.edgeBlend.right;
    if (right.enabled && right.width > 0 && x > this.width - right.width) {
      const t = (this.width - x) / right.width; // 1 -> 0
      const f = right.blackLevel + (1 - right.blackLevel) * Math.pow(t, right.gamma);
      factor = Math.min(factor, f);
    }

    // Bordo Superiore
    const top = this.edgeBlend.top;
    if (top.enabled && top.width > 0 && y < top.width) {
      const t = y / top.width;
      const f = top.blackLevel + (1 - top.blackLevel) * Math.pow(t, top.gamma);
      factor = Math.min(factor, f);
    }

    // Bordo Inferiore
    const btm = this.edgeBlend.bottom;
    if (btm.enabled && btm.width > 0 && y > this.height - btm.width) {
      const t = (this.height - y) / btm.width;
      const f = btm.blackLevel + (1 - btm.blackLevel) * Math.pow(t, btm.gamma);
      factor = Math.min(factor, f);
    }

    return Math.max(0, Math.min(1, factor));
  }

  /**
   * Disegna la maschera Edge Blending su un contesto Canvas 2D
   * (usando gradienti lineari neri con blending composito)
   * 
   * @param {CanvasRenderingContext2D} ctx 
   */
  renderEdgeBlendMask(ctx) {
    if (!ctx) return;

    ctx.save();
    // Bordo Sinistro
    if (this.edgeBlend.left.enabled && this.edgeBlend.left.width > 0) {
      const w = this.edgeBlend.left.width;
      const grad = ctx.createLinearGradient(0, 0, w, 0);
      grad.addColorStop(0, 'rgba(0,0,0,1)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, this.height);
    }

    // Bordo Destro
    if (this.edgeBlend.right.enabled && this.edgeBlend.right.width > 0) {
      const w = this.edgeBlend.right.width;
      const grad = ctx.createLinearGradient(this.width, 0, this.width - w, 0);
      grad.addColorStop(0, 'rgba(0,0,0,1)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(this.width - w, 0, w, this.height);
    }

    // Bordo Superiore
    if (this.edgeBlend.top.enabled && this.edgeBlend.top.width > 0) {
      const h = this.edgeBlend.top.width;
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(0,0,0,1)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, this.width, h);
    }

    // Bordo Inferiore
    if (this.edgeBlend.bottom.enabled && this.edgeBlend.bottom.width > 0) {
      const h = this.edgeBlend.bottom.width;
      const grad = ctx.createLinearGradient(0, this.height, 0, this.height - h);
      grad.addColorStop(0, 'rgba(0,0,0,1)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, this.height - h, this.width, h);
    }

    ctx.restore();
  }

  // --- TEST PATTERNS ---

  /**
   * Renderizza uno dei test pattern professionali per calibrazione su Canvas
   * 
   * @param {CanvasRenderingContext2D} ctx 
   * @param {string} patternType 
   */
  renderTestPattern(ctx, patternType = this.activeTestPattern) {
    if (!ctx || patternType === TestPatternType.NONE) return;

    ctx.save();
    ctx.globalAlpha = this.testPatternBrightness;

    const w = this.width;
    const h = this.height;

    switch (patternType) {
      case TestPatternType.GRID: {
        // Sfondo grigio scuro
        ctx.fillStyle = '#111115';
        ctx.fillRect(0, 0, w, h);

        const step = 80;
        ctx.strokeStyle = '#2d2d38';
        ctx.lineWidth = 1;

        // Linee secondarie
        ctx.beginPath();
        for (let x = 0; x <= w; x += step) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
        }
        for (let y = 0; y <= h; y += step) {
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
        }
        ctx.stroke();

        // Linee assi principali centrali (ciano / rosso)
        ctx.strokeStyle = '#0a84ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(w / 2, 0);
        ctx.lineTo(w / 2, h);
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();

        // Diagonali per verifica linearità angolare
        ctx.strokeStyle = '#ff9f0a44';
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(w, h);
        ctx.moveTo(w, 0);
        ctx.lineTo(0, h);
        ctx.stroke();

        // Testo risoluzione centrale
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 22px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${w} × ${h} [ALIGNMENT GRID]`, w / 2, h / 2 - 24);
        break;
      }

      case TestPatternType.CIRCLES: {
        // Sfondo nero
        ctx.fillStyle = '#0a0a0c';
        ctx.fillRect(0, 0, w, h);

        const cx = w / 2;
        const cy = h / 2;
        const maxRadius = Math.min(w, h) * 0.45;

        // Cerchi concentrici
        const circleRadii = [0.2, 0.4, 0.6, 0.8, 1.0];
        circleRadii.forEach((factor, idx) => {
          ctx.strokeStyle = idx === circleRadii.length - 1 ? '#30d158' : '#0a84ff';
          ctx.lineWidth = idx === circleRadii.length - 1 ? 3 : 1.5;
          ctx.beginPath();
          ctx.arc(cx, cy, maxRadius * factor, 0, Math.PI * 2);
          ctx.stroke();
        });

        // Croce centrale con mirino
        ctx.strokeStyle = '#ff453a';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx - 40, cy);
        ctx.lineTo(cx + 40, cy);
        ctx.moveTo(cx, cy - 40);
        ctx.lineTo(cx, cy + 40);
        ctx.stroke();

        // Angoli di riferimento
        const cornerSize = 100;
        ctx.strokeStyle = '#ffd60a';
        ctx.lineWidth = 3;
        ctx.strokeRect(20, 20, cornerSize, cornerSize);
        ctx.strokeRect(w - 20 - cornerSize, 20, cornerSize, cornerSize);
        ctx.strokeRect(w - 20 - cornerSize, h - 20 - cornerSize, cornerSize, cornerSize);
        ctx.strokeRect(20, h - 20 - cornerSize, cornerSize, cornerSize);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 18px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`CIRCULAR CONVERGENCE & ASPECT RATIO TEST`, cx, cy + 50);
        break;
      }

      case TestPatternType.COLOR_BARS: {
        // 8 Barre Colore Standard SMPTE: White, Yellow, Cyan, Green, Magenta, Red, Blue, Black
        const colors = [
          '#ffffff', // 100% White
          '#ffff00', // Yellow
          '#00ffff', // Cyan
          '#00ff00', // Green
          '#ff00ff', // Magenta
          '#ff0000', // Red
          '#0000ff', // Blue
          '#000000', // Black
        ];
        const barW = w / colors.length;
        const barH = h * 0.75;

        colors.forEach((col, i) => {
          ctx.fillStyle = col;
          ctx.fillRect(i * barW, 0, barW, barH);
        });

        // Sezione inferiore in scala di grigi (10 passi)
        const stepW = w / 10;
        const btmH = h - barH;
        for (let i = 0; i < 10; i++) {
          const luma = Math.round((i / 9) * 255);
          ctx.fillStyle = `rgb(${luma}, ${luma}, ${luma})`;
          ctx.fillRect(i * stepW, barH, stepW, btmH);
        }
        break;
      }

      case TestPatternType.CHECKERBOARD: {
        const sq = 64;
        const cols = Math.ceil(w / sq);
        const rows = Math.ceil(h / sq);
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            ctx.fillStyle = (r + c) % 2 === 0 ? '#ffffff' : '#141416';
            ctx.fillRect(c * sq, r * sq, sq, sq);
          }
        }
        break;
      }

      case TestPatternType.CROSSHAIR: {
        ctx.fillStyle = '#050508';
        ctx.fillRect(0, 0, w, h);

        ctx.strokeStyle = '#30d158';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(w / 2, 0);
        ctx.lineTo(w / 2, h);
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();

        ctx.arc(w / 2, h / 2, 100, 0, Math.PI * 2);
        ctx.stroke();
        break;
      }

      case TestPatternType.WHITE_UNIFORMITY: {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, w, h);
        break;
      }

      default:
        break;
    }

    ctx.restore();
  }

  // --- RENDERING DELLA SUPERFICIE WARPED & CORNER PINNED ---

  /**
   * Esegue il rendering della mesh deformata su Canvas 2D.
   * Divide la mesh in quad/triangoli e disegna linee o texture deformate.
   * 
   * @param {CanvasRenderingContext2D} ctx Contesto target
   * @param {CanvasImageSource} [sourceImage] Immagine/canvas sorgente (opzionale)
   * @param {boolean} [drawWireframe=true] Se disegnare le linee della griglia mesh
   */
  renderWarpedSurface(ctx, sourceImage = null, drawWireframe = true) {
    if (!ctx) return;

    ctx.save();

    // Se fornito un test pattern attivo e nessuna immagine, disegnalo prima nel buffer
    if (this.activeTestPattern !== TestPatternType.NONE && !sourceImage) {
      this.renderTestPattern(ctx, this.activeTestPattern);
    }

    // Se esiste una sourceImage da proiettare
    if (sourceImage && typeof ctx.drawImage === 'function') {
      // Disegno quad-by-quad sulla mesh deformata
      for (let r = 0; r < this.gridRows - 1; r++) {
        for (let c = 0; c < this.gridCols - 1; c++) {
          const p0 = this.mesh[r][c];         // TL
          const p1 = this.mesh[r][c + 1];     // TR
          const p2 = this.mesh[r + 1][c + 1]; // BR
          const p3 = this.mesh[r + 1][c];     // BL

          const srcX = p0.u * this.width;
          const srcY = p0.v * this.height;
          const srcW = (p1.u - p0.u) * this.width;
          const srcH = (p3.v - p0.v) * this.height;

          // Rendering approssimato quad tramite clipping trapezoidale
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(p0.x, p0.y);
          ctx.lineTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.lineTo(p3.x, p3.y);
          ctx.closePath();
          ctx.clip();

          const minX = Math.min(p0.x, p1.x, p2.x, p3.x);
          const minY = Math.min(p0.y, p1.y, p2.y, p3.y);
          const maxX = Math.max(p0.x, p1.x, p2.x, p3.x);
          const maxY = Math.max(p0.y, p1.y, p2.y, p3.y);
          const dstW = Math.max(1, maxX - minX);
          const dstH = Math.max(1, maxY - minY);

          try {
            ctx.drawImage(sourceImage, srcX, srcY, srcW, srcH, minX, minY, dstW, dstH);
          } catch {
            // Ignora fallimenti su source fittizie
          }
          ctx.restore();
        }
      }
    }

    // Disegno wireframe mesh e punti di controllo
    if (drawWireframe) {
      ctx.strokeStyle = '#0a84ff88';
      ctx.lineWidth = 1.5;

      // Linee orizzontali
      for (let r = 0; r < this.gridRows; r++) {
        ctx.beginPath();
        ctx.moveTo(this.mesh[r][0].x, this.mesh[r][0].y);
        for (let c = 1; c < this.gridCols; c++) {
          ctx.lineTo(this.mesh[r][c].x, this.mesh[r][c].y);
        }
        ctx.stroke();
      }

      // Linee verticali
      for (let c = 0; c < this.gridCols; c++) {
        ctx.beginPath();
        ctx.moveTo(this.mesh[0][c].x, this.mesh[0][c].y);
        for (let r = 1; r < this.gridRows; r++) {
          ctx.lineTo(this.mesh[r][c].x, this.mesh[r][c].y);
        }
        ctx.stroke();
      }
    }

    // Applica maschera Edge Blending se presente
    this.renderEdgeBlendMask(ctx);

    ctx.restore();
  }

  toJSON() {
    return {
      width: this.width,
      height: this.height,
      corners: this.corners,
      keystone: this.keystone,
      gridRows: this.gridRows,
      gridCols: this.gridCols,
      mesh: this.mesh,
      edgeBlend: this.edgeBlend,
      activeTestPattern: this.activeTestPattern,
      testPatternBrightness: this.testPatternBrightness,
    };
  }

  fromJSON(json = {}) {
    if (json.width) this.width = json.width;
    if (json.height) this.height = json.height;
    if (Array.isArray(json.corners)) this.corners = json.corners;
    if (json.keystone) this.keystone = json.keystone;
    if (json.gridRows) this.gridRows = json.gridRows;
    if (json.gridCols) this.gridCols = json.gridCols;
    if (Array.isArray(json.mesh)) this.mesh = json.mesh;
    if (json.edgeBlend) this.edgeBlend = json.edgeBlend;
    if (json.activeTestPattern) this.activeTestPattern = json.activeTestPattern;
    if (json.testPatternBrightness !== undefined) this.testPatternBrightness = json.testPatternBrightness;
  }
}
