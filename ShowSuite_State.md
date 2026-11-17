# ShowSuite - Project Status

## Ultimo aggiornamento
- **Data**: 17 Novembre 2026
- **Stato**: STEP 0.1÷8.2 Completati ✅
- **Build**: `npm run build` ✓ (2205 moduli, 505.61 kB JS bundle)

---

## STEP 8.2 — Packaging & Distribuzione Cross-Platform (`electron-builder.json`, Windows & Linux) ✅ COMPLETATO

### Componenti e Configurazioni Sviluppate
- `electron-builder.json`:
  - Target Windows completi:
    - **NSIS**: Installer personalizzabile con selezione directory, creazione scorciatoie Desktop e Start Menu (`oneClick: false`).
    - **Portable**: Eseguibile stand-alone portatile senza necessità di installazione per chiavette USB e regie live.
  - Target Linux completi:
    - **AppImage**: Formato universale standalone eseguibile su qualsiasi distribuzione Linux moderna (Ubuntu, Debian, Fedora, Arch).
    - **Debian (.deb)**: Pacchetto nativo per distribuzioni Debian/Ubuntu con categoria `AudioVideo`.
  - Icone applicative:
    - Generazione automatica di `build/icon.ico` (256x256 multi-payload Windows) e `build/icon.png` (256x256 RGBA per Linux).
  - Regole ASAR e packaging `files`: inclusione bundle compilato `dist/**/*`, main process `src/main/**/*`, moduli core `src/core/**/*` e manifest `package.json`.
  - Collaudo packaging con esito positivo: generazione corretta dell'eseguibile e del pacchetto integrato `app.asar`.

---

## STEP 7.3 — Inspector e UI per Network, MIDI e Timecode Cues & Timecode HUD (`src/frontend-qlab/`) ✅ COMPLETATO

### Componenti e Interfacce Sviluppate
- `NetworkInspectorTab.jsx`:
  - Scheda dedicata nell'Inspector di QLab per `NetworkCue`.
  - Configurazione protocollo di rete: **OSC**, **UDP Plain Text**, **TCP Stream Text**, **RAW HEX Byte Stream**.
  - Impostazione Host/IP di destinazione e porta (con fallback 53000).
  - Editor OSC: indirizzo personalizzato e argomenti con pulsanti di preset rapidi verso i comandi interni di Lightkey (`/live/blackout`, `/live/grandMaster`, `/live/speedMaster`, `/live/cue/go`, ecc.).
  - Editor RAW HEX con validatore e scelta trasporto (UDP/TCP).
  - Pulsante **"Test Trasmissione Ora"** con feedback visivo immediato (successo, fallimento, o notifica di routing interno via bridge in-process verso Lightkey).
- `MidiInspectorTab.jsx`:
  - Scheda dedicata nell'Inspector di QLab per `MidiCue`.
  - Configurazione tipologie messaggio: Note On, Note Off, Control Change (CC), Program Change (PC), Pitch Bend, MIDI Show Control (MSC SysEx).
  - Canale MIDI 1–16.
  - Selettore note musicali interattivo con matrice a 12 semitoni (C..B), selettore ottave (-1..9) e calcolo dinamico del numero MIDI `#` e nome nota. Slider di velocity dinamica (0–127).
  - Editor MSC (MIDI Show Control MMA RP-002): Device ID, Command Format (Lighting, Sound, Video, All), Comandi (GO, STOP, RESUME, LOAD, RESET, ALL OFF) e numero cue target.
  - Pulsante **"Test Invio MIDI Ora"** con anteprima esadecimale compilata del pacchetto.
- `TimecodeInspectorTab.jsx`:
  - Scheda dedicata nell'Inspector di QLab per `TimecodeCue`.
  - Selezione formato di uscita: MTC (MIDI Timecode) o LTC (Audio SMPTE 12M).
  - Frame rate configurabile (24, 25, 29.97 DF, 30 fps) con gestione automatica del flag Drop-Frame.
  - Impostazione Start Timecode (`HH:MM:SS:FF`) e interfaccia/canale di destinazione.
  - Display digitale di anteprima timecode calcolato in tempo reale e pulsante di test emissione.
- `TimecodeHUD.jsx`:
  - Display Timecode ad alto contrasto e monitor di sincronizzazione integrato nella barra superiore del QLab Workspace.
  - Visualizzazione del timecode SMPTE corrente (`HH:MM:SS:FF`).
  - Indicatore visivo dello stato della macchina TimecodeChaser: **OFFLINE**, **LOCKING**, **LOCKED**, **FREEWHEELING**.
  - Indicazione del frame rate attivo e della sorgente (MTC o LTC Audio).
- Integrazione in `QLabWorkspace.jsx` e `CueInspector.jsx`:
  - Aggiunta bottoni rapidi Network, MIDI e Timecode nella toolbar per la creazione immediata di Cue istanziate con le classi corrette (`NetworkCue`, `MidiCue`, `TimecodeCue`).
  - Switch contestuale automatico delle schede nell'Inspector alla selezione della Cue.

---

---

## STEP 8.1 — Unificazione ShowSuite & OSC Bridge In-Process (`src/shared/ShowSuiteBridge.js`) ✅ COMPLETATO

### Componenti e Funzionalità Sviluppate
- `ShowSuiteBridge.js`:
  - Singleton ES Module che funge da ponte di routing OSC in-process tra il modulo QLab e il modulo Lightkey.
  - Permette alle Cue di QLab (`NetworkCue`) di pilotare e triggerare azioni di Lightkey all'interno dello stesso runtime senza passare attraverso lo stack di rete UDP loopback.
  - Registrazione dinamica delle istanze dei motori:
    - Lightkey: `LiveController`, `CueEngine`, `PaletteManager`, `EffectsEngine`.
    - QLab: `CueScheduler`.
  - Instradamento bidirezionale OSC via `OSCDictionary`:
    - Dispatch immediato dei comandi `/live/...` (Grand Master, Speed Master, Blackout, Blind, Freeze, Cue Go, Cell trigger, ecc.).
    - Gestione abilitazione/disabilitazione on-the-fly (`setEnabled`, `isEnabled`).
    - Registro cronologia dei pacchetti instradati (`routingHistory`, limitato agli ultimi 100 eventi con timestamp).
  - Metodi helper ad alto livello: `triggerLightkeyCell(index)`, `triggerLightkeyGo()`, `setLightkeyGrandMaster(level)`, `setLightkeyBlackout(state)`.
