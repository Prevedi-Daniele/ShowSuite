/**
 * SMPTETimecode.js — Modello matematico SMPTE Timecode (SMPTE 12M standard) per ShowSuite
 * 
 * Supporta:
 * - Frame rate standard del settore broadcast e theatrical:
 *   - 24 fps (Cinema / Film)
 *   - 25 fps (EBU / PAL broadcast TV)
 *   - 29.97 fps (NTSC Drop-Frame e Non-Drop-Frame)
 *   - 30 fps (SMPTE standard / NTSC B&W)
 * - Conversione bidirezionale accurata tra Timecode (HH:MM:SS:FF.sub) e numero di frame lineari
 * - Gestione rigorosa del Drop-Frame (salto frame 0 e 1 all'inizio di ogni minuto tranne i multipli di 10)
 * - Operazioni aritmetiche (add, subtract, diff, compare) e interpolazione continua
 */

export const SMPTEFrameRate = {
  FPS_24: 24,
  FPS_25: 25,
  FPS_29_97: 29.97,
  FPS_30: 30,
};

export const MTC_RATE_CODES = {
  FPS_24: 0,     // 00 = 24 fps
  FPS_25: 1,     // 01 = 25 fps
  FPS_29_97_DF: 2, // 10 = 29.97 fps drop frame
  FPS_30: 3,     // 11 = 30 fps (e 29.97 non-drop)
};

export default class SMPTETimecode {
  constructor(hours = 0, minutes = 0, seconds = 0, frames = 0, subframes = 0, fps = SMPTEFrameRate.FPS_25, isDropFrame = false) {
    this.fps = fps === SMPTEFrameRate.FPS_29_97 ? 29.97 : Number(fps) || 25;
    this.isDropFrame = Boolean(isDropFrame);

    this.hours = Math.max(0, Math.min(23, Math.floor(hours)));
    this.minutes = Math.max(0, Math.min(59, Math.floor(minutes)));
    this.seconds = Math.max(0, Math.min(59, Math.floor(seconds)));
    this.frames = Math.max(0, Math.floor(frames));
    this.subframes = Math.max(0, Math.min(99, Math.floor(subframes))); // 0-99 subframes (centesimi di frame)

    this._normalize();
  }

  // ─── Normalizzazione & Validazione ─────────────────────────────

  get nominalFps() {
    if (this.fps === 29.97) return 30;
    return Math.round(this.fps);
  }

  _normalize() {
    const maxFrames = this.nominalFps;
    if (this.frames >= maxFrames) {
      const extraSec = Math.floor(this.frames / maxFrames);
      this.frames = this.frames % maxFrames;
      this.seconds += extraSec;
    }

    if (this.seconds >= 60) {
      const extraMin = Math.floor(this.seconds / 60);
      this.seconds = this.seconds % 60;
      this.minutes += extraMin;
    }

    if (this.minutes >= 60) {
      const extraHours = Math.floor(this.minutes / 60);
      this.minutes = this.minutes % 60;
      this.hours = (this.hours + extraHours) % 24;
    }

    // Se drop frame, verifica che non sia sui frame vietati (0 e 1 all'inizio del minuto non multiplo di 10)
    if (this.isDropFrame && this.seconds === 0 && this.minutes % 10 !== 0) {
      if (this.frames < 2) {
        this.frames = 2;
      }
    }
  }

  // ─── Conversioni: Frame Lineari ────────────────────────────────

  /**
   * Converte il timecode in numero totale di frame lineari dall'inizio (00:00:00:00 = 0)
   */
  toFrames() {
    const nominal = this.nominalFps;

    if (!this.isDropFrame) {
      return (
        this.hours * 3600 * nominal +
        this.minutes * 60 * nominal +
        this.seconds * nominal +
        this.frames
      );
    }

    // Calcolo Drop-Frame (29.97 DF)
    // In 29.97 DF vengono scartati 2 frame ogni minuto eccetto i minuti multipli di 10 (00, 10, 20...)
    const totalMinutes = this.hours * 60 + this.minutes;
    const dropMinutes = totalMinutes - Math.floor(totalMinutes / 10);
    const droppedFrames = dropMinutes * 2;

    const rawFrames =
      this.hours * 3600 * nominal +
      this.minutes * 60 * nominal +
      this.seconds * nominal +
      this.frames;

    return Math.max(0, rawFrames - droppedFrames);
  }

