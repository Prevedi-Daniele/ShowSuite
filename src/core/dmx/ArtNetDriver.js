import BaseDmxDriver from './BaseDmxDriver.js';
import dgram from 'dgram';

const ARTNET_PORT = 6454;
const ARTNET_HEADER = Buffer.from('Art-Net\0', 'ascii');
const OP_DMX = 0x5000;
const PROTOCOL_VERSION = 14;

/**
 * ArtNetDriver - Trasmettitore Art-Net v4 ad alte prestazioni via UDP
 */
export default class ArtNetDriver extends BaseDmxDriver {
  constructor(options = {}) {
    super('Art-Net v4 UDP', options);
    this.host = options.host || '255.255.255.255'; // Broadcast per default
    this.port = options.port || ARTNET_PORT;
    this.net = options.net || 0; // 0..127
    this.subnet = options.subnet || 0; // 0..15
    this.universe = options.universe || 0; // 0..15
    this.sequence = 1;
    this.socket = null;

    // Buffer Art-Net preallocato: 18 byte header + 512 byte data = 530 byte
    this.packet = Buffer.alloc(530);
    ARTNET_HEADER.copy(this.packet, 0); // 0..7
    this.packet.writeUInt16LE(OP_DMX, 8); // 8..9 OpCode
    this.packet.writeUInt16BE(PROTOCOL_VERSION, 10); // 10..11 ProtVer
    this.packet.writeUInt8(0, 13); // Physical port
    this.packet.writeUInt16BE(512, 16); // Data length (512)
  }

  async connect() {
    return new Promise((resolve) => {
      try {
        this.socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });
        this.socket.bind(() => {
          this.socket.setBroadcast(true);
          this.isConnected = true;
          this.lastError = null;
          this.emit('connected', { host: this.host, port: this.port });
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

    // Calcolo universo Art-Net (16 universi per subnet)
    const effectiveUniverse = (this.universe + universeIndex) & 0x0f;
    const subUni = ((this.subnet & 0x0f) << 4) | effectiveUniverse;

    this.packet.writeUInt8(this.sequence, 12);
    this.sequence = (this.sequence % 255) + 1;

    this.packet.writeUInt8(subUni, 14);
    this.packet.writeUInt8(this.net & 0x7f, 15);

    // Copia i 512 byte nel payload
    const copyLength = Math.min(512, dmxBuffer.length);
    for (let i = 0; i < copyLength; i++) {
      this.packet[18 + i] = dmxBuffer[i];
    }

    return new Promise((resolve) => {
      this.socket.send(this.packet, 0, this.packet.length, this.port, this.host, (err) => {
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
