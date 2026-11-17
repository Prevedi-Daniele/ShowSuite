/**
 * NetworkCue.js — Network Cue per ShowSuite (conforme a QLab 5)
 * 
 * Gestisce l'invio di comandi e messaggi su reti IP:
 * 1. Messaggi OSC custom (/address + argomenti tipizzati)
 * 2. Datagrammi UDP (testo o dati formattati)
 * 3. Connessioni TCP stream (testo o dati)
 * 4. Codici RAW HEX (es. "01 03 00 00 00 02 C4 0B" o "0xAA, 0xBB") inviati via UDP o TCP
 */

import BaseCue from '../qlab/BaseCue.js';
import { CueType } from '../qlab/CueTypes.js';
import OscPacket from './OscPacket.js';

export const NetworkProtocol = {
  OSC: 'osc',
  UDP: 'udp',
  TCP: 'tcp',
  HEX: 'hex',
};

export const NetworkTransport = {
  UDP: 'udp',
  TCP: 'tcp',
};

export default class NetworkCue extends BaseCue {
  constructor(options = {}) {
    super({
      ...options,
      type: CueType.NETWORK,
    });

    // Destinazione di rete
    this.destination = options.destination || '127.0.0.1';
    this.port = Number(options.port) || 53000;

    // Protocollo di trasmissione ('osc' | 'udp' | 'tcp' | 'hex')
    this.protocol = options.protocol || NetworkProtocol.OSC;

    // Configurazione specifica OSC
    this.oscAddress = options.oscAddress || '/show/action';
    this.oscArguments = Array.isArray(options.oscArguments) ? [...options.oscArguments] : [];

    // Configurazione specifica UDP/TCP plain text
    this.messageText = options.messageText || '';

    // Configurazione specifica RAW HEX
    this.hexString = options.hexString || '';
    this.transport = options.transport || NetworkTransport.UDP; // Transport per HEX

    // Callback di trasmissione
    this.onTransmit = options.onTransmit || null;

    // Traccia dell'ultimo pacchetto inviato
    this.lastTransmission = null;
  }

  // ─── Parsing & Compilazione Codici RAW HEX ─────────────────────

  /**
   * Converte una stringa esadecimale flessibile in un Uint8Array
   * Supporta formati:
   *   "01 02 03 04"
   *   "0x01, 0x02, 0x03"
   *   "01:02:03:04"
   *   "AABBCCDD"
   */
  static hexStringToBytes(hex) {
    if (!hex || typeof hex !== 'string') {
      return new Uint8Array(0);
    }

    // Rimuovi prefissi '0x', virgole, due punti, trattini
    let sanitized = hex.replace(/0x/gi, '').replace(/[,:\-\s]/g, '');

    // Se lunghezza dispari, prepend 0
    if (sanitized.length % 2 !== 0) {
      sanitized = '0' + sanitized;
    }

    const byteLen = sanitized.length / 2;
    const bytes = new Uint8Array(byteLen);

    for (let i = 0; i < byteLen; i++) {
      const byteHex = sanitized.substr(i * 2, 2);
      const val = parseInt(byteHex, 16);
      bytes[i] = isNaN(val) ? 0 : val;
    }

    return bytes;
  }

  /**
   * Converte un Uint8Array in una stringa esadecimale leggibile ("01 02 0A FF")
   */
  static bytesToHexString(bytes) {
    if (!bytes || !(bytes instanceof Uint8Array)) {
      return '';
    }
    return Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0').toUpperCase())
      .join(' ');
  }

  // ─── Compilazione del Payload ──────────────────────────────────

  /**
   * Compila il pacchetto binario/testuale pronto per la trasmissione di rete
   * @returns {{ protocol: string, destination: string, port: number, bytes: Uint8Array, text?: string, transport: string }}
   */
  compilePayload() {
    let bytes = new Uint8Array(0);
    let text = '';
    let transport = NetworkTransport.UDP;

    switch (this.protocol) {
      case NetworkProtocol.OSC: {
        bytes = OscPacket.encodeMessage(this.oscAddress, this.oscArguments);
        text = `${this.oscAddress} ${JSON.stringify(this.oscArguments)}`;
        transport = NetworkTransport.UDP;
        break;
      }

      case NetworkProtocol.UDP: {
        text = this.messageText;
        bytes = new TextEncoder().encode(this.messageText);
        transport = NetworkTransport.UDP;
        break;
      }

      case NetworkProtocol.TCP: {
        text = this.messageText;
        bytes = new TextEncoder().encode(this.messageText);
        transport = NetworkTransport.TCP;
        break;
      }

      case NetworkProtocol.HEX: {
        bytes = NetworkCue.hexStringToBytes(this.hexString);
        text = NetworkCue.bytesToHexString(bytes);
        transport = this.transport === NetworkTransport.TCP ? NetworkTransport.TCP : NetworkTransport.UDP;
        break;
      }

      default:
        throw new Error(`Protocollo di rete non supportato: "${this.protocol}"`);
    }

    return {
      protocol: this.protocol,
      destination: this.destination,
      port: this.port,
      transport,
      bytes,
      text,
    };
  }

