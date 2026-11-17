import BaseDmxDriver from './BaseDmxDriver.js';
import { SerialPort } from 'serialport';

const ENTTEC_PRO_START = 0x7E;
const ENTTEC_PRO_END = 0xE7;
const LABEL_SEND_DMX_PACKET = 6;

/**
 * EnttecProDriver - Supporta Enttec DMX USB Pro, DMXking ultraDMX, Eurolite USB-DMX512 Pro e cloni
 */
export default class EnttecProDriver extends BaseDmxDriver {
  constructor(options = {}) {
    super('Enttec DMX USB Pro / DMXking', options);
    this.portName = options.port || 'COM3';
    this.baudRate = options.baudRate || 57600; // Il firmware USB Pro gestisce l'FTDI a qualsiasi baudrate
    this.serialPort = null;
    this.txBuffer = Buffer.alloc(518);

    // Header costante
    this.txBuffer[0] = ENTTEC_PRO_START;
    this.txBuffer[1] = LABEL_SEND_DMX_PACKET;
    this.txBuffer[2] = 0x01; // LSB di 513 (1 start code + 512 data)
    this.txBuffer[3] = 0x02; // MSB di 513
    this.txBuffer[4] = 0x00; // DMX Start Code (0x00 per dimmer/lighting data)
    this.txBuffer[517] = ENTTEC_PRO_END;
  }

  async connect() {
    return new Promise((resolve) => {
      try {
        this.serialPort = new SerialPort({
          path: this.portName,
          baudRate: this.baudRate,
          dataBits: 8,
          stopBits: 1,
          parity: 'none',
          autoOpen: false,
        });

        this.serialPort.open((err) => {
          if (err) {
            this.lastError = err.message;
            this.isConnected = false;
            this.emit('error', err);
            resolve(false);
          } else {
            this.isConnected = true;
            this.lastError = null;
            this.emit('connected', { port: this.portName });
            resolve(true);
          }
        });

        this.serialPort.on('error', (err) => {
          this.lastError = err.message;
          this.isConnected = false;
          this.emit('error', err);
        });

        this.serialPort.on('close', () => {
          this.isConnected = false;
          this.emit('disconnected');
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
      if (this.serialPort && this.serialPort.isOpen) {
        this.serialPort.close(() => {
          this.isConnected = false;
          resolve(true);
        });
      } else {
        this.isConnected = false;
        resolve(true);
      }
    });
  }

  async send(universeIndex, dmxBuffer) {
    if (!this.isConnected || !this.serialPort || !this.serialPort.isOpen) {
      return false;
    }

    // Copia i 512 byte nel pacchetto Enttec (offset 5..516)
    const copyLength = Math.min(512, dmxBuffer.length);
    for (let i = 0; i < copyLength; i++) {
      this.txBuffer[5 + i] = dmxBuffer[i];
    }

    return new Promise((resolve) => {
      this.serialPort.write(this.txBuffer, (err) => {
        if (err) {
          this.lastError = err.message;
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  }

  /**
   * Scansiona porte seriali disponibili nel sistema
   */
  static async listAvailablePorts() {
    try {
      const ports = await SerialPort.list();
      return ports.map((p) => ({
        path: p.path,
        manufacturer: p.manufacturer || 'Generico',
        serialNumber: p.serialNumber,
      }));
    } catch {
      return [];
    }
  }
}
