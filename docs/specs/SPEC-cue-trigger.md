# SPEC — Cue QLab 5: trigger e avanzamento

Fonte: documentazione QLab 5 (Figure 53) e conoscenza del prodotto; da ricontrollare sul manuale ufficiale prima di dichiarare la parità.
Legenda: [OK] presente nel repo · [PARZ] parziale · [GAP] mancante · [MAC] specifico macOS.
Stato del codice: stima dai file letti (`CueTypes.js`, `BaseCue.js`, `ShowControlManager.js`); i punti marcati "verificare" richiedono lettura/test.

## 1. Modello di avanzamento
- Playhead nella cue list; GO avvia la cue sotto il playhead e lo sposta alla successiva. [OK]
- Pre-wait, durata, post-wait per cue. [OK, `BaseCue.js`]
- Continue mode: Do not continue / Auto-continue (parte a preWait+postWait) / Auto-follow (parte a preWait+durata+postWait). [OK, `ContinueMode`]
- Group mode: Timeline, Playlist, Start first and go to next, Random. [OK, `GroupMode`]
  - Nota: in QLab 5 i nomi/semantica dei modi vanno verificati sul manuale; qui i nomi interni seguono il codice.

## 2. Trigger per singola cue (tab "Triggers" dell'Inspector)
Ogni cue può avere più trigger che la avviano senza passare dal GO:

| Trigger | Descrizione | Stato |
|---|---|---|
| Hotkey | Tasto/combinazione che avvia la cue (anche con cue list non in primo piano, opzione "Hotkey triggers" della list) | [GAP] verificare |
| MIDI | Note on / CC / Program Change / MSC → avvia la cue | [PARZ] esiste mappatura MIDI→azioni show in `ShowControlManager`, non per-cue |
| Timecode | Cue parte a un timecode (MTC/LTC) | [PARZ] `TimecodeChaser`/`TimecodeTriggerAction` esistono; manca UI per-cue (verificare `MidiInspectorTab`) |
| Wall clock | Ora del giorno, con giorni/data | [GAP] |
| OSC | Messaggio OSC in ingresso → avvia | [PARZ] `OSCDictionary` espone comandi; manca trigger per-cue custom |

Opzione "Allow trigger while cue running" / "Trigger only when idle": da definire. [GAP]

## 3. Controllo remoto (OSC)
- Dizionario OSC: go, start, stop, pause, load, playhead, panic, reset, cue/selected/..., per-cue properties. [PARZ, `OSCDictionary.js`] — fare un audit dei comandi contro l'OSC dictionary ufficiale di QLab 5 e produrre una tabella comando-per-comando.
- Bridge QLab↔Lightkey in-process. [OK, `ShowSuiteBridge.js`]
- Rete OSC reale (UDP) con porta configurabile e passcode: verificare se `OSCController` copre sia ingresso che uscita.

## 4. Cue di controllo
- Network (OSC/UDP/TCP) [OK], MIDI (incl. MSC) [OK], Timecode [OK], Script [tipo definito; esecuzione da verificare], Wait [definito], Fade [definito], Light [definito; integrazione con Lightkey via bridge].
- Cue "Start/Stop/Pause/Load/Reset/Devamp/Goto/Target/Arm/Disarm/Wait/Memo/Cue List": confrontare `CueType` con l'elenco QLab 5: mancano almeno Start, Stop, Pause, Load, Reset, Devamp, GoTo, Target, Arm, Disarm, Memo, Cue List. [GAP]

## 5. Cue list, cart, workspace
- Cue list multiple, cart (griglia), nesting di liste (cue list cue). [PARZ: `CueCartGrid.jsx` esiste]
- Colori, flag (Armed, Auto-load), numerazione con sotto-numeri. [verificare]
- Workspace Settings: Audio devices/patch, Video stages, Network, MIDI, Timecode, Triggers. [PARZ]

## 6. Priorità proposta
1. Tab "Triggers" per-cue: hotkey, MIDI, timecode, wall clock, OSC (un solo modello dati `cue.triggers[]`, valutato da un `TriggerManager` unico).
2. Cue di controllo mancanti (Start/Stop/Pause/Load/Reset/GoTo/Target/Arm/Disarm/Memo).
3. Audit OSC dictionary + test di conformità.
4. Hotkey e wall clock.

## 7. Criteri di accettazione
- Ogni tipo di trigger ha test automatici (`test/`), con clock simulato per wall clock e timecode.
- Un trigger non può bypassare lo stato Armed.
- Nessun trigger si perde se la finestra non è in primo piano (Electron: gestire via main process / globalShortcut dove serve).