  /**
   * Crea un'istanza SMPTETimecode da un numero totale di frame lineari
   */
  static fromFrames(totalFrames, fps = SMPTEFrameRate.FPS_25, isDropFrame = false) {
    const nominal = fps === 29.97 ? 30 : Math.round(fps);
    let f = Math.max(0, Math.floor(totalFrames));

    if (!isDropFrame) {
      const frames = f % nominal;
      let remSec = Math.floor(f / nominal);
      const seconds = remSec % 60;
      let remMin = Math.floor(remSec / 60);
      const minutes = remMin % 60;
      const hours = Math.floor(remMin / 60) % 24;

      return new SMPTETimecode(hours, minutes, seconds, frames, 0, fps, isDropFrame);
    }

    // Inversione matematica Drop-Frame:
    // Blocco da 10 minuti = 10 * 60 * 30 - 18 = 17982 frame
    const framesPer10Min = 17982;
    const framesPerMin = 1798; // 60 * 30 - 2

    const d = Math.floor(f / framesPer10Min);
    const m = f % framesPer10Min;

    let fAdjusted = f;
    if (m > 2) {
      fAdjusted = f + 2 * (9 * d + Math.floor((m - 2) / framesPerMin));
    } else {
      fAdjusted = f + 2 * (9 * d);
    }

    const frames = fAdjusted % nominal;
    const seconds = Math.floor(fAdjusted / nominal) % 60;
    const minutes = Math.floor(fAdjusted / (nominal * 60)) % 60;
    const hours = Math.floor(fAdjusted / (nominal * 3600)) % 24;

    return new SMPTETimecode(hours, minutes, seconds, frames, 0, fps, isDropFrame);
  }

  // ─── Conversioni: Secondi ──────────────────────────────────────

  toSeconds() {
    const totalFrames = this.toFrames() + this.subframes / 100;
    return totalFrames / this.fps;
  }

  static fromSeconds(seconds, fps = SMPTEFrameRate.FPS_25, isDropFrame = false) {
    const realFps = fps === 29.97 ? 29.97 : Number(fps) || 25;
    const totalFrames = Math.max(0, seconds * realFps);
    const baseFrames = Math.floor(totalFrames);
    const sub = Math.round((totalFrames - baseFrames) * 100);

    const tc = SMPTETimecode.fromFrames(baseFrames, fps, isDropFrame);
    tc.subframes = Math.min(99, sub);
    return tc;
  }

  // ─── Parsing da Stringa (HH:MM:SS:FF o HH:MM:SS;FF) ────────────

  /**
   * Converte una stringa (es. "01:23:45:12" o "01:23:45;12") in SMPTETimecode
   */
  static fromString(tcStr, defaultFps = SMPTEFrameRate.FPS_25, defaultDropFrame = null) {
    if (!tcStr || typeof tcStr !== 'string') {
      return new SMPTETimecode(0, 0, 0, 0, 0, defaultFps, false);
    }

    const trimmed = tcStr.trim();
    // Il punto e virgola ';' indica tradizionalmente Drop-Frame SMPTE
    const hasSemicolon = trimmed.includes(';');
    const isDrop = defaultDropFrame !== null ? defaultDropFrame : hasSemicolon;

    const parts = trimmed.split(/[:;.]/);
    const h = parseInt(parts[0], 10) || 0;
    const m = parseInt(parts[1], 10) || 0;
    const s = parseInt(parts[2], 10) || 0;
    const f = parseInt(parts[3], 10) || 0;
    const sub = parts[4] !== undefined ? parseInt(parts[4], 10) : 0;

    return new SMPTETimecode(h, m, s, f, sub, defaultFps, isDrop);
  }

  // ─── Operazioni Aritmetiche ────────────────────────────────────

  addFrames(deltaFrames) {
    const current = this.toFrames();
    const updated = Math.max(0, current + Math.floor(deltaFrames));
    const res = SMPTETimecode.fromFrames(updated, this.fps, this.isDropFrame);
    res.subframes = this.subframes;
    return res;
  }

  subtractFrames(deltaFrames) {
    return this.addFrames(-deltaFrames);
  }

  diffFrames(other) {
    if (!(other instanceof SMPTETimecode)) return 0;
    return this.toFrames() - other.toFrames();
  }

  compare(other) {
    if (!(other instanceof SMPTETimecode)) return 0;
    const diff = this.toFrames() - other.toFrames();
    if (diff !== 0) return diff > 0 ? 1 : -1;
    if (this.subframes !== other.subframes) return this.subframes > other.subframes ? 1 : -1;
    return 0;
  }

  // ─── Formattazione ─────────────────────────────────────────────

  /**
   * Restituisce la stringa SMPTE formattata ("01:00:00:00" o "01:00:00;00" per Drop-Frame)
   */
  toString(includeSubframes = false) {
    const pad = (n) => String(n).padStart(2, '0');
    const separator = this.isDropFrame ? ';' : ':';

    let res = `${pad(this.hours)}:${pad(this.minutes)}:${pad(this.seconds)}${separator}${pad(this.frames)}`;
    if (includeSubframes) {
      res += `.${pad(this.subframes)}`;
    }
    return res;
  }

  clone() {
    return new SMPTETimecode(
      this.hours,
      this.minutes,
      this.seconds,
      this.frames,
      this.subframes,
      this.fps,
      this.isDropFrame
    );
  }
}
