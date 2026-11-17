/**
 * VideoCue.js — Modello per le Video Cue di QLab 5 in ShowSuite
 * 
 * Supporta:
 * - Assegnazione allo Stage virtuale target (stageId)
 * - File video / media stream (hardware-accelerated)
 * - Punti di In e Out (inPoint, outPoint)
 * - Vari-speed playback rate e contatore loop
 * - Geometria e trasformazioni 2D: Translation (X, Y), Scale (X, Y), Rotation (gradi)
 * - Opacità (0..1) e modalità di fusione (blendMode)
 * - Ordinamento a livelli (Layer 1..1000)
 * - Modalità proporzioni Aspect Ratio ('fit', 'fill', 'stretch', 'custom')
 */

import BaseCue from '../BaseCue.js';
import { CueType } from '../CueTypes.js';

export default class VideoCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.VIDEO,
    });

    this.filePath = options.filePath || options.targetId || null;
    this.stageId = options.stageId || 'stage_main';
    this.layer = options.layer !== undefined ? Math.max(1, parseInt(options.layer, 10)) : 1;

    // Dimensioni native del video
    this.videoWidth = Math.max(1, parseInt(options.videoWidth, 10) || 1920);
    this.videoHeight = Math.max(1, parseInt(options.videoHeight, 10) || 1080);

    // Modalità di adattamento aspect ratio: 'fit' | 'fill' | 'stretch' | 'custom'
    this.aspectRatioMode = options.aspectRatioMode || 'fit';

    // Trasformazioni geometriche
    this.translation = {
      x: options.translation?.x !== undefined ? Number(options.translation.x) : 0,
      y: options.translation?.y !== undefined ? Number(options.translation.y) : 0,
    };

    this.scale = {
      x: options.scale?.x !== undefined ? Number(options.scale.x) : 1.0,
      y: options.scale?.y !== undefined ? Number(options.scale.y) : 1.0,
    };

    this.rotation = options.rotation !== undefined ? Number(options.rotation) : 0; // gradi
    this.opacity = options.opacity !== undefined ? Math.max(0, Math.min(1, Number(options.opacity))) : 1.0;
    this.blendMode = options.blendMode || 'normal'; // 'normal' | 'add' | 'screen' | 'multiply' | etc.

    // Hardware acceleration flag
    this.hardwareAccelerated = options.hardwareAccelerated !== undefined ? Boolean(options.hardwareAccelerated) : true;

    // Punti di In / Out e timing
    this.inPoint = Math.max(0, Number(options.inPoint) || 0);
    this.outPoint = options.outPoint !== undefined ? Number(options.outPoint) : (this.duration || 10.0);
    if (this.outPoint <= this.inPoint) {
      this.outPoint = this.inPoint + (this.duration || 10.0);
    }

    this.playbackRate = options.playbackRate !== undefined ? Math.max(0.1, Number(options.playbackRate)) : 1.0;
    this.playCount = Math.max(1, parseInt(options.playCount, 10) || 1);
    this.infiniteLoop = Boolean(options.infiniteLoop);

    this.updateEffectiveDuration();
  }

  updateEffectiveDuration() {
    const rawSpan = Math.max(0.01, this.outPoint - this.inPoint);
    const speed = Math.max(0.1, this.playbackRate);
    if (this.infiniteLoop) {
      this.duration = Infinity;
    } else {
      this.duration = (rawSpan / speed) * this.playCount;
    }
  }

  setTranslation(x, y) {
    this.translation.x = Number(x) || 0;
    this.translation.y = Number(y) || 0;
  }

  setScale(x, y = x) {
    this.scale.x = Number(x) || 1.0;
    this.scale.y = Number(y) || 1.0;
  }

  setRotation(degrees) {
    this.rotation = Number(degrees) || 0;
  }

  setOpacity(val) {
    this.opacity = Math.max(0, Math.min(1, Number(val)));
  }

  setBlendMode(mode) {
    this.blendMode = mode || 'normal';
  }

  setStage(stageId) {
    this.stageId = stageId;
  }

  setLayer(layerNum) {
    this.layer = Math.max(1, parseInt(layerNum, 10) || 1);
  }

  /**
   * Rendering del frame video sul contesto 2D dello Stage
   * (invocato dal VideoStage dopo l'applicazione di translate, rotate, scale, opacity)
   * 
   * @param {CanvasRenderingContext2D} ctx 
   * @param {number} stageW 
   * @param {number} stageH 
   */
  renderLayer(ctx, stageW, stageH) {
    let drawW = this.videoWidth;
    let drawH = this.videoHeight;

    if (this.aspectRatioMode === 'fit') {
      const scale = Math.min(stageW / this.videoWidth, stageH / this.videoHeight);
      drawW = this.videoWidth * scale;
      drawH = this.videoHeight * scale;
    } else if (this.aspectRatioMode === 'fill') {
      const scale = Math.max(stageW / this.videoWidth, stageH / this.videoHeight);
      drawW = this.videoWidth * scale;
      drawH = this.videoHeight * scale;
    } else if (this.aspectRatioMode === 'stretch') {
      drawW = stageW;
      drawH = stageH;
    }

    const halfW = drawW / 2;
    const halfH = drawH / 2;

    // Se esiste un frame video reale (HTMLVideoElement / ImageBitmap), disegnalo
    if (this.videoElement && typeof ctx.drawImage === 'function') {
      try {
        ctx.drawImage(this.videoElement, -halfW, -halfH, drawW, drawH);
        return;
      } catch {
        // Fallback al placeholder grafico
      }
    }

    // Render placeholder video professionale
    ctx.fillStyle = '#0a1628';
    ctx.strokeStyle = '#0a84ff';
    ctx.lineWidth = 2;
    ctx.fillRect(-halfW, -halfH, drawW, drawH);
    ctx.strokeRect(-halfW, -halfH, drawW, drawH);

    // Griglia/croce video centrale
    ctx.strokeStyle = '#0a84ff44';
    ctx.beginPath();
    ctx.moveTo(-halfW, 0);
    ctx.lineTo(halfW, 0);
    ctx.moveTo(0, -halfH);
    ctx.lineTo(0, halfH);
    ctx.stroke();

    // Etichetta testuale
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.name || 'Video Layer', 0, -10);

    ctx.fillStyle = '#8e8e93';
    ctx.font = '12px sans-serif';
    const filename = this.filePath ? this.filePath.split(/[\\/]/).pop() : 'No Media Assigned';
    ctx.fillText(`${filename} • ${this.videoWidth}x${this.videoHeight} • Layer ${this.layer}`, 0, 14);
  }

  toJSON() {
    return {
      ...super.toJSON(),
      filePath: this.filePath,
      stageId: this.stageId,
      layer: this.layer,
      videoWidth: this.videoWidth,
      videoHeight: this.videoHeight,
      aspectRatioMode: this.aspectRatioMode,
      translation: this.translation,
      scale: this.scale,
      rotation: this.rotation,
      opacity: this.opacity,
      blendMode: this.blendMode,
      hardwareAccelerated: this.hardwareAccelerated,
      inPoint: this.inPoint,
      outPoint: this.outPoint,
      playbackRate: this.playbackRate,
      playCount: this.playCount,
      infiniteLoop: this.infiniteLoop,
    };
  }
}
