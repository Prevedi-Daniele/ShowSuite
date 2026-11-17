# SPEC-cue-tipi.md  (ShowSuite / sezione Cue, riferimento: QLab 5)
Complementa SPEC-cue-modello.md (campi comuni, timing, stati). Qui: campi specifici per tipo, regole, stati "broken".
Convenzioni: livelli in dB (range workspace default +12..-60, -60 = -INF "silenzio"); numero senza segno = negativo; campo vuoto matrice = -INF.

## A. AUDIO
**Target**: file audio (WAV, AIFF, CAF, AAC, M4A, MP4, MP3 [timing impreciso], audio di qualsiasi file video). Primi 24 canali, 8–192 kHz, 8–32 bit; conversione SR/bit-depth al volo verso il device (ShowSuite: resample libsamplerate/soxr; decode con libsndfile+ffmpeg/PyAV).
**Campi**: file_target, audio_output_patch (o `unpatched` = non suona), start_time (def 0), end_time (def fine file), play_count (def 1, intero), infinite_loop, slices[], rate (0.03..33, def 1), preserve_pitch (bool), integrated_fade{enabled, curve: custom|linear, lock_to_start_end, points[(t,dB)]}, levels, trim.
**I/O tab**: mostra formato file (tipo, codec, canali, SR) e formato patch.
**Slices**: marker ogni ≥0.05 s; ogni slice ha play_count (def 1; 0 = salta senza gap; lettera/“inf” = loop infinito); almeno una slice > 0 altrimenti broken. Marker WAV/AIFF importati come slice (scartati se <0.05 s). Shortcut: M aggiunge slice; Shift+I/O imposta start/end dal playback; Delete rimuove. "Delete All" non tocca marker nel file.
**Rate/pitch**: rate 1=100%; senza preserve_pitch il pitch segue (nastro); con preserve_pitch usa time-stretch (più CPU).
**Integrated fade**: inviluppo di volume sulla durata; modifiche mentre suona valgono al prossimo avvio. Lock-to-start/end = inviluppo stirato su [start,end] invece che sul file naturale.
**Levels**: matrice mixer righe=canali file, colonne=cue outputs (max 64 con licenza audio; gratis solo 2). Main level top-left. Crosspoint max 0 dB trascinando, oltre digitando fino al max workspace. Gang: campi con stesso testo si muovono insieme (clamp proporzionale solo se uno raggiunge limite). Pulsanti: Set Default Levels (da template), Set all silent, Visible channels (solo UI). Live: modifiche immediate durante playback.
**Trim**: livelli post-fader (main + cue outputs) NON automatizzabili (no Fade/OSC/MIDI).
**Audio FX**: catena ordinata di effetti per cue (bypass per effetto, drag per ordine). ShowSuite: effetti built-in (EQ, comp, riverbero, delay, pitch…) + VST3/LV2 al posto di AudioUnit; effetto mancante = broken. Richiede tail time.
**Anteprima**: V = preview senza avanzare playhead né auto-continue/follow; Reset ferma e azzera temporanei.
**Duration**: (end−start)/rate × play_count (slice incluse); infinito se loop infinito.
**Broken**: nessun file; file mancante; file nel cestino; no permessi lettura; nessun patch; patch con problemi; effetto mancante; slice tutte 0; licenza (ShowSuite: nessuna licenza, flag lasciato per compatibilità = off).

## B. MIC
Audio live in ingresso. Campi: audio_input_patch (o unpatched), n_channels (1..min(canali device,24)), first_input, audio_output_patch, levels, trim, audio_fx (come Audio).
Input e output su device diversi ammessi: algoritmo di sincronizzazione drift ≤ buffer_in + buffer_out + margine (resampling adattivo).
Duration: indefinita (finché non stoppato). Fade, Stop e Level valgono come Audio.
**Broken**: no accesso microfono (permesso OS); input patch con canali insufficienti; effetto mancante; no input patch; input patch con problemi; no output patch; output patch con problemi.

