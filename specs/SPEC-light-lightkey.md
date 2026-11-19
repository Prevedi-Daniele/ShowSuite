# SPEC-light-lightkey.md — Sezione "Light" di ShowSuite

Fonte: Lightkey User Guide rev. 6.1. Obiettivo: stesse funzioni e stessa logica di Lightkey, su Windows/Linux, con più interfacce DMX supportate. Il motore è separato dalla UI (Python 3.12 + PySide6).

Legenda: [CORE] indispensabile per Fase 1 · [V2] dopo · [MAC] specifico macOS, da sostituire.

---

## 1. Modello dati (progetto)

Un progetto è un file unico contenente:
- Patch fixture e configurazione universi
- Preview (layout 2D)
- Preset, sequenze, gruppi (Preset Palette)
- Template effetti e percorsi di movimento
- Pagine Live (pulsanti, frame, cuelist)
- Configurazioni di controllo esterno
- Copie dei profili fixture usati (il progetto è portabile)

Regole: un solo progetto aperto alla volta; salvataggio automatico; undo/redo su quasi tutto; le versioni vecchie non aprono file nuovi (campo `schema_version`). [CORE]

## 2. Universi e output DMX

- Fino a 16 universi (8192 canali), 512 canali ciascuno, valori 0–255. [CORE]
- Ogni universo: numero, etichetta, direzione (Output/Input), destinazione, refresh rate, priorità (solo sACN 0–200).
- Numeri universo: Art-Net 0–15 (net 0–127, subnet 0–15), sACN 1–63999, ESP Net 0–511, USB solo per ordinamento.
- Limiti originali (da decidere se replicarli): 1 sola interfaccia USB, 1 solo nodo Art-Net (max 4 porte), max 4 universi Art-Net. ShowSuite può rimuoverli.
- Fixture disabilitati o nello Storage: canali a 0, non contano per i limiti.
- DMX Monitor: vista a 512 canali per universo, tooltip con fixture/proprietà; vista output per fixture selezionati. [CORE]

### Backend di output (architettura a plugin)
Interfaccia comune `DmxOutput`: `open()`, `send_frame(universe, bytes512)`, `close()`, più `DmxInput` per DMX-In.

| Backend | Note | Priorità |
|---|---|---|
| Art-Net (v1–4, ArtPoll, broadcast/limited broadcast/loopback, manuale net/subnet) | UDP 6454 | CORE |
| sACN E1.31 (multicast, priorità, DSCP) | UDP 5568 | CORE |
| Enttec DMX USB Pro / Pro Mk2, DMXking ultraDMX, Jese DMX-TRI, Robe Universal | seriale (FTDI), protocollo con start code | CORE |
| Open DMX USB (senza microprocessore, frame generati dal PC) | timing critico, refresh configurabile | CORE |
| Eurolite USB-DMX512-PRO (MK2, Cable), Stage-Profi | protocolli proprietari | V2 |
| ESP Net (Enttec) | UDP | V2 |
| FreeStyler-style / interfacce rare (Velleman K8062, Digital Enlightenment, DMX4ALL, Showtec, ecc.) | driver dedicati | V2 |
| Server OLA esterno | opzionale | V2 |
| Hue Bridge (smart lights) | vedi §12 | V2 |

Note Windows/Linux: su Windows le USB FTDI richiedono driver D2XX o libusb; su Linux permessi udev. Rilevamento con "Find Devices". Il macOS "Local Network permission" non serve.

## 3. Fixture e profili

### Profili
- Contenuto: produttore, modello, modalità (con numero canali), canali con capacità (dimmer, colore RGB/CMY/ruote, gobo, pan/tilt, shutter/strobe, prisma, focus, zoom, iris, frost, fog, speed, lamp, command, proprietà custom slider/lista), beam multipli, range pan/tilt, beam angle.
- Libreria: built-in (sola lettura, duplicabile), importati, creati dall'utente. Preferiti, ricerca per produttore/modello, filtro tipo e numero canali (es. "11, 15").
- Formati di import: nativo, SSL2 (Sunlite), FXT/PFF (DMX FreeStyler). [CORE per FXT/SSL2, poiché serve la compatibilità ampia]
- Futuro: import profili Open Fixture Library (JSON) e GDTF. [V2, consigliato]
- Editor profili integrato (wizard di creazione, modalità, beam, capacità custom). [V2]
- Profili generici (Appendice 2): Bulb, Fog Machine, PAR Spot/Wash/Beam (mono, DRGB, RGB, RGBW, RGBAW), LED Strip/Matrix flessibili (Mono, DRGB, RGB, RGBA, RGBAW, RGBD, RGBW), Switch. [CORE]

