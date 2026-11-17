# SPEC-cue-modello.md  (ShowSuite / sezione Cue, riferimento: QLab 5)

## 1. Gerarchia
Workspace ⊃ {CueList | CueCart}+ ⊃ Cue ⊃ (solo se Group) Cue figli.
- Lista e Cart sono "Group" speciali: hanno number, name, trigger, ma non pre/post-wait.
- Group può annidarsi senza limite. Il Cart NON può contenere Group.
- Default: 1 lista "Main Cue List". Numero di liste/cart illimitato.
- Cart: griglia R×C, 1..10 × 1..10; ogni cue ha (row,col); non si riduce sotto l'ingombro dei cue.
- unique_id: stringa immutabile per ogni cue/lista/workspace (UUID). Number e name sono modificabili.
- Il workspace ha workspace_id, nome file, "active list" (la lista mostrata).

## 2. Campi comuni di ogni Cue
number (str, opz., UNICO nel workspace; no spazi/#*,/?[]{} per uso OSC; solo cifre per MIDI/MSC)
name (str; se vuoto -> default_name del tipo)
notes (testo ricco), color (none|red|orange|green|blue|purple), color_condition (always|before_action|after_action)
flagged, armed (default true), auto_load (default da workspace), continue_mode (do_not_continue|auto_continue|auto_follow)
pre_wait, duration (se editabile), post_wait, target (file | cue | nessuno)
triggers{hotkey, midi, wall_clock, timecode}, second_trigger_action, second_trigger_on_release
fade_and_stop_others{mode 0..3, time}, duck_others{enabled, level dB, time}

Default names: Audio/Video=nome file; Text=testo; Light=comando (1) o "fade x lights"; Fade="fade "+nome target (o "fade and stop "+nome); Network=comando; MIDI=tipo messaggio; MIDI File=nome file; Timecode=frame iniziale; Start/Stop/Pause/Load/Reset/GoTo/Arm/Disarm="<tipo> "+nome target; Wait="wait "+durata. Se cambia il nome del target e il cue usa il default, il default si aggiorna. Nome cancellato -> torna al default.
display name = list name = nome mostrato; "standby display" = "numero • nome".

## 3. Stato runtime di un cue
loaded, running (action in corso), pre_wait_running, post_wait_running, paused, tailing_out (effetto audio che decade), panicking, crossfading_out (solo playlist), auditioning, broken, warning(non-breaking), overridden (output soppresso da override).
Temporanei (non sporcano il documento; si azzerano con reset cue/workspace/riapertura): target temporaneo (Target cue), durata temporanea, parametri modificati via OSC "live"/"temp", colore condizionale, modifiche di Fade cue.
Elapsed: pre_wait_elapsed, action_elapsed, post_wait_elapsed (+ percentuali).

## 4. Tempi
- Precisione 1 ms; display 0.01 (opz. 0.1).
- Input: `s`, `m:s`, `h:m:s`, decimali ok; normalizza in h:mm:ss.xx.
- Auto-follow: post_wait mostrato = duration (non editabile).
- Wait cue e cue in Playlist: post_wait = duration automatico.
- Cue istantanei (Pause, MIDI singolo…) non hanno duration.
- Input dB: senza segno = negativo. "+" per positivo. Blank = -INF. Range workspace: max (>=-30, default +12), min (-180..-40, default -60).

## 5. Playhead e GO
- Ogni lista ha un proprio playhead = cue "standing by". Cart: nessun playhead.
- Il GO agisce sulla lista attiva: avvia il cue in standby (se armato esegue azione) e sposta il playhead al primo cue dopo il cue/sequenza avviato.
- Nome pulsante: GO | Preview (cart attivo) | Audition (always audition). Bordo verde = ok, rosso = double-GO protection.
- Se playhead su Group: vedi §7.
- `lock_playhead_to_selection` (workspace): selezione e playhead si muovono insieme.
- Nessun cue in standby (fine lista): GO non fa nulla.
- Modi di avvio e effetti sul playhead:
  | Origine | Sequenza | Playhead |
  | GO | sì | avanza oltre la sequenza |
  | hotkey/MIDI/timecode/wall clock/Start cue/OSC start | sì | fermo |
  | Audition GO | sì (su output audition) | avanza |
  | Preview | solo il cue, no pre-wait, no continue | fermo |
  | Audition Preview | idem su output audition | fermo |
- Cue running ignora un nuovo start, salvo second trigger.
- Double-GO: `min_go_time` (>=0). Si applica a click GO, tasto GO, MIDI/MSC/OSC "go" di workspace; NON ai trigger dei singoli cue né ad AppleScript/script. "key up" richiesto opzionale.
- Spostamenti playhead: next/prev cue, next/prev sequence, to cue N, to selected, to first active, none.
- GoTo cue sposta il playhead al suo target.

## 6. Esecuzione di un cue (macchina a stati)
start(cue):
1. se già running e second_trigger -> applica azione (§9); altrimenti ignora.
2. pre_wait (se >0) – clock di sistema.
3. se armed: esegue azione (per tipo); se disarmed: NON esegue, ma conserva pre-wait/durata/post-wait/follow.
4. continue:
   - auto_continue: dopo post_wait (dall'istante di start del cue, parallelo all'azione) avvia il cue successivo.
   - auto_follow: al completamento dell'azione avvia il successivo.
5. fine azione -> running=false (cue con slice a loop infinito o freeze-on-completion non terminano mai da soli).
Cue Group sequenza: catena di cue connessi da continue è una "cue sequence"; Preview la rompe.
Cue broken: non esegue azione, ma pre-wait/durata/post-wait/continue sono rispettati.
Load: prepara il cue (apre file, decodifica); `load(t)`: t>0 secondi dall'inizio, t<0 dalla fine, include pre-wait; `loadAction`: ignora pre-wait; `loadFile`: ignora loop slice. Auto-load: dopo l'avvio di un cue, carica il successivo se ha auto_load. Load di un cue in una sequenza carica tutta la sequenza.
Panic = fade out su `panic_duration` poi hard stop; secondo panic = hard stop immediato. Stop = ferma ma lascia decadere effetti; Hard stop = taglia tutto. Esc = panic; Esc Esc = hard stop (fissi). Pause/Resume, Pause all/Resume all, Reset (stop + azzera temporanei; reset workspace = stop tutto, playhead in cima, carica primo cue di ogni lista).

## 7. Group cue
Modi (valori OSC/AppleScript): 0 list, 1 start_first_and_enter, 2 start_first, 3 timeline, 4 start_random, 5 cart, 6 playlist.
- Timeline: avvia tutti i figli insieme (ognuno col proprio pre-wait); figli senza continue (auto-continue/follow vietati -> broken). Playhead -> cue dopo il Group. UI timeline: drag(pre-wait), nudge ±0.1/0.01 s, trim, slip, scala, pin, zoom.
- Playlist: avvia primo figlio; figli in sequenza automatica (continue = auto-follow forzato, post-wait=duration). Opzioni: auto_shuffle (ordine casuale a ogni load/start, non salvato), loop_until_stopped (richiede >=1 figlio con duration>0, altrimenti broken), crossfade (durata min 0.05 s; curve out/in indipendenti; figlio più corto del crossfade = broken). Second trigger extra: 6 play next, 7 play previous (rispettano loop/crossfade). Comandi: next/previous/shuffle.
- Start First and Enter: avvia il primo figlio; il playhead entra nel Group sul 2° figlio, uscendo dopo l'ultimo.
- Start First: avvia il primo figlio; playhead salta dopo il Group; gli altri partono solo via continue.
- Start Random: avvia un figlio armato e non in play a caso, round-robin (ognuno una volta prima di ripetere); memoria azzerata a ogni apertura workspace.
- Group collapsed/expanded: solo visivo; flag figli -> flag "vuoto" sul Group. Creare Group con >=2 cue selezionati li inserisce dentro.
- Spostare cue su Group con drag: il Group diventa target (non ritarget dei figli).

## 8. Triggers (per cue, indipendenti dal GO)
- hotkey: qualsiasi tasto non riservato (no Esc, no su/giù, no modificatori soli, no tasti assegnati in Workspace Settings); ammesse ←/→ e combinazioni.
- midi: Note On/Off, Program Change, Control Change; byte1/byte2 ammettono `>n`, `<n`, `any`; canale 0=canale workspace, -1=any; capture.
- wall clock: hh:mm:ss (12h/24h), giorni settimana; richiede workspace aperto.
- timecode: LTC/MTC; richiede che la lista/cart contenitore abbia "sync to incoming timecode"; formato `h:m:s:f` o tempo reale; capture da timecode in ingresso.
Lista/cart contenitore (tab Timecode): sync_mode MTC|LTC, device/canale, smpte_format (24,25,30df,30,29.97,29.97df,60,59.94,60df,59.94df,50,23.98), on_start (0 skip precedenti, 1 ultimo minuto, 2 ultima ora, 3 lookback X s, 4 tutti), on_stop (0 niente, 1 pausa, 2 stop), freewheel 0..2 s. Chasing: un cue che dovrebbe già essere in corso parte dal punto giusto; skip avanti/indietro seguito. Un cue la cui durata finisce prima del lookback non parte.
Liste/cart possono avere trigger propri: avviarli = GO sulla lista (cart: avvia tutti i cue? no — equivale a "start" della lista).

## 9. Second trigger e opzioni di avvio
second_trigger_action: 0 niente (default), 1 panic, 2 stop, 3 hard stop, 4 hard stop + restart, 5 devamp (se non devampabile non fa nulla), 6 playlist next, 7 playlist previous.
second_trigger_on_release: solo hotkey/MIDI/cart; il rilascio vale come secondo trigger (comportamento sampler).
fade_and_stop_others: 0 off, 1 peers, 2 list/cart, 3 all; fade e stop di altri cue in `time` s all'avvio.
duck/boost_others: livello dB (neg=duck, pos=boost, -120..+12) su altri cue con audio nella stessa lista/cart, fade in `time`, dopo il pre-wait.

## 10. Arm / Disarm
Cue disarmato: tratteggiato; non produce output; sequenza intatta. Cue Arm/Disarm cambiano lo stato del target. Disarm sui figli: Start Random li salta.

## 11. Flag, colori, selezione
- Flag: marker, compare in Warnings. Group con figlio flaggato mostra flag vuoto.
- Colore: 5 + nessuno; `before_action`: colore finché il cue non è partito; `after_action`: colore dopo la prima esecuzione; si ripristinano con reset/riapertura.
- Highlight related cues: grigio per cue che targettano/sono targettati.
- Selezione multipla: batch editing solo di proprietà in comune; l'impostazione imposta lo stesso valore a tutti (con tasto/inspector/menu contestuale).

## 12. Numerazione
- Unico per workspace, stringa (1 ≠ 1.0 ≠ 1.00). Riordinare non rinumera.
- Auto-number nuovi cue (opz. con incremento): sceglie tra vicini (es. 2,4,6 -> inserimento dopo 6 = 7; tra 2 e 4 = 3; poi 2.5). Non si applica a cue creati via OSC/AppleScript/copia.
- Renumber selected: start, increment, prefix, suffix; salta numeri già esistenti. Delete numbers of selected.
- Cambiare numero non rompe i target.

## 13. Target
- File target (Audio, Video, MIDI File): file valido; copia nel project folder se abilitato. File mancante/cestino/non leggibile -> broken. Ricerca file mancanti in una cartella.
- Cue target (Fade, Start, Stop, Pause, Load, Reset, Devamp, GoTo, Target, Arm, Disarm): per numero, id o drag&drop bidirezionale (se ambiguo: il trascinato diventa target del rilasciato). Creare un cue con target-richiesto: 0 selezionati = senza target; 1 = target quel cue; >1 = chiede (un cue dopo ciascuno / tutti dopo l'ultimo / uno solo).
- Target cue: imposta target TEMPORANEO di un altro cue (non su Fade).
- Cue lista/cart possono essere target (Start = GO su quella lista; Fade = fade di tutto ciò che suona).

## 14. Modi del workspace
- Edit mode / Show mode. Show mode disabilita: inspector, toolbar, toolbox, Load to Time, Find, aggiunta/eliminazione/spostamento cue, copia/incolla, modifica parametri via UI. Non disabilita: Esc, apertura/salvataggio, OSC/AppleScript edit, Workspace Settings. Chiudere/quit chiede conferma. Finestre secondarie (lista/cart) sembrano sempre show ma sono editabili se il workspace è in edit.
- Show Mode (opz. preferenze): blocca ⌘Tab, Mission Control, sleep, App Nap (su ShowSuite: inibire sleep e screensaver).
- Always audition: GO/Preview diventano Audition/Audition Preview solo da UI (non da MIDI/MSC/OSC/script).
- Audition: 7 categorie di output (audio, video, MIDI, MTC, LTC, network, light), ciascuna: invariato | nessun output | patch alternativa | finestra (video) | tab (light).
- Override controls (globali): input/output separati per MIDI, MSC, SysEx, network esterno, network locale, timecode, DMX (solo output). Cue sovrascritto = icona di divieto.
- Undo/redo per workspace; in collaborazione: storia undo propria per cue, condivisa per Settings e Light Dashboard; creare/eliminare/spostare cue non annullabile.

## 14b. Workspace Settings (General)
min_go_time, key-up, panic_duration, start_cue_on_open (⌃⌥ all'apertura lo salta), prompt_cue_on_close, auto_number+increment, auto_load_default, lock_playhead_to_selection, display_size lista/cart (small/medium/large), file management (copia media, autosave su copia, snapshot prima del salvataggio max 1/min), tastiera/MIDI/MSC/OSC controls del workspace (§ separata), cue templates (default per tipo), workspace templates.
Tasti default: GO space, Preview V, Load L, Panic S (doppio = hard stop), Pause P, Pause all [, Resume all ], Panic all Esc, edit number N, name Q, notes O, target T, pre-wait E, duration D, post-wait W, continue C, flag F.
MIDI musical controls: Note On/Off/PC/CC per ogni comando (byte `>`,`<`,`any`, Capture). MSC (device id 0..126, 127=all-call; categorie Lighting/Sound/Video General): GO[n], STOP[n]=pausa, RESUME[n], LOAD[n], ALL_OFF=panic, STANDBY+/-, SEQUENCE+/-, RESET[n].

## 15. Stati di errore (Warnings)
Categorie: broken cue, flagged, non-breaking, breaking, disconnection. Ogni warning ha "Inspect"/"Open Help". Hide/Show hidden. Cause comuni per tipo in SPEC-cue-tipi.

## 16. Persistenza
Formato proposto: `*.showcue` (JSON versionato) + cartella progetto con sottocartelle audio/video/midi/backups. Salvataggio: opzione crea project folder e copia media. Autosave (5..600 s) su copia separata, solo dopo il primo salvataggio manuale. Snapshot con timestamp.

## 17. Invarianti da testare
1. numeri unici; 2. GO avanza il playhead di una sequenza intera; 3. disarmed rispetta timing; 4. auto-follow = start al termine azione; 5. auto-continue = start a t=post_wait; 6. Preview non avvia successivi; 7. second trigger solo se running; 8. Playlist: crossfade >= durata figlio = broken; 9. Timeline: figlio con continue = broken; 10. Start Random round-robin; 11. reset azzera temporanei e non modifica il documento; 12. double-GO ignora GO entro min_go_time ma non i trigger dei cue.