- `NetworkCue.js` integrato con il bridge:
  - Rilevamento automatico degli indirizzi loopback (`127.0.0.1`, `localhost`) su porta OSC standard di Lightkey (o porta locale): prima della trasmissione via socket di rete, tenta il routing diretto in-process tramite `showSuiteBridge`.
  - Se il bridge è attivo e consuma il comando, evita round-trip UDP inutili garantendo latenza sub-millisecondo.
- `LightkeyMainView.jsx` e `QLabWorkspace.jsx`:
  - Registrazione automatica delle istanze attive dei rispettivi engine nel `showSuiteBridge` al montaggio dei componenti React.
- `GlobalSettingsModal.jsx`:
  - Sincronizzazione in tempo reale dello stato dell'OSC Bridge con `showSuiteBridge`.
  - Badge diagnostico con indicazione visiva dello stato del bridge (attivo/inattivo) e contatore pacchetti instradati.
  - Selezione della modalità di avvio preferita (Suite completa, Standalone Lightkey, Standalone QLab).
- Opzioni di avvio CLI e Script NPM:
  - CLI `main.cjs` configurato con supporto per `--standalone-lightkey`, `--standalone-qlab`, `--module=lightkey`, `--module=qlab`.
  - Script aggiunti in `package.json`: `"start:lightkey"`, `"start:qlab"`.

### Test (`test_unification_bridge.js`)
- **28/28 test superati al 100%**:
  1. Registrazione motori e stato: LiveController, CueEngine, PaletteManager, CueScheduler, abilitazione/disabilitazione.
  2. Routing OSC in-process QLab -> Lightkey: /live/grandMaster, speed master, blackout, blind, freeze, trigger cella griglia, cue go.
  3. Metodi helper diretti e registro cronologia.
  4. Trigger da NetworkCue di QLab verso Lightkey (attivazione e disattivazione blackout in-process).
  5. Parsing opzioni CLI (--standalone-lightkey, --standalone-qlab, --module=...).

---

---

## STEP 7.2 — Timecode Engine & Chasing (`src/core/timecode/`) ✅ COMPLETATO

### Componenti e Modelli Sviluppati
- `SMPTETimecode.js`:
  - Modello matematico rigoroso per SMPTE Timecode (SMPTE 12M standard).
  - Supporto per tutti i frame rate del settore: **24 fps** (Cinema/Film), **25 fps** (EBU/PAL TV), **29.97 fps** (NTSC Drop-Frame e Non-Drop-Frame), **30 fps** (SMPTE standard/NTSC B&W).
  - Conversione bidirezionale simmetrica tra timecode (`HH:MM:SS:FF.sub`) e numero totale di frame lineari (`toFrames()`, `fromFrames()`).
  - Implementazione delle regole Drop-Frame: salto dei frame 0 e 1 all'inizio di ciascun minuto non multiplo di 10 (17982 frame ogni 10 minuti). Formattazione automatica con punto e virgola `;` per Drop-Frame.
  - Aritmetica temporale completa: add/subtract frames, diffFrames, compare, conversione in secondi continui (`toSeconds()`, `fromSeconds()`) e parsing flessibile da stringa (`fromString`).
- `MTCDecoder.js`:
  - Decoder e generatore per **MIDI Timecode (MTC)** secondo le specifiche MMA.
  - **MTC Quarter-Frame Messages (`0xF1 data`)**:
    - Elaborazione dei messaggi a 2 byte ricevuti a $4\times$ il frame rate (pezzi 0..7).
    - Rilevamento automatico del rate code a 2 bit (24, 25, 29.97 DF, 30 fps).
    - Compensazione standard della latenza di trasmissione (+2 frame al completamento del pezzo 7).
  - **MTC Full-Frame SysEx (`F0 7F <dev> 01 01 hr mn sc fr F7`)**:
    - Riposizionamento e seek istantaneo del timecode con estrazione dei bit di rate e ore.
  - `MTCGenerator`: generazione dei messaggi Quarter-Frame e Full-Frame SysEx per la trasmissione verso porte MIDI esterne.
- `LTCDecoder.js`:
  - Decoder e sintetizzatore per **Audio Linear Timecode (LTC - SMPTE 12M)**.
  - Modulazione **Bi-phase Mark Code (BMC)**:
    - Transizione a inizio cella per tutti i bit.
    - Transizione a metà cella per bit '1' (2 transizioni); livello costante per bit '0' (1 transizione).
  - Struttura frame a 80 bit con parola di sincronizzazione standard (Sync Word: `0011 1111 1111 1101` sui bit 64..79).
  - Demodulatore audio PCM a rilevamento dei passaggi per lo zero (zero-crossing) con soglie di classificazione dinamiche e tolleranza al rumore.
  - Decodifica dei campi BCD: Frame, Secondi, Minuti, Ore e flag Drop-Frame.
  - `LTCGenerator`: sintesi audio PCM `Float32Array` a 48 kHz / 44.1 kHz per playback e trasmissione su canali audio di linea.
- `TimecodeChaser.js`:
  - Motore di sincronizzazione e chasing continuo con macchina a stati a 4 fasi:
    1. `OFFLINE`: nessun segnale timecode in arrivo (timeout configurabile, es. 600ms).
    2. `LOCKING`: segnale rilevato, verifica di continuità su soglia frame consecutivi (default 3 frame).
    3. `LOCKED`: segnale stabile e sincronizzato, chasing nominale attivo.
    4. `FREEWHEELING`: tolleranza ai dropout temporanei di audio/rete (avanzamento autonomo fino a $N$ frame per evitare interruzioni nello show dal vivo).
  - Riarmo automatico dei trigger quando il timecode viene riavvolto (rewind).
- **Trigger Cue sincronizzato a Timecode**:
  - Registrazione di trigger su Cue (`registerCueTrigger(cueId, targetTimecode, action)`).
  - Azioni supportate: `START` (tasto GO automatico), `STOP`, `PAUSE`, `LOAD`.
  - Innesco istantaneo e preciso al frame quando il timecode in ingresso o chased raggiunge o attraversa il punto di target.