### Patch
- Drag del profilo sulla griglia canali; indirizzo 1–512 senza sovrapposizioni.
- Campi: modalità, nome corto (max 4 caratteri, auto-incremento numerico), indirizzo (con valore DIP switch), count (istanze nel Preview con stesse proprietà), numero di fixture consecutivi, numero LED (profili flex), riferimento esterno, commenti.
- Modifica multipla (finestra staccata), cambio indirizzo/universo senza perdere dati, duplicazione (con opzione "adotta dati nei preset"), riassegnazione profilo (singolo/universo/tutti), disabilita, elimina (rimuove i dati da preset/cue).
- Import/Export CSV/TSV (universo+indirizzo, produttore+modello, posizione X/Y, riferimento esterno; update o creazione; mapping profili). Stampa lista patch. [V2]

## 4. Preview (layout 2D)

- Vista 2D di fixture, forme (rettangoli, ovali, linee, tralicci, triangoli), immagini, testo. Griglia, guide di allineamento, distribuzione, ordine, rotazione, flip, zoom. [CORE per fixture, V2 per forme/immagini]
- Icone per tipo (PAR, moving head, scanner, lampadina, array, strobo, blinder, pannello, fog, switch, laser, LED bar/matrix/strip aperta/chiusa). Strip LED con forma editabile.
- Raggi virtuali con colore, direzione, angolo (da zoom/beam angle), opzione nascondi.
- Calibrazione moving head: Home, Rotazione, Limiti, Prospettiva. Fixture statici: direzione e colore del beam.
- Opzioni fixture: beam angle, nascondi beam, dimmer min/max (solo output DMX), ignora Master Dimmer, range e offset pan/tilt, disabilita.
- Gruppi di fixture, Fixture Storage, Highlight Mode (accende il fixture selezionato per identificarlo).
- Selezione: click, drag, per tipo, per nome (digitando il prefisso, es. "MH2"), frecce, Tab alfabetico, selezione singolo beam o gruppi di beam (sintassi "1–2, 9–10").

## 5. Proprietà fixture (Design view + HUD)

Concetto chiave: una proprietà è **definita (overridden)** o non definita. Una proprietà definita sovrascrive preset/sequenze/cue. Punto blu = definita, grigio = definita su alcuni. Clear con punto, Delete o menu. [CORE]

| Proprietà | Controlli | Tasto |
|---|---|---|
| Dimmer | slider; Assoluto/Relativo su multi-selezione; senza canale dimmer agisce sulla luminosità RGB | D |
| Master Dimmer | globale, moltiplicativo, esclusione per fixture | — |
| Color (RGB/CMY) | hue/saturation/brightness, colore di sistema, extra (caldo/freddo, ambra, lime, UV, temperatura Kelvin, green saturation, xfade to color), favoriti | C |
| Color Wheel (fino a 3) | griglia colori, split colors, rainbow (velocità/direzione), random, sound | C |
| Gobo Wheel (fino a 3) | selezione, rotazione/bounce/indexing/shake, ciclo, random, sound | G |
| Position | pan/tilt circolare con convenzioni di segno, Assoluto/Relativo a Home/Relativo a corrente, rotazione infinita, joystick, tastierino numerico | P |
| On/Off | switch pack, plug | — |
| Shutter/Strobe | open/closed, strobe (sync, random, lightning), pulse (varie forme), velocità | S |
| Movement Speed | Tracking, Vector, Blackout durante movimento | — |
| Prism (fino a 2) | tipo, rotazione, bounce, indexing | M |
| Focus, Zoom, Iris | HUD o Design view, Assoluto/Relativo | F, Z, I |
| Frost | on/off, lineare, pulse | R |
| Fog | slider | O |
| Custom | slider, lista opzioni, lista+slider; riordino/nascondi | — |
| Lamp, Command | solo menu, **non salvabili in preset** | — |

Altro: valori di default per fixture (Set/Load/Reset Default; default colore blu), copia/incolla proprietà anche tra fixture diversi (conversione colore CMY↔RGB), vista overrides (Cmd+P), clear singolo/selezione/tutti, undo.
Beam-level: solo Dimmer, Color, Shutter/Strobe, Position.

