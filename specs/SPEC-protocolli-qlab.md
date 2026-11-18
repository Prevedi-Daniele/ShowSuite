# SPEC-protocolli-qlab.md  (ShowSuite / sezione Cue, riferimento: QLab 5)
Tutti i modi con cui un cue/workspace **riceve** trigger o **invia** messaggi, fuori dall'API OSC dettagliata (→ SPEC-osc-qlab.md). Trigger per-cue (hotkey, MIDI, wall clock, timecode) → SPEC-cue-modello.md §8.

## 1. Mappa dei protocolli
| Protocollo | Ingresso (controllo/trigger) | Uscita (cue) |
|---|---|---|
| Tastiera | hotkey per cue + comandi workspace | — |
| OSC (UDP/TCP/SLIP) | API completa, mapping "OSC" dei comandi | Network cue (OSC, query, fade 1D/2D) |
| Testo semplice UDP | porta 53535 → interpretato come OSC | Network cue Plain Text (TCP/UDP) |
| Hex TCP/UDP | — | Network cue Hex Code |
| MIDI voice | comandi workspace, trigger cue, Light Dashboard | MIDI cue (voice), MIDI File cue |
| MSC | comandi workspace (GO, STOP…) | MIDI cue (MSC) |
| SysEx | — | MIDI cue (SysEx) |
| MTC | sync liste/cart + trigger cue | Timecode cue (MTC) |
| LTC (audio) | sync liste/cart + trigger cue | Timecode cue (LTC) |
| Wall clock | trigger cue a ora reale | — |
| Collaboration | multi-computer su un workspace (§7) | — |
| Remote (app) | app iOS "QLab Remote" (§8) | — |
| Script | AppleScript → Python (§9) | — |

## 2. Workspace Settings → Controls
**Tab Keyboard**: tasti per comandi core/editing, per workspace. Si può rimuovere/cambiare (con ⌘⇧⌃⌥ → ShowSuite Ctrl/Shift/Alt/Meta). Nessun blocco su conflitti con altri shortcut. **Esc singolo = Panic, doppio = Hard stop: fissi, non riassegnabili.** Frecce su/giù non assegnabili; sinistra/destra sì. Default: SPEC-cue-modello §14b.
**Tab Workspace MIDI**: canale MIDI del workspace (1–16 o `any`; i trigger dei cue e il Light Dashboard possono usare il canale del workspace o uno proprio). Checkbox "Use MIDI Show Control" + Device ID (0–126). Checkbox "Use 'Musical' MIDI Controls" → tabella comando→messaggio.
**Tab OSC**: per ogni comando workspace si assegna un messaggio OSC testuale (digitato/incollato o Capture) — per dispositivi che non possono mandare OSC personalizzato. Richiede OSC access attivo.
**Capture**: pulsante per ascoltare il prossimo messaggio compatibile (MIDI o OSC) e assegnarlo; secondo click annulla ("Waiting…").

## 3. MIDI voice come controllo
- Tipi accettati per i controlli workspace: **Note On, Note Off, Program Change, Control Change**. byte1 = nota/programma/controller; byte2 = velocity/valore (ignorato per Program Change). Campi byte accettano numero 0–127, **`>N`**, **`<N`**, **`any`** (attenzione: dispositivi che usano Note On vel 0 come Note Off → doppio trigger con `any`; usare `>0`).
- Ingresso: tutti i device MIDI connessi sul canale scelto. Trigger per-cue: vedi SPEC-cue-modello §8.
- **MIDI feedback** (solo Light Dashboard): QLab invia al device indicato messaggi uguali a quelli assegnati (fader motorizzati).
- **Light Dashboard MIDI** (Workspace Settings → Light): canale = segue workspace | 1–16 | any; tabella con una riga per strumento/gruppo (+ righe speciali **subcontrollers** e **selected** = strumenti selezionati nel Dashboard), espandibile ai parametri; binding message type/byte; Capture; Command Filter (ricerca per nome).

