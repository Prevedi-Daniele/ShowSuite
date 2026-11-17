/**
 * VideoStage.js — Modello per il concetto di 'Stages' di QLab 5
 * 
 * In QLab 5, uno Stage è una superficie virtuale di rendering a cui vengono indirizzate
 * le Video Cue, le Text Cue e le Camera Cue.
 * 
 * Ogni Stage:
 * - Ha dimensioni arbitrarie (es. 1920x1080 standard, 3840x1080 per blend a 2 proiettori, LED wall panoramici)
 * - Mappa porzioni o l'intera superficie su uscite fisiche monitor / schermi (Displays)
 * - Compone i livelli (Layers) ordinati dal più basso al più alto
 */

import { StageGeometry } from './StageGeometry.js';

export default class VideoStage {
  constructor(options = {}) {
    this.id = options.id || `stage_${Date.now()}`;
    this.name = options.name || 'Main Stage';
    this.width = Math.max(320, parseInt(options.width, 10) || 1920);
    this.height = Math.max(240, parseInt(options.height, 10) || 1080);

    // Mappatura verso schermi fisici monitor (Displays)
    const rawMappings = Array.isArray(options.screenMappings) && options.screenMappings.length > 0
      ? options.screenMappings
      : [
          {
            screenId: 'display_1',
            screenName: 'Display 1 (Primary)',
            stageX: 0,
            stageY: 0,
            stageWidth: this.width,
            stageHeight: this.height,
            rotation: 0,
            enabled: true,
          },
        ];

    this.screenMappings = rawMappings.map((m) => ({
      ...m,
      geometry: m.geometry instanceof StageGeometry
        ? m.geometry
        : new StageGeometry({
            width: m.stageWidth || this.width,
            height: m.stageHeight || this.height,
            ...(m.geometry || {}),
          }),
    }));

    // Colore di sfondo dello stage
    this.backgroundColor = options.backgroundColor || '#000000';
  }

  setDimensions(width, height) {
    this.width = Math.max(320, parseInt(width, 10) || 1920);
    this.height = Math.max(240, parseInt(height, 10) || 1080);
  }

  addScreenMapping(mapping) {
    const stageW = Math.min(this.width, mapping.stageWidth || this.width);
    const stageH = Math.min(this.height, mapping.stageHeight || this.height);
    const newMapping = {
      screenId: mapping.screenId || `display_${Date.now()}`,
      screenName: mapping.screenName || 'Display',
      stageX: Math.max(0, mapping.stageX || 0),
      stageY: Math.max(0, mapping.stageY || 0),
      stageWidth: stageW,
      stageHeight: stageH,
      rotation: mapping.rotation || 0,
      enabled: mapping.enabled !== undefined ? Boolean(mapping.enabled) : true,
      geometry: mapping.geometry instanceof StageGeometry
        ? mapping.geometry
        : new StageGeometry({
            width: stageW,
            height: stageH,
            ...(mapping.geometry || {}),
          }),
    };
    this.screenMappings.push(newMapping);
    return newMapping;
  }

  removeScreenMapping(screenId) {
    this.screenMappings = this.screenMappings.filter((m) => m.screenId !== screenId);
  }

  updateScreenMapping(screenId, patch) {
    const mapping = this.screenMappings.find((m) => m.screenId === screenId);
    if (mapping) {
      Object.assign(mapping, patch);
    }
  }

  /**
   * Ordina e filtra le cue video attive assegnate a questo Stage
   * e le ordina per Layer (dal più basso al più alto)
   * 
   * @param {Array<Object>} activeCues Elenco delle cue attive
   * @returns {Array<Object>} Cue ordinate per layer
   */
  getSortedLayers(activeCues = []) {
    return activeCues
      .filter((cue) => cue.stageId === this.id && cue.state === 'running')
      .sort((a, b) => (a.layer || 1) - (b.layer || 1));
  }

  /**
   * Rendering composito dei layer su un contesto Canvas 2D
   * 
   * @param {CanvasRenderingContext2D} ctx Contesto 2D su cui disegnare
   * @param {Array<Object>} activeCues Cue video/text/camera attive
   */
  render(ctx, activeCues = []) {
    if (!ctx) return;

    // 1. Sfondo stage
    ctx.fillStyle = this.backgroundColor;
    ctx.fillRect(0, 0, this.width, this.height);

    // 2. Disegno dei layer ordinati per livello (layer 1..N)
    const layers = this.getSortedLayers(activeCues);
    for (const cue of layers) {
      ctx.save();

      // Posizionamento al centro dello stage + offset translation
      const centerX = this.width / 2 + (cue.translation?.x || 0);
      const centerY = this.height / 2 + (cue.translation?.y || 0);
      ctx.translate(centerX, centerY);

      // Rotazione
      if (cue.rotation) {
        ctx.rotate((cue.rotation * Math.PI) / 180);
      }

      // Scala
      const sx = cue.scale?.x !== undefined ? cue.scale.x : (cue.scale || 1.0);
      const sy = cue.scale?.y !== undefined ? cue.scale.y : (cue.scale || 1.0);
      ctx.scale(sx, sy);

      // Opacità e Blend Mode
      ctx.globalAlpha = Math.max(0, Math.min(1, cue.opacity !== undefined ? cue.opacity : 1.0));
      if (cue.blendMode && cue.blendMode !== 'normal') {
        ctx.globalCompositeOperation = cue.blendMode;
      }

      // Disegno specifico per tipo di cue
      if (typeof cue.renderLayer === 'function') {
        cue.renderLayer(ctx, this.width, this.height);
      } else if (typeof cue.renderText === 'function') {
        cue.renderText(ctx);
      } else {
        // Placeholder visivo ad alta visibilità se la sorgente è virtuale/mock
        this._renderPlaceholderLayer(ctx, cue);
      }

      ctx.restore();
    }
  }

  _renderPlaceholderLayer(ctx, cue) {
    const w = 480;
    const h = 270;
    ctx.fillStyle = cue.type === 'video' ? '#0a84ff33' : '#30d15833';
    ctx.strokeStyle = cue.type === 'video' ? '#0a84ff' : '#30d158';
    ctx.lineWidth = 2;
    ctx.fillRect(-w / 2, -h / 2, w, h);
    ctx.strokeRect(-w / 2, -h / 2, w, h);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${cue.name || 'Media Layer'} [${cue.type?.toUpperCase()}]`, 0, 0);
  }

  toJSON() {
    return {
      id: this.id,
      name: this.name,
      width: this.width,
      height: this.height,
      backgroundColor: this.backgroundColor,
      screenMappings: this.screenMappings.map((m) => ({
        ...m,
        geometry: m.geometry?.toJSON ? m.geometry.toJSON() : m.geometry,
      })),
    };
  }
}