### Fanning (spread)
Distribuisce i valori su ≥3 pixel (fixture o beam) a partire da ≥2 valori definiti. Applicabile a Dimmer, Color, Position, Focus, Zoom, Iris, Frost, Fog, custom slider. Ordine: L→R, R→L, alto→basso, basso→alto, per nome, per indirizzo, considera spaziatura, fixture vs beam. Per Position: solo pan, solo tilt o entrambi. Copia/incolla valori tra pixel. Elimina con o senza mantenere i valori. [CORE]

## 6. Preset, sequenze, Preset Palette

- **Preset**: combinazione di proprietà per un insieme di fixture (+ effetti e fanning, sempre editabili). Non definisce a metà una proprietà. Creazione da override, vuoto, o snapshot dello stato intero. Modifica (Edit/Update/Cancel), applica agli override, merge, "Add Overrides" (anche solo ai selezionati).
- **Gruppi**: annidabili, opzione "preset mutuamente esclusivi".
- **Sequenze**: lista di preset (step), non annidabili. Opzioni: repeat (anche infinito), backwards, autoreverse, random, freeze on completion. Reverse/Shuffle degli step.
- **Timing manuale**: hold + fade per step, default di sequenza, tempi individuali per step, speed rate globale, curva di fade. Crossfade solo su proprietà fadeable e definite in entrambi gli step; le non fadeable cambiano al 50%.
- **Timing a beat**: lunghezza step, beat multiplier (da ÷12 a ×12), quantizzazione, quantum, offset. Tutte le sequenze/effetti con lo stesso multiplier condividono la griglia.
- **Movimenti da sequenza**: interpolazione lineare, "Smooth movements" (curva), "Constant pace".
- Palette: split fino a 3 viste, filtro/ricerca, "Select Unused Items", "Show in Cue", export/import con mappatura fixture. Duplica, rinomina, riordina, elimina (avvisa se usato in cue).
- Smart lights: fade interno e fisso, curve non applicabili.

## 7. Effetti

Aggiunti a fixture/beam selezionati; sempre in loop, durata fissa o a beat o casuali. Overlay di più effetti sulla stessa proprietà (somma; colori in blend "screen"). Template di effetto salvabili (70+ built-in), copia/incolla, elimina mantenendo i valori.

### Tipi
- **Pattern** (Dimmer, Color): campioni (colori/intensità) riordinabili. Pattern: Chase, Scanner, Yo-yo, Fill, Rain, Meteor, Sparkle, Fire, Jellyfish, Snakes. Parametri: steps per value, phase, time offset, delay, smoothness, length, distance, fringe, noise, trail, palette, ecc.
- **Curve** (Dimmer, Color, Position, Focus, Zoom, Iris, Frost, Fog, custom): curva a punti di controllo (segmenti dritti/curvi), una curva per componente (HSB/RGB/CMY + extra; pan/tilt). Template, trasformazione, flip, copia/incolla, asse in % o secondi, time offset, opzioni Position (mirror pan/tilt, relativo).
- **Movement** (Position): percorsi chiusi (tipi Smooth, Line, Points), punti di controllo, punto di partenza, reverse, flip, trasformazione, pan/tilt offset, time offset. Percorsi salvati nel progetto, i built-in si duplicano alla modifica.

### Ordine fixture
Direzioni, per nome/indirizzo, random fisso/variabile, custom order, custom direction, spacing, fixtures vs beams, origine (inizio/centro/verso centro), grouping, repeat.

## 8. Live view (pagine, cue, cuelist)

