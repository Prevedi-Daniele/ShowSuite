# SPEC — Architettura ShowSuite

## 1. Stack reale
Electron (`src/main/main.cjs`, `preload.cjs`) + React 18 + Vite + Tailwind. ES modules. Test: runner Node (`npm test` → `test/runner.js`). Packaging: electron-builder (Windows NSIS/Portable, Linux AppImage/deb). Licenza Apache-2.0.
Nota: le prime bozze delle spec parlavano di Python/PySide6: superato, vale il repo.

## 2. Livelli
- `src/core/` — motori senza UI, testabili in Node:
  - `dmx/` DmxEngine + driver (Art-Net, sACN, Enttec Pro, Open DMX)
  - `fixtures/` profili, patch, import OFL (`OflParser`), DIP switch
  - `effects/` BeatClock, EffectsEngine, generatori di movimento
  - `control/` CueEngine (Lightkey), LiveController, PaletteManager, FanEngine, OSC (controller, dictionary, packet), MIDI/Network cue, ShowControlManager
  - `qlab/` BaseCue, GroupCue, CueScheduler, Audio/Mic, video
  - `timecode/` SMPTE, LTC/MTC, chaser
- `src/shared/ShowSuiteBridge.js` — routing OSC in-process tra QLab e Lightkey.
- `src/frontend-lightkey/`, `src/frontend-qlab/` — UI React; avviabili anche standalone (`--standalone-lightkey`, `--standalone-qlab`, `--module=...`).

## 3. Regole
1. Il core non importa React né Electron.
2. Ogni feature del core ha test in `test/`.
3. UI ↔ core solo tramite API pubbliche degli `index.js`.
4. Modifiche di formato progetto: sempre con `schema_version` e migrazione.
5. Output DMX: 44 Hz default, configurabile per universo; ogni universo sceglie il proprio driver; nessun limite artificiale sul numero di interfacce.

## 4. Decisioni prese
- Interfacce DMX multiple senza limiti artificiali (più USB + più nodi Art-Net/sACN).
- Formato progetto `.showsuite-light` (ZIP con `project.json`) — da verificare quanto già implementato.
- Stato reale dei lavori tracciato in `ShowSuite_State.md` (che resta il file di stato).

## 5. Gap rispetto alle spec (da verificare con audit)
**Light (vs SPEC-light-lightkey.md)**: persistenza progetto e formato file; Preview con immagini di sfondo/calibrazione; modificatori e curve di fade dei cue; blind/freeze/lock; beat esterno (MIDI clock, Ableton Link, OS2L); DMX-In; ordine di precedenza degli output; import FXT/SSL2/GDTF; Hue.
**Cue (vs SPEC-cue-trigger.md)**: trigger per-cue, cue di controllo mancanti, audit OSC.
**Trasversali**: salvataggio/caricamento workspace QLab; gestione errori driver (disconnessione USB); test su hardware reale; CI su Linux e Windows (esiste `build.yml`).

## 6. Rischi
- Latenza e jitter di Node/Electron sul DMX Open DMX (richiede timing preciso): considerare worker thread dedicato.
- Audio multicanale e video su più monitor in Electron: limiti di Chromium; valutare backend nativo se serve.
- Driver USB seriali su Windows/Linux (permessi udev, driver FTDI).

## 7. Prossimi passi
Audit del codice contro le tabelle di gap; poi ordine suggerito: persistenza progetto → trigger per-cue → cue di controllo → precedenza output/blind/freeze → beat esterno.
