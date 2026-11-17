/**
 * OscPacket.js — Open Sound Control (OSC 1.0 / 1.1) Codec per ShowSuite
 * 
 * Implementazione nativa ad alte prestazioni in JavaScript per:
 * - Codifica e decodifica di messaggi OSC (/address, typetags, argomenti)
 * - Supporto tipi OSC standard:
 *   - 'i' (int32 big-endian)
 *   - 'f' (float32 IEEE 754 big-endian)
 *   - 's' (stringa UTF-8 con terminatore nullo, allineata a 4 byte)
 *   - 'b' (blob binario: lunghezza int32 + byte grezzi, allineato a 4 byte)
 *   - 'T' / 'F' (booleani True / False senza payload)
 *   - 'N' (Null / Nil senza payload)
 *   - 'd' (float64 double precision big-endian)
 *   - 'h' (int64 BigInt big-endian)
 * - Supporto per OSC Bundles ("#bundle", timetag a 64 bit, messaggi nidificati)
 * - Parser di stringhe testuali OSC (es. "/cue/1/start 1.5 'test'")
 */

/**
 * Calcola la lunghezza allineata a multipli di 4 byte per stringhe terminate da null
 */
export function getPaddedStringLength(str) {
  const byteLen = new TextEncoder().encode(str).length + 1; // +1 per terminatore null
  return Math.ceil(byteLen / 4) * 4;
}

/**
 * Codifica una stringa con terminatore nullo e padding a 4 byte in un Uint8Array
 */
export function writePaddedString(str, targetBuffer, offset = 0) {
  const encoded = new TextEncoder().encode(str);
  targetBuffer.set(encoded, offset);
  const end = offset + encoded.length;
  const paddedLen = Math.ceil((encoded.length + 1) / 4) * 4;
  for (let i = end; i < offset + paddedLen; i++) {
    targetBuffer[i] = 0;
  }
  return paddedLen;
}

/**
 * Legge una stringa terminata da null allineata a 4 byte da un Uint8Array
 */
export function readPaddedString(buffer, offset = 0) {
  let end = offset;
  while (end < buffer.length && buffer[end] !== 0) {
    end++;
  }
  const strBytes = buffer.subarray(offset, end);
  const str = new TextDecoder('utf-8').decode(strBytes);
  const paddedLen = Math.ceil((end - offset + 1) / 4) * 4;
  return { str, bytesRead: paddedLen };
}

/**
 * Classe per la manipolazione e serializzazione di pacchetti OSC
 */
