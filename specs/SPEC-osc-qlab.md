# SPEC-osc-qlab.md  (ShowSuite / sezione Cue, riferimento: QLab 5 OSC API)
Obiettivo: server OSC **compatibile** con l'API di QLab 5 (così client esistenti — script, Companion, controller — funzionano) + client OSC dei Network cue. Modello dati: SPEC-cue-modello.md / SPEC-cue-tipi.md.
Legenda accesso: V=view, E=edit, C=control. R=lettura, W=scrittura, A=azione.

## 1. Trasporto e porte
- **OSC UDP+TCP**: porta 53000 (config per workspace; ShowSuite lo ascolta comunque a livello app). UDP: 1 messaggio = 1 datagram; **risposte UDP sulla porta 53001** (per workspace: `udpReplyPort`). TCP: framing **SLIP doppio END** (RFC 1055, OSC 1.1).
- **Plain text UDP**: porta 53535 (config); il testo (es. `/cue/selected/start`) è interpretato come OSC; nessuna risposta.
- Messaggi arrivati su una porta sono ricevuti da **ogni workspace aperto** in ascolto su quella porta (QLab 5). Instradamento selettivo: porte diverse, prefisso `/workspace/{id}` o `/workspace/{nome}`.
- Discovery: Bonjour/mDNS (ShowSuite: zeroconf, servizio `_qlab._tcp` e `_osc._udp`) per le app remote; senza mDNS → IP manuale.
- Firewall: 53000/53001 (e porta custom).

## 2. Impostazioni di accesso (Workspace Settings → Network → OSC Access)
- Checkbox globale "OSC access" (default **on**). Mostra IP della macchina.
- Tabella permessi **View / Edit / Control** (Edit/Control disabilitati se View off). Prima riga **No Passcode** (default: nessun permesso). Nuovo workspace: 1 passcode casuale **4 cifre** con accesso completo; Add/Delete passcode; più passcode ammessi.
- View = leggere info; Edit = creare/eliminare cue, cambiare parametri e settings; Control = muovere playhead, avviare/fermare cue.
- Se **tutti** i workspace aperti richiedono passcode, i messaggi applicativi sono accettati solo dopo un `/connect` valido su almeno un workspace; eccezioni sempre accettate: `/version`, `/workspaces`.
- `/workspace/{id}/connect {passcode?}` → `ok` | `badpass` | `error`. Tentativi errati ripetuti → ritardo progressivo crescente. Senza passcode → permessi della riga No Passcode (se nessuno: impossibile).
- Dopo `/connect` con passcode, va inviato prima di ogni altro messaggio.

## 3. Sessione client
- UDP: client disconnesso dopo **61 s** di inattività (qualsiasi messaggio, es. `/thump`, resetta). `/forgetMeNot true` / `/udpKeepAlive true` → il client e le sue impostazioni (`alwaysReply`, passcode…) restano memorizzati fino a quit o `false`. TCP: nessun timeout; resta fino a `/disconnect` o chiusura socket.
- **Updates**: `/updates 1` abilita notifiche push al client, `/updates 0` le disabilita (permesso V). Messaggi push:
  - `/update/workspace/{ws_id}` → ricaricare le liste di cue.
  - `/update/workspace/{ws_id}/cue_id/{cue_id}` → ricaricare quel cue (se Group/lista, anche figli).
  - `/update/workspace/{ws_id}/cueList/{list_id}/playbackPosition {cue_id}` → playhead cambiato (senza argomento = nessun playhead).
  - `/update/workspace/{ws_id}/disconnect` → il client deve disconnettersi (workspace in chiusura).
  - `/workspace/{id}/updates {n}` deprecato.
- **Risposte**: `/reply{indirizzo_inviato} {json}` con json `{ "workspace_id": str (opzionale), "address": str, "status": "ok"|"error"|"denied", "data": valore }`. `denied` = non connesso o permessi insufficienti. Azioni discrete (`/go`, `/panic`) non rispondono salvo `/alwaysReply`.
  - `/alwaysReply {n}` (R/W; V,E,C): ≠0 → risposta a ogni messaggio (json con workspace_id, address, status ok|error); 0 → stop.
  - `/replyFormat {fmt}`: stringa con token `#workspace_id#`, `#address#`, `#status#`, `#data#`; stringa vuota = formato default. Es. `/replyFormat "#data# #address#"`, poi `/cue/1/colorName` → `green /cue/1/colorName`.
