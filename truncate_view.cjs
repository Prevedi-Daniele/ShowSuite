const fs = require('fs');
const p = 'd:/Documenti/Prove e lavori personali/ShowSuite/src/frontend-lightkey/LightkeyMainView.jsx';
const lines = fs.readFileSync(p, 'utf8').split('\n');
const first = lines.slice(0, 509).join('\n');
fs.writeFileSync(p, first, 'utf8');
console.log('OK: troncato a ' + first.split('\n').length + ' righe');