- **Pagine**: nome, fade time, priorità; split view e finestre Live aggiuntive; cambio pagina con fade. Setting "disattiva cue prima di cambiare pagina". [CORE]
- **Cue** = combinazione di preset + sequenze + "Ad hoc properties" (override catturati alla creazione).
- **Pulsanti**: push (Toggle o Flash) e fader (orizzontali/verticali; controlla tutte le proprietà o solo alcune). Opzioni: priorità, colore, allineamento, font, Activate at startup, Activate before quitting, Always active, Require unlocked app, Exclude from Live Triggers.
- **Attached buttons**: gruppo in cui è attivo uno solo, con crossfade (curve di fade-in/out coerenti).
- **Frame**: raggruppamento, titolo, frecce prev/next, priorità, modificatori di frame (tipo submaster), shrink-wrap.
- **Cuelist** (una per pagina): cue e gruppi, hold time (vuoto = manuale), fade time, curva, skip (checkbox), numerazione/rinumerazione, "Go to cue", activate con/senza fade, manual crossfade (Xfade slider, anche cuelist verso precedente con Shift), loop, priorità, avanzamento automatico quando le sequenze finiscono.
- **Modificatori** (per cue e frame): Speed (con scelta degli aspetti: sequenze, effetti, rainbow, vector, pan/tilt infinito, gobo rotazione/shake/cambio, strobe, pulse, prisma), Beat Multiplier, Time Offset, Fade Time, Dimmer, Hue, Color Temperature, Green Saturation, Xfade to Color, Pan, Tilt, Focus, Zoom, Iris, Frost, Fog. Neutro vs default, reset, punto di stato.
- **Fade curve**: template, curva a punti, anteprima, curve speciali per proprietà/fixture (es. move-in-black), assi, default globali. Non applicabili a smart lights né ai fade manuali con Xfade.
- Continuità degli effetti tra cue attaccati o nella stessa cuelist se condividono lo stesso preset e gli stessi modificatori.
- **Blind mode** (modifiche senza output, applica/annulla), **Freeze output** (anche momentaneo), **Lock** (password; blocca Palette, Design, HUD opzionalmente).
- **Startup state**: pulito, oppure ripristino di pagine, cue attivi, modificatori, Master.

### Ordine di precedenza dell'output (CORE, da implementare esattamente così)
1. Override delle proprietà
2. Preset selezionati e sequenze in esecuzione nella Palette (in ordine di attivazione)
3. Cue sulle pagine visibili, per priorità decrescente: pagina → frame → pulsante/cuelist; a parità vince il più recente
4. Valori di default

## 9. Beat control

- Sorgente beat globale unica: BPM (anche frazionari), fase (downbeat).
- Impostazione: tap (4 colpi), valore esatto, ÷2/×2, sync beat/downbeat con offset.
- Sorgenti esterne: **MIDI Beat Clock**, **Ableton Link**, **OS2L**. Indicatore di beat nella Live view. [CORE tap+manuale+MIDI clock; V2 Link e OS2L]
- Su Windows/Linux Ableton Link è disponibile come libreria open source; MIDI via `rtmidi`/`mido`.

## 10. Controllo esterno

Sistema trigger→azione ("binding"), per categoria DMX-In / MIDI / Tastiera, con più configurazioni salvate nel progetto e import/export.

- **Trigger**: pulsante, fader/knob, wheel (solo MIDI). DMX-In: universo, canale, valore/range, inverso. MIDI: comando (Note, CC, Program Change, Pitch Wheel), canale 1–15, nota, controllo, valore, 14-bit, sensibilità, on/off, inverso, Shift, feedback (default, Note, CC, Program, SysEx). Tastiera: lettere, numeri, funzioni con Shift/Ctrl/Alt.
- **Capture** automatico del trigger, selezione automatica del binding, pulizia dei binding incompleti, ricerca, Test.
- **Azioni**: preset (toggle/flash/activate/deactivate), sequenze, cue, frame, cuelist (start/stop, pause, next, prev, xfade), intensità e modificatori cue/frame (anche "tutti i cue"), reset modificatori, deactivate all, selezione pagina/fixture/configurazione, cambia proprietà fixture, clear properties, blind, freeze, Master Dimmer, tap/sync/halve/double/set beat, Shift.
- **Feedback MIDI** a LED e fader motorizzati; porta virtuale "Lightkey Input/Output" (su Windows servono loopMIDI o equivalente, su Linux ALSA virtual ports).
- **OSC** (UDP/TCP, porta 21600, Bonjour/mDNS): indirizzi per nome con `_` al posto degli spazi, pattern (`? * [] {}` e `//`).
  - `/live/<pagina>/select`, `/live/<pagina>/cue/<cue>/activate|deactivate|toggle [fade]`, `/intensity`, frame (`previousCue`, `nextCue`), cuelist (`start|stop|toggle|pause|resume|nextCue|previousCue|xfade`, `skip|unskip`), modificatori (`speed`, `beatMultiplier`, `timeOffset`, `fadeTime`, `dimmer`, `hue`, `colorTemperature`, `greenSaturation`, `xfadeToColor`, `panAngle`, `tiltAngle`, `focus`, `zoomAngle`, `irisSize`, `frostAmount`, `fogAmount`)
  - `/palette/...` (activate/deactivate/toggle, start/stop sequenze)
  - `/output/` (blind, freeze, master), `/beat/` (tap, sync, syncDownbeat, halve, double, tempo)
  - `/fixture/<nome>/overrides/<proprietà> valore` (elenco completo nella guida, pag. 312–315), `/clear`, `/lamp/on|off`, `/command/<nome>`, `/select`, `/deselect`