export default class OscPacket {
  /**
   * Codifica un messaggio OSC in un Uint8Array
   * 
   * @param {string} address Indirizzo OSC (inizia con '/')
   * @param {Array<any>} args Argomenti opzionali
   * @param {string} [typeTags] Typetag espliciti (es. 'ifsb'); se omessi vengono dedotti
   * @returns {Uint8Array}
   */
  static encodeMessage(address, args = [], typeTags = null) {
    if (!address || typeof address !== 'string' || !address.startsWith('/')) {
      throw new Error(`Indirizzo OSC non valido: "${address}". Deve iniziare con '/'`);
    }

    // Se non forniti, deduci i typetag dagli argomenti
    let tags = '';
    const normalizedArgs = [];

    if (typeTags && typeof typeTags === 'string') {
      tags = typeTags.startsWith(',') ? typeTags.slice(1) : typeTags;
      for (let i = 0; i < tags.length; i++) {
        normalizedArgs.push(args[i]);
      }
    } else {
      for (const arg of args) {
        if (typeof arg === 'number') {
          if (Number.isInteger(arg)) {
            tags += 'i';
            normalizedArgs.push(arg);
          } else {
            tags += 'f';
            normalizedArgs.push(arg);
          }
        } else if (typeof arg === 'string') {
          tags += 's';
          normalizedArgs.push(arg);
        } else if (typeof arg === 'boolean') {
          tags += arg ? 'T' : 'F';
          normalizedArgs.push(arg);
        } else if (arg === null || arg === undefined) {
          tags += 'N';
          normalizedArgs.push(null);
        } else if (typeof arg === 'bigint') {
          tags += 'h';
          normalizedArgs.push(arg);
        } else if (arg instanceof Uint8Array || (typeof Buffer !== 'undefined' && Buffer.isBuffer(arg))) {
          tags += 'b';
          normalizedArgs.push(new Uint8Array(arg));
        } else {
          // Fallback a stringa JSON
          tags += 's';
          normalizedArgs.push(JSON.stringify(arg));
        }
      }
    }

    const typeTagString = ',' + tags;

    // Calcolo dimensione totale del buffer
    let totalSize = getPaddedStringLength(address) + getPaddedStringLength(typeTagString);

    for (let i = 0; i < tags.length; i++) {
      const tag = tags[i];
      const val = normalizedArgs[i];
      switch (tag) {
        case 'i':
        case 'f':
          totalSize += 4;
          break;
        case 'd':
        case 'h':
          totalSize += 8;
          break;
        case 's':
          totalSize += getPaddedStringLength(String(val || ''));
          break;
        case 'b': {
          const blobLen = val ? val.length : 0;
          totalSize += 4 + Math.ceil(blobLen / 4) * 4;
          break;
        }
        case 'T':
        case 'F':
        case 'N':
          // Nessun byte di payload per i flag
          break;
        default:
          throw new Error(`Typetag OSC non supportato per la codifica: "${tag}"`);
      }
    }

    const output = new Uint8Array(totalSize);
    const view = new DataView(output.buffer, output.byteOffset, output.byteLength);
    let offset = 0;

    // 1. Scrivi Address
    offset += writePaddedString(address, output, offset);

    // 2. Scrivi TypeTag
    offset += writePaddedString(typeTagString, output, offset);

    // 3. Scrivi Argomenti
    for (let i = 0; i < tags.length; i++) {
      const tag = tags[i];
      const val = normalizedArgs[i];

      switch (tag) {
        case 'i':
          view.setInt32(offset, Number(val) || 0, false); // Big-Endian
          offset += 4;
          break;
        case 'f':
          view.setFloat32(offset, Number(val) || 0.0, false);
          offset += 4;
          break;
        case 'd':
          view.setFloat64(offset, Number(val) || 0.0, false);
          offset += 8;
          break;
        case 'h':
          view.setBigInt64(offset, BigInt(val || 0), false);
          offset += 8;
          break;
        case 's':
          offset += writePaddedString(String(val || ''), output, offset);
          break;
        case 'b': {
          const blobBytes = val instanceof Uint8Array ? val : new Uint8Array(val || []);
          view.setInt32(offset, blobBytes.length, false);
          offset += 4;
          output.set(blobBytes, offset);
          const paddedBlobLen = Math.ceil(blobBytes.length / 4) * 4;
          for (let p = offset + blobBytes.length; p < offset + paddedBlobLen; p++) {
            output[p] = 0;
          }
          offset += paddedBlobLen;
          break;
        }
        case 'T':
        case 'F':
        case 'N':
          // Nessun byte aggiuntivo
          break;
      }
    }

    return output;
  }

  /**
   * Decodifica un messaggio o bundle OSC da un buffer/Uint8Array
   * 
   * @param {Uint8Array|ArrayBuffer|Buffer} rawBuffer 
   * @returns {{ address?: string, args?: Array<any>, types?: string, timetag?: BigInt, elements?: Array<any>, isBundle: boolean }}
   */
  static decode(rawBuffer) {
    const buffer = rawBuffer instanceof Uint8Array ? rawBuffer : new Uint8Array(rawBuffer);
    if (buffer.length < 4) {
      throw new Error('Buffer OSC troppo piccolo (meno di 4 byte)');
    }

    // Verifica se è un bundle OSC
    const headerStr = new TextDecoder('ascii').decode(buffer.subarray(0, 8));
    if (headerStr.startsWith('#bundle\0')) {
      return this.decodeBundle(buffer);
    }

    return this.decodeMessage(buffer);
  }

  /**
   * Decodifica un messaggio OSC singolo
   */
  static decodeMessage(buffer) {
    const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
    let offset = 0;

    // 1. Leggi Indirizzo OSC
    const addrResult = readPaddedString(buffer, offset);
    const address = addrResult.str;
    offset += addrResult.bytesRead;

    if (!address.startsWith('/')) {
      throw new Error(`Messaggio OSC malformato: indirizzo "${address}" non valido`);
    }

    const args = [];
    let types = '';

    // Se non ci sono altri byte, è un messaggio senza typetag né argomenti
    if (offset >= buffer.length) {
      return { address, args, types, isBundle: false };
    }

    // 2. Leggi TypeTag
    const tagResult = readPaddedString(buffer, offset);
    offset += tagResult.bytesRead;

    if (tagResult.str.startsWith(',')) {
      types = tagResult.str.slice(1);
    }

    // 3. Leggi Argomenti secondo i TypeTag
    for (let i = 0; i < types.length; i++) {
      const tag = types[i];
      if (offset > buffer.length) {
        break;
      }

      switch (tag) {
        case 'i':
          args.push(view.getInt32(offset, false));
          offset += 4;
          break;
        case 'f':
          args.push(view.getFloat32(offset, false));
          offset += 4;
          break;
        case 's': {
          const sResult = readPaddedString(buffer, offset);
          args.push(sResult.str);
          offset += sResult.bytesRead;
          break;
        }
        case 'b': {
          const blobLen = view.getInt32(offset, false);
          offset += 4;
          const blobData = buffer.slice(offset, offset + blobLen);
          args.push(blobData);
          offset += Math.ceil(blobLen / 4) * 4;
          break;
        }
        case 'd':
          args.push(view.getFloat64(offset, false));
          offset += 8;
          break;
        case 'h':
          args.push(view.getBigInt64(offset, false));
          offset += 8;
          break;
        case 'T':
          args.push(true);
          break;
        case 'F':
          args.push(false);
          break;
        case 'N':
          args.push(null);
          break;
        default:
          // Salta typetag sconosciuto se possibile
          break;
      }
    }

    return {
      address,
      args,
      types,
      isBundle: false,
    };
  }

