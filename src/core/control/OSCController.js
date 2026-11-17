/**
 * OSCController.js — Ricevitore e Trasmettitore OSC integrato per ShowSuite
 * 
 * Fornisce:
 * - OSCReceiver: ascolto UDP (porta 53000 default QLab o personalizzata), decodifica pacchetti,
 *   routing su OSCDictionary e generazione automatica dei messaggi di risposta (/reply/...)
 * - OSCTransmitter: invio pacchetti e bundle OSC formattati via socket UDP
 * - Supporto dual-mode: Node.js/Electron (dgram) o ambiente browser/mock per test
 */

import OscPacket from './OscPacket.js';
import { OSCDictionary } from './OSCDictionary.js';

export class OSCTransmitter {
  constructor(options = {}) {
    this.defaultHost = options.defaultHost || '127.0.0.1';
    this.defaultPort = options.defaultPort || 53000;
    this.socket = null;
    this.sentPackets = []; // Traccia per test e diagnostica

    // Prova ad inizializzare socket UDP se dgram è disponibile (Node/Electron)
    this._initSocket();
  }

  async _initSocket() {
    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const dgram = await import('dgram');
        this.socket = dgram.createSocket ? dgram.createSocket('udp4') : null;
      }
    } catch (e) {
      this.socket = null;
    }
  }

  /**
   * Invia un messaggio OSC a un host e porta di destinazione
   * 
   * @param {string} host Indirizzo IP o hostname (es. "127.0.0.1")
   * @param {number} port Porta UDP (es. 53000)
   * @param {string} address Indirizzo OSC (es. "/cue/1/start")
   * @param {Array<any>} args Argomenti
   * @param {string} [types] Typetags opzionali
   * @returns {Promise<Uint8Array>} I byte inviati
   */
  async send(host, port, address, args = [], types = null) {
    const targetHost = host || this.defaultHost;
    const targetPort = port || this.defaultPort;

    const bytes = OscPacket.encodeMessage(address, args, types);
    this.sentPackets.push({
      host: targetHost,
      port: targetPort,
      address,
      args,
      bytes,
      timestamp: Date.now(),
    });

    if (this.socket && typeof this.socket.send === 'function') {
      return new Promise((resolve, reject) => {
        this.socket.send(bytes, 0, bytes.length, targetPort, targetHost, (err) => {
          if (err) reject(err);
          else resolve(bytes);
        });
      });
    }

    return bytes;
  }

  /**
   * Invia un bundle OSC a un host e porta di destinazione
   */
  async sendBundle(host, port, timetag = 1n, elements = []) {
    const targetHost = host || this.defaultHost;
    const targetPort = port || this.defaultPort;

    const bytes = OscPacket.encodeBundle(timetag, elements);
    this.sentPackets.push({
      host: targetHost,
      port: targetPort,
      isBundle: true,
      elements,
      bytes,
      timestamp: Date.now(),
    });

    if (this.socket && typeof this.socket.send === 'function') {
      return new Promise((resolve, reject) => {
        this.socket.send(bytes, 0, bytes.length, targetPort, targetHost, (err) => {
          if (err) reject(err);
          else resolve(bytes);
        });
      });
    }

    return bytes;
  }

  close() {
    if (this.socket && typeof this.socket.close === 'function') {
      try {
        this.socket.close();
      } catch (e) {}
      this.socket = null;
    }
  }
}

export class OSCReceiver {
  constructor(options = {}) {
    this.port = options.port || 53000;
    this.host = options.host || '0.0.0.0';
    this.dictionary = options.dictionary || new OSCDictionary();
    this.context = options.context || {};
    this.socket = null;
    this.isListening = false;
    this.listeners = {
      message: [],
      command: [],
      error: [],
    };
  }

  on(event, cb) {
    if (this.listeners[event]) this.listeners[event].push(cb);
    return () => this.off(event, cb);
  }