- **Booleani** accettati: bool OSC; numeri (0=false, altro=true, anche 0.5); stringhe (inizio N,n,F,f,0 → false; Y,y,T,t,1–9 → true). Argomenti OSC 1.1 accettati: `T`,`F`,`I`(impulse),`N`(null).

## 4. Indirizzamento dei cue
- `/workspace/{id}/cue/{numero}/…` oppure `/cue_id/{uuid}/…`; senza prefisso workspace → tutti i workspace in ascolto su quella porta.
- Speciali: `/cue/selected` (cue selezionati), `/cue/playhead` = `/cue/playbackPosition` (cue in standby), `/cue/active` (cue in esecuzione o in pausa).
- Wildcard OSC pattern: `*`, `?`, `[..]`. Es. `/cue/*/armed 0` (tutti), `/cue/?/armed 0`, `/cue/[*]/armed 0` (solo con numero), `/cue/understudy-*/colorName green`.
- **Spazi non ammessi** negli indirizzi → niente spazi nei numeri cue se controllati via OSC. Nome workspace: solo caratteri validi in OSC (no spazi/unicode/diacritici), senza estensione.
- **Incremento/decremento**: `/cue/1/prop/+ {d}`, `/cue/1/prop/- {d}` per proprietà numeriche contrassegnate "+/-" (es. `/cue/10/preWait/+ 1`).
- **Live**: molte proprietà hanno forma `…/live` che agisce sul valore *attivo* (non sullo stato di avvio): non marca il documento come modificato, sparisce al reset del cue/workspace. Es. `/cue/1/rate 2` vs `/cue/1/rate/live 2`. Proprietà con "temp" (tempDuration, tempCueTarget…) = modifiche temporanee (si azzerano col reset).

## 5. Messaggi applicativi (non per workspace)
| Indirizzo | Acc | Note |
|---|---|---|
| `/version` | A | versione app |
| `/workspaces` | R | array `{uniqueID, displayName, port, udpReplyPort, version}` |
| `/disconnect` | A | |
| `/alwaysReply`, `/replyFormat`, `/forgetMeNot`, `/udpKeepAlive` | R/W | vedi §3 |
| `/fontNames` | R | array nomi/PostScript dei font |
| `/fontFamiliesAndStyles` | R | dict famiglia→[stili] |
| `/liveFadePreview {b}`, `/toggleLiveFadePreview` | R/W (C), A | |
| `/overrides/{x}Enabled {b}` + `/overrides/toggle{X}` | R/W, A | x ∈ dmxOutput, midiInput, midiOutput, mscInput, mscOutput, sysexInput, sysexOutput, networkExternalInput, networkExternalOutput, networkLocalInput, networkLocalOutput, timecodeInput, timecodeOutput (external=altri dispositivi in rete; local=QLab stesso/software sulla stessa macchina) |
| `/overrideWindow {b}`, `/toggleOverrideWindow`, `/timecodeWindow {b}`, `/toggleTimecodeWindow` | R/W, A | |
| `/workingDirectory {path}` | R/W | supporta `~`; solo per open/save via OSC |