## C. AUDIO OUTPUT PATCH (Workspace Settings → Audio)
Patch = {name, device, cue_outputs[], routing matrix, device_outputs[]}.
- **Cue Outputs**: nome per riga (testo breve, 2 righe), catena effetti per output, raggruppamento a coppie ("1 channel"/"2 channels") per effetti stereo.
- **Patch Routing**: matrice righe=cue outputs, colonne=device outputs, crosspoint dB, main level della patch; più cue output possono confluire su uno stesso device output (aux send con effetti su uno).
- **Device Outputs**: come Cue Outputs ma senza nome; effetti per device output.
- Menu "Set from other patch or defaults…".
- Default: cue output n → device output n.
- **Warning**: nessun device; device mancante; device senza uscite.
- Fade cue NON può modificare effetti su output (solo su cue).
- Input patches (Audio Inputs) analoghi per Mic/Camera.

## D. FADE
Cambia parametri del target nel tempo. Target obbligatorio: Audio, Mic, Video, Camera, Text (parametri video/geometria/effetti), Light (vedi sezione Light), e anche altri tipi con parametri supportati. Ispettore mostra solo le tab del tipo del target.
**Campi**: target, duration, curve{type: s_curve (def, da template)|custom|parametric(intensity)|linear; rising e falling separate per custom/linear}, audio_domain: slider|decibel|linear, stop_target_when_done, mode: absolute (def)|relative, levels attivi (celle gialle=attive, grigie=ignorate), fx_states, fade_rate_to (rate target 0.03..33), live_fade_preview (def on).
**Curva**: asse x tempo, y % del cambio totale; rising per valori che salgono, falling per quelli che scendono.
- Equal power = parametric + dominio linear; equal gain = linear curve + dominio linear.
**Relative**: somma/sottrae delta al valore corrente; clamp a max level workspace (def +12). Assoluti sostituiscono i relativi precedenti (QLab 5: "più assoluto").
**Set Levels from Target** (Shift+Cmd+T) copia i livelli del target; **Set All Silent Levels** azzera attivazioni.
**Audio FX**: per ogni effetto del target, checkbox (def off) → fade dell'intero stato effetto da A a B (non per parametro); "Set Audio FX from Target".
**Panning**: più Fade sullo stesso target con controlli attivi diversi possono girare insieme senza interferire (ognuno gestisce solo i propri parametri).
**Revert Fade Action** (Shift+Cmd+R, menu Tools): dopo l'esecuzione ripristina solo i parametri toccati da quel fade e non modificati poi da altri.
**Broken**: target mancante; nessun parametro attivo; effetto audio mancante; licenza (rate/FX audio; geometria/effetti video).

## E. VIDEO
**Target**: file video o immagine. Codec previsti: MPEG-1/2/4, H.263, H.264, H.265, ProRes (Proxy/LT/422/HQ/4444/4444XQ), Photo-JPEG, DV/DVCPRO, Hap (Standard/Alpha/Q). Contenitori consigliati MOV/MP4. Immagini: PNG/JPG consigliati (no PSD/PDF). ShowSuite: decode via libmpv/ffmpeg (ProRes/Hap supportati da ffmpeg).
**Campi**: file_target, stage (obbligatorio; `unpatched` = non suona), audio_output_patch (se il file ha audio), clock: `video` (def, segue display) | `audio` (sync perfetta con altri cue sulla stessa patch, possibili frame ripetuti/saltati), audio_track (se più tracce), mode: `fill_stage` | `custom`, preserve_aspect_ratio (fill), opacity 0–100%, smooth (antialias vs nearest), layer (1001 livelli: top, 999..1, bottom; stessa layer → ordine di avvio, ultimo sopra), blend_mode, video_fx[] (ordinati, live), time&loops (come Audio: start/end/play_count/slices/rate/preserve pitch/integrated fade), levels/trim/audio_fx (solo se il file ha audio).
**Geometry custom**: dimensioni naturali; crop (top,bottom,left,right in px); translation (px dal centro; +dx destra, +dy su); scale (x,y; lock aspect; 1.0 naturale); rotation 3D via **quaternione** (UI mostra gradi relativi all'inizio dell'aggiustamento, il fade interpola con slerp); anchor (def 0,0 = centro) per rotate/translate/scale; reset per parametro.
**Clock con più output**: se uno stage va su più output usa clock dell'output con refresh più alto; a parità priorità a fisici su virtuali.
**Video FX**: catena effetti live (lista in "Parameter Reference" del manuale: da riprodurre con shader GLSL/Qt RHI); "Set Default Parameters" ripristina l'effetto selezionato. Blend modes = operazione per pixel fg(layer alta) vs bg su canali 0..1 (lista in manuale "Blend Mode").
**Broken**: no file; file mancante/cestino/no permessi; no stage; stage incompleto; no audio patch (file con audio); problema patch; effetto audio mancante; slice tutte 0; licenza (gratis = un solo device di output; geometria custom/blend/FX/timecode a licenza — ShowSuite: nessuna licenza).