- **OS2L** (VirtualDJ): beat + `os2l_button`. [V2]
- **Live Trigger Ableton**: bindings automatici su canale MIDI 16, clip generati per cue (fino a 128 per pagina). [V2]
- **Log controllo esterno**: finestra con messaggi DMX-In/MIDI/OSC/OS2L, filtri, pausa, marker (1000 messaggi). [CORE per debug]
- **[MAC] da sostituire**: Shortcuts/Siri, Touch ID/Apple Watch, gesture multi-touch/Force Touch (rimappabili su scorciatoie e modificatori mouse), Touch Bar.

## 11. Interfaccia (da replicare)

- Finestra unica scura, pensata per luce bassa, aree grandi cliccabili (touch-friendly): toolbar, Preview, Design view/Live view (Cmd+D / Cmd+L), Preset Palette, Shortcuts view contestuale, Master + indicatore beat.
- Modalità fullscreen all'apertura, colore di sfondo adattivo (colore predominante), nascondi/mostra pannelli.
- Scorciatoie: la guida elenca centinaia di combinazioni (Appendice 1). Su Windows/Linux Cmd→Ctrl, Option→Alt, Control-click→tasto destro.
- Impostazioni: General (azioni prima di uscire: dimmer a 0, cue "before quitting" 0,5 s, Lamp Off, canali a 0), Timing (default hold/fade/curve, precisione), DMX Output, Gestures, External Control.
- Licenze: ShowSuite non ha limiti di canali (nessun sistema di licenza richiesto).

## 12. Smart lights (Philips Hue) [V2]

Hue Bridge v2/Pro, pairing con pulsante, stanze/zone, stato Unreachable/Removed, adopt data, sposta tra bridge. Vincoli: latenza alta, niente effetti/beat/curve, fade gestiti dal bridge, ottimizzazione per stanza (≥5 luci).

---

## 13. Piano per fasi (proposta)

**Fase 1 – Motore + patch + output**
Modello dati, universi, backend Art-Net/sACN/Enttec/Open DMX, profili (generici + import FXT/SSL2), patch UI minima, DMX Monitor, salvataggio progetto.

**Fase 2 – Proprietà e Preview**
Preview 2D, selezione, calibrazione, Design view con tutte le proprietà, override, fanning, default, copia/incolla.

**Fase 3 – Preset, sequenze, Palette, effetti**
Più timing a beat e tap tempo.

**Fase 4 – Live view**
Pagine, cue, pulsanti, frame, cuelist, modificatori, curve di fade, blind/freeze/lock, ordine di precedenza.

**Fase 5 – Controllo esterno**
MIDI, OSC, DMX-In, tastiera, log; poi Link, OS2L, Ableton.

**Fase 6 – Extra**
Editor profili, import/export CSV, altre interfacce USB rare, Hue, OFL/GDTF.

## 14. Decisioni prese

1. **Interfacce multiple**: nessun limite artificiale. Più interfacce USB e più nodi Art-Net/sACN contemporaneamente; ogni universo sceglie la propria destinazione. I limiti di Lightkey (1 USB, 1 nodo Art-Net, 4 universi Art-Net) non vengono replicati. Resta il tetto di 16 universi per progetto, aumentabile in seguito.
2. **Formato progetto**: file `.showsuite-light` = archivio ZIP con `project.json` (con `schema_version`), `profiles/` (copie dei profili usati) e `assets/` (immagini del Preview). Leggibile, versionabile con git, portabile.
3. **Frequenza output**: 44 Hz di default (frame ogni ~23 ms), configurabile per universo. Open DMX: il motore genera i frame con timer dedicato.
4. **Preview**: QPainter 2D in Fase 2; passaggio a OpenGL solo se le matrici LED grandi lo richiedono.
5. **Ordine di supporto interfacce**: Art-Net → sACN → Enttec DMX USB Pro/Open DMX → DMXking/Jese/Robe → Eurolite/Stage-Profi → interfacce rare in stile FreeStyler (Velleman K8062, DMX4ALL, Digital Enlightenment, ecc.), una per volta in base a quali possiedi davvero e puoi testare.

## 15. Punti ancora aperti

- Quali interfacce fisiche hai a disposizione per i test (decide l'ordine reale della Fase 1 e 6).
- Se importare anche profili Open Fixture Library/GDTF già in Fase 1, per avere subito molti fixture.