  // ─── Trasmissione di Rete ──────────────────────────────────────

  /**
   * Trasmette il payload compilato
   * 
   * @param {Object} [networkManager] Manager di rete opzionale con sendUdp/sendTcp/sendOsc
   * @returns {Promise<Object>} Dati della trasmissione
   */
  async transmit(networkManager = null) {
    if (!this.isArmed()) {
      return null;
    }

    const payload = this.compilePayload();
    this.lastTransmission = {
      ...payload,
      timestamp: Date.now(),
    };

    // Callback utente / notifica immediata
    if (typeof this.onTransmit === 'function') {
      try {
        this.onTransmit(this, payload);
      } catch (err) {
        console.error('Errore nel callback onTransmit di NetworkCue:', err);
      }
    }

    // Se è un messaggio OSC verso localhost (o destinazione locale) o verso comandi /live/,
    // prova prima a instradarlo nel bridge in-process di ShowSuite se abilitato
    if (this.protocol === NetworkProtocol.OSC) {
      try {
        const bridge = (await import('../../shared/ShowSuiteBridge.js')).default;
        if (bridge && bridge.isEnabled()) {
          const isLocal = this.destination === '127.0.0.1' || this.destination === 'localhost' || this.destination === '0.0.0.0';
          if (isLocal || this.oscAddress.startsWith('/live/')) {
            bridge.routeOsc(this.oscAddress, this.oscArguments, 'qlab');
          }
        }
      } catch (e) {
        // Ignora se non in ambiente browser o se il bridge non è caricabile
      }
    }

    // 1. Invio tramite networkManager passato
    if (networkManager) {
      if (payload.protocol === NetworkProtocol.OSC && typeof networkManager.sendOsc === 'function') {
        await networkManager.sendOsc(payload.destination, payload.port, this.oscAddress, this.oscArguments);
      } else if (payload.transport === NetworkTransport.TCP && typeof networkManager.sendTcp === 'function') {
        await networkManager.sendTcp(payload.destination, payload.port, payload.bytes);
      } else if (typeof networkManager.sendUdp === 'function') {
        await networkManager.sendUdp(payload.destination, payload.port, payload.bytes);
      }
    } else {
      // 2. Invio diretto se in ambiente Node.js con dgram / net
      await this._directSend(payload);
    }

    return payload;
  }

  /**
   * Invio diretto via socket Node nativi
   */
  async _directSend(payload) {
    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        if (payload.transport === NetworkTransport.TCP) {
          const net = await import('net');
          return new Promise((resolve) => {
            const client = new net.Socket();
            client.connect(payload.port, payload.destination, () => {
              client.write(Buffer.from(payload.bytes));
              client.end();
              resolve();
            });
            client.on('error', (err) => {
              client.destroy();
              resolve(); // Non bloccare il flusso dello show in caso di timeout socket
            });
          });
        } else {
          const dgram = await import('dgram');
          const client = dgram.createSocket('udp4');
          return new Promise((resolve) => {
            client.send(Buffer.from(payload.bytes), 0, payload.bytes.length, payload.port, payload.destination, (err) => {
              try { client.close(); } catch (e) {}
              resolve();
            });
          });
        }
      }
    } catch (e) {
      // Ignora se non in Node
    }
  }

  // ─── Override Ciclo di Vita BaseCue ────────────────────────────

  _enterActionPhase() {
    super._enterActionPhase();

    // Esegui la trasmissione se armata
    if (this.armed) {
      this.transmit().catch(e => {
        console.warn(`Errore durante la trasmissione di NetworkCue "${this.number}":`, e);
      });
    }

    // Se durata è 0 (default per cue di comando immediato), completa subito l'azione
    if (this.duration === 0) {
      this._checkActionCompletion();
    }
  }

  // ─── Serializzazione ───────────────────────────────────────────

  toJSON() {
    return {
      ...super.toJSON(),
      destination: this.destination,
      port: this.port,
      protocol: this.protocol,
      oscAddress: this.oscAddress,
      oscArguments: this.oscArguments,
      messageText: this.messageText,
      hexString: this.hexString,
      transport: this.transport,
    };
  }
}