## 6. Messaggi workspace `/workspace/{id}/…`
**Stato/liste (R, V)**: `cueLists`, `selectedCues`, `runningCues` (in esecuzione, con durata che scorre), `runningOrPausedCues` (= Active Cues) → array di `{uniqueID, number, name, listName, type, colorName, colorName/live, flagged, armed}`; per Group includono `cues:[…]` ricorsivo. Varianti `…/shallow` (senza figli) e `…/uniqueIDs`, `…/uniqueIDs/shallow` (solo ID). `basePath` (cartella del workspace, vuota se non salvato). `thump` → "thump" (heartbeat). `doubleGoWindowRemaining` (secondi mancanti al prossimo GO consentito).
**Trasporto (C)**: `go [numero]` / `go/{numero}` (se numero: avvia quel cue, altrimenti GO della lista corrente), `auditionGo [n]`/`auditionGo/{n}`, `pause`, `resume`, `stop` (code di effetti continuano), `hardStop` (taglio immediato anche effetti), `panic` (fade breve poi hard stop; secondo panic = hard stop immediato), `panicInTime {s}` (≥0), `reset` (ferma tutto, playhead in cima alla lista corrente, azzera temporanei).
**Playhead (C)**: `playhead/{numero}`, `playheadID/{id}` (valore `none` = nessun playhead), `playhead/next|previous|nextSequence|previousSequence|active|selected` (stesso con alias `playbackPosition…`).
**Selezione (V)**: `select/{numero}`, `select_id/{id}`, `select/next`, `select/previous`.
**Editing (E)**: `new {tipo}` | `new {tipo} {cue_id} {riga} {colonna}` (crea dopo cue_id; se cue_id è un cart crea dentro alla posizione) → ritorna unique ID e seleziona il nuovo cue; tipi: audio, mic, video, camera, text, light, fade, network, midi, "midi file", timecode, group, start, stop, pause, load, reset, devamp, goto, target, arm, disarm, wait, memo, script, list/cuelist/"cue list", cart/cuecart/"cue cart". `delete/{numero}`, `delete_id/{id}`, `delete/selected`, `delete/active` (cancella cue in corso o in pausa). `move/{cue_id} {nuovo_indice} [parent_id]`. `renumber {start} {incremento} {prefisso} {suffisso}` (cue selezionati; numeri positivi). `undo`, `redo`, `save`.
**Modalità/UI**: `currentCueList {nome}`, `currentCueListID {id}` (R/W); `showMode {b}`/`toggleEditShowMode`; `alwaysAudition {b}`; `auditionMonitors {b}`/`toggleAuditionMonitors`; `fullScreen {b}`/`toggleFullScreen`; `lightDashboard {b}`/`toggleLightDashboard`.
**Light dashboard** `dashboard/…`: `clear` (tutti i parametri a home; parked esclusi), `mode {s}` / `nextMode` (sliders↔tiles), `newCueWithAll`, `newCueWithChanges`, `recordAllToLatest`, `recordAllToSelected`, `updateLatestCue`, `updateSelectedCues`, `updateOriginatingCues`, `revert`, `undo`, `redo`, `setLight {nome[.param]} {valore} [tempo]` e forma `setLight/{nome} {valore} [tempo]` (senza param = parametro di default; es. `/dashboard/setLight frontlight 50 5`, `myMover.cyan 75`).

## 7. Settings `/workspace/{id}/settings/…`
- `general/minGoTime {n}` (≥0, decimali), `general/selectionIsPlayhead {b}` + `toggleSelectionIsPlayhead`, `general/undo|redo`.
- `audio/maxVolume`, `audio/minVolume` (dB), `audio/outputChannelNames` (e `mic/…`), `audio/patchList` (JSON patch di uscita), `audio/undo|redo`; `mic/patchList` (ingressi), `midi/patchList`, `network/patchList`, `light/patch` (JSON verboso del patch luci), ognuno con `undo|redo`.
- `video/inputPatchList`, `video/routes`, `video/route/{nome}|routeIndex/{n}|routeID/{id}` (+ `/enableGuides {b}`, `/uniqueID`), `video/stages`, `video/stage/{nome}|stageID/{id}` (+ `/name {s}`, `/regions`, `/size`, `/size/width`, `/size/height`, `/uniqueID`), `…/region/{nome}|regionID|regionIndex` (+ `/bounds {x y w h}` o stringa, `/enableGrid {b}`, `/enableGuide {b}`, `/resetControlPoints`), `video/undo|redo`.

