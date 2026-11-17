/**
 * test/runner.js — Runner completo di tutte le suite di test di ShowSuite
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { fork } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const testFiles = fs.readdirSync(__dirname)
  .filter(f => f.startsWith('test_') && f.endsWith('.js'))
  .sort();

console.log(`==========================================================`);
console.log(` SHOWSUITE TEST RUNNER — Esecuzione di ${testFiles.length} suite`);
console.log(`==========================================================\n`);

let passedSuites = 0;
let failedSuites = 0;

async function runTest(file) {
  return new Promise((resolve) => {
    const fullPath = path.join(__dirname, file);
    const child = fork(fullPath, [], { stdio: 'inherit' });
    child.on('close', (code) => {
      if (code === 0) {
        passedSuites++;
        resolve(true);
      } else {
        failedSuites++;
        resolve(false);
      }
    });
  });
}

for (const file of testFiles) {
  await runTest(file);
  console.log('\n----------------------------------------------------------\n');
}

console.log(`==========================================================`);
console.log(` RISULTATO TEST RUNNER:`);
console.log(` Suite superate: ${passedSuites} / ${testFiles.length}`);
console.log(` Suite fallite:  ${failedSuites} / ${testFiles.length}`);
console.log(`==========================================================`);

if (failedSuites > 0) {
  process.exit(1);
} else {
  console.log(` TUTTI I TEST SONO STATI SUPERATI AL 100%! ✓\n`);
  process.exit(0);
}