  /**
   * Codifica un bundle OSC contenente timetag e molteplici elementi
   */
  static encodeBundle(timetag = 1n, elements = []) {
    const encodedElements = [];
    let elementsTotalSize = 0;

    for (const elem of elements) {
      let rawBytes;
      if (elem instanceof Uint8Array) {
        rawBytes = elem;
      } else if (elem && elem.address) {
        rawBytes = this.encodeMessage(elem.address, elem.args || [], elem.types);
      } else {
        continue;
      }
      encodedElements.push(rawBytes);
      elementsTotalSize += 4 + rawBytes.length; // 4 byte int32 length prefix + bytes
    }

    const totalSize = 8 + 8 + elementsTotalSize; // 8 bytes "#bundle\0" + 8 bytes timetag + elements
    const output = new Uint8Array(totalSize);
    const view = new DataView(output.buffer, output.byteOffset, output.byteLength);

    // 1. Header "#bundle\0"
    writePaddedString('#bundle', output, 0);

    // 2. Timetag 64-bit
    const tt = typeof timetag === 'bigint' ? timetag : BigInt(timetag);
    view.setBigUint64(8, tt, false);

    // 3. Elementi con prefisso di lunghezza int32
    let offset = 16;
    for (const rawElem of encodedElements) {
      view.setInt32(offset, rawElem.length, false);
      offset += 4;
      output.set(rawElem, offset);
      offset += rawElem.length;
    }

    return output;
  }

  /**
   * Decodifica un bundle OSC
   */
  static decodeBundle(buffer) {
    const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
    let offset = 8; // salta "#bundle\0"

    const timetag = view.getBigUint64(offset, false);
    offset += 8;

    const elements = [];

    while (offset < buffer.length) {
      if (offset + 4 > buffer.length) break;
      const elemSize = view.getInt32(offset, false);
      offset += 4;

      if (elemSize <= 0 || offset + elemSize > buffer.length) break;

      const elemSlice = buffer.subarray(offset, offset + elemSize);
      offset += elemSize;

      // Parsing ricorsivo dell'elemento
      elements.push(this.decode(elemSlice));
    }

    return {
      isBundle: true,
      timetag,
      elements,
    };
  }

  /**
   * Converte una stringa di testo di comando OSC in un oggetto { address, args }
   * Esempi:
   *   "/go" -> { address: "/go", args: [] }
   *   "/cue/1/start 10.5" -> { address: "/cue/1/start", args: [10.5] }
   *   "/live/group/All/level 0.8" -> { address: "/live/group/All/level", args: [0.8] }
   *   "/custom/text \"Spettacolo Teatrale\" 42" -> { address: "/custom/text", args: ["Spettacolo Teatrale", 42] }
   */
  static parseOscString(inputStr) {
    if (!inputStr || typeof inputStr !== 'string') {
      return { address: '', args: [] };
    }

    const trimmed = inputStr.trim();
    if (!trimmed.startsWith('/')) {
      return { address: '', args: [] };
    }

    // Tokenizzazione che preserva virgolette doppie o singole
    const regex = /[^\s"']+|"([^"]*)"|'([^']*)'/g;
    const tokens = [];
    let match;

    while ((match = regex.exec(trimmed)) !== null) {
      if (match[1] !== undefined) {
        tokens.push(match[1]); // Contenuto tra doppie virgolette
      } else if (match[2] !== undefined) {
        tokens.push(match[2]); // Contenuto tra singole virgolette
      } else {
        tokens.push(match[0]); // Parola senza virgolette
      }
    }

    if (tokens.length === 0) {
      return { address: '', args: [] };
    }

    const address = tokens[0];
    const rawArgs = tokens.slice(1);
    const args = rawArgs.map((token) => {
      // Prova intero
      if (/^-?\d+$/.test(token)) {
        return parseInt(token, 10);
      }
      // Prova float
      if (/^-?\d*\.\d+$/.test(token)) {
        return parseFloat(token);
      }
      // Prova booleani
      if (token.toLowerCase() === 'true') return true;
      if (token.toLowerCase() === 'false') return false;
      // Stringa standard
      return token;
    });

    return { address, args };
  }
}
