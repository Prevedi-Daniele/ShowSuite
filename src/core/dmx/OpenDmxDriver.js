import BaseDmxDriver from './BaseDmxDriver.js';
import { SerialPort } from 'serialport';

/**
 * OpenDmxDriver - Supporta FTDI Open DMX (cavi generici USB RS-485, chip FT232R/FT232BM)
 * come utilizzato ampiamente in FreeStyler e QLC+.
 */
export default class OpenDmxDriver extends BaseDmxDriver {
  constructor(options = {}) {
    super('FTDI Open DMX / FreeStyler Serial', options);
    this.portName = options.port || 'COM3';
    this.serialPort = null;
    this.txBuffer = Buffer.alloc(513); // 1 start code + 512 channels
    this.txBuffer[0] = 0x00; // DMX Start Code
    this.isSending = false;
  }

  async connect() {
    return new Promise((resolve) => {
      try {
        this.serialPort = new SerialPort({
          path: this.portName,
          baudRate: 250000, // DMX 512 standard
          dataBits: 8,
          stopBits: 2, // 2 stop bits per standard DMX
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

  /**
   * Genera il ciclo Break + MAB (Mark After Break) e scrive il buffer DMX
   */
  async send(universeIndex, dmxBuffer) {
    if (!this.isConnected || !this.serialPort || !this.serialPort.isOpen || this.isSending) {
      return false;
    }

    this.isSending = true;

    // Copia i 512 canali
    const copyLength = Math.min(512, dmxBuffer.length);
    for (let i = 0; i < copyLength; i++) {
      this.txBuffer[1 + i] = dmxBuffer[i];
    }

    return new Promise((resolve) => {
      // 1. Asserisce Break (linea TX a livello basso per ~100 µs)
      this.serialPort.set({ brk: true }, (err) => {
        if (err) {
          this.isSending = false;
          return resolve(false);
        }

        // Breve ritardo per Break time (circa 100 µs)
        setTimeout(() => {
          // 2. Rilascia Break -> MAB (Mark After Break ~12 µs)
          this.serialPort.set({ brk: false }, (err) => {
            if (err) {
              this.isSending = false;
              return resolve(false);
            }

            // 3. Invia i 513 byte a 250k baud 8N2
            this.serialPort.write(this.txBuffer, (err) => {
              this.isSending = false;
              if (err) {
                this.lastError = err.message;
                resolve(false);
              } else {
                resolve(true);
              }
            });
          });
        }, 1);
      });
    });
  }
}
