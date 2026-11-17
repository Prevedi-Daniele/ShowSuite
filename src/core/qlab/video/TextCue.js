/**
 * TextCue.js — Modello per le Text Cues (Titoli, Sottotitoli, Grafiche di testo) di QLab 5
 * 
 * Supporta:
 * - Rendering tipografico avanzato su VideoStage
 * - Testo multi-riga con gestione di interlinea (lineHeight) e allineamento (left, center, right)
 * - Famiglia di font, dimensione, spessore (weight), stile (corsivo/normale)
 * - Colore testo, ombreggiatura morbida (drop shadow: blur, offset, colore)
 * - Riquadro di sfondo personalizzabile (colore, padding, border radius)
 * - Geometria completa: translation, scale, rotation, opacity, layer
 */

import BaseCue from '../BaseCue.js';
import { CueType } from '../CueTypes.js';

export default class TextCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.TEXT,
    });

    this.stageId = options.stageId || 'stage_main';
    this.layer = options.layer !== undefined ? Math.max(1, parseInt(options.layer, 10)) : 10;

    // Testo e tipografia
    this.text = options.text !== undefined ? String(options.text) : 'SHOWSUITE';
    this.fontFamily = options.fontFamily || '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
    this.fontSize = Math.max(8, parseInt(options.fontSize, 10) || 48);
    this.fontWeight = options.fontWeight || 'bold'; // 'normal' | 'bold' | '300' | '600' | etc.
    this.fontStyle = options.fontStyle || 'normal'; // 'normal' | 'italic'
    this.color = options.color || '#ffffff';
    this.alignment = options.alignment || 'center'; // 'left' | 'center' | 'right'
    this.lineHeight = options.lineHeight !== undefined ? Math.max(0.5, Number(options.lineHeight)) : 1.25;
    this.letterSpacing = options.letterSpacing !== undefined ? Number(options.letterSpacing) : 0;

    // Ombreggiatura (Drop Shadow)
    this.dropShadow = {
      enabled: options.dropShadow?.enabled !== undefined ? Boolean(options.dropShadow.enabled) : true,
      color: options.dropShadow?.color || 'rgba(0, 0, 0, 0.75)',
      blur: options.dropShadow?.blur !== undefined ? Number(options.dropShadow.blur) : 8,
      offsetX: options.dropShadow?.offsetX !== undefined ? Number(options.dropShadow.offsetX) : 2,
      offsetY: options.dropShadow?.offsetY !== undefined ? Number(options.dropShadow.offsetY) : 4,
    };

    // Riquadro di sfondo (Box background)
    this.background = {
      enabled: options.background?.enabled !== undefined ? Boolean(options.background.enabled) : false,
      color: options.background?.color || 'rgba(0, 0, 0, 0.6)',
      padding: options.background?.padding !== undefined ? Number(options.background.padding) : 16,
      borderRadius: options.background?.borderRadius !== undefined ? Number(options.background.borderRadius) : 8,
    };

    // Geometria e trasformazioni 2D
    this.translation = {
      x: options.translation?.x !== undefined ? Number(options.translation.x) : 0,
      y: options.translation?.y !== undefined ? Number(options.translation.y) : 0,
    };

    this.scale = {
      x: options.scale?.x !== undefined ? Number(options.scale.x) : 1.0,
      y: options.scale?.y !== undefined ? Number(options.scale.y) : 1.0,
    };

    this.rotation = options.rotation !== undefined ? Number(options.rotation) : 0;
    this.opacity = options.opacity !== undefined ? Math.max(0, Math.min(1, Number(options.opacity))) : 1.0;
    this.blendMode = options.blendMode || 'normal';
  }

  setText(newText) {
    this.text = String(newText || '');
  }

  setFont(fontFamily, fontSize, fontWeight = 'bold') {
    if (fontFamily) this.fontFamily = fontFamily;
    if (fontSize) this.fontSize = Math.max(8, parseInt(fontSize, 10));
    if (fontWeight) this.fontWeight = fontWeight;
  }

  setColor(hexOrRgba) {
    this.color = hexOrRgba;
  }

  setShadow(shadowOpts) {
    Object.assign(this.dropShadow, shadowOpts);
  }

  setBackground(bgOpts) {
    Object.assign(this.background, bgOpts);
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

  /**
   * Rendering tipografico del testo su Canvas 2D
   * 
   * @param {CanvasRenderingContext2D} ctx 
   * @param {number} stageW 
   * @param {number} stageH 
   */
  renderLayer(ctx, stageW, stageH) {
    if (!this.text) return;

    const lines = this.text.split('\n');
    const lineStep = this.fontSize * this.lineHeight;
    const totalTextHeight = lines.length * lineStep;

    ctx.font = `${this.fontStyle} ${this.fontWeight} ${this.fontSize}px ${this.fontFamily}`;

    // Misurazione della larghezza massima tra le righe per il box di sfondo
    let maxLineWidth = 0;
    for (const line of lines) {
      const metrics = ctx.measureText ? ctx.measureText(line) : { width: line.length * (this.fontSize * 0.6) };
      if (metrics.width > maxLineWidth) {
        maxLineWidth = metrics.width;
      }
    }

    // Disegno riquadro di sfondo se abilitato
    if (this.background.enabled) {
      const p = this.background.padding;
      const boxW = maxLineWidth + p * 2;
      const boxH = totalTextHeight + p * 2;
      const boxX = -boxW / 2;
      const boxY = -boxH / 2;
      const r = this.background.borderRadius;

      ctx.save();
      ctx.fillStyle = this.background.color;
      if (r > 0 && typeof ctx.roundRect === 'function') {
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, boxW, boxH, r);
        ctx.fill();
      } else {
        ctx.fillRect(boxX, boxY, boxW, boxH);
      }
      ctx.restore();
    }

    // Configurazione ombreggiatura (Drop Shadow)
    ctx.save();
    if (this.dropShadow.enabled) {
      ctx.shadowColor = this.dropShadow.color;
      ctx.shadowBlur = this.dropShadow.blur;
      ctx.shadowOffsetX = this.dropShadow.offsetX;
      ctx.shadowOffsetY = this.dropShadow.offsetY;
    }

    ctx.fillStyle = this.color;
    ctx.textAlign = this.alignment;
    ctx.textBaseline = 'middle';

    // Calcolo coordinata Y di partenza per centrare il blocco di testo
    const startY = -(totalTextHeight / 2) + lineStep / 2;

    lines.forEach((line, index) => {
      const y = startY + index * lineStep;
      let x = 0;
      if (this.alignment === 'left') {
        x = -maxLineWidth / 2;
      } else if (this.alignment === 'right') {
        x = maxLineWidth / 2;
      }
      ctx.fillText(line, x, y);
    });

    ctx.restore();
  }

  toJSON() {
    return {
      ...super.toJSON(),
      stageId: this.stageId,
      layer: this.layer,
      text: this.text,
      fontFamily: this.fontFamily,
      fontSize: this.fontSize,
      fontWeight: this.fontWeight,
      fontStyle: this.fontStyle,
      color: this.color,
      alignment: this.alignment,
      lineHeight: this.lineHeight,
      letterSpacing: this.letterSpacing,
      dropShadow: this.dropShadow,
      background: this.background,
      translation: this.translation,
      scale: this.scale,
      rotation: this.rotation,
      opacity: this.opacity,
      blendMode: this.blendMode,
    };
  }
}