## 4. MIDI Show Control (MSC)
**Ricezione** (con "Use MIDI Show Control", Device ID 0–126, risponde anche a 127 = all-call). Categorie accettate: **Lighting (General), Sound (General), Video (General)**. Canale MIDI e Device ID sono indipendenti.
| MSC | Funzione |
|---|---|
| GO | GO (stesso del pulsante) |
| GO {cue} | avvia quel cue (playhead non si muove) |
| STOP | **pausa** tutto |
| STOP {cue} | pausa quel cue |
| RESUME / RESUME {cue} | riprende tutto / quel cue |
| LOAD / LOAD {cue} | load del cue in standby / di quel cue |
| ALL_OFF | Panic |
| STANDBY+ / STANDBY- | playhead giù / su di un cue |
| SEQUENCE+ / SEQUENCE- | playhead alla sequenza successiva/precedente |
| RESET | senza cue: stop di tutto e playhead in cima alla lista; con cue: ferma e azzera temporanei di quel cue |
I numeri cue MSC sono **stringhe** (1, 01, 1.0, 1.00 diversi): devono combaciare esattamente. Attenzione a console che inviano MSC GO per ogni cue (es. ETC Eos per lista): numeri cue di QLab che non devono partire non devono coincidere con quelli della console.
**Invio** (MIDI cue, tipo MSC): campi command_format, command, device_id (0–127), q_number, q_list, q_path, e per SET: macro, control_number/value (0–16383), timecode h/m/s/f/subframes+formato (vedi §6 tabella).
**Indici comando** (usati da OSC `command` e script): GO 1, STOP 2, RESUME 3, TIMED_GO 4, LOAD 5, SET 6, FIRE 7, ALL_OFF 8, RESTORE 9, RESET 10, GO_OFF 11, GO/JAM_CLOCK 16, STANDBY_+ 17, STANDBY_- 18, SEQUENCE_+ 19, SEQUENCE_- 20, START_CLOCK 21, STOP_CLOCK 22, ZERO_CLOCK 23, SET_CLOCK 24, MTC_CHASE_ON 25, MTC_CHASE_OFF 26, OPEN_CUE_LIST 27, CLOSE_CUE_LIST 28, OPEN_CUE_PATH 29, CLOSE_CUE_PATH 30.
**Indici command format**: All Types 127; Lighting General 1, Moving Lights 2, Color Changers 3, Strobes 4, Lasers 5, Chasers 6; Sound General 16, Music 17, CD Players 18, EPROM Playback 19, Audio Tape Machines 20, Intercoms 21, Amplifiers 22, Audio Effects Devices 23, Equalizers 24; Machinery General 32, Rigging 33, Flys 34, Lifts 35, Turntables 36, Trusses 37, Robots 38, Animation 39, Floats 40, Breakaways 41, Barges 42; Video General 48, Video Tape Machines 49, Video Cassette Machines 50, Video Disc Players 51 (tabella del manuale troncata qui: completare con spec MSC 1.0 — Projection 64.., Process Control 80.., Pyro 96.. — in implementazione).
**SysEx**: payload hex senza F0/F7 (aggiunti in invio).

## 5. MIDI patches (uscite)
- N patch per workspace; nuovo workspace crea un patch per ogni uscita MIDI presente. Azioni: nuovo (Cmd+N nel tab), elimina, riordina (drag; numeri 1..N rinumerati), duplica (Alt+drag), copia in altro workspace, esporta, selezione multipla (Shift/Cmd).
- Campi: numero, nome (opzionale), destinazione (tendina di tutte le destinazioni MIDI; su Linux ALSA/JACK/PipeWire, su Windows WinMM/WinRT; virtuali: loopMIDI/rtpMIDI/ipMIDI come loopback; IAC → su Windows loopMIDI).
- Usati da MIDI cue, MIDI File cue, Timecode MTC.
- Avviso interfacce MIDI: i carichi alti (MSC/MTC/MIDI File) possono far perdere messaggi su interfacce economiche → ShowSuite: coda di uscita con rate-limit configurabile, warning in Workspace Status.