## 8. Proprietà cue `/cue/{n}/…` (R lettura; W scrittura; A azione)
**Azioni (C)**: `go`, `start`, `startAndAutoloadNext`, `stop`, `pause`, `resume`, `togglePause`, `hardPause`, `hardStop`, `panic`, `panicInTime {s}`, `preview`, `auditionGo`, `auditionPreview`, `load`, `loadAt {t}`, `loadActionAt {t}`, `loadFileAt {t}`, `loadAndSetPlayhead`, `reset`, `captureTimecode`.
**Comuni R/W (E)**: `name`, `number`, `notes`, `armed {b}`, `autoLoad {b}`, `flagged {b}`, `colorName {s}` (+`/live`; none, red, orange, green, blue, purple + altri), `colorCondition {0 always|1 before action|2 after action}`, `continueMode {0 no|1 auto-continue|2 auto-follow}`, `preWait`, `postWait`, `duration` (solo se `allowsEditingDuration`), `tempDuration`, `cueTargetID`, `cueTargetNumber` (`none`/"" = nessun target), `tempCueTargetID`, `tempCueTargetNumber`, `fileTarget`, `secondTriggerAction {0 nulla|1 panic|2 stop|3 hard stop|4 hard stop & restart|5 devamp|6 playlist next|7 playlist previous (6,7 solo Playlist)}`, `secondTriggerOnRelease {b}`, `duckOthers {b}`, `duckLevel`, `duckTime`, `fadeAndStopOthers {n}`, `fadeAndStopOthersTime`, `soloCueInTime`.
**Comuni sola lettura**: `uniqueID`, `type`, `defaultName`, `displayName`, `listName`, `parent`, `currentCueTarget`, `currentDuration`, `actionElapsed`, `percentActionElapsed`, `preWaitElapsed`, `percentPreWaitElapsed`, `postWaitElapsed`, `percentPostWaitElapsed`, `maxTimeInCueSequence`, `allowsEditingDuration`, `hasCueTargets`, `hasFileTargets`, `isLoaded`, `isRunning`, `isPaused`, `isBroken`, `isWarning`, `isActionRunning`, `isAuditioning`, `isCrossfadingOut`, `isOverridden`, `isPanicking`, `isTailingOut`, `cartPosition` (+`/row`,`/column`, [0,0] se fuori cart).
**Trigger timecode (cue)**: `timecodeTrigger` (+`/hours|minutes|seconds|frames|bits|text`).
**Query personalizzata**: `valuesForKeys "[\"opacity\",\"surfaceSize\"]"`; `valuesForKeysWithArguments "{\"level\":[0,0]}"` (un valore per chiave).
**Group/List/Cart**: `children/` (+`/shallow`, `/uniqueIDs`, `/uniqueIDs/shallow`), `mode {0 list|1 start first & enter|2 start first|3 timeline|4 start random|5 cart|6 playlist}` (0 e 5 sola lettura), `playhead|playbackPosition {num}` e `playheadID|playbackPositionID {id}` (+ `/next|previous|nextSequence|previousSequence`), `isChildFlagged`, `isChildAuditioning`, `cartRows`, `cartColumns`, `moveCartCue/{figlio} {riga} {col}`, `shuffle`; playlist: `playlistLoop {b}`, `playlistShuffle {b}`, `playlistCrossfade {b}`, `playlistCrossfadeDuration {s}` (alias `playlist/doLoop|doShuffle|doCrossfade`, `playlist/crossfade/duration`), `playlist/next`, `playlist/previous`; timecode di lista/cart: `currentTimecode` (+ `/hours|minutes|seconds|frames|bits|text`), `timecodeSyncMode {0 MTC|1 LTC}`, `timecodeSMPTEFormat {0 24|1 25|2 30df|3 30|4 29.97|5 29.97df|6 60|7 59.94|8 60df|9 59.94df|10 50|11 23.98}`, `timecodeStartBehavior {0 non partire per trigger precedenti|1 ultimo minuto|2 ultima ora|3 lookback|4 tutti i precedenti}`, `timecodeStopBehavior {0 nulla|1 pausa cue|2 stop cue}`, `timecodeLookbackTime {s}`, `timecodeFreewheelTime`.
**Audio (valgono anche Mic, Video, Camera)**: `fileTarget`, `startTime`, `endTime`, `playCount`, `infiniteLoop {b}`, `lastSliceInfiniteLoop {b}`, `lastSlicePlayCount`, `rate` (+`/live`), `preservePitch {b}`, `doFade {b}` (integrated fade), `lockFadeToCue {b}`, `currentFileTime`, `numChannelsIn`, `patch {n}`, `patchList`, `audioOutputPatchName|Number|ID`, `audioTrackFormats`, `audioTrackID`; slice: `sliceMarkers`, `sliceMarker {i} {t} {n}` (+`/{i}/time`, `/{i}/playCount`), `addSliceMarker {t} {n}` (n=-1 infinito; indice da 0), `deleteSliceMarker {i}`, `deleteSliceMarkers`; livelli: `level {in} {out} {dB}` (`level/{in}/{out}`; 0 0 = main), `levels`, `sliderLevel {ch} {dB}`, `sliderLevels`, `gang {in} {out} {g}`, `setDefaultLevels`, `setSilentLevels`, `liveAverageLevel/{out} {low} {high}` (livello medio live riscalato in [low,high]). Mic/Camera: `audioInputPatchName|Number|ID`, `channels`, `channelOffset`; Camera: `cameraPatch`, `videoInputPatchName|Number|ID`.
**Video/Camera/Text** (+`/live` dove esiste): `fillStage`, `preserveAspectRatio`, `opacity`, `layer`, `smooth`, `blendMode`, `clockType` (+`/video`…), `holdLastFrame`, `crop {t b l r}` (+`cropTop|Bottom|Left|Right`), `translation {x y}` (+`/x`,`/y`), `scale {x y}` (+`/x`,`/y`), `origin {x y}` (+x,y), `anchor {x y}` (+x,y), `quaternion {a b c d}`, `rotate/x|y|z`, `resetRotation`, `cueSize` (+`/width`,`/height`), `stage`, `stageName`, `stageNumber`, `stageID`, `stage/name|size|size/width|size/height|uniqueID`, `surfaceID`, `surfaceList`, `surfaceName`, `surfaceSize` (legacy), `videoEffects` (+`/live`). **Text**: `text` (+live), `fixedWidth`, `text/format` (JSON) e `text/format/{alignment|fontFamily|fontStyle|fontName|fontSize|lineSpacing|color|backgroundColor|strikethroughColor|underlineColor|strikethroughStyle|underlineStyle}` (+live; indici per range `fontFamily/{index}/{length}`, `fontFamily/word/{n}`), `text/outputSize` (+`/width`,`/height`).
**Fade**: `doOpacity`, `doRate`, `doRotation`, `doScale`, `doTranslation` (`{b}`), `geoMode {0 assoluto|1 relativo}`, `levelsMode {0 assoluto|1 relativo}` (`mode` deprecato = levelsMode), `rotationType {0 3D|1 X|2 Y|3 Z}`, `rotation {deg}`, `setGeometryFromTarget`, `setLevelsFromTarget`, `stopTargetWhenDone {b}`, `willFade {riga} {colonna} {b}` (attiva cella matrice).
**Light**: `lightCommandText {s}`, `setLight {s} {valore}`, `replaceLightCommand {old} {new}`, `removeLightCommandsMatching {s}`, `prune`/`pruneCommands`, `safeSort`/`safeSortCommands`, `alwaysCollate {b}`, `collateAndStart`, `subcontroller {b}`.
**Network**: `networkPatchName|Number|ID`, `customString {s}`, `fadeType {0 no fade/resend|1 1D|2 2D}`, `fadeNumberType {0 int|1 float}`, `fadeFrom`, `fadeTo`, `fadeEntries`, `fps {1..120}`, `pathWidth`, `pathHeight`, `parameterValue/{indice|chiave} {v}`, `parameterValues`, `parameterFadeEnabled/{indice|chiave} {b}`, `parameterFadesEnabled`.
**MIDI**: `messageType {1 voice|2 MSC|3 SysEx}`, `midiPatchName|Number|ID`, `status {0 note off|1 note on|2 key pressure|…}`, `channel`, `byte1`, `byte2`, `byteCombo`, `endValue` (fade), MSC: `commandFormat {0..127}`, `command {0..127}`, `deviceID`, `qNumber`, `qList`, `qPath`, `macro`, `controlNumber` (0..16383), `controlValue` (0..16383), `hours|minutes|seconds|frames|subframes`, `timecodeFormat`, `timecodeString`; SysEx: `rawString`. (Indici MSC e formati: SPEC-protocolli-qlab.md.)
**Devamp**: `devampType {1 slice in loop|2 cue in loop}`, `startNextCueWhenSliceEnds {b}`, `stopTargetWhenSliceEnds {b}`. **Script**: `scriptSource`, `compileSource`.
Indici patch: 0 = unpatched, 1 = primo patch della lista; nome `none`/"" = unpatched.