  off(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(l => l !== cb);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      for (const cb of this.listeners[event]) {
        try {
          cb(data);
        } catch (e) {
          console.error(`Errore nel listener OSC "${event}":`, e);
        }
      }
    }
  }

  setContext(context) {
    this.context = Object.assign(this.context, context);
  }

  /**
   * Avvia il server di ricezione UDP
   */
  async start() {
    if (this.isListening) return true;

    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const dgram = await import('dgram');
        this.socket = dgram.createSocket('udp4');

        this.socket.on('message', (msg, rinfo) => {
          this.processPacket(msg, rinfo);
        });

        this.socket.on('error', (err) => {
          this.emit('error', err);
        });

        return new Promise((resolve) => {
          this.socket.bind(this.port, this.host, () => {
            this.isListening = true;
            resolve(true);
          });
        });
      }
    } catch (e) {
      // Ambiente browser / test senza porte di rete native
    }

    this.isListening = true;
    return true;
  }

  /**
   * Elabora un pacchetto raw OSC ricevuto (sia in arrivo dal socket che simulato/test)
   * 
   * @param {Uint8Array|Buffer} buffer Buffer binario ricevuto
   * @param {Object} [remoteInfo] Informazioni mittente { address, port }
   */
  processPacket(buffer, remoteInfo = { address: '127.0.0.1', port: 53000 }) {
    try {
      const decoded = OscPacket.decode(buffer);
      this.emit('message', { decoded, remoteInfo });

      if (decoded.isBundle) {
        const results = [];
        for (const elem of decoded.elements) {
          if (!elem.isBundle && elem.address) {
            const res = this.dispatchMessage(elem.address, elem.args, remoteInfo);
            results.push(res);
          }
        }
        return results;
      } else {
        return this.dispatchMessage(decoded.address, decoded.args, remoteInfo);
      }
    } catch (err) {
      this.emit('error', err);
      return { handled: false, error: err.message };
    }
  }

  /**
   * Invia un comando all'OSCDictionary e gestisce eventuale risposta
   */
  dispatchMessage(address, args = [], remoteInfo = null) {
    const result = this.dictionary.dispatch(address, args, this.context);
    this.emit('command', { address, args, result, remoteInfo });

    // Se il messaggio richiede una risposta e abbiamo il socket attivo
    if (result.replyAddress && this.socket && remoteInfo && remoteInfo.address && remoteInfo.port) {
      try {
        const replyBytes = OscPacket.encodeMessage(result.replyAddress, result.replyArgs || []);
        this.socket.send(replyBytes, 0, replyBytes.length, remoteInfo.port, remoteInfo.address);
      } catch (e) {
        // Ignora errori di risposta di rete
      }
    }

    return result;
  }

  /**
   * Esegue direttamente un comando testuale (es. "/go" o "/cue/1/start 2.0")
   */
  executeText(oscString) {
    const { address, args } = OscPacket.parseOscString(oscString);
    if (!address) {
      return { handled: false, error: 'Indirizzo OSC non trovato nella stringa' };
    }
    return this.dispatchMessage(address, args);
  }

  stop() {
    if (this.socket) {
      try {
        this.socket.close();
      } catch (e) {}
      this.socket = null;
    }
    this.isListening = false;
  }
}

/**
 * Controller integrato OSC: combina Receiver e Transmitter
 */
export default class OSCController {
  constructor(options = {}) {
    this.dictionary = new OSCDictionary();
    this.receiver = new OSCReceiver({
      port: options.listenPort || 53000,
      host: options.listenHost || '0.0.0.0',
      dictionary: this.dictionary,
      context: options.context || {},
    });
    this.transmitter = new OSCTransmitter({
      defaultHost: options.targetHost || '127.0.0.1',
      defaultPort: options.targetPort || 53000,
    });
  }

  setContext(context) {
    this.receiver.setContext(context);
  }

  registerRoute(pattern, handler) {
    this.dictionary.registerRoute(pattern, handler);
  }

  async start() {
    return this.receiver.start();
  }

  stop() {
    this.receiver.stop();
    this.transmitter.close();
  }

  // Metodi proxy per comodità
  send(host, port, address, args, types) {
    return this.transmitter.send(host, port, address, args, types);
  }

  sendBundle(host, port, timetag, elements) {
    return this.transmitter.sendBundle(host, port, timetag, elements);
  }

  processPacket(buffer, remoteInfo) {
    return this.receiver.processPacket(buffer, remoteInfo);
  }

  executeText(str) {
    return this.receiver.executeText(str);
  }
}