## 6. Timecode in ingresso (sync liste/cart)
Abilitazione per **cue list o cart** (tab Timecode dell'ispettore): "Sync cues in this list from incoming timecode"; sync source: **MTC** (device MIDI) o **LTC** (audio patch input + canale ingresso); SMPTE format uguale al mittente (indici: 0 24, 1 25, 2 30df, 3 30, 4 29.97, 5 29.97df, 6 60, 7 59.94, 8 60df, 9 59.94df, 10 50, 11 23.98). 
- **On Start** (comportamento all'arrivo del timecode): 0 non avviare cue il cui trigger precede il primo frame; 1 avviare quelli nell'ultimo minuto; 2 nell'ultima ora; 3 entro lookback X s (campo testo); 4 tutti quelli che precedono.
- **On Stop**: 0 nulla; 1 pausa cue partiti da timecode; 2 stop.
- **Freewheel** 0–2 s: finestra in cui i drop-out sono ignorati (utile con MTC).
- QLab 5 **si sincronizza**: se il timecode si ferma, salta avanti o indietro, i cue rispondono (riposizionamento).
- Trigger per-cue: checkbox Timecode, formato `h:m:s:f` oppure **Real Time** `h:m:s:ms`; cattura da timecode in arrivo (`captureTimecode`). Tutti i cue di una lista condividono la sorgente della lista.
- Finestra Timecode (Window): monitor timecode in/out.
- Uscita timecode: SPEC-cue-tipi.md §M (MTC clock interno, LTC clock dispositivo audio; più flussi indipendenti). LTC → implementare encoder biphase-mark in buffer audio; MTC quarter-frame a 4×fps.
- Linee guida: iniziare timeline a 01:00:00:00 con preroll in ora 0; non inviare MTC su rete/interfacce scarse.

## 7. Collaboration (multi-computer)
- Ruoli: **primary** (host del workspace, esegue tutti i cue) e **remote** (client). I cue girano **sempre sul primary**.
- Permessi: **Connect & View** (vedere; solo flag/note modificabili), **Edit** (modifica cue/settings, no run/playhead), **Control** (start/stop/pause/resume/playhead, no edit). Senza view non si connette.
- Licenze: sul primary senza licenza, remote licenziati con qualsiasi permesso, non licenziati solo view; ogni licenza sul primary abilita un remote non licenziato (ShowSuite: **nessuna licenza** → tutti i remote con i permessi assegnati; mantenere solo la struttura permessi).
- Rete: LAN/VPN, **Bonjour/mDNS** per scoperta. Connessione: Launcher/File → Connect to Workspace… (Ctrl+Shift+K).
- Settings → Collaboration: Allow connections (off = disconnette tutti), **Ask before allowing new collaborator** (dialog con permessi), **In Show Mode restrict all to view-only**, tabella con riga default + collaboratori (Collaboration Name, Machine ID, IP) con checkbox e pulsanti Disconnect / Disconnect & forget. Riconnessione senza approvazione dopo la prima.
- UI remote: barra del titolo viola "Remote", GO con bordo viola, footer con icona e permessi (click → IP primary), **colonna collaboration** con pallino colorato per cue selezionato da ogni altro utente; indicatore colorato sulla tab ispettore se due utenti guardano lo stesso cue.
- Edit: **last-edit-wins**. Undo/redo **per utente** per cue list/cart; Light Dashboard e ogni area Settings hanno **un solo** undo condiviso. In collaborazione **creare/eliminare/spostare cue non è annullabile** (messaggio informativo).
- File target dai remote: browser dedicato che mostra solo i file nella cartella del workspace sul primary (sottocartelle con file validi per il tipo); il primary deve essere stato salvato.
- Errori: Access Denied, Action Rejected (manca Control), Change Rejected (manca Edit), Connection Rejected, View Permission Disabled.
- Protocollo ShowSuite: WebSocket TLS (stessa API OSC-JSON incapsulata) + mDNS `_showsuite._tcp`; autenticazione per collaboratore (token) — formato proprio, non compatibile col QLab reale.

## 8. QLab Remote (app) e compatibilità
- App iOS gratuita con due acquisti: *Show Control & Editing* (run cue, playhead, edit parametri limitati, geometria stage) e *Light Tools* (Light Keypad, Instrument Check). Vede workspace via Bonjour o IP manuale; porte 53000/53001 (o custom); passcode con keypad (sempre mostrato per QLab 5; "No passcode" se permesso); comunicazioni cifrate (QLab 5). Rispetta Show/Edit mode, Read-Only mode. Modalità cart per carte; swipe per spostare playhead.
- ShowSuite: **non ricreare l'app iOS**; fornire (a) compatibilità OSC (SPEC-osc-qlab.md) così l'app reale/altri client funzionano, (b) **web remote** (HTML/WebSocket) con le stesse funzioni (cue list, GO, playhead, carte, Light keypad) servito dal programma; QR/URL sulla macchina.

## 9. Scripting e automazione
- AppleScript (dizionario QLab) → **Python** nel Script cue e API esterna: stessi comandi (go, preview, audition go/preview, capture timecode, clear dashboard, collapse/expand, make/delete cue, set/get property, new workspace, open, save…). Mappatura 1:1 delle proprietà con quelle OSC (SPEC-osc-qlab.md §8). Shortcuts/Apple Watch/Touch ID: sostituiti (vedi stack: password, web remote).
- Esempi OSC del manuale (da usare come test): pacchetto di casi in `tests/osc_examples/`.

## 10. Network Outputs (patch di rete) — dettaglio
Tabella a 8 colonne: **numero** (auto, 1..N), **nome** (opz.), **tipo** (OSC generico | Plain Text | Hex? | device description), **rete** (TCP|UDP), **interfaccia** (automatic o specifica NIC), **destinazione** (IP o nome mDNS `.local`; `localhost` = ritorna dentro QLab a latenza minima, non esce; `127.0.0.1` = altro software sulla stessa macchina), **passcode** (per inviare a workspace QLab con passcode), cancella. Nuovo workspace: 1 patch preconfigurato "OSC verso se stesso". Azioni tabella come MIDI patch. Warning NDI per collisione porte.
- **Override** (finestra): disattiva ingressi/uscite per categoria (DMX, MIDI in/out, MSC in/out, SysEx in/out, network esterno/locale in/out, timecode in/out) senza modificare i cue; stato riflesso nei cue (`isOverridden`).

## 11. Audition per tipo di uscita (Workspace Settings → Audition)
Per ogni tipo di output: *Leave unchanged* | *No output* | *Alternate patch* | (video) *Audition window* (monitor invece dello stage) | (light) *Audition tab* (Dashboard, non invia Art-Net/DMX). "Edit…" apre il patch alternativo. Anteprima = Audition GO/Preview (SPEC-cue-modello §14).

## 12. Estensioni ShowSuite (oltre QLab, opzionali)
- **ipMIDI** (UDP multicast, porta 21928 + n) e **RTP-MIDI** (AppleMIDI) come patch MIDI; **MIDI 2.0** in valutazione.
- Dispositivi DMX/luci per cue Light: SPEC DMX (Lightkey) — Art-Net/sACN/USB.
- **HTTP/WebSocket API** (stessi indirizzi OSC come JSON) per integrazione web.
- **Bitfocus Companion**: documentare configurazione tramite OSC (modulo QLab esistente) per i pulsanti.

## 13. Test di conformità (invarianti)
1. MSC GO senza cue = GO; con cue non muove il playhead. 2. MSC STOP = pausa. 3. `>0` su Note On vel=0 non scatta. 4. `any` su Note On può doppio-scattare (documentare). 5. Esc=panic, Esc Esc=hard stop non riassegnabili. 6. Plain text UDP non produce risposte. 7. UDP client scade a 61 s senza keep-alive. 8. Freewheel ignora drop < N s. 9. On Start mode 1–4 selezionano correttamente i cue precedenti. 10. Collaboration: remoto senza Edit → Change Rejected; senza Control → Action Rejected. 11. Override disabilita uscita senza toccare i cue. 12. `localhost` nel patch di rete non esce dall'applicazione.