## F. CAMERA
Video live + Mic embedded. Sorgenti video: webcam USB (UVC), IIDC/DV, Blackmagic DeckLink/UltraStudio/Intensity (plugin opzionale), Syphon (→ Spout su Windows; su Linux v4l2loopback/PipeWire), NDI (opzionale).
**I/O**: video_input_patch (o unpatched), audio_input_patch (o unpatched; con NDI l'audio è sempre quello NDI), n_channels (1..24) + first_input, stage, audio_output_patch. Input e output audio su device diversi consentiti (vedi Mic).
Tab Geometry, Video FX, Levels/Trim/Audio FX (solo se usa audio) come Video/Audio.
**Broken**: no accesso camera; no video input patch; patch incompleto; no stage; stage incompleto; no accesso mic; canali audio insufficienti; problema audio input patch; no audio output patch; problema output patch; effetto audio mancante; licenza.

## G. TEXT
Testo stilizzato renderizzato come **PNG** all'avvio, poi comportamento da Video cue. 
**Campi**: testo ricco (stili multipli nello stesso cue), font/dimensione/stile, colore testo (def bianco), colore sfondo del testo (def trasparente → sul nero se solo), allineamento (sx/centro/giustificato/dx, unico per cue), width (px; def auto-fit), line_spacing, stage, geometry (come Video), video_fx, preview scale (solo UI).
Altezza automatica; per alzarla aggiungere a-capo. Righello mostra larghezza reale in px.
**Broken**: font mancante (aprire senza salvare e installare; se salvi, adotta font default); no stage; stage incompleto; licenza.

## H. VIDEO OUTPUT (stage)
Glossario: **stage** = raster virtuale (fino a 16384×16384, def 1920×1080) a cui vanno Video/Camera/Text; **device** = display fisico o NDI/Syphon output; **region** = porzione di stage mostrata su un device; **route** = intermediario region→device (permette di cambiare hardware senza toccare cue).
Nuovo workspace: crea uno stage per ogni display. Tabella stage: nome, risoluzione, devices, Edit, Monitor, Delete (undoable). Menu New Stage: Empty (1920×1080, nessuna region/route), Stage with output, Stage with partial output, Multi-Output (n proiettori/risoluzione/disposizione, con blending), con nuovo NDI output, con nuovo Syphon(Spout) output.
Attributi stage: name, layer (impilamento tra stage sullo stesso device, prevale sulla layer dei cue), **keep rendering between cues** (nero fisso tra i cue fino a quit/panic).
Senza licenza: unico device "Video output for all cues".
Editor stage: tab Layout (regions) e Warping (mesh/keystone/edge blend) — dettagli in SPEC-audio-video-light-qlab.md.

## I. LIGHT (cue)
Nessun target. Modello **tracking**: un Light cue assegna livelli solo agli strumenti elencati; gli altri mantengono il livello corrente (non 0). L'ordine di esecuzione conta. Ogni livello live ha un **cue d'origine** (l'ultimo Light cue che l'ha impostato).
**Campi**: commands[] (testo, interpretati dall'alto in basso; linguaggio in SPEC-audio-video-light-qlab.md), duration, curve{custom (def)|linear|s_curve|parametric(intensity); rising/falling separate}, collate_effects_of_previous_cues (bool: simula l'esecuzione di tutti i Light cue precedenti della stessa lista → stato identico indipendentemente dall'ordine, comportamento da console), use_as_subcontroller (bool, compare nel Dashboard).
**Levels tab**: riga di comando; menu Add Command (strumenti/gruppi del patch, già usati in grigio); Safe Sort Commands (ordina alfabeticamente senza cambiare il risultato); viste Slider / Tile / Text (vista = solo UI; reorder solo in slider e text; in tile no); parametri virtuali (colore additivo/sottrattivo, HSI, pan/tilt) senza slider ma con picker nel pannello laterale. Modifiche nel cue = "blind": si vedono solo eseguendo il cue. Bottoni Light Patch… e Dashboard….
**Light Dashboard** (Shift+Cmd+D → ShowSuite Ctrl+Shift+D): 
- Tab **Live**: livelli correnti di tutti gli strumenti, modificabili in tempo reale e inviati subito all'hardware; riflette i Light cue eseguiti. Tab **Audition**: livelli dei Light cue in anteprima.
- Command line con **Over Time** (sneak; si azzera dopo ogni uso). Filtro **All/Used** (Used = registrati nei cue + modificati a mano). Viste Slider/Tile. Decimali per parametri a percentuale (trascinando campo; Shift = più fine; 16-bit mostra più decimali; slider/tile arrotondano). Selezione multipla con Shift-click. Triangolo di disclosure per strumenti multi-parametro (default = intensità). Controlli modificati diventano gialli (slider con triangolo direzionale).
- Pannello **virtuale**: additive picker (≥RGB, + ambra/bianco/lime/indaco…; slider per componente; slider % scala tutti), subtractive (CMY, capovolto), HSI (circolare; intensità = parametro intensità reale), Pan/Tilt (griglia 10%). Shift = precisione.
- **Latest Light cue**: ultimo Light cue eseguito.
- **Revert Changes** (Cmd+R): ripristina i valori modificati all'ultimo stato in `panic duration`; undo/redo supportati. **Clear All**: tutti i parametri a home value (in genere blackout; = "Go To Cue Out").
- **Record All…**: Latest Cue | Selected Cue(s) | New Cue → registra TUTTI i parametri (non toccati = home) ⇒ cue *blocking*. **Update…** (attivo se ci sono valori gialli): Latest (Cmd+U) | Selected (Shift+Cmd+U) | Originating (Alt+Cmd+U): sovrascrive o aggiunge solo i livelli modificati. **New Cue with All** (Shift+Cmd+N) = Record All→New. **New Cue with Changes** = solo i livelli modificati ⇒ cue *tracking*. Nuovi cue inseriti dopo la selezione (o in fondo).
- **Update Originating**: ogni livello modificato va nel cue che l'ha originato (≈ "record track").
**Broken**: comando non valido (solo visibile in text view); nessuno strumento patchato; definizione luce rotta; device USB DMX scollegato.

## J. NETWORK
Invia messaggi TCP o UDP. Tipi: **OSC**, **Plain Text** (solo ASCII), **Hex Code** (solo 0-9A-F). Richiede licenza (ShowSuite: no).
**Campi**: network_patch (o unpatched), fade: `no_fade` (def senza durata) | `resend` (def con durata; fps 1..120) | `1d` | `2d`, duration, messaggio, From/To (1D), curva, Width/Height + path + immagine di sfondo (2D), live_preview.
**Sintassi OSC**: `address arg arg…`; spazio come separatore; stringhe con spazi tra virgolette; solo cifre = int; con separatore decimale = float; OSC 1.1: `\T` true, `\F` false, `\I` impulse, `\N` null. Virgola decimale del locale → sempre punto in uscita.
**Resend**: ripete lo stesso messaggio a fps scelto per la durata. **1D**: sostituisce il token `#v#` (indirizzo o argomento) con valore interpolato From→To via curva, float (6 decimali) o int. **2D**: token `#x#`,`#y#` da percorso disegnato in rettangolo W×H (centro = 0,0; +x destra, +y su), solo int.
Plain text/hex: nessuna durata/fade.
**Device descriptions** (patch con template di dispositivo → UI a menu/campi): QLab 5 (Workspace GO ecc.), Go Button 3, atemOSC, ADM, Bitfocus Companion, Behringer X32/Midas M32, Blackmagic Videohub, ChamSys MagicQ, Christie RS232C, Spikemark, d&b DS100, disguise, ETC ColorSource, ETC Eos, Flux Spat, High End Hog 4, L-ISA, MOTU AVB, Meyer GALAXY, Mixeffect, panLab 2, Luminair 4, Borealis Vor, Yamaha Rivage, ZoomOSC. ShowSuite: formato dati (JSON/YAML) per descrizioni; ELENCO iniziale ridotto (QLab, Eos, X32, Companion, Lightkey/ShowSuite-Light, generico) + estendibile; non copiare tabelle proprietarie senza verifica.
**Template cue**: ogni patch può avere un set di default; cambiando patch si applicano i default di quel patch (Workspace Settings → Templates → Cue Templates → Network).
**Broken/warning**: no patch; patch incompleto; messaggio mancante; valori mancanti (device description); hex non validi; (non bloccante) immagine di sfondo 2D mancante; licenza.

## K. MIDI (cue)
Nessun target, durata 0 salvo fade. Campi: midi_patch (o unpatched), message_type: `voice` | `msc` | `sysex`.
**Voice**: Note On, Note Off, Program Change, Control Change, Key Pressure, Channel Pressure, Pitch Bend; canale 1–16 + parametri. **Fade** (solo CC, Key Pressure, Channel Pressure, Pitch Bend): value (start) → fade_to_value su durata con curva (non conosce il valore corrente).
**MSC**: command_format (categoria del ricevente; QLab risponde a Sound/Video/Lighting General), command, device_id (127 = all-call), q_number, q_list, q_path (di solito vuoto; Eos: q_list vuoto se cue nella lista attiva).
**SysEx**: hex senza F0/F7 (aggiunti automaticamente).
**Broken**: no patch; patch incompleto; lunghezza SysEx non valida; caratteri non validi; licenza.

## L. MIDI FILE
Target: file MIDI Type 0 o 1 (no Type 2). Campi: midi_patch, playback_rate (moltiplicatore tempi; 0.5=metà). Qualsiasi numero di tracce, canali 1–16, tutti su UN'unica porta (anche virtuale/loopback → permette di auto-triggerare cue). Timing da clock interno del computer (non agganciato ad audio/video). Tempo/meter map del file rispettati.
**Broken**: no file; mancante; non valido; cestino; no patch; patch incompleto; licenza.

## M. TIMECODE (cue, generatore)
Genera **MTC** (MIDI patch, nessun canale) o **LTC** (audio patch + cue output channel; def 0 = non valido finché non scelto). Più flussi indipendenti simultanei. Framerate (film: 24, 25, 30 drop, 30 non-drop; video: 23.976, 24.975[sic], 29.97 drop, 29.97 non-drop; stessa codifica, −0.1%); start_time (prima frame inviata; best practice: 01:00:00:00 come inizio timeline, ora 0 = preroll); duration opzionale (si ferma da solo; altrimenti finché fermato). LTC segue clock del device audio (no drift); MTC segue clock interno. Finestra Timecode mostra solo il cue partito per ultimo (gli altri continuano). Avvisi: MTC su rete scoraggiato; LTC a livello alto → attenzione ai monitor.
**Broken**: no MIDI patch; patch incompleto; no audio patch; problema patch audio; canale non valido; licenza.

## N. SCRIPT
In QLab: AppleScript (campo script, Compile, "Run in separate process" def on; off = esegue dentro QLab con timing più preciso). **ShowSuite**: sostituito da **Python** (sandbox con API `cue`, `workspace`, `osc`, `midi`…; stessa semantica compile/errore/processo separato). AppleScript non supportato (nota in UI). Dizionario AppleScript → mappato 1:1 sull'API Python (vedi SPEC-osc-qlab.md).
**Broken**: errore di script; licenza.

## O. CUE DI CONTROLLO
- **Start**: avvia il target (se in pausa → riprende). Può puntare anche a Group Playlist. NON sposta il playhead.
- **Stop**: ferma il target (qualsiasi cue). **Pause**: mette in pausa (richiede licenza). **Reset**: ferma il target e scarta modifiche temporanee (parametri cambiati da Fade, target cambiato da Target cue, colore "before/after action", parametri cambiati via OSC con "temp" nell'indirizzo).
- **Load**: prepara il target (apre file, decodifica) per latenza minima. Tab *Load Time*: tempo di destinazione (loading-to-time); valore negativo = indietro dalla fine del cue/sequenza; i cue seguenti nella sequenza seguono. Load numeri negativi anche via OSC/script.
- **Devamp** (target: Audio o Video): quando eseguito, osserva il target in riproduzione; alla fine della slice corrente (o alla fine del cue) esegue l'azione. Settings: `slice_or_cue`: *devamp currently looping slice* (esce dal loop e prosegue alla slice successiva) | *devamp looping cue* (ignora slice; a fine cue, se in loop, si ferma); `start_next` (avvia il cue successivo esattamente al momento del devamp: post-wait dinamico); `stop_target` (abilitato solo se start_next: ferma il target invece di devampare → hand-off). Più Devamp per più loop.
- **GoTo**: sposta il playhead al target (il target diventa "standing by"; il prossimo GO lo avvia). Complemento di Start. Rotto solo se senza target.
- **Target**: cambia il target *temporaneo* di un altro cue (tab *Cue Number*: numero del nuovo target; il nuovo target deve avere un numero). Non può avere come target un Fade cue. Non rende il workspace "modificato"; ripristinato a reset cue/workspace e riaprendo.
- **Arm / Disarm**: armano/disarmano il target (qualsiasi cue).
- **Wait**: solo trascorre; post_wait = duration automaticamente. **Memo**: nessun effetto (note, separatore). **Group**: vedi SPEC-cue-modello §7.
- Cue di controllo: solo Basics+Triggers (Load: +Load Time; Target: +Cue Number; Devamp: +Settings).
**Broken**: senza target (Start/Stop/Pause/Load/Reset/GoTo/Target/Arm/Disarm/Devamp); Target senza nuovo numero; Wait/Memo mai broken.

## P. EDITING MULTIPLO E REGOLE GENERALI
- Selezione multipla → ispettore mostra solo tab con proprietà batch-editable (tipi misti: solo Basics e Triggers). Impostare una proprietà batch la imposta uguale su tutti; modifica da cue list riga = solo quel cue.
- Cue in esecuzione ignorano ulteriori start (override nel tab Triggers). Durata default Fade = 5 s (da template). 
- Dopo GO il playhead avanza; il GO successivo avvia il cue seguente (non è un player di musica).
- Nuovo cue: dialog (se applicabile) per scegliere il comportamento alla creazione da file multipli (es. un cue per file / gruppo); ultima scelta ricordata.

## Q. INVARIANTI PER TEST (tipi)
1. Fade assoluto sostituisce relativi precedenti; due Fade con controlli diversi non interferiscono. 2. Revert Fade ripristina solo parametri toccati e non modificati da altri. 3. Trim non modificabile da Fade/OSC. 4. Slice tutte a 0 = broken; slice ≥0.05 s. 5. Devamp esce dal loop a fine slice (non subito). 6. Target cue non marca il workspace modificato. 7. Reset azzera temporanei, non il documento. 8. Light: ordine di esecuzione conta; collate = stesso risultato indipendente dall'ordine. 9. Update Originating scrive nel cue d'origine di ciascun livello. 10. Network 1D invia fps×durata messaggi con #v# sostituito. 11. Wait.post_wait == duration. 12. Load con tempo negativo = fine−|t|.