## 9. OSC Query nei Network cue
Sintassi `#/indirizzo [args]#` dentro un messaggio di un Network cue: sostituito col valore **al momento dell'invio** (es. `/device/standby #/cue/selected/number#`). Se il cue ha **durata**, la query è rivalutata continuamente (messaggio inviato a fps) finché il cue gira. Funziona anche verso `localhost` (QLab su se stesso): es. `/dashboard/setLight myLight #/cue/10/liveAverageLevel/1 0 100#` (livello mic → luminosità). Proprietà interrogabili = colonna "query" del dizionario.

## 10. Architettura consigliata (ShowSuite)
- `osc/` modulo: parser/encoder OSC 1.0/1.1 (python-osc o proprio), SLIP TCP, server asyncio UDP+TCP+plain-text, router a pattern (fnmatch OSC), tabella `ROUTES` dichiarativa: `{path_template, access(view/edit/control), getter, setter, increment_ok, query_ok, live}` generata da questa spec; test automatici "tabella→handler".
- Sessioni client: stato (connected, perms, alwaysReply, replyFormat, updates, last_seen) con timeout 61 s UDP.
- Event bus del motore → push `/update/...`.
- Risposte JSON esattamente nel formato §3.
- Nessun accesso di scrittura da client senza E; azioni senza C → `denied`.