- `TimecodeCue.js` (estende `BaseCue` con `CueType.TIMECODE`):
  - Output Timecode Cue conforme a QLab 5.
  - Calcolo del timecode corrente basato sulla durata e sul tempo trascorso.
  - Emissione di pacchetti MTC (Full-Frame SysEx all'avvio e Quarter-Frame durante la riproduzione) o bitstream LTC.
- `ShowControlManager.js` aggiornato:
  - Integra nativamente `TimecodeChaser`, `MTCDecoder` e `LTCDecoder`.
  - Rilevamento automatico di MTC in `processIncomingMidi` e campioni audio in `processIncomingLtcAudio`.
  - Metodo `mapTimecodeTrigger(cueId, timecode, action)` per collegare ingressi timecode alle Cue del CueScheduler.

### Test (`test_timecode_engine.js`)
- **72/72 test superati al 100%**:
  1. SMPTETimecode: normalizzazione, 24/25/30 fps, drop-frame 29.97 (17982 frame / 10 min, salto frame al minuto 1), aritmetica (add, diff, compare) e parsing stringa.
  2. MTCDecoder & Generator: 8 quarter-frame, rate codes, compensazione latenza +2 frame, Full-Frame SysEx seek istantaneo.
  3. LTCDecoder & Generator: struttura 80 bit, sync word 0x3FFD, sintesi PCM Float32Array modulata BMC, decodifica zero-crossing e frame drop-frame.
  4. TimecodeChaser: OFFLINE -> LOCKING -> LOCKED, freewheeling su dropout e ripristino istantaneo in LOCKED.
  5. Cue Triggering: innesco automatico di Cue Intro e Cue Chorus su punti SMPTE esatti e riarmo al rewind.
  6. TimecodeCue: ciclo di vita, avanzamento temporale, Full-Frame all'avvio, Quarter-Frames periodici e serializzazione toJSON.
  7. ShowControlManager: integrazione MTC e LTC audio end-to-end con trigger su CueScheduler.

---

## STEP 7.1 — Network & Show Control Engine (`src/core/control/`) ✅ COMPLETATO

### Componenti e Modelli Sviluppati
- `OscPacket.js`:
  - Codec nativo puro JavaScript per Open Sound Control (OSC 1.0 / 1.1) senza dipendenze binarie native.
  - Codifica e decodifica di messaggi OSC (`encodeMessage`, `decodeMessage`) con allineamento rigoroso a 4 byte per stringhe e typetags.
  - Supporto per typetags completi: `'i'` (int32 big-endian), `'f'` (float32 IEEE 754), `'s'` (string UTF-8 null-padded), `'b'` (blob binario Uint8Array), `'T'`/`'F'` (booleani immediati), `'N'` (null/nil), `'d'` (float64 double), `'h'` (int64 BigInt).
  - Supporto per OSC Bundles (`#bundle`, timetag a 64 bit e messaggi multipli nidificati).
  - Parser testuale di stringhe comandi OSC (`parseOscString`) con gestione apici e argomenti multi-tipo.
- `OSCDictionary.js`:
  - Dizionario comandi OSC completo e router compatibile al 100% con QLab 5 e Lightkey.
  - **Comandi Workspace QLab**: `/go`, `/stop`, `/hardStop`, `/pause`, `/resume`, `/panic` (con tempo di dissolvenza opzionale), `/reset`, `/load`, `/next`, `/previous`.
  - **Targeting Cue**:
    - Per numero: `/cue/{number}/start`, `/stop`, `/pause`, `/resume`, `/load`, `/reset`, `/arm`, `/disarm`, `/flagged`, `/unflagged`, `/preWait`, `/duration`, `/postWait`, `/continueMode`, `/name`, `/notes`, `/number`, `/colorName`.
    - Per ID univoco: `/cue_id/{id}/...`.
    - Per Cue selezionata / Standby: `/cue/selected/...`.
    - Regolazione Audio Matrix Crosspoint: `/cue/{number}/level/{inChannel}/{outChannel}/decibel`.
  - **Query di stato**: `/runningOrPausedCues`, `/standbyCue`.
  - **Mapping Lightkey Live**:
    - `/live/grandMaster`, `/live/speedMaster`, `/live/blackout`, `/live/blind`, `/live/freeze`.
    - Trigger pad celle: `/live/cell/{index}/trigger` e `/live/cell/{row}/{col}/trigger`.
    - Fader di gruppo: `/live/group/{nameOrId}/level`.
    - Lighting Cue controls: `/live/cue/go`, `/live/cue/stop`.
- `OSCController.js`:
  - Controller unificato con `OSCReceiver` e `OSCTransmitter`.
  - Ascolto su socket UDP (porta standard 53000 o custom) tramite `dgram` in ambiente Node/Electron o mock reattivo per test.
  - Generazione e invio automatico dei messaggi di risposta `/reply/...` all'host mittente.
  - Registrazione di rotte personalizzate (`registerRoute`).
- `NetworkCue.js` (estende `BaseCue` con `CueType.NETWORK`):
  - Supporto per 4 protocolli e formati di rete:
    1. **OSC**: indirizzo custom e argomenti tipizzati compilati in pacchetto binario.
    2. **UDP**: datagrammi testuali o raw su socket UDP.
    3. **TCP**: streaming client su connessione TCP.
    4. **RAW HEX**: parser flessibile per codici esadecimali (es. `"01 03 00 00 00 02 C4 0B"`, `"0xAA, 0xBB"`, stringhe continue) compilati in `Uint8Array`.
  - Esecuzione nel ciclo di vita dello show control e gestione cue disarmata (skip trasmissione materiale).
- `MidiCue.js` (estende `BaseCue` con `CueType.MIDI`):
  - Supporto per messaggi Canale Voce MIDI standard:
    - **Note On** / **Note Off** (canale 1–16, nota 0–127 o nome musicale es. `'C4'`, `'A4'`, velocity 0–127).
    - **Control Change (CC)** (canale 1–16, numero controller 0–127, valore 0–127).
    - **Program Change (PC)** (canale 1–16, program 0–127, Bank Select MSB CC 0 e LSB CC 32 opzionale).
    - **Pitch Bend** (canale 1–16, valore bipolare $-8192 \dots +8191$ con centro a 8192).
  - Supporto per **MIDI Show Control (MSC)** standard MMA RP-002:
    - Pacchetto SysEx standard: `F0 7F <deviceId> 02 <commandFormat> <command> [Q_number 00 Q_list 00 Q_path] F7`.
    - Categorie/Formati: Lighting (0x01), Sound (0x10), Machinery (0x20), Video (0x30), Projection (0x40), All (0x7F).
    - Comandi: GO, STOP, RESUME, TIMED_GO, LOAD, SET, FIRE, ALL_OFF, RESTORE, RESET, GO_OFF.
    - Encoder e decoder automatico per pacchetti SysEx MSC.
- `ShowControlManager.js`:
  - Hub centrale di show control che collega `CueScheduler` e `LiveController`.
  - Instradamento automatico di comandi MSC in ingresso su cue scheduler (es. MSC GO su cue "2.0" avvia Scena 2; MSC ALL_OFF esegue hard stop e attiva blackout).
  - Sistema di mapping per trigger MIDI esterni (Note On / CC) verso callback e azioni di regia.
  - Cronologia e diagnostica in tempo reale per trasmissioni e ricezioni di rete e MIDI.
- `src/core/control/index.js` e `src/core/qlab/index.js`:
  - Barrel export aggiornati per esportare tutte le nuove classi e tipi sia dal modulo control che da qlab.

### Test (`test_show_control.js`)
- **140/140 test superati al 100%**:
  1. OscPacket Codec: codifica/decodifica messaggi, typetags misti, blob binari, bundle #bundle con timetag 64-bit, parser testuale con quotes.
  2. OSCDictionary: QLab workspace transport (/go, /stop, /hardStop, /pause, /resume, /panic, /reset, /load, /next, /previous), targeting per numero, targeting per ID, cue in standby, query di stato (/runningOrPausedCues, /standbyCue), e mapping Lightkey Live (/live/grandMaster, /live/speedMaster, /live/blackout, /live/blind, /live/freeze, /live/cell/trigger, /live/group/level).
  3. OSCController: ricezione binaria, esecuzione testuale, route personalizzate, tracciamento pacchetti inviati.
  4. NetworkCue: OSC, UDP, TCP, RAW HEX parsing flessibile (spazi, virgole, prefissi 0x), compilazione byte, trasmissione, ciclo di vita e disarm skip.
  5. MidiCue: traduzione note musicali ('C4' <-> 60), Note On, Note Off, Control Change, Program Change con Bank Select, Pitch Bend, MSC SysEx conformi a MMA RP-002 (GO, STOP, ALL_OFF, deviceId, cue number/list/path).
  6. ShowControlManager: instradamento MSC GO/STOP/ALL_OFF, trigger MIDI Note On/CC, cronologia trasmissioni e invio helper di rete/MIDI.

---

## STEP 6.2 — Stage Geometry Editor (`src/frontend-qlab/StageGeometryEditor.jsx`) ✅ COMPLETATO

### Modello matematico (`src/core/qlab/video/StageGeometry.js`)
- **Corner Pinning / Keystone**:
  - 4 angoli configurabili (TL, TR, BR, BL) con coordinate absolute in pixel.
  - `setKeystone(h, v)` applica correzione prospettica simmetrica bilanciata. Clamp in [-1, 1].
  - `setCorner(idx, x, y)` per posizionamento diretto con propagazione alla mesh.
  - `resetCorners()` ripristina la configurazione rettangolare di default e azzera keystone.
- **Surface Warping — Mesh Bézier NxM**:
  - Griglia di punti di controllo (da 2×2 a 10×10) inizializzata per interpolazione bilineare dai 4 angoli.
  - `createDefaultMesh(rows, cols)` distribuisce i punti uniformemente sulla superficie.
  - `setGridDensity(rows, cols)` ridimensiona e ricostruisce la mesh preservando gli angoli correnti.
  - `setMeshPoint(r, c, x, y)` deforma un singolo vertice; aggiorna automaticamente `corners` se il punto è agli angoli.
  - `rebuildMeshFromCorners()` propaga una modifica agli angoli su tutti i punti interni via interpolazione bilineare.
  - `resetMesh()` restituisce la mesh alla configurazione derivata dai corner attuali.
- **Edge Blending** — 4 bordi indipendenti (left, right, top, bottom):
  - `enabled`, `width` (pixel di overlap), `gamma` (curva di dissolvenza), `blackLevel` (compensazione black level 0..20%).
  - `getEdgeBlendFactor(x, y)` calcola il fattore di attenuazione moltiplicativo in un punto qualsiasi.
  - `renderEdgeBlendMask(ctx)` applica gradienti lineari `rgba(0,0,0,*)` sul canvas per la sovrapposizione morbida.
  - Formula: $f = \text{blackLevel} + (1 - \text{blackLevel}) \cdot t^\gamma$
- **Test Pattern Professionali** (`TestPatternType`):
  - `GRID` — Griglia di allineamento con assi principali (ciano/arancione) e diagonali di verifica linearità.
  - `CIRCLES` — Cerchi concentrici + reticolo broadcast per verifica aspect ratio e convergenza.
  - `COLOR_BARS` — 8 barre colore standard SMPTE + scala di grigi a 10 passi.
  - `CHECKERBOARD` — Scacchiera 64px per uniformità e badatura.
  - `CROSSHAIR` — Mirino centrale con cerchio di centratura.
  - `WHITE_UNIFORMITY` — Bianco pieno per hot-spot e uniformità luminosità.
  - `renderTestPattern(ctx, type)` esegue il rendering diretto sul canvas 2D dello Stage.
- **Rendering composito** `renderWarpedSurface(ctx, sourceImage, drawWireframe)`:
  - Rendering quad-by-quad della mesh deformata via clipping trapezoidale.
  - Wireframe overlay della griglia di deformazione.
  - Applicazione automatica della maschera Edge Blend al termine.
- **Integrazione VideoStage**: ogni `screenMapping` porta la propria istanza `StageGeometry` indipendente con serializzazione completa in `toJSON()`.

### UI Editor (`src/frontend-qlab/StageGeometryEditor.jsx`)
- **Layout 2 pannelli**: anteprima canvas interattiva (640×360) a sinistra, pannello a tab verticale a destra.
- **Canvas interattivo** (`GeometryCanvas`):
  - Rendering del test pattern attivo in scala ridotta sul canvas di anteprima.
  - Overlay Edge Blend visivo.
  - **Tab Corner Pin**: 4 handle draggabili colorati (rosso TL, giallo TR, verde BR, blu BL) con hover e active state.
  - **Tab Surface Warp**: punti mesh draggabili con differenziazione visiva degli angoli.
  - Tooltip con coordinate Stage e risoluzione.
- **5 schede di controllo**:
  1. **Corner Pin** — Slider Keystone H/V + 4 campi numerici per angolo (X, Y) + pulsante reset.
  2. **Surface Warp** — Slider righe/colonne, tabella coordinate mesh con editing numerico inline, reset.
  3. **Edge Blend** — Card per ogni bordo con toggle, slider Larghezza/Gamma/Black Level + anteprima curva gamma live.
  4. **Test Pattern** — Selezione radio + slider luminosità.
  5. **Display** — Lista display/mapping con editor inline (nome, offset, dimensioni, rotazione 0/90/180/270°, enable).
- **Stage selector** in toolbar: aggiunta/selezione di Stage multipli.
- **Integrazione QLabWorkspace**: terza tab `Stage Geo` nella barra di modalità del workspace, affiancata a "Cue List" e "Cue Cart".

### Test (`test_stage_geometry.js`)
- **61/61 test superati al 100%** su:
  - Costruzione base e angoli predefiniti
  - Corner Pinning (setCorner, setKeystone H/V, simmetria, clamp, reset)
  - Surface Warping (mesh NxM, interpolazione bilineare, setMeshPoint, ridimensionamento, propagazione angoli)
  - Edge Blending (4 bordi, gamma, blackLevel, getEdgeBlendFactor, setEdgeBlend patch)
  - Test Pattern (selezione tipo, brightness)
  - Rendering Canvas 2D headless (Grid, Color Bars, Checkerboard, Edge Blend mask, Warp wireframe)
  - VideoStage integrazione (geometry su screenMappings, addScreenMapping, toJSON serializzazione)

---

## STEP 6.1 — Video & Text Engine (`src/core/qlab/video/`) ✅ COMPLETATO

### Componenti e Modelli Sviluppati
- `VideoStage.js`:
  - Modello per il concetto fondamentale di 'Stages' di QLab 5 (superfici virtuali di rendering multi-proiettore/display).
  - Dimensioni configurabili (es. 1920x1080 standard, 3840x1080 panoramiche, LED wall a matrice estesa).
  - Mappature verso display fisici multipli (`screenMappings`) con coordinate di ritaglio (`stageX`, `stageY`, `stageWidth`, `stageHeight`) e rotazione hardware.
  - Ordinamento automatico per livello (`layer` 1..1000) e filtro su cue in stato `running`.
  - Pipeline di rendering composito 2D con centratura geometrica, traslazione, rotazione, scalatura, opacità e compositing blend modes.
- `VideoCue.js`:
  - Modello per le Video Cue di QLab 5 con riproduzione hardware-accelerata.
  - In/Out points (`inPoint`, `outPoint`), vari-speed playback rate e contatore loop (`infiniteLoop` / `playCount`).
  - Geometria e trasformazioni 2D: `translation` (X, Y), `scale` (X, Y), `rotation` (gradi), `opacity` (0..1), `blendMode` (`normal`, `screen`, `add`, `multiply`, ecc.).
  - Gestione aspect ratio: `'fit'`, `'fill'`, `'stretch'`, `'custom'`.
  - Metodo `renderLayer(ctx, stageW, stageH)` per rendering frame / placeholder diagnostico.
- `TextCue.js`:
  - Modello per le Text Cue (titoli, grafiche di testo, sottotitoli).
  - Rendering tipografico avanzato multi-riga su VideoStage con interlinea personalizzabile (`lineHeight`).
  - Famiglia di font, dimensione, spessore (`fontWeight`), stile (`fontStyle`), colore e allineamento (`left`, `center`, `right`).
  - Ombreggiatura morbida configurabile (`dropShadow`: blur, offset X/Y, colore).
  - Riquadro di sfondo opzionale (`background`: colore, padding, border radius arrotondato).
- `CameraCue.js`:
  - Acquisizione video live da telecamere, schede di acquisizione (Blackmagic DeckLink, Elgato Cam Link) e flussi virtuali (OBS).
  - Supporto per driver multipli cross-platform: **WebRTC** (`getUserMedia`), Windows **DirectShow** e Linux **v4l2**.
  - Formato e risoluzione configurabili (es. 1920x1080@60fps, 4K@60fps) e ribaltamento speculare (`mirror`).
  - Banner diagnostico Live Cam con stato broadcast e metadati hardware.
- `VideoEngine.js`:
  - Motore video centrale con registro degli Stages (`stages: Map<string, VideoStage>`).
  - Rilevamento schermi fisici multipli (`getDisplayOutputs()`) con integrazione Electron / display bounds.
  - Enumerazione telecamere hardware (`getCameraDevices()`) con driver metadata.
  - Pipeline globale di rendering `renderStage(stageId, ctx, activeCues)`.
  - Serializzazione e deserializzazione stato (`toJSON()`, `loadFromJSON()`).
- `test_video_engine.js`:
  - **49/49 test superati al 100%** su VideoStage, VideoCue, TextCue, CameraCue e VideoEngine.

---

## STEP 5.2 — Cue Inspector per Audio e Mic (`AudioInspector.jsx`) ✅ COMPLETATO

### Componenti e Modelli Sviluppati
- `AudioCue.js`:
  - Modello specializzato per le cue audio con gestione nativa dei punti di In/Out (`inPoint`, `outPoint`).
  - Calcolo dinamico della durata effettiva: $\text{durata} = \frac{\text{outPoint} - \text{inPoint}}{\text{playbackRate}} \times \text{playCount}$ (oppure $\infty$ per `infiniteLoop`).
  - Slicing temporale (`addSlice`, `removeSlice` con ordinamento cronologico automatico e loop count per slice).
  - Vari-speed ($0.2\times - 4.0\times$) e Pitch Shifting ($-24 .. +24$ semitoni) con opzione `preservePitch`.
  - Istanza `AudioMatrixMixer` integrata a bordo della cue.
- `MicCue.js`:
  - Modello specializzato per le sorgenti live microfoniche e line input hardware.
  - Assegnazione del nome del dispositivo di cattura e numero di canali (Mono, Stereo).
  - Regolazione del `micGain` con propagazione automatica sui trim della matrice audio.
- `AudioInspector.jsx`:
  - Componente inspector dedicato per Audio e Mic con due schede ad alta produttività:
    1. **Time & Loops (Waveform interattiva)**:
       - Rendering Canvas ad alte prestazioni con gradiente cromatico e griglia temporale.
       - Indicatori In/Out dorati ad alta visibilità draggabili via mouse o inserimento numerico (Shift+Click per IN, Alt+Click per OUT).
       - Visualizzazione e inserimento grafico delle **Slices** (linee ciano tratteggiate con badge $S_1, S_2\dots$ e loop count).
       - Cursore Playhead dinamico illuminato in tempo reale durante la riproduzione.
       - Mini-player di anteprima locale con Play/Pause e riavvolgimento.
       - Controlli per Vari-speed (cursore + preset $0.5\times, 1.0\times, 1.5\times, 2.0\times$) e Pitch Shifting con semitoni e preservazione tonalità.
    2. **Audio Matrix Mixer (QLab 5 Style)**:
       - Tabella di missaggio completa $N \times M$ con layout fedele a QLab 5.
       - Master Fader generale in dB con slider, mute e indicatore di picco.
       - Fader Master d'Uscita individuali su ciascuna colonna con barre VU meter progressive.
       - Controlli di riga per ciascun canale d'ingresso (Trim dB e LED verde di picco).
       - Celle Crosspoint $(i, j)$ in decibel con doppio click per mute immediato (`-INF` / `0.0 dB`) e LED d'attività di segnale.
       - Preset rapidi di routing: 1:1 Diretto, Mono Sum, Mute All.
- `CueInspector.jsx`:
  - Integrato per mostrare la scheda "Audio & Matrix Mixer" quando è selezionata una Cue di tipo Audio o Mic.
- `test_audio_inspector_models.js`:
  - **19/19 test superati al 100%** su modelli AudioCue, MicCue, slicing e vari-speed.

---

## STEP 5.1 — Audio Matrix Mixer Engine (`src/core/qlab/audio/`) ✅ COMPLETATO

### Core Architecture & File
- `AudioMath.js`:
  - Conversioni decibel/lineare: `dbToLinear(dB)` (con threshold di silenzio a $\le -60$ dB), `linearToDb(linear)`.
  - Curve di dissolvenza (`FadeCurveType`): `SMOOTHSTEP` (S-curve Hermite $3t^2 - 2t^3$), `LINEAR`, `EXPONENTIAL`, `DECIBEL` (dissolvenza percettiva logaritmica).
  - Formattazione dB (`formatDb`) con visualizzazione `-INF`.
- `AudioTarget.js`:
  - Modello dati per il target audio multicanale sorgente e destinazione.
  - Supporto per profili surround standard e custom: Mono (1ch), Stereo (2ch), LCR (3ch), Quad (4ch), 5.1 Surround (6ch), 7.1 Surround (8ch).
  - Mappatura verso dispositivi hardware (ASIO, WASAPI, ALSA, Dante Virtual Soundcard).
- `AudioFadeController.js`:
  - Controller dedicato per l'interpolazione a 60 FPS delle dissolvenze temporizzate della matrice (Fade Cues).
  - Supporto per transizioni coordinate su: Master Level, Output Masters, Input Trims e singoli nodi Crosspoint.
  - Callback `onComplete` e monitoraggio del progresso `getProgress()`.
- `AudioMatrixMixer.js`:
  - Matrice configurabile $N \times M$ con routing crosspoint, fader master d'uscita, trim d'ingresso e fader master generale.
  - Calcolo del guadagno lineare effettivo combinando i quattro stadi di fader e rispettando gli stati di Mute indipendenti.
  - `process(inputBuffers, sampleCount)`: elaborazione e mixaggio a blocchi PCM Float32 con sommatoria ponderata dei canali.
  - **Peak Metering**: calcolo in tempo reale dei picchi di ampiezza per tutti gli ingressi, uscite e punti di incrocio.
  - **Decadimento Balistico**: decadimento esponenziale programmabile (es. $24$ dB/s) che emula i VU/peak meter delle console broadcast digitali.
  - Ridimensionamento dinamico della matrice (`resize(newIn, newOut)`) con preservazione delle impostazioni e default routing 1:1.
  - Integrazione completa del controller fade (`fadeTo`, `stopFade`, `tick`).
- `index.js`: Barrel export completo per il sottosistema audio di QLab.

### Test (`test_audio_matrix.js`)
- **47/47 test superati al 100%**:
  1. Matematica audio: conversioni dB/lineare, soglie $-60$ dB, curve di interpolazione.
  2. Inizializzazione matrice: routing 1:1, guadagni combinati e isolamento Mute.
  3. Processing PCM: sommatoria canali corretta sui buffer di destinazione e picchi rilevati.
  4. Balistica Peak Meters: decadimento esponenziale nel tempo.
  5. Dissolvenze temporizzate: esecuzione interpolata e callback di completamento.
  6. Multichannel Target & Resize: surround 5.1 e conservazione delle proprietà.

---

## STEP 4.2 — Interfaccia QLab Workspace (`QLabWorkspace.jsx`) ✅ COMPLETATO

### Componenti UI (`src/frontend-qlab/`)
- `QLabWorkspace.jsx`:
  - Controller principale del workspace di QLab 5 collegato a `CueScheduler`.
  - Loop di animazione fluido a 60 FPS con precisione temporale al millisecondo per progress bar, countdown e show time.
  - Tasto **GO** gigante ad alto contrasto con barra di progresso integrata e shadow luminosa.
  - Barra di trasporto completa:
    - **Panic** (ESC): dissolvenza di emergenza progressiva (1.0s) con pulsazione visiva.
    - **Stop** (.): arresto immediato senza dissolvenza.
    - **Pause / Resume** (P): congelamento e ripresa simultanea di tutte le cue attive.
    - **Load** (L): pre-caricamento immediato della cue in Standby.
    - **Reset**: azzeramento show time e riposizionamento del playhead all'inizio.
  - **Standby Cue Display**: box centrale ad alta leggibilità con numero cue, nome, tipo, pre-wait, durata, post-wait e icona del follow action.
  - Barra superiore per la creazione rapida di qualsiasi tipologia di Cue: Group, Audio, Mic, Video, Text, Fade, Light, Network, MIDI, Timecode.
  - Switcher di modalità: **Cue List** vs **Cue Cart**.
  - Dropdown per la configurazione dinamica della visibilità delle colonne della tabella.
- `CueListTable.jsx`:
  - Tabella gerarchica in stile nativo macOS Dark.
  - Supporto per espansione e compressione ad albero dei GroupCue (`Folder` / `FolderOpen`).
  - Indentazione dinamica in base alla profondità (`depth`) dei figli.
  - Colonne configurabili: Q#, Stato (Armed/Disarmed toggle), Tipo con icona, Nome, Target, Pre-Wait, Durata (con barra di progresso live verde integrata), Post-Wait, Seguito (Auto-Continue / Auto-Follow), Note.
  - Cursore Standby dorato con punto luminoso pulsante e bordo di selezione.
  - Indicatori colore etichetta a sinistra di ciascuna riga (rosso, arancione, verde, blu, viola).
  - Tasti hover di riga: Play/Stop per singola cue, eliminazione.
- `CueInspector.jsx`:
  - Pannello inferiore dockable ed espandibile/comprimibile per la modifica live della cue selezionata.
  - Tab **Generale**: numero, nome, target/file, colore etichetta, toggle Armed/Disarmed, Flagged, e modalità GroupCue (Timeline, Playlist, Start-First, Random).
  - Tab **Tempi & Seguito**: modifica numerica precisa di Pre-Wait, Durata, Post-Wait e menu a tendina per Continue Mode (Do Not Continue, Auto-Continue, Auto-Follow).
  - Tab **Note**: textarea per indicazioni di regia e cambi scena.
- `CueCartGrid.jsx`:
  - Cue Cart a griglia con pulsanti/pad colorati per il trigger live istantaneo di clip audio, jingle ed effetti speciali.
  - Hotkey numeriche da `1` a `9` per trigger da tastiera.
  - Barra di progresso interna e anello di stato su ogni cella attiva.
  - Modale di editing rapido su ogni cart button (nome, target, durata, colore).
- `QLabMainView.jsx`:
  - Aggiornato per montare l'interfaccia completa `QLabWorkspace`.

---

## STEP 4.1 — Motore Gerarchico Cue QLab 5 ✅ COMPLETATO

### Core Engine (`src/core/qlab/`)
- `CueTypes.js`:
  - `CueState`: `IDLE`, `LOADED`, `RUNNING`, `PAUSED`, `COMPLETED`, `BROKEN`
  - `CuePhase`: `NONE`, `PRE_WAIT`, `ACTION`, `POST_WAIT`, `COMPLETED`
  - `ContinueMode`: `DO_NOT_CONTINUE`, `AUTO_CONTINUE`, `AUTO_FOLLOW`
  - `GroupMode`: `TIMELINE`, `PLAYLIST`, `START_FIRST_AND_GO_TO_NEXT`, `RANDOM`
  - `CueType`: `BASE`, `GROUP`, `AUDIO`, `MIC`, `VIDEO`, `CAMERA`, `TEXT`, `LIGHT`, `FADE`, `NETWORK`, `MIDI`, `TIMECODE`, `WAIT`, `SCRIPT`
- `BaseCue.js`:
  - Modello base unificato per qualsiasi cue di show control con timing ad alta precisione.
  - Proprietà temporali: `preWait`, `duration`, `postWait`, `continueMode` (in secondi).
  - Ciclo di vita: `load()`, `start()`, `pause()`, `resume()`, `stop()`, `reset()`.
  - Gestione stato Armed/Disarmed: se disarmata (`armed: false`), salta l'azione materiale ma propaga le tempistiche di Pre-Wait/Post-Wait e i Follow Action.
  - Gestione stato Broken: blocco sicuro se il file/target è mancante o invalido.
  - Metodo `tick(dt)` con gestione transizioni di fase e trigger dell'avanzamento sequenziale (`shouldTriggerNext`).
  - Differenziazione rigorosa:
    - **Auto-continue**: scatta a `preWait + postWait` anche se l'azione dura ancora.
    - **Auto-follow**: scatta a `preWait + duration + postWait` solo al termine dell'azione.
- `GroupCue.js` (estende `BaseCue`):
  - Supporto per figli gerarchici con nidificazione arbitraria (`children`, `addChild`, `removeChild`, `moveChild`).
  - Implementazione delle 4 modalità native di QLab 5:
    1. **Timeline**: avvia tutti i figli contemporaneamente; durata calcolata sul figlio con estensione massima.
    2. **Playlist**: esecuzione sequenziale progressiva automatica da un figlio all'altro.
    3. **Start first and go to next**: avvia il primo figlio e fa avanzare l'indice interno ad ogni GO successivo.
    4. **Random**: estrae e avvia un figlio a sorte da un bag senza ripetizione immediata.
- `CueScheduler.js`:
  - Scheduler centrale del workspace QLab:
    - Gestione coda Cue (radice e rami gerarchici), ricerca ricorsiva per ID o numero.
    - Playhead / Standby tracking con avanzamento automatico del cursore al tasto GO.
    - Loop di tick ad alta precisione (60 FPS o delta time variabile).
    - Risoluzione automatica dei trigger Auto-continue e Auto-follow sia a livello radice che tra fratelli di gruppo.
    - Trasporto: `go(cueId)`, `stop(cueId)`, `pause(cueId)`, `resume(cueId)`.
    - **Panic**: dissolvenza d'emergenza temporizzata (fading progressivo e stop globale di tutte le cue attive).
    - `getFlattenedCues()` per il rendering gerarchico con indicatore di profondità (`depth`).
- `index.js`: Barrel export completo per il modulo QLab.

### Test (`test_qlab_engine.js`)
- **59/59 test superati al 100%** su 6 gruppi di verifica:
  1. BaseCue: creazione, stati (Loaded, Broken, Running, Paused, Idle).
  2. Fasi temporali: Pre-wait, Action, Post-wait, Completed con passaggio fluido dei tempi in eccesso.
  3. Follow Actions: Auto-continue vs Auto-follow timing.
  4. Cue disarmata: skip immediato dell'azione e propagazione follow action.
  5. GroupCue: Timeline, Playlist, Start-first e Random.
  6. CueScheduler: GO, playhead, auto-triggering a cascata, Panic con dissolvenza e flattening gerarchico.

---

## STEP 3.2 — Live View di Lightkey ✅ COMPLETATO

### Core Engine (`src/core/control/LiveController.js`)
- **Grand Master** (0–100%): scala l'intensità di TUTTI i fari prima dell'output DMX.
- **Speed Master** (0.1×–4.0×): moltiplica il tempo passato all'EffectsEngine per modulare la velocità degli effetti in real-time.
- **Blind Mode**: sospende l'invio DMX al palco senza interrompere il calcolo (editing senza output).
- **Freeze**: congela l'ultimo frame DMX calcolato (nessun aggiornamento finché non disattivato).
- **Trigger Grid 6×8 = 48 celle**: ogni cella può essere tipo `Scena`, `Palette`, `Cue` o `Blackout`; modalità `Latch` (toggle) o `Flash` (momentaneo). 11 celle preset al lancio (Ambra, Blu, Rosso, UV, Verde, Cyano, Bianco, Strobe FLASH, Bump FLASH, Blackout).
- **Group Faders**: 3 gruppi predefiniti (Spot Posteriori, Wash Frontali, All); livello 0–100%; il fader più basso tra i gruppi che contengono il faro vince (non somma). Aggiungi/rimuovi gruppi custom.
- `src/core/control/index.js` aggiornato: esporta `LiveController`, `TriggerMode`, `CellType`.

### UI (`src/frontend-lightkey/LiveView.jsx`)
- **Override Strip** (top bar 44px):
  - Grand Master: slider progressivo con colore adattivo (blu >60%, ambra 30-60%, rosso <30%).
  - Speed Master: slider 0.1×–4.0×, colore verde.
  - `BLIND` toggle (giallo quando attivo, con banner warning "Nessun output DMX").
  - `FREEZE` toggle (blu cielo quando attivo, con banner "Output DMX congelato").
  - `BLACKOUT` (rosso pulsante quando attivo).
  - BPM + TAP integrati.
  - Indicatore DMX live (verde/ambra/azzurro in base allo stato).
- **Trigger Grid**: griglia 6×8 CSS Grid, celle colorate con glow attivo, badge modalità (⚡ Flash / ◉ Latch). Doppio click su una cella apre il modale di configurazione.
- **Modale configurazione cella**: label, color picker nativo, tipo (Scena/Cue/Palette/Blackout/Vuota), modalità (Latch/Flash), anteprima live. ESC per chiudere.
- **Group Faders**: fader verticali per ogni gruppo con fill colorato adattivo, track visiva e knob. Pulsante "+ Aggiungi Gruppo".
- **Cue List integrata**: sempre visibile a h=196px in fondo alla Live View.

### Integrazione `LightkeyMainView.jsx`
- Importa `LiveController` e `LiveView`.
- Stato aggiunto: `liveController`, `grandMaster`, `speedMaster`, `isBlind`, `isFrozen`.
- **RAF loop aggiornato**: `Effects(now × speedMaster) → Cue tick → setFixtures(pre-GM) → applyGroupFaders → applyGrandMaster → DMX` (Blind/Freeze rispettati).
- Handler: `handleGrandMasterChange`, `handleSpeedMasterChange`, `handleToggleBlind`, `handleToggleFreeze`.
- **Switch render**: `viewMode === 'design'` → StageCanvas + HUD + Cassetto dockable; `viewMode === 'live'` → `<LiveView>` full-screen (senza canvas).
- Toolbar: i tab Cue/Palette/Effetti sono visibili **solo in Design mode**; il status DMX in toolbar cambia colore (verde/ambra/azzurro).

### Test (`test_live_controller.js`)
- **44/44 test superati** (5 gruppi):
  1. Grand Master (scaling, clamp, applyGrandMaster)
  2. Speed Master (scaling, clamp min/max)
  3. Blind & Freeze (toggle indipendente, stato combinato)
  4. Trigger Grid (init 48 celle, Latch toggle, Flash + release, updateCell, cella vuota → null)
  5. Group Faders (setGroupFader, applyGroupFaders min-wins, grp All, addGroup/removeGroup)

---

## STEP 3.1 — Effects Engine ✅ COMPLETATO
*(dettagli nella versione precedente del file)*

---

## STEP 2.3 — Palettes & Cues Engine ✅ COMPLETATO

---

## Prossimo Passo
- **STEP 6.1**: Video & Text Engine (`src/core/qlab/video/`)
  - Concetto di 'Stages' di QLab con mapping su uscite monitor fisiche multiple, supporto per video player hardware-accelerato, Text Cues con rendering tipografico avanzato, e camera input via WebRTC/v4l2/DirectShow.






## Effects Engine — STEP 3.1 ✅ COMPLETATO

### Core Engine (`src/core/effects/`)
- `Waveforms.js` — Forme d'onda matematiche: Sinusoidale, Dente di Sega (Sawtooth), Rampa (Ramp), Onda Quadra (duty-cycle variabile), Triangolare, Curva di Bézier Cubica (Newton-Raphson solver).
- `MotionGenerators.js` — Generatori di movimento Pan/Tilt: Cerchio/Ellisse, Figura a 8 (Lissajous 2:1), Spirale logaritmica, Lineare.
- `PhaseModulator.js` — Modulatore di fase per fanning temporale tra fari: Lineare (360°/N), Simmetrico (specchio), Pari/Dispari alternato, Casuale deterministico (hash).
- `BeatClock.js` — Clock BPM: BPM manuale (20–300), Tap Tempo (media mobile 6 colpi), Resync, `getPhase()` per divisioni musicali (1/32…2 misure), rilevatore beat pulse.
- `EffectInstance.js` — Modello dati per un singolo effetto (attributo, forma d'onda/movimento, timing, fase, range).
- `EffectsEngine.js` — Motore principale: applica effetti attivi ai fari a 60 FPS, 4 template predefiniti (Ballyhoo Circolare, Figura a 8, Dimmer Pulse, Chase Colore Arcobaleno).
- `index.js` — Barrel exports di tutti i tipi e classi.

### UI Panel (`src/frontend-lightkey/EffectsPanel.jsx`)
- Pannello dockabile "Effetti" nel cassetto inferiore di LightkeyMainView.
- BPM Master + Tap Tempo in tempo reale.
- Lista effetti con miniatura waveform/motion (canvas inline), toggle attivo/inattivo, rimozione.
- Editor contestuale: attributo target (Pan/Tilt, Dimmer, Hue, Saturazione), forma d'onda o shape di movimento, divisione musicale (sincronizzazione BPM), spread di fase, velocità.
- Pulsante "+ Effetto" che aggiunge dal template selezionato.

### Integrazione in `LightkeyMainView.jsx`
- `EffectsEngine` istanziato a 120 BPM; `applyEffects()` chiamato nel RAF loop **prima** del tick CueEngine.
- Stato `bpm` e `effects` collegati alle funzioni handler (`handleBpmChange`, `handleTapTempo`, `handleToggleEffect`, `handleAddEffect`, `handleRemoveEffect`, `handleUpdateEffect`).
- Cassetto inferiore espanso a 3 tab: **Cue List**, **Palette**, **Effetti** (icona `Wand2`).

### Test
- `test_effects_engine.js` — 5 suite di test, **100% superati**:
  - Forme d'onda matematiche (Sine, Sawtooth, Square, Bezier)
  - Generatori di movimento (Cerchio, Figura a 8)
  - PhaseModulator (Lineare e Simmetrico)
  - BeatClock & Tap Tempo
  - EffectsEngine applicazione real-time su fixture multiple

---

## Presets, Palettes & Cues Engine (STEP 2.3)
- `src/core/control/PaletteManager.js` — 21 palette predefinite, snapshotting, fusione attributi selettiva.
- `src/core/control/CueEngine.js` — 60 FPS, GO/Back/Pause/Stop/Blackout, crossfader manuale A/B, snap Gobo/Prism/Shutter a t≥0.5.
- `src/frontend-lightkey/PalettesPanel.jsx` — grid a schede (Tutte, Colore, Posizione, Beam, Preset).
- `src/frontend-lightkey/CueListPanel.jsx` — consolle live con GO animato, progress bar, tabella cue LIVE/NEXT.
- `test_cues_and_palettes.js` — 100% superato.

---

## Prossimo Passo
- **STEP 7.3**: Inspector e UI per Network, MIDI e Timecode Cues in QLabWorkspace
  - Schede Inspector dedicate per NetworkCue (protocollo OSC/UDP/TCP/HEX, IP, porta, payload, test live di trasmissione)
  - Schede Inspector dedicate per MidiCue (Note On/Off con picker grafico, CC, PC, parametri MSC)
  - Schede Inspector dedicate per TimecodeCue (sorgente MTC/LTC, frame rate, timecode start, formati)
  - Box di visualizzazione e monitoraggio Timecode live nella barra superiore del Workspace (chasing status, freewheeling, sync status, HUD timecode)




