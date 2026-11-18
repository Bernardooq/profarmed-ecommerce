/**
 * compress-to-webp.js
 * ===================
 * Utility script to compress any image (PNG, JPG, JPEG, TIFF) into WebP format.
 * Uses the 'sharp' library for efficient, high-performance image compression.
 * 
 * Usage:
 *   node compress-to-webp.js
 */

import readline from 'readline';
import path from 'path';
import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const prompt = (query) => new Promise((resolve) => rl.question(query, resolve));

async function main() {
  console.log('=========================================');
  console.log('   Compresor de Imágenes a WebP (Sharp)  ');
  console.log('=========================================');

  let sharp;
  try {
    sharp = require('sharp');
  } catch (err) {
    console.error('\nError: No se encontró la librería "sharp" instalada.');
    console.log('Por favor instala las dependencias ejecutando: npm install\n');
    rl.close();
    return;
  }

  try {
    // 1. Solicitar ruta del archivo
    const filePathInput = await prompt('\nIntroduce la ruta del archivo de imagen (PNG, JPG, etc.): ');
    const rawPath = filePathInput.trim().replace(/^['"]|['"]$/g, ''); // Limpiar comillas si las hay

    if (!rawPath) {
      console.log('Ruta inválida.');
      rl.close();
      return;
    }

    const absolutePath = path.resolve(rawPath);

    if (!fs.existsSync(absolutePath)) {
      console.error(`\nError: El archivo no existe en la ruta: ${absolutePath}`);
      rl.close();
      return;
    }

    const stats = fs.statSync(absolutePath);
    if (!stats.isFile()) {
      console.error('\nError: La ruta provista no corresponde a un archivo válido.');
      rl.close();
      return;
    }

    // 2. Solicitar calidad de compresión (0-100)
    const qualityInput = await prompt('Introduce la calidad de compresión WebP (1-100) [Por defecto: 80]: ');
    let quality = parseInt(qualityInput.trim(), 10);
    if (isNaN(quality) || quality < 1 || quality > 100) {
      quality = 80;
    }

    const fileExt = path.extname(absolutePath);
    const fileDir = path.dirname(absolutePath);
    const fileNameWithoutExt = path.basename(absolutePath, fileExt);
    const outputPath = path.join(fileDir, `${fileNameWithoutExt}.webp`);

    console.log('\nComprimiendo...');

    // 3. Procesar y comprimir la imagen
    await sharp(absolutePath)
      .webp({ quality: quality })
      .toFile(outputPath);

    const oldSizeKB = (stats.size / 1024).toFixed(2);
    const newStats = fs.statSync(outputPath);
    const newSizeKB = (newStats.size / 1024).toFixed(2);
    const savings = ((1 - newStats.size / stats.size) * 100).toFixed(1);

    console.log('\n¡Compresión completada con éxito!');
    console.log('-----------------------------------------');
    console.log(`Origen:    ${absolutePath} (${oldSizeKB} KB)`);
    console.log(`Destino:   ${outputPath} (${newSizeKB} KB)`);
    console.log(`Ahorro:    Reducción de tamaño del ${savings}%`);
    console.log('-----------------------------------------');

  } catch (error) {
    console.error('\nError al procesar la imagen:', error.message);
  } finally {
    rl.close();
  }
}

main();
