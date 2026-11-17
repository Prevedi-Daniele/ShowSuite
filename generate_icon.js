import fs from 'fs';
import zlib from 'zlib';

// Generatore di PNG 256x256 RGBA non compresso
function create256Png() {
  const width = 256;
  const height = 256;

  // Header PNG
  const signature = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);

  // IHDR Chunk
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData.writeUInt8(8, 8); // bit depth
  ihdrData.writeUInt8(6, 9); // RGBA color type
  ihdrData.writeUInt8(0, 10); // compression method
  ihdrData.writeUInt8(0, 11); // filter method
  ihdrData.writeUInt8(0, 12); // interlace method

  const ihdrChunk = createChunk('IHDR', ihdrData);

  // Raw Image Data (Filter byte 0x00 + RGBA per ogni riga)
  const rawData = Buffer.alloc(height * (1 + width * 4));
  let offset = 0;

  for (let y = 0; y < height; y++) {
    rawData[offset++] = 0; // Filter: None
    for (let x = 0; x < width; x++) {
      // Gradiente Dark Blue / Purple ShowSuite
      const dx = x - 128;
      const dy = y - 128;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 110) {
        // Cerchio centrale dell'icona
        rawData[offset++] = 10;   // R
        rawData[offset++] = 132;  // G
        rawData[offset++] = 255;  // B (Apple Accent Blue)
        rawData[offset++] = 255;  // A
      } else if (dist < 118) {
        // Bordo sottile lucido
        rawData[offset++] = 50;
        rawData[offset++] = 160;
        rawData[offset++] = 255;
        rawData[offset++] = 200;
      } else {
        // Sfondo scuro trasparente
        rawData[offset++] = 24;
        rawData[offset++] = 24;
        rawData[offset++] = 27;
        rawData[offset++] = 255;
      }
    }
  }

  const compressedData = zlib.deflateSync(rawData);
  const idatChunk = createChunk('IDAT', compressedData);

  // IEND Chunk
  const iendChunk = createChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

function createChunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);

  const crcBuf = Buffer.alloc(4);
  const crc = crc32(Buffer.concat([typeBuf, data]));
  crcBuf.writeUInt32BE(crc, 0);

  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

function crc32(buf) {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let j = 0; j < 8; j++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

const pngBuffer = create256Png();
fs.writeFileSync('public/icon.png', pngBuffer);
console.log('✓ Icona PNG 256x256 generata con successo in public/icon.png (Bytes: ' + pngBuffer.length + ')');
