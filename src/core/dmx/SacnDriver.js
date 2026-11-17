import BaseDmxDriver from './BaseDmxDriver.js';
import dgram from 'dgram';
import crypto from 'crypto';

const SACN_PORT = 5568;
const ACN_PID = Buffer.from('ASC-E1.17\0\0\0', 'ascii'); // 12 bytes
const SOURCE_NAME = 'ShowSuite DMX Controller';

/**
 * SacnDriver - Trasmettitore sACN (ANSI E1.31) via UDP Multicast o Unicast
 */
export default class SacnDriver extends BaseDmxDriver {
  constructor(options = {}) {
    super('sACN (ANSI E1.31)', options);
    this.universe = options.universe || 1; // sACN universe 1-based (1..63999)
    this.priority = options.priority || 100; // 0..200 (100 default)
    this.sequence = 0;
    this.socket = null;
    this.cid = options.cid || crypto.randomBytes(16); // 16-byte UUID

    // Dimensione totale pacchetto: 638 bytes
    // Root Layer (38 bytes) + Framing Layer (77 bytes) + DMP Layer (523 bytes)
    this.packet = Buffer.alloc(638);
    this._buildStaticHeader();
  }

  _buildStaticHeader() {
    // 1. Root Layer
    this.packet.writeUInt16BE(0x0010, 0); // Preamble Size (16)
    this.packet.writeUInt16BE(0x0000, 2); // Post-amble Size (0)
    ACN_PID.copy(this.packet, 4); // 4..15 ACN Packet Identifier
    this.packet.writeUInt16BE(0x7000 | (638 - 16), 16); // Flags & Length (Root: 622)
    this.packet.writeUInt32BE(0x00000004, 18); // Root Vector (VECTOR_ROOT_E131_DATA)
    this.cid.copy(this.packet, 22); // 22..37 Sender CID (UUID)

    // 2. Framing Layer
    this.packet.writeUInt16BE(0x7000 | (638 - 38), 38); // Flags & Length (Framing: 600)
    this.packet.writeUInt32BE(0x00000002, 40); // Framing Vector (VECTOR_E131_DATA_PACKET)

    // Source Name (64 bytes null-padded)
    const sourceBuf = Buffer.alloc(64);
    sourceBuf.write(SOURCE_NAME, 'utf8');
    sourceBuf.copy(this.packet, 44);

    this.packet.writeUInt8(this.priority, 108); // Priority
    this.packet.writeUInt16BE(0x0000, 109); // Synchronization Address
    this.packet.writeUInt8(0x00, 112); // Options

    // 3. DMP Layer
    this.packet.writeUInt16BE(0x7000 | (638 - 115), 115); // Flags & Length (DMP: 523)
    this.packet.writeUInt8(0x02, 117); // DMP Vector (VECTOR_DMP_SET_PROPERTY)
    this.packet.writeUInt8(0xa1, 118); // Address Type & Data Type
    this.packet.writeUInt16BE(0x0000, 119); // First Property Address
    this.packet.writeUInt16BE(0x0001, 121); // Address Increment
    this.packet.writeUInt16BE(513, 123); // Property value count (1 start code + 512 channels)
    this.packet.writeUInt8(0x00, 125); // DMX Start Code
  }

  _getMulticastIp(universe) {
    const high = (universe >> 8) & 0xff;
    const low = universe & 0xff;
    return `239.255.${high}.${low}`;
  }

  async connect() {
    return new Promise((resolve) => {
      try {
        this.socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });
        this.socket.bind(() => {
          this.socket.setMulticastTTL(64);
          this.isConnected = true;
          this.lastError = null;
          this.emit('connected');
          resolve(true);
        });

        this.socket.on('error', (err) => {
          this.lastError = err.message;
          this.emit('error', err);
        });
      } catch (err) {
        this.lastError = err.message;
        this.isConnected = false;
        resolve(false);
      }
    });
  }

  async disconnect() {
    return new Promise((resolve) => {
      if (this.socket) {
        this.socket.close(() => {
          this.isConnected = false;
          resolve(true);
        });
      } else {
        this.isConnected = false;
        resolve(true);
      }
    });
  }

  async send(universeIndex = 0, dmxBuffer) {
    if (!this.isConnected || !this.socket) {
      return false;
    }

    const targetUniverse = Math.max(1, this.universe + universeIndex);

    // Aggiorna sequence number e universo nel framing layer
    this.packet.writeUInt8(this.sequence, 111);
    this.sequence = (this.sequence + 1) % 256;
    this.packet.writeUInt16BE(targetUniverse, 113);

    // Copia i 512 canali nel DMP Layer
    const copyLength = Math.min(512, dmxBuffer.length);
    for (let i = 0; i < copyLength; i++) {
      this.packet[126 + i] = dmxBuffer[i];
    }

    const multicastIp = this._getMulticastIp(targetUniverse);

    return new Promise((resolve) => {
      this.socket.send(this.packet, 0, this.packet.length, SACN_PORT, multicastIp, (err) => {
        if (err) {
          this.lastError = err.message;
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  }
}
