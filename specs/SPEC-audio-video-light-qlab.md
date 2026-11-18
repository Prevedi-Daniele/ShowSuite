# SPEC-audio-video-light-qlab.md  (ShowSuite / sezione Cue, riferimento: QLab 5.1.1)
Complementa SPEC-cue-modello.md (campi comuni, timing, stati), SPEC-cue-tipi.md (campi per tipo; §C Audio Output Patch, §H Video Output e §I Light sono qui approfonditi), SPEC-osc-qlab.md (indirizzi `/settings/…`, `dashboard/…`) e SPEC-protocolli-qlab.md (MIDI/Dashboard MIDI, override).
Fonte: *QLab 5 Reference Manual* (aggiornato 21/03/2023, QLab 5.1.1): §2.2 Workspace Settings, §5.1/5.4 Audio, §6.2/6.5/6.6/6.7 Video, §7.1–7.6 Lighting, §9.1 OSC Dictionary (JSON di patch/stage/route/light), §9.5 Parameter Reference (blend mode ed effetti video).

## 0. Convenzioni e marcatori
- Livelli audio in dB (dBFS, 0 = guadagno unitario; vuoto = −INF). Range workspace default +12…−60, configurabile (max ≥ −30; min −180…−40).
- Marcatori: **[ShowSuite]** = scelta di implementazione (stack Python 3.12 + PySide6, motore separato dalla UI; niente AudioUnit/Core Image/Syphon/licenze). **[ipotesi]** = il manuale non lo dice: va verificato contro QLab reale o deciso. **[manuale-refuso]** = errore evidente nel manuale, qui corretto. Tutto il resto è comportamento documentato.
- Le liste "Lacune" (§D) raccolgono ciò che il manuale non specifica. Non inventare in silenzio: ogni [ipotesi] deve diventare un test o una decisione.
- Tasti: Cmd → Ctrl su Windows/Linux (es. Dashboard ⇧⌘D → Ctrl+Shift+D).

---
# A. AUDIO

## A1. Modello del segnale
Ogni cue che genera audio (Audio, Mic, Video, Camera, Timecode-LTC) è assegnato a **un solo** Audio Output Patch. Catena:

`canale file/ingresso → [CUE MATRIX MIXER del cue] → cue output i → [effetti del cue output i] → [PATCH MATRIX MIXER] → device output j → [effetti del device output j] → hardware`

**Matrix mixer** = righe=ingressi, colonne=uscite; 4 famiglie di controlli: *input level* (colonna 0, per ingresso), *output level* (riga 0, per uscita), *crosspoint* (incrocio), *main level* (angolo 0/0). Guadagno di un percorso (dB) = input + crosspoint + output + main (somma in dB; lineare = prodotto). Più segnali sulla stessa uscita si **sommano in ampiezza lineare**. Clamp finale a [min, max] workspace.
- Vettori di test dal manuale: ingresso 3 a −3 dB, crosspoint (3→1) +2 → −1 dB su cue out 1; stesso ingresso, crosspoint 0, output level −2 → −5 dB su cue out 3.
- Unità: dBFS, non dB SPL. Il livello 0 è guadagno unitario: un file a −14 dBFS con tutti i controlli a 0 esce a −14 dBFS.
- **Cue matrix** (per cue, tab Levels): righe = canali del file (Audio/Video) o dell'ingresso device (Mic/Camera); colonne = cue outputs del patch. Dettagli (gang, set default, Trim) in SPEC-cue-tipi §A.
- **Patch matrix** (per patch, tab Patch Routing): righe = cue outputs (tutte le uscite dei cue, sommate), colonne = device outputs; ha il **main level del patch**. [ipotesi] input/output level per riga/colonna come nella cue matrix: il manuale mostra solo main + crosspoint.

### Sincronizzazione (regola di progetto)
1. Le cue con audio sono pilotate dal **clock del device** del loro patch → cue sullo **stesso patch** restano sample-accurate fra loro.
2. Cue avviate dalla **stessa azione** partono nello stesso istante (primo campione insieme).
Quattro casi: stesso patch+simultanee = in sync; stesso patch ma non simultanee (pre-wait, GO separati, trigger diversi) = offset costante per sempre; patch diversi+simultanee = partono insieme ma derivano (clock diversi; soluzione hardware: word clock); patch diversi+non simultanee = indipendenti. Le attese (pre-wait/post-wait) usano il **clock di sistema**, non quello audio → non sono sample-accurate.
**[ShowSuite]** un solo thread real-time per device; scheduling in numero di campioni; i cue avviati dalla stessa azione ricevono lo stesso `start_sample`. Patch su device diversi: nessuna correzione di drift (a meno di resampling opzionale, vedi Mic in SPEC-cue-tipi §B).

## A2. Workspace Settings → Audio → Audio Outputs
- Un workspace ha **N audio output patch** (illimitati). Un workspace nuovo crea **un patch per ogni device con uscite** presente. Si possono avere più patch sullo stesso device, ognuno con routing/effetti propri.
- Il device deve avere ≥1 canale di uscita, altrimenti warning. Un patch può usare l'**uscita di sistema** (il device di default dell'OS) **[ShowSuite]** = "System default" via PortAudio/WASAPI/PipeWire.
- Se il device sparisce il patch ne **mostra ancora il nome** (lavoro "offline"). Buffer di default 512 campioni per device (Preferenze → Hardware; più piccolo = meno latenza, rischio glitch con effetti). Sample rate/bit depth: i file vengono convertiti al formato del device (vedi SPEC-cue-tipi §A).
- Azioni sulla tabella patch: nuovo (Ctrl+N a tab attivo), elimina, riordina (drag; numeri rinumerati 1..N), duplica (Alt+drag), copia in altro workspace (drag), esporta (drag su file) **[ShowSuite]** `.showpatch` JSON; selezione multipla (Shift = range, Ctrl = singoli).
- **Volume Limits** (max/min) per workspace: valgono per slider, Fade, OSC, script. Max default +12 (pericolo: tenere basso); min default −60. Procedura di calibrazione del minimo (min a −120 → cue con rumore rosa → abbassare main fino a inaudibile → quel valore = min): è documentazione utente, non logica.
- **Audio Inputs**: analogo (Mic/Camera); il device deve avere ≥1 ingresso.

## A3. Audio Output Patch Editor
Apertura: Settings → Audio Outputs → Edit, oppure tab I/O di un cue → Edit…. Finestra: nome patch (testo), menu device, 3 tab, menu **Set from other patch or defaults…** (4 voci: copia da altro patch o reset; copre i contenuti dei tre tab; [ipotesi] voci = Cue Outputs / Patch Routing / Device Outputs / tutto), pulsante Done (conferma e chiude).

### Tab Cue Outputs
Una riga per **cue output** (= colonne della cue matrix in tutti i cue Audio/Mic/Video/Fade).
- `name` (testo; default = numero; max 2 righe con Alt+Invio; compare sotto gli slider della tab Levels; tenerlo breve).
- `effects[]`: menu *Add effect…* (AudioUnit compatibili; **[ShowSuite]** effetti built-in + VST3/LV2), applicati **in ordine sinistra→destra**; numero limitato solo dalla CPU.
- `group`: "1 channel" | "2 channels": raggruppa l'uscita con la **successiva** per effetti che richiedono 2 canali in ingresso (es. AUMatrixReverb). Vale **solo** per gli effetti sui cue output, non altrove.

### Tab Patch Routing
Matrice righe=cue outputs, colonne=device outputs (numero colonne = uscite del device), crosspoint in dB; **main level** del patch in alto a sinistra. Qualsiasi cue output → qualsiasi device output o combinazione; più cue output su uno stesso device output (con effetti solo su uno = **aux send**).
Esempio del manuale (8 uscite: 1 L, 2 R, 3 C, 4 sub, 5–6 effetti, 7–8 front fill): cue out 1 → dev 1 a 0 dB e dev 7 a −3 dB; cue out 2 → dev 2 (0) e dev 8 (−3); cue out 3 → dev 7 e dev 8 a −6 dB.
Default: cue output n → device output n a 0 dB (diagonale).

### Tab Device Outputs
Come Cue Outputs ma per le uscite del device: **senza nome**; stessi effetti per uscita (e raggruppamento).

### Limiti
- **I Fade cue NON possono modificare gli effetti** su cue output/device output (solo quelli del cue).
- Il numero massimo di cue output è 64 nel manuale con licenza audio (2 senza). **[ShowSuite]** senza licenze: 64 (valutare più alto).
- Il numero di cue output di un patch nuovo = [ipotesi] numero di uscite del device (max 64).

### Warning del patch (rendono "rotti" i cue che lo usano)
1. *No audio output device selected* (nessun device assegnato). 2. *Audio output device missing* (spento/scollegato/guasto). 3. *Audio device has no outputs* (device senza canali di uscita, es. microfono interno). Riflessi sul cue: "No audio output patch" / "Issue with audio output patch" (SPEC-cue-tipi §A/E).

### Modello dati proposto **[ShowSuite]**
```json
{ "id":"uuid","name":"Main PA","device":{"id":"wasapi:{...}","name":"Focusrite USB","missing":false},
  "cue_outputs":[{"index":1,"name":"L","group":1,"effects":[{"type":"vst3:…","bypass":false,"state":"…"}]}],
  "routing":{"main_db":0,"xp":{"1":{"1":0,"7":-3},"2":{"2":0,"8":-3}}},   // assente = -inf
  "device_outputs":[{"index":1,"group":1,"effects":[]}] }
```
Query OSC già coperta da `/settings/audio/patchList` → `[{uniqueID, name, routing:[numeri dei device output che ricevono almeno un cue output]}]` (nome = nome device se il patch non ha nome) e `/settings/audio/outputChannelNames` (solo patch con nomi personalizzati; altrimenti oggetto vuoto).

## A4. Test (audio)
1. Somma dB della matrice (vettori A1). 2. −INF = cella vuota. 3. Clamp ai limiti workspace per slider, Fade, OSC. 4. Patch condiviso da 2 cue partiti insieme → stesso `start_sample`. 5. Cue su patch diversi: nessuna garanzia di sync. 6. Effetti sul cue output applicati in ordine; Fade non li tocca. 7. Patch con device mancante → cue rotto, ma pre-wait/duration/continue rispettati (SPEC-cue-modello §6). 8. Duplicare/esportare un patch conserva routing, nomi, effetti.

---
# B. VIDEO

## B1. Glossario e flusso
`Video/Camera/Text cue → STAGE (raster virtuale) → REGION (porzione dello stage) → ROUTE (output route) → DEVICE (schermo/proiettore/NDI/Syphon)`
- **Stage**: raster virtuale a cui sono assegnati i cue; fino a **16384×16384** px (default 1920×1080). Ogni cue video ha **un solo** stage (`unpatched` = non suona).
- **Region**: sezione di uno stage mostrata su un device; può coprire tutto o parte; più region possono sovrapporsi.
- **Route**: intermediario region→device; permette di **cambiare hardware senza toccare cue, stage o region**.
- **Device**: rappresentazione di un dispositivo reale (monitor, TV, proiettore, LED wall) oppure di un output virtuale NDI/Syphon.
- Senza licenza (QLab) esiste un solo device "Video output for all cues". **[ShowSuite]** nessuna licenza: modello completo sempre attivo.
- Workspace nuovo: **uno stage + una route per ogni display collegato** (stage con la stessa risoluzione del device, una region a pieno stage). Tutta la configurazione sta in Workspace Settings → Video (4 tab: Video Outputs, Output Routing, Output Devices, Video Inputs).

## B2. Stage (tab Video Outputs)
Tabella: nome, risoluzione, devices (elenco), **Edit**, **Monitor** (finestra di monitor dello stage), **Delete** (annullabile).
**Menu New Video Stage** (Ctrl+N a tab attivo):
| Voce | Effetto |
|---|---|
| Empty Stage | 1920×1080, nessuna region, nessuna route |
| Stage with output | per ogni route esistente: stage della stessa risoluzione, con output su quella route (come il default) |
| Stage with partial output | per ogni route, sottomenu di porzioni: stage grande quanto una parte dell'output |
| Multi-Output Stage… | dialog (n proiettori, risoluzione, disposizione) → stage preconfigurato (con blending) |
| Stage with new NDI output… / new Syphon output… | crea device virtuale + route + stage |
**[ShowSuite]** Syphon → **Spout** (Windows) e v4l2loopback/PipeWire (Linux); NDI invariato.

### Attributi base (editor stage, parte alta)
- `name` (testo libero). `size` (w×h) con **Resize…** (opzioni: mantieni aspect ratio; ridimensiona o no le region).
- `layer`: ordine di impilamento fra **stage che usano la stessa area dello stesso device**; prevale sulla layer dei singoli cue (stage 100 "Angelica" sopra stage 50 "Eliza" anche se i cue di Eliza hanno layer più alta).
- `keep_rendering_between_cues` (bool): per default, se nessun cue gira lo stage **non** disegna nulla (si vede il desktop); quando ≥1 cue video gira, QLab disegna uno **sfondo nero su tutto lo stage**. Con la spunta lo sfondo nero resta finché si chiude l'app o il workspace riceve **panic** (nero fisso, transizioni più fluide su GPU al limite).
- `mask` (opzionale): immagine (qualsiasi formato immagine supportato) convertita in **scala di grigi** e scalata alla dimensione dello stage; **nero = nascosto, bianco = visibile** (grigi = parziale). Usi: stage non rettangolare, vignettatura (bordi sfumati), "buco" per far vedere uno stage di layer inferiore. Niente editor integrato: il file è **osservato** e ricaricato a caldo; stessa dimensione dello stage per evitare scaling live (costo prestazioni). Pulsante di rimozione.
**[ShowSuite]** watcher con `QFileSystemWatcher`; la maschera si applica allo stage **prima** del campionamento delle region.

## B3. Layout tab (region)
**Lista region** (tabella, 5 colonne): lettera-indice automatica (A, B, …) + colore; miniatura; **route** (menu); **grid** (checkbox: griglia di allineamento monocromatica sulla region); elimina.
Sotto la lista: menu per creare una region direttamente su una route; interruttore **Move Regions / Draw Regions** (muovere/ridimensionare esistenti vs disegnare nuove — le nuove vanno poi assegnate a una route).

**Parametri della region selezionata**
- `size` (w,h) — non può uscire dallo stage. `lower_left` (x,y) rispetto al **centro dello stage** (editabili); `upper_right` (x,y) **sola lettura**.
- **Edge blend**: per ciascun lato (sinistra/destra/alto/basso) checkbox + ampiezza del fall-off (sfumatura) — serve per proiettori affiancati ma vale anche per ammorbidire i bordi di una singola region. **Gamma** (curva di luminosità) unico per **tutti** gli edge blend dello stage.
- Regole: region mai fuori dallo stage; region senza route → bordo tratteggiato; edge blend → area retinata nel canvas.
**Canvas**: rettangolo bianco con griglia nera = stage; region disegnate colorate (nome+uscita); la selezionata è più scura; trascinare bordo = ridimensiona, centro = sposta; **magnetismo** su lati/centrilinee dello stage e sui bordi delle altre region (nessun gap/overlap accidentale). Scala di visualizzazione (menu, default "fit"). **Grid options…**: mostra/nascondi tutte le griglie, **esporta PNG** della griglia, bianco-su-nero / nero-su-bianco. Checkbox **Show alignment guides on all output routes used by this stage**: bordo colorato + centrilinee + etichette su ogni route usata, sempre sul raster **pieno** della route (senza warping/crop), per identificare e allineare fisicamente i device.
**Perché le region**: (a) due proiettori FHD affiancati = stage 3840×1080, region A (sinistra) → route proiettore sinistro, region B → destro; (b) un unico stage suddiviso in settori controllabili/warpabili separatamente anche sulla stessa route (3 quadranti su una route).
Coordinate: **[ipotesi]** la UI usa origine al centro dello stage; `/settings/video/…/bounds` (OSC) usa interi dentro lo stage con origine nell'angolo in basso a sinistra (x,y = angolo basso-sinistra). Verificare con QLab reale prima di implementare l'API.

## B4. Warping tab
Stessa lista di region, parametri diversi. Scopo: geometria **per region** (correzione keystone di proiettore fuori asse, adattamento a superfici non piane, effetti creativi).
**Parametri**: `center` (centro **funzionale**, editabile), `selected` (coordinate del punto di controllo selezionato, editabili), **mesh splits** (frecce su/giù, per asse: **1, 2, 4, 8, 16, 32** — potenze di 2), pulsanti di reset: **Size on Stage** (mesh splits=1 e region = dimensione della region del Layout) e **Size of Route** (mesh splits=1 e region = dimensione dell'intera route).
**Canvas**: rettangolo grigio con sottile bordo violetto = **route** della region selezionata; tutte le region assegnate a quella route sono disegnate a colori, la selezionata ha bordo giallo. Guide di warping (default griglia 4×4; menu cambia layout) mai in uscita. Bordi e guide **magnetici**. Interazioni: trascina punto = warpa; Alt+trascina punto = muove tutta la region usando il punto come riferimento; trascina interno (mano) = sposta; trascina bordo (freccia bidirezionale) = warpa spostando il bordo; trascina appena dentro il bordo (freccia verso l'interno) = warpa su **un solo asse**; **Shift** = regolazione fine; **Cmd/Ctrl** = disattiva snap.
**Warp Type** (per route, vale per **tutte** le region della route):
| Tipo | Comportamento |
|---|---|
| Perspective (default) | "continuous perspective": garantisce continuità, ma warp estremi possono non essere perfettamente corretti in prospettiva; un oggetto proiettato ha la stessa dimensione ovunque |
| Linear | trasformazione lineare diretta; meglio per warp multifaccia complessi, strano ad angoli estremi |
| Bézier | per superfici curve; **16 punti di controllo per mesh split** (4×4 per sotto-regione), ogni punto piega la superficie "elastica" |
Indice numerico `warpType` in JSON: **[ipotesi]** 0=Perspective, 1=Linear, 2=Bézier (ordine del menu).
**Link/unlink** dei punti di controllo: se i punti di due o più region coincidono esattamente si possono **collegare** (disegnati come rombo; muoverne uno muove tutti) o scollegare. Esempio del manuale: tre region su tre facce di un cubo con i vertici condivisi collegati.
Dati: `region = {name, uniqueID, boundsOnStage{x,y,width,height}, meshWidth, meshHeight, warpType, controlPoints[{x,y}]}`; OSC `…/subregionIndex/{i}/controlPointIndex/{j} {x} {y}` (interi, dentro l'area), `…/resetControlPoints`, `…/enableGrid`, `…/enableGuide`.
**[ShowSuite] pipeline di rendering** (per frame): (1) compongo i cue dello stage in una texture W×H per layer/blend (B7); (2) applico la maschera di stage; (3) per ogni region: campiono `boundsOnStage`, applico alpha di edge blend (curva con gamma), disegno la mesh deformata nello spazio-pixel della **route**; (4) region sulla stessa route composte nell'ordine della lista (**[ipotesi]**); (5) route raster → rotazione (0/90/180/270) → eventuale mirror orizzontale (rear) → scaling mode verso il device. Mesh: (N+1)×(M+1) vertici per Perspective/Linear (omografia per cella con continuità C0), patch bicubici di Bézier 4×4 per sotto-regione. Shader GLSL via Qt RHI; ≥60 fps.

## B5. Output Routing tab (route)
Tabella: nome, risoluzione, **device** (2 menu: quale device e come lo usa), **guides** (checkbox: contorno colorato, centrilinee, marcatori circolari agli angoli/centro e nome route sul raster pieno; non influenzati dal warping), Edit, elimina. Device mancante: nome in **corsivo** + "(missing)". Nuova route (Ctrl+N): con un device, NDI…, Syphon…, o con **partial screen device**.
**Route editor**
- `name`; `size` 1×1…**30000×30000** px (**Set from Device** copia la risoluzione del device).
- `rotation`: 0/90/180/270° (JSON `rotationDegrees`). `rear` (bool): mirror orizzontale per retroproiezione.
- `scaling_mode` (se route ≠ device; JSON `scalingMode` 0..3, **[ipotesi]** ordine del menu): **Center** (centra a densità originale; taglia o bordi neri), **Fit** (scala mantenendo aspect, bande nere), **Fill** (scala w e h indipendenti → deforma), **Aspect Fill** (scala e **ritaglia** senza deformare).
- `device` (+ dimensioni mostrate). Uso tipico: tournée con proiettori diversi per sede → si cambia solo il device della route, e lo scaling mode decide la resa.
**Partial outputs**: splitter (Matrox DualHead2Go/TripleHead2Go/QuadHead2Go, Datapath Fx4/Hx4, AJA HA5-4K) appaiono come un display enorme; una route può usare **solo una porzione** del device e comportarsi come se fosse un device intero.
**Dati**: `route = {uniqueID, name, enableGuides, destinationInfo{name, destinationType, videoOutputKeyPath, videoOutputRasterSize{w,h}, videoOutputRefreshRate}, rotationDegrees, scalingMode, naturalSize{w,h}, rear}`; display aggiungono `screenID`/`screenSerialNumber`; Blackmagic `deckLinkHandle, displayName, displayMode, displayModeInfo{identifier, displayName, pixelDimensions, fpsDuration, fpsScale, fieldDominance}, keyingMode`; NDI `pixelSize, audioChannels, audioSampleRate, audioBufferSize`; Syphon `pixelSize`.

## B6. Output Devices tab
Colonne: numero (automatico, **non riordinabile**), nome (fisso per hardware; **editabile** per NDI/Syphon), risoluzione, info (refresh rate; per NDI con audio: canali), Edit (solo Blackmagic e virtuali), elimina (solo virtuali, annullabile).
- **Display**: ogni schermo visibile al sistema operativo.
- **Blackmagic** (UltraStudio/Intensity/DeckLink con uscita; schede multi-uscita = più device). Display mode (risoluzione+fps). **Keying**: *None* (default) | *External* (2 uscite fisiche A/B = **key** e **fill**, sincronizzate al frame, per un mixer a valle; senza hardware compatibile il key è un grigio e il fill è sull'opaco nero) | *Internal* (sovrappone l'uscita di QLab a un ingresso live **che non passa da QLab**, compositing in hardware a bassissima latenza; molti modelli richiedono stessa risoluzione/fps su tutti gli I/O — primo controllo in caso di problemi). Per chiavi da green/blue screen: effetto **Linear Key** (B8). **[ShowSuite]** Blackmagic Desktop Video SDK, opzionale/plugin.
- **NDI** (virtuale): nome, pixel size, fps, audio (canali, sample rate, buffer). L'audio di un cue assegnato a uno stage NDI va **automaticamente e obbligatoriamente** sulla parte audio del device NDI. In ingresso, NDI è sorgente dei Camera cue (video input patch → Device → "NDI sources"; identificativo `DEVICE_NAME (NDI_SOURCE_NAME)`; evitare nomi duplicati).
- **Syphon** (virtuale): nome, pixel size.
**Rete NDI** (utente/diagnostica): stessa subnet (salvo NDI Bridge), multicast, mDNS (il manuale scrive "TCP 5353": **[manuale-refuso]** mDNS è UDP 5353), TCP 5960 messaggistica, stream da 5961 in su (dispositivi pre-2016: porte effimere 49152–65535); banda tipica con 16 canali audio: SD 20 Mbps, 720p60 90, 1080i60 100, 1080p60 125, UHDp30 250, UHDp60 400 Mbps; tenere il traffico NDI ≤75% della capacità; perdita ≤1%, latenza ≤150 ms, jitter ≤30 ms.
**Video Inputs tab**: patch di ingresso per Camera cue: numero, nome opzionale, device (webcam UVC, IIDC/DV, Blackmagic, Syphon, NDI), display mode (solo Blackmagic), Monitor, elimina; stessi gesti di riordino/duplica/copia/esporta dei patch audio.

## B7. Layer e Blend mode
**Layer del cue**: intero (1001 livelli: top, 999…1, bottom); stessa layer → ordine di avvio, l'ultimo sopra. **Layer dello stage** prevale (B2).
**Blend mode** (tab Video FX del cue): operazione **per pixel e per canale** fra il *foreground* (cue a layer più alta) e il *background* (ciò che sta sotto, accumulato dai cue a layer inferiore sullo stesso stage), valori canale 0.0…1.0 (rosso puro = (1,0,0)). Default **Normal**. Nome ufficiale (stringa per OSC/script, nomi completi):
`Normal, Darken, Multiply, Color Burn, Linear Burn, Lighten, Screen, Color Dodge, Linear Dodge, Overlay, Soft Light, Hard Light, Pin Light, Difference, Exclusion, Subtract, Divide, Hue, Saturation, Color, Luminosity, Addition Compositing, Maximum Compositing, Source Atop Compositing` (**24 modi**).
Il manuale **non** pubblica le formule (rimanda a video di riferimento e al workspace tutorial "Blend Mode Demo": 2 Video cue L1 oceano layer 1, L2 skyline layer 2; Network cue cambiano il blend di L2). **[ipotesi]** formule standard (W3C Compositing / Photoshop), con *s* = foreground, *b* = background, per canale:
| Modo | Formula |
|---|---|
| Normal | s (con alpha-over) |
| Darken / Lighten | min(b,s) / max(b,s) |
| Multiply | b·s |
| Screen | 1−(1−b)(1−s) |
| Color Burn | s=0 → 0, altrimenti 1−min(1,(1−b)/s) |
| Linear Burn | max(0, b+s−1) |
| Color Dodge | s=1 → 1, altrimenti min(1, b/(1−s)) |
| Linear Dodge | min(1, b+s) |
| Overlay | b<0.5 ? 2bs : 1−2(1−b)(1−s) |
| Hard Light | Overlay con b e s scambiati |
| Soft Light | formula W3C: s≤0.5 → b−(1−2s)·b·(1−b); altrimenti b+(2s−1)(D(b)−b), D(b)=b≤0.25 ? ((16b−12)b+4)b : √b |
| Pin Light | s<0.5 ? min(b,2s) : max(b,2s−1) |
| Difference / Exclusion | \|b−s\| / b+s−2bs |
| Subtract | max(0, b−s) (verso: **[ipotesi]**) |
| Divide | s=0 → 1, altrimenti min(1, b/s) |
| Hue / Saturation / Color / Luminosity | non separabili (W3C: SetLum/SetSat/ClipColor su luminanza Rec.601 .3/.59/.11) |
| Addition / Maximum / Source Atop Compositing | **[ipotesi]** equivalenti ai compositing filter di Core Image: somma / massimo / `s·αb + b·(1−αs)` (alpha premoltiplicato) |
Test di accettazione: riprodurre il workspace "Blend Mode Demo" in ShowSuite e confrontare **visivamente** i 24 modi con QLab reale prima di fidarsi delle formule.

## B8. Video FX (effetti video)
- Catena **ordinata** per cue (menu *Add video effect…*); renderizzati **in ordine** nell'elenco; **live** (in tempo reale, parametri modificabili durante il playback). Più effetti per cue; si possono avere più istanze (**[ipotesi]** anche dello stesso tipo).
- Selezionato = bordo grigio chiaro, controlli a destra: campi testo e slider; alcuni parametri usano selettori colore (click per iniziare). **Set Default Parameters** ripristina **solo** l'effetto selezionato. Pulsante rimozione per effetto.
- Costo CPU/GPU alto: da sperimentare prima dello show. **[ShowSuite]** shader GLSL/Qt RHI; ogni effetto = 1+ passate; fallback: avviso "effetto troppo pesante" se il frame time supera il budget.
- **Scripting**: effetto e parametro per **nome di scripting** (colonna `Script`); alcuni parametri accettano valori oltre il range indicato ("provare altri valori"); range sotto = "Allowed Values" del manuale. Colori = RGBA 4 float 0…1. Parametri `_protocolInput_X/Y` e `Point_*` sono coordinate normalizzate 0…1 (**[ipotesi]** origine in basso a sinistra, convenzione Core Image). I parametri `Choose_Effect`/`Choose_Blur` sono **enumerazioni** (indice 0…n).
- Nomi/parametri seguono le convenzioni **Core Image** (prefisso `input…`): in ShowSuite vanno riprodotti con shader propri, non esiste una libreria equivalente su Windows/Linux. Priorità di implementazione consigliata: Color Controls, Exposure, Gamma, Sepia/Monochrome, Min/Max/Invert, Highlights and Shadows, Temperature and Tint, Vibrance, Color Clamp, Color Matrix, Linear Key, blur (Box/Disc/Gaussian, Motion, Zoom), Shutter, Window, Keystone Correction, Spotlight; poi il resto.
- Refuso nel manuale: Spotlight "Points At X" compare due volte; il terzo (`Light_Points_Z`) è la coordinata **Z**.

**Tabella completa (59 effetti; fonte §9.5, "Video Effects")** — formato: *Etichetta* `scripting name` range.
- **Color Controls** (`ColorControls`): Brightness `inputBrightness` -1.0…1.0; Contrast `inputContrast` 0.25…4.0; Hue Angle `inputAngle` -180.0…180.0; Saturation `inputSaturation` 0.0…2.0
- **Exposure** (`Exposure`): Exposure Value `inputEV` -10.0…10.0
- **Gamma** (`Gamma`): Power `inputPower` -0.1…3.0
- **Sepia / Monochrome** (`SepiaMonochrome`): Choose Effect `Choose_Effect`: 0 (Sepia); 1 (Monochrome); Color `inputColor` RGBA 4×float 0..1; Intensity `inputIntensity` 0.0…1.0
- **Min / Max / Invert** (`MinMaxInvert`): Choose Effect `Choose_Effect`: 0 (Minimum Component); 1 (Maximum Component); 2 (Color Invert)
- **White Point** (`WhitePoint`): Color `inputColor` RGBA 4×float 0..1
- **Highlights and Shadows** (`HighlightShadow`): Highlight `inputHighlightAmount` 0.0…1.0; Shadow `inputShadowAmount` -1.0…1.0; Radius `inputRadius` 0.0…100.0
- **Temperature and Tint** (`TemperatureTint`): Source Temperature `Source_Temperature` 2000.0…10000.0; Source Tint `Source_Tint` -500.0…500.0; Target Temperature `Target_Temperature` 2000.0…10000.0; Target Tint `Target_Tint` -500.0…500.0
- **Vibrance** (`Vibrance`): Amount `inputAmount` -1.0…1.0
- **Tone Curve** (`ToneCurve`): Point 1 X `Point_0_X` 0.0…1.0; Point 1 Y `Point_0_Y` 0.0…1.0; Point 2 X `Point_1_X` 0.0…1.0; Point 2 Y `Point_1_Y` 0.0…1.0; Point 3 X `Point_2_X` 0.0…1.0; Point 3 Y `Point_2_Y` 0.0…1.0; Point 4 X `Point_3_X` 0.0…1.0; Point 4 Y `Point_3_Y` 0.0…1.0; Point 5 X `Point_4_X` 0.0…1.0; Point 5 Y `Point_4_Y` 0.0…1.0
- **Color Clamp** (`ColorClamp`): Minimum Red `Min_R` 0.0…1.0; Maximum Red `Max_R` 0.0…1.0; Minimum Green `Min_G` 0.0…1.0; Maximum Green `Max_G` 0.0…1.0; Minimum Blue `Min_B` 0.0…1.0; Maximum Blue `Max_B` 0.0…1.0; Minimum Alpha `Min_A` 0.0…1.0; Maximum Alpha `Max_A` 0.0…1.0
- **Color Matrix** (`ColorMatrix`): Red to Red `R_R` -1.0…1.0; Green to Red `G_R` -1.0…1.0; Blue to Red `B_R` -1.0…1.0; Alpha to Red `A_R` -1.0…1.0; Red Bias `R_Bias` -1.0…1.0; Red to Green `R_G` -1.0…1.0; Green to Green `G_G` -1.0…1.0; Blue to Green `B_G` -1.0…1.0; Alpha to Green `A_G` -1.0…1.0; Green Bias `G_Bias` -1.0…1.0; Red to Blue `R_B` -1.0…1.0; Green to Blue `G_B` -1.0…1.0; Blue to Blue `B_B` -1.0…1.0; Alpha to Blue `A_B` -1.0…1.0; Blue Bias `B_Bias` -1.0…1.0; Red to Alpha `R_A` -1.0…1.0; Green to Alpha `G_A` -1.0…1.0; Blue to Alpha `B_A` -1.0…1.0; Alpha to Alpha `A_A` -1.0…1.0; Alpha Bias `A_Bias` -1.0…1.0
- **Color Threshold** (`ColorThreshold`): Threshold `inputThreshold` 0.0…1.0
- **Spot Color** (`SpotColor`): Center Color 1 `inputCenterColor1` RGBA 4×float 0..1; Replacement Color 1 `inputReplacementColor1` RGBA 4×float 0..1; Closeness 1 `inputCloseness1` 0.0…1.0; Contrast 1 `inputContrast1` 0.0…10.0; Center Color 2 `inputCenterColor2` RGBA 4×float 0..1; Replacement Color 2 `inputReplacementColor2` RGBA 4×float 0..1; Closeness 2 `inputCloseness2` 0.0…1.0; Contrast 2 `inputContrast2` 0.0…10.0; Center Color 3 `inputCenterColor3` RGBA 4×float 0..1; Replacement Color 3 `inputReplacementColor3` RGBA 4×float 0..1; Closeness 3 `inputCloseness3` 0.0…1.0; Contrast 3 `inputContrast3` 0.0…10.0
- **Linear Key** (`LinearKey`): Key Color `inputKeyColor`: 0 (Green); 1 (Blue); Cutoff `inputCutoff` 0.0…4.0; Contrast `inputContrast` 0.0…10.0
- **Box / Disc / Gaussian Blur** (`BoxDiscGaussianBlur`): Choose Blur `Choose_Blur`: 0 (Box Blur); 1 (Disc Blur); 2 (Gaussian Blur); Radius `inputRadius` 0.0…400.0
- **Bokeh Blur** (`BokehBlur`): Radius `inputRadius` 0.0…500.0; Ring Amount `inputRingAmount` 0.0…1.0; Ring Size `inputRingSize` 0.0…500.0; Softness `inputSoftness` 0.0…10.0
- **Motion Blur** (`MotionBlur`): Radius `inputRadius` 0.0…400.0; Angle `inputAngle` -360.0…360.0
- **Sharpen Luminance** (`SharpenLuminance`): Sharpness `inputSharpness` 0.0…2.0
- **Unsharp Mask** (`UnsharpMask`): Radius `inputRadius` 0.0…100.0; Intensity `inputIntensity` 0.0…1.0
- **Zoom Blur** (`ZoomBlur`): Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Amount `inputAmount` 0.0…200.0
- **Morphology Gradient** (`MorphologyGradient`): Radius `inputRadius` 0.0…100.0
- **Morphology Min / Max** (`MorphologyMinMax`): Choose Effect `Choose_Effect`: 0 (Morphology Minimum); 1 (Morphology Maximum); Width `inputWidth` 1.0…101.0; Height `inputHeight` 1.0…101.0
- **Depth of Field** (`DepthOfField`): Point 1 X `Point_0_X` 0.0…1.0; Point 1 Y `Point_0_Y` 0.0…1.0; Point 2 X `Point_1_X` 0.0…1.0; Point 2 Y `Point_1_Y` 0.0…1.0; Radius `inputRadius` 0.0…100.0; Saturation `inputSaturation` 0.0…5.0; Unsharp Mask Intensity `inputUnsharpMaskIntensity` 0.0…10.0; Unsharp Mask Radius `inputUnsharpMaskRadius` 0.0…20.0
- **Pixellation** (`Pixellation`): Choose Effect `Choose_Effect`: 0 (Pixellate); 1 (Hexagonal Pixellate); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Scale `inputScale` 1.0…100.0
- **Screen** (`Screen`): Choose Effect `Choose_Effect`: 0 (Dot Screen); 1 (Line Screen); 2 (Hatched Screen); 3 (Circular Screen); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Width `inputWidth` 2.0…50.0; Sharpness `inputSharpness` 0.0…1.0
- **Bloom and Gloom** (`BloomGloom`): Choose Effect `Choose_Effect`: 0 (Bloom); 1 (Gloom); Radius `inputRadius` 0.0…100.0; Intensity `inputIntensity` 0.0…1.0
- **CMYK Halftone** (`CMYKHalftone`): Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Width `inputWidth` 0.0…100.0; Sharpness `inputSharpness` 0.0…1.0; Gray Component Replacement `inputGCR` 0.0…1.0; Under Color Removal `inputUCR` 0.0…1.0
- **Photo Effects** (`PhotoEffects`): Choose Effect `Choose_Effect`: 0 (Chrome); 1 (Fade); 2 (Instant); 3 (Mono); 4 (Noir); 5 (Process); 6 (Tonal); 7 (Transfer)
- **Color Posterize** (`ColorPosterize`): Levels `inputLevels` 2.0…30.0
- **Crystallize and Pointillize** (`CrystallizePointillize`): Choose Effect `Choose_Effect`: 0 (Crystallize); 1 (Pointillize); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Radius `inputRadius` 0.0…100.0
- **Edge Work** (`EdgeWork`): Choose Effect `Choose_Effect`: 0 (Edge Work); 1 (Edges); Intensity `inputIntensity` 0.0…10.0; Radius `inputRadius` 0.0…20.0
- **Line Overlay** (`LineOverlay`): Contrast `inputContrast` 0.25…10.0; Edge Intensity `inputEdgeIntensity` 0.0…1.0; Threshold `inputThreshold` 0.0…1.0; NR Noise Level `inputNRNoiseLevel` 0.0…4.0; NR Sharpness `inputNRSharpness` 0.0…1.0
- **Kaleidoscope** (`Kaleidoscope`): Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Count `inputCount` 1.0…64.0
- **Triangle Kaleidoscope** (`TriangleKaleidoscope`): Center X `Point_X` 0.0…1.0; Center Y `Point_Y` 0.0…1.0; Rotation `inputRotation` -360.0…360.0; Size `inputSize` 1.0…4000.0; Decay `inputDecay` 0.0…1.0
- **Droste** (`Droste`): Inset Point 1 X `Point_0_X` 0.0…1.0; Inset Point 1 Y `Point_0_Y` 0.0…1.0; Inset Point 2 X `Point_1_X` 0.0…1.0; Inset Point 2 Y `Point_1_Y` 0.0…1.0; Periodicity `inputPeriodicity` 1.0…400.0; Strands `inputStrands` 0.0…20.0; Zoom `inputZoom` 0.0…5.0; Rotation `inputRotation` -360.0…360.0
- **Light Tunnel** (`LightTunnel`): Center X `Center_X` 0.0…1.0; Center Y `Center_Y` 0.0…1.0; Radius `inputRadius` 1.0…4000.0; Rotation `inputRotation` -360.0…360.0
- **Median and Comic Effect** (`MedianComicEffect`): Choose Effect `Choose_Effect`: 0 (Median); 1 (Comic Effect)
- **False Color** (`FalseColor`): No scriptable parameters.
- **Thermal / X-Ray** (`ThermalXRay`): Choose Effect `Choose_Effect`: 0 (Thermal); 1 (X-Ray)
- **Gabor Gradients** (`GaborGradients`): No parameters.
- **Spotlight** (`Spotlight`): Color `inputColor` RGBA 4×float 0..1; Brightness `inputBrightness` 0.0…2.0; Concentration `inputConcentration` 0.0…5.0; Light Position X `Light_Pos_X` -1.0…2.0; Light Position Y `Light_Pos_Y` -1.0…2.0; Light Position Z `Light_Pos_Z` -1.0…2.0; Points At X `Light_Points_X` -1.0…2.0; Points At Y `Light_Points_Y` -1.0…2.0; Points At Z `Light_Points_Z` (nel manuale etichettato "X" per refuso) -1.0…2.0
- **Dither** (`Dither`): Intensity `inputIntensity` 0.0…5.0
- **Noise Reduction** (`NoiseReduction`): Noise Level `inputNoiseLevel` 0.0…0.1; Sharpness `inputSharpness` 0.0…2.0
- **Circle Splash / Hole Distortion** (`CircleSplashHoleDistortion`): Choose Effect `Choose_Effect`: 0 (Circle Splash); 1 (Hole); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Radius `inputRadius` 0.0…1000.0
- **Pinch / Bump Distortion** (`PinchBumpDistortion`): Choose Effect `Choose_Effect`: 0 (Pinch); 1 (Bump); 2 (Bump Linear); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Radius `inputRadius` 0.0…1000.0; Angle `inputAngle` -360.0…360.0; Scale `inputScale` 0.0…2.0
- **Torus / Lens Distortion** (`TorusLensDistortion`): Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Radius `inputRadius` 0.0…500.0; Width `inputWidth` 0.0…200.0; Refraction `inputRefraction` -5.0…5.0
- **Twirl / Circular Wrap / Vortex** (`TwirlVortexDistortion`): Choose Effect `Choose_Effect`: 0 (Twirl); 1 (Circular Wrap); 2 (Vortex); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Radius `inputRadius` 0.0…1000.0; Angle `inputAngle` -360.0…360.0
- **Glass Lozenge** (`GlassLozenge`): Point 1 X `Point_0_X` 0.0…1.0; Point 1 Y `Point_0_Y` 0.0…1.0; Point 2 X `Point_1_X` 0.0…1.0; Point 2 Y `Point_1_Y` 0.0…1.0; Radius `inputRadius` 0.0…1000.0; Refraction `inputRefraction` -5.0…5.0
- **Keystone Correction** (`KeystoneCorrection`): Correction Type `Choose_Effect`: 0 (Combined); 1 (Horizontal); 2 (Vertical); Upper Left X `UL_X` 0.0…1.0; Upper Left Y `UL_Y` 0.0…1.0; Upper Right X `UR_X` 0.0…1.0; Upper Right Y `UR_Y` 0.0…1.0; Lower Left X `LL_X` 0.0…1.0; Lower Left Y `LL_Y` 0.0…1.0; Lower Right X `LR_X` 0.0…1.0; Lower Right Y `LR_Y` 0.0…1.0; Focal Length `inputFocalLength` 0.0…30.0
- **Op Tile** (`OpTile`): Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Scale `inputScale` 0.1…10.0; Width `inputWidth` 0.0…1000.0
- **Perspective Tile** (`PerspectiveTile`): Bottom Left X `Bottom_Left_X` 0.0…1.0; Bottom Left Y `Bottom_Left_Y` 0.0…1.0; Bottom Right X `Bottom_Right_X` 0.0…1.0; Bottom Right Y `Bottom_Right_Y` 0.0…1.0; Top Left X `Top_Left_X` 0.0…1.0; Top Left Y `Top_Left_Y` 0.0…1.0; Top Right X `Top_Right_X` 0.0…1.0; Top Right Y `Top_Right_Y` 0.0…1.0
- **Quad Tiles** (`QuadTiles`): Choose Effect `Choose_Effect`: 0 (Fourfold Translated Tile); 1 (Fourfold Reflected Tile); 2 (Parallelogram Tile); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Acute Angle `inputAcuteAngle` -360.0…360.0; Width `inputWidth` 1.0…200.0
- **Reflected Tiles** (`ReflectedTiles`): Choose Effect `Choose_Effect`: 0 (Glide Tile); 1 (Sixfold Reflected Tile); 2 (Eightfold Reflected Tile); 3 (Twelvefold Reflected Tile); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Width `inputWidth` 1.0…200.0
- **Rotated Tiles** (`RotatedTiles`): Choose Effect `Choose_Effect`: 0 (Triangle Tile); 1 (Fourfold Reflected Tile); 2 (Sixfold Reflected Tile); Input X `_protocolInput_X` 0.0…1.0; Input Y `_protocolInput_Y` 0.0…1.0; Angle `inputAngle` -360.0…360.0; Width `inputWidth` 1.0…200.0
- **Nine-Part Stretched** (`NinePartStretched`): Lower Left X `LL_X` 0.0…1.0; Lower Left Y `LL_Y` 0.0…1.0; Upper Right X `UR_X` 0.0…1.0; Upper Right Y `UR_Y` 0.0…1.0; Grow Amount X `Grow_X` 0.0…1000.0; Grow Amount Y `Grow_Y` 0.0…1000.0
- **Nine-Part Tiled** (`NinePartTiled`): Lower Left X `LL_X` 0.0…1.0; Lower Left Y `LL_Y` 0.0…1.0; Upper Right X `UR_X` 0.0…1.0; Upper Right Y `UR_Y` 0.0…1.0; Grow Amount X `Grow_X` 0.0…5000.0; Grow Amount Y `Grow_Y` 0.0…5000.0; Flip Vertically `inputFlipYTiles` BOOLEAN
- **Shutter** (`Shutter`): Left `Left` 0.0…1.0; Right `Right` 0.0…1.0; Top `Top` 0.0…1.0; Bottom `Bottom` 0.0…1.0
- **Window** (`Window`): Origin X `Origin_X` 0.0…1.0; Origin Y `Origin_Y` 0.0…1.0; Width `Size_W` 0.0…1.0; Height `Size_H` 0.0…1.0

## B9. Fade di parametri video (aggiunte a SPEC-cue-tipi §D)
- Il Fade su Video/Camera/Text agisce su: **Opacity** (0–100 intero), **Translation** (X,Y), **Scale** (X,Y, bloccabili), **Rotation** (X,Y,Z), **3D orientation**, **Video FX** (qualsiasi parametro di qualsiasi effetto), **playback rate** ("Fade rate to": 0.03…33; nessun effetto su Camera/Text), più **Levels/Audio FX** se il target ha audio. Ogni parametro ha una **checkbox** (default off = non toccato); i parametri attivi sono fadati, gli altri restano intatti. "Set Geometry from Target" (⌃⌥⌘V) / "Set Video FX from Target" copiano i valori correnti come punto di partenza.
- **Diverso dall'audio FX**: per i video FX si fada **parametro per parametro** (checkbox per parametro); per gli audio FX si fada l'**intero stato** dell'effetto (SPEC-cue-tipi §D).
- **Rotazione**: di default **quaternione 3D** (movimento naturale su più assi, ma **mai oltre 180° per asse** in un fade); alternativa: scegliere un asse e gradi esatti. **Reset** azzera X/Y/Z = frontale.
- **Relativo** (menu "Absolute Fade"): **scale** e **opacity** sono **moltiplicativi** (scale 0.9 tre volte → 72.9%; opacity relativa 90% riduce del 10% del valore corrente); **translation** e **rotation 2D** sono **additivi** (+100 px X ogni esecuzione). Relativi su rotazione 3D o video FX = **risultati difficili da prevedere** (non garantiti). Un Fade **assoluto sostituisce** i relativi precedenti (QLab 5).
- Valori enumerati (`Choose_Effect`) e booleani non hanno interpolazione: **[ipotesi]** scatto all'istante di inizio. Colori RGBA: interpolazione per componente (**[ipotesi]**).
- Rotto se: no target; nessun parametro attivo; effetto audio mancante; (licenza: rate/FX audio, geometria/FX video) — **[ShowSuite]** niente licenza.

## B10. Broken/warning (video, stage e route)
Cue: *No video output stage*; *Incomplete video output* (stage assegnato ma configurazione incompleta, es. region senza route); device mancante → **disconnection warning** (route in corsivo). Stage: nessuna region utile, region senza route (dotted), route con device mancante. Route: dimensioni fuori range.

## B11. Test (video)
1. Stage 3840×1080 con region A/B su due route 1920×1080: pixel (x<1920) escono su A, il resto su B. 2. Cambiare il device di una route non altera stage/region/cue. 3. Layer di stage prevale su layer di cue. 4. `keep_rendering`: nero fisso finché panic. 5. Maschera: pixel nero = invisibile; modificare il file ricarica a caldo. 6. Mesh splits ∈ {1,2,4,8,16,32}; reset "Size on Stage"/"Size of Route" riportano split=1. 7. Warp type condiviso da tutte le region di una route. 8. Punti collegati si muovono insieme in region diverse. 9. Scaling mode: Center/Fit/Fill/Aspect Fill su route 1920×1080 → device 1280×720, 1920×1200, 3840×2160. 10. Rotation 90° e rear. 11. Relativo: scale ×0.9 tre volte = 72.9%; translation +100 additiva. 12. Fade assoluto dopo relativo = valore assoluto. 13. 24 blend mode selezionabili e salvati col nome esatto. 14. Set Default Parameters ripristina solo l'effetto selezionato; effetti senza parametri scriptable (False Color, Gabor Gradients) non rompono il cue.

---
# C. LUCI (Light cue di QLab)

## C1. Trasporto e DMX
- QLab parla con le luci in due modi: **Art-Net** (rete Ethernet/WiFi; QLab usa Art-Net **v3**, compatibile con nodi ≤ v4) e **USB-DMX** (Enttec DMX USB Pro / Pro Mk2, DMXking ultraDMX Micro / ultraDMX RDM Pro / ultraDMX2 Pro, Yarilo DMX PRO). Un **nodo** Art-Net converte rete→DMX512 (XLR-3/5). Connettori RJ-45 DMX **non** sono Ethernet.
- **DMX**: un universo = 512 canali (indirizzo+valore 0…255); frame completo ritrasmesso ogni ~23 ms (~44 Hz). Molti dispositivi mostrano 0…100%.
- **Art-Net addressing**: **Net** 0–127 (128), **Sub-Net** 0–15, **Universe** 0–15 (16 universi = 8192 indirizzi per sub-net); il primo universo è **0** (0/0/0). **[ShowSuite]** port-address a 15 bit = `net<<8 | subnet<<4 | universe`. I nodi sulla stessa rete condividono **un solo** spazio di indirizzi (due nodi entrambi su 3/2/1 = 512 indirizzi totali); ogni **device USB** ha il **proprio** spazio (universo 0 di ciascuno: due device = 1024 indirizzi).
- Preferenze → Hardware: **interfaccia di rete Art-Net** (default *Automatic*; esplicita solo con più NIC su reti con lo stesso schema IP), **Use broadcast mode** (default off: meno traffico; da attivare per nodi che non supportano il polling e per coesistere con altro software Art-Net sulla stessa macchina).
- **Override Controls**: `DMX output` (solo output, nessun input perché QLab non risponde a Art-Net/DMX in ingresso); OSC `/overrides/dmxOutputEnabled`, `…/toggleDmxOutput`. Un cue il cui output è sovrascritto mostra l'icona di divieto.
- **DMX Status Window** (menu Window): mostra **un universo** per volta e permette di forzare a mano i singoli indirizzi; **non** registrabile nei cue; serve a debug di patch/indirizzi.
- **Audition**: i Light cue in audition vanno al **tab Audition** del Dashboard, **mai** su Art-Net/DMX (blind). Settings → Audition: "Audition tab (light only)".
- **[ShowSuite] backend**: motore DMX separato dalla UI; thread a 44 Hz (configurabile 30–44); Art-Net: UDP 6454, ArtPoll/ArtPollReply per scoperta nodi, ArtDmx unicast ai nodi o broadcast (opzione); USB: protocollo **Enttec DMX USB Pro** (messaggio `0x7E`, label 6 "Send DMX", lunghezza LSB/MSB, start code 0 + dati, `0xE7`) su porta seriale, e driver "open DMX" FTDI come estensione. sACN (E1.31) e altri backend: SPEC DMX/Lightkey (SPEC-protocolli §12, estensioni). Licenza: QLab senza licenza limita a 16 indirizzi (strumenti oltre → rotti); ShowSuite **nessun limite**.

## C2. Light Patch (Workspace Settings → Light → Light Patch)
Concetti: **strumento (instrument)** = un oggetto fisico DMX (apparecchio, accessorio, dimmer) con ≥1 **parametro**; i convenzionali hanno solo *intensity*. **Gruppo (light group)** = insieme di strumenti **o di altri gruppi**; ogni strumento appartiene sempre al gruppo implicito **all**. **Nomi**: lettere, numeri e spazi; **unici nel workspace** (strumenti e gruppi nello stesso spazio); default numerico ("1","2",…); es. "chair", "front light", "src4", "viper". **[ipotesi]** vietare i nomi riservati `home`, `pass`, `cue` (il JSON li elenca come `settingKeywords`).
**Pulsanti**: *New Instrument* (Ctrl+N: popover con quantità, definizione, ecc.), *New Group* (Ctrl+G: quantità; opzione "includi gli strumenti selezionati"), *Auto-patch Selected…* (dialog: device + indirizzo iniziale; assegna in sequenza), *Delete Selected* (Ctrl+Backspace).
**Tabella patch** (ordinata alfabeticamente; triangolo di disclosure → parametri dello strumento / membri del gruppo): *Status* (icona "rotto" o "senza indirizzo"), *Name*, *Address(es)* (doppio click; per strumenti multi-indirizzo **solo l'indirizzo iniziale**), *Output* (Art-Net o USB + universo), *Note*; colonne opzionali (click destro sull'intestazione): *Definition* (clic sull'icona per cambiare), *Groups* (esclude "all"). Mini-inspector sotto: Name/Note/Definition (stessi dati), **Output**: *Art-Net* (campi Universe, Sub-Net, Net) | *USB* (menu device + universo, se multi-universo) | *None* (non patchato); **Add to Group…** + elenco dei gruppi di appartenenza.
**Regole di indirizzamento**: gli indirizzi sono **unici per universo e per device**; QLab **consente** di inserirne uno già usato ma marca **rotti** (e inutilizzabili) gli strumenti in conflitto finché non lo si risolve. Strumento che supera 512 canali nell'universo: **[ipotesi]** rotto. **Strumenti non patchati non compaiono nel Dashboard.** Strumenti con >16 indirizzi senza licenza = rotti (**[ShowSuite]** nessun limite).
**Menu Patch** (al posto di Tools quando l'editor è attivo): Unpatch All, Unpatch Selected, Auto-patch All…, Auto-patch Selected… (sovrascrive indirizzi esistenti; **non** tocca nomi, definizioni, gruppi), Select all instruments, Select all unpatched instruments. Auto-patch avanza in sequenza fino all'ultimo parametro dell'ultimo strumento; **[ipotesi]** passa all'universo successivo se supera 512 (da decidere).

## C3. Definizioni luce (Light Definitions)
**Definizione** = descrive i parametri di un tipo di apparecchio. Obbligatori: `name` **unico**, `manufacturer`, ≥1 parametro. Opzionali: parametri virtuali, `default_parameter`.
- **Default parameter** (menu): il parametro che risponde ai comandi **senza** parametro (`20 = 75` ≡ `20.intensity = 75`); di solito intensity; può essere **un altro** o **nessuno**.
- **Parametri** (ordine = **ordine dei canali DMX** definito dal costruttore: aggiungere nell'ordine corretto): `#` (posizione/offset), `name` (unico per strumento; lettere/numeri/spazi), `16-bit` (usa **due indirizzi adiacenti** come un solo valore 0…65535), `use %` (mostra come 0–100%; **non cambia il comportamento**, solo la visualizzazione), `home` (valore di riposo: dimmer 0%, iris 100%, specchio mobile 50%).
- **Parametri virtuali** (4+1 tipi; uniscono parametri in un solo comando + un controllo grafico nel Dashboard e nell'ispettore del cue):
  | Tipo | Uso | Controllo |
  |---|---|---|
  | **RGB Color** | colore additivo: ≥1 red, 1 green, 1 blue (+ white/amber/lime/indigo…); uno per cella/zona | additive picker |
  | **CMY Color** | sottrattivo (anche simulato): cyan, magenta, yellow | subtractive picker (capovolto) |
  | **HSI Color** | hue, saturation, intensity (o value) | picker circolare |
  | **Pan/Tilt** | pan + tilt | griglia pan (x) / tilt (y), linee ogni 10% |
  | **One-to-Many** | un comando pilota più parametri (anche altri virtuali), es. intensity generale di una barra multicella senza canale master | slider |
- JSON di `settings/light/patch`: ogni parametro ha `type` ∈ `"scalar" | "pantilt" | "rgbcolor" | "cmycolor" | "muxer"` (muxer = One-to-Many; **HSI non compare** nell'elenco del dizionario OSC: **[ipotesi]** omissione del manuale). Campi: `name, homeValue, valueIsPercentage, twoBytes, isBroken`; definizione: `manufacturer, name, defaultParameter (numero), definitionVersion, parameters{n:{…}}, isBroken`; parametro di strumento: `uniqueName "{strumento}.{parametro}"`, `instrumentName`, `homeValue`, `homeValueInDMX`.
- **Tab Light Definitions** (nel workspace): elenca le definizioni **usate da almeno uno strumento**; copiate dalla **Light Library** quando scelte; restano nel workspace anche se non più usate. Pulsanti: *New*, *Duplicate*, *Delete* (**vietato** se in uso; non cancella dalla library), *Save to library* (attivo se esiste solo nel workspace), *Update from library* (attivo se stesso nome ma parametri diversi → sostituisce con la versione globale), *Filter* (nome). Ordinamento gerarchico per costruttore → alfabetico. Ogni definizione usata è salvata **sia** nella library globale **sia** incorporata nel workspace (portabile tra computer).
- **Light Library** (finestra Window): come il tab ma sulla collezione globale. File: una definizione per **JSON** con estensione `.qlablight` in `~/Library/Application Support/QLab/LightLibrary` (cartella creata solo se si aggiungono/modificano definizioni; le stock stanno dentro l'app). Stock: **Generic** (Dimmer; DMX Iris 8/16 bit; RGB, RGBW, RGBAW con/senza intensity 8/16 bit; Scroller; Variable white con intensity 8/16 bit) + cataloghi costruttori (Acme, Altman, American DJ, …).
- **[ShowSuite]** formato `.showlight` JSON versionato (`format:1`) + cartella library utente (`%APPDATA%/ShowSuite/LightLibrary`, `~/.local/share/ShowSuite/LightLibrary`) + copia incorporata nel workspace. Inclusi di serie solo i **Generic**; import best-effort di `.qlablight` (lo schema reale **non** è documentato: si ricava da `settings/light/patch`) e valutare import da **Open Fixture Library** (verificare licenza). **Non** copiare in massa i cataloghi dei costruttori senza verificarne la licenza.
```json
{ "format":1,"manufacturer":"Generic","name":"RGBW + intensity 8-bit","default_parameter":"intensity","version":3,
  "parameters":[{"name":"intensity","bits":8,"percent":true,"home":0},
                {"name":"red","bits":8,"percent":true,"home":0}, {"name":"green","bits":8,"percent":true,"home":0},
                {"name":"blue","bits":8,"percent":true,"home":0}, {"name":"white","bits":8,"percent":true,"home":0}],
  "virtual":[{"type":"rgb","name":"color","members":["red","green","blue","white"]}] }
```
- **Valori**: parametro a percentuale accetta **decimali**; il valore è arrotondato al livello DMX più vicino: 8-bit `dmx=round(p·255/100)`, 16-bit `round(p·65535/100)`; visualizzazione `dmx/255·100`. Esempio del manuale: `1 = 10.7` → **DMX 27 → 10.59%** (**[manuale-refuso]**: il manuale scrive "DMX 25", ma 25/255=9.80% e 10.59% è 27/255). Parametri non-percentuali: valore grezzo 0…255 (0…65535 se 16-bit).

## C4. Linguaggio dei comandi luce
Ogni Light cue contiene un blocco di **testo** interpretato **riga per riga, dall'alto in basso**. Gli spazi sono **sempre opzionali** (`10=53` ≡ `10 = 53`).
```
comando   = bersagli "=" valore
bersagli  = bersaglio {"," bersaglio} | numero "-" numero          ; es.  10, 12, 14   |   1 - 3
bersaglio = rif ["." parametro]
rif       = nome-strumento | nome-gruppo | "[" bersagli "]"          ; [..] = gruppo ad-hoc
valore    = numero | "home" | "pass" | "cue" numero-cue ["*" fattore]
```
- `strumento = v` ≡ `strumento.<default_parameter> = v`. `gruppo.param = v` applica **a tutti i membri che hanno quel parametro**, ignora gli altri.
- **Percentuali/DMX**: vedi C3 (decimali ammessi per parametri a %, arrotondati a DMX).
- **`pass`**: lo strumento/gruppo **non viene toccato** da questo cue. Es. `backlight = 75` poi `12 = pass` → 10 e 11 a 75, 12 intatto. Serve a *sottrarre* da un gruppo (si applica in sequenza).
- **`home`**: valore home della definizione (dimmer 0; DMX iris 100). `x.param = home` solo quel parametro.
- **Range**: `1 - 3 = 50` e `10, 12, 14 = 75` sono **espansi** in comandi singoli (`1=50`, `2=50`, `3=50`) prima di essere aggiunti al cue o applicati al Dashboard. **[ipotesi]** range solo su nomi interi; strumento inesistente → comando non valido (cue rotto); mescolare `1-3, 10` non è documentato.
- **Gruppo ad-hoc** `[1 - 3] = 50`, `[10, 12, 14] = 50`: **non** viene espanso; resta **un solo comando** che si comporta come un gruppo.
- **Pull da cue** (`10 = cue A`): al momento dell'esecuzione inserisce il livello che lo strumento ha **registrato nel cue A** (come palette/preset di una console). Se lo strumento non è nel cue A → **nessun effetto**. Multi-parametro: tutti i parametri; `10.zoom = cue A`: solo zoom. Con gruppi: `group1 = cue A` / `3 = pass` / `4 = 75` → 1 e 2 = valori in A, 3 intatto, 4 = 75. Il pull è **collegato**: se A cambia, i cue che lo usano ricevono i nuovi valori alla prossima esecuzione; il pulsante **Expand** accanto al comando **copia** il livello nel cue corrente e lo trasforma in comando normale (rompe il link). **[ipotesi]** cicli di pull = comando non valido; pull di un pull risolto ricorsivamente.
- **Pull proporzionale**: `10 = cue A * .5` = metà del valore in A (rendere più scura/chiara una look precedente).
- **Cronologia** (↑ nella command line): `1 = 80`, ↑, `70`, ↑, `75` → non serve ridigitare `1=`.
- **Comando non valido** → cue rotto; si vede solo in **vista testo**.
- **Case/virgolette/virtuali**: la sintassi del valore per i parametri **virtuali** (colore RGB/CMY/HSI, pan/tilt) nei comandi **non è documentata** (il manuale dice solo che si controllano "con un solo comando"): aprire un Light cue reale con color picker in vista testo e copiare il formato **prima** di implementare (§D, lacuna 1).
**Safe Sort Commands**: ordina alfabeticamente, ma **non sposta** un comando se lo spostamento cambierebbe il risultato. **[ShowSuite]** due comandi **commutano** se gli insiemi di (strumento,parametro) espansi sono disgiunti e nessuno dei due è `pass` o `cue` che dipende dall'altro; sorting stabile con vincolo "non attraversare comandi non commutanti".
**Add Command** (menu): elenca strumenti e gruppi del patch; già presenti = in grigio.
**Viste del cue** (solo UI): *Slider* (segno giallo = valore; riordino con drag; delete con ✕; virtuali = picker nel pannello a destra), *Tile* (contorno giallo più luminoso = livello più alto; **niente riordino**; si selezionano **righe**), *Text* (modifica testuale; riordino con copia/incolla). Le modifiche nell'ispettore sono **blind**: si vedono solo eseguendo il cue.

## C5. Light cue: modello runtime
- **Tracking**: strumenti non citati **mantengono** il livello corrente (non 0). L'**ordine di esecuzione conta** (esempio: 6 strumenti, cue 1 tutti a 100; cue 2 porta 1–3 a 15 → live 15,15,15,100,100,100; partendo da buio ed eseguendo **solo** il cue 2 → 15,15,15,0,0,0).
- Per ogni parametro si tiene: `value`, **cue d'origine** (ultimo Light cue che lo ha impostato), `modified` (giallo, toccato nel Dashboard dopo l'ultimo cue), `parked`.
- **Collate effects of previous light cues** (per cue): simula l'esecuzione di **tutti i Light cue precedenti della stessa lista** → stesso look finale **indipendentemente da quali cue siano stati eseguiti** (comportamento da console). **[ipotesi]** l'insieme dei parametri bersaglio = unione di tutti i cue precedenti + questo; i valori = fold in ordine di lista; il cue fada dal valore **live corrente** al valore collazionato nella sua `duration`.
- **Durata e curva**: `duration` (stessa del tab Basics/colonna Duration) = tempo di fade; 0 = immediato. Curve (C8). Ogni parametro si muove dal valore live al valore del cue; parametri a livello crescente usano la curva *rising*, decrescente la *falling*; interpolazione nell'unità nativa del parametro (percentuale/DMX/16-bit) e arrotondamento a DMX solo in uscita.
- **Sub-controller** (`use_as_subcontroller`): il Light cue **con numero** compare nel Dashboard come fader 0–100% che scala **proporzionalmente** tutti i parametri registrati. Regola **HTP** (highest takes precedence) fra sub-controller e cue (sub a 20% + cue "tutto a 0" → resta 20%; cue "tutto a 100" → 100); fra sub-controller e Dashboard/altre regole vale **LTP** (latest takes precedence). Attenzione: **non** includere nei sub-controller parametri di timing per teste mobili (comportamento imprevedibile) né comandi di strike/spegnimento lampade ad arco (dannoso per le lampade).
- **Parking** (C7): un parametro parcheggiato ignora cue e Dashboard in uscita e il valore parcheggiato **non è registrabile**.
- Uscita finale per parametro: `out = parked ? parked_value : htp_merge(ltp_value, sub_controllers)` → DMX 8/16 bit sugli indirizzi patchati → Art-Net/USB.

## C6. Light cue: ispettore e broken
Tab **Basics**, **Triggers** (comuni), **Levels** (riga di comando, Add Command, Safe Sort, lista comandi, viste, `Collate…`, `Use as subcontroller…`, pulsanti **Light Patch…** e **Dashboard…**), **Curve**. Nessun target; può agire su uno, più o tutti i parametri.
**Broken**: *Invalid light command*; *No instrument in this cue is patched* (tutti i comandi su strumenti non/parzialmente patchati; è un **warning non bloccante** se solo alcuni lo sono); *Broken light definition*; *Missing USB DMX device* (device USB scollegato → **disconnection**). Una definizione mal configurata genera un warning **non bloccante** finché nessuno strumento la usa.

## C7. Light Dashboard (Ctrl+Shift+D)
Due tab: **Live** (livelli correnti di tutti gli strumenti, modificabili in tempo reale e inviati subito all'hardware; riflette i cue eseguiti) e **Audition** (livelli dei cue in audition; **nessuna uscita** DMX; niente *Clear All*, al suo posto **Reset from Live** che allinea tutti i livelli del tab ai Live; i pulsanti in basso funzionano come in Live).
**Modifica dei livelli**: command line; trascinare slider/tile; doppio click sul campo e digitare; trascinare il campo. **Shift-click** su più slider e trascinare = multi-selezione. Decimali (solo parametri a %): digitando o trascinando i **campi** (slider/tile arrotondano all'intero); trascinando il campo il numero di decimali dipende da 8/16 bit (16 bit = più decimali); **Shift** = più preciso. Un controllo modificato diventa **giallo** (slider con maniglia triangolare nella direzione dell'ultimo movimento; tile con sfondo giallo).
**Command line** (in alto): linguaggio C4. **Over Time** (secondi): se valorizzato il comando **fada** in quel tempo ("sneak"); **si azzera a 0 dopo ogni uso**.
**All / Used**: *All* = ogni strumento e gruppo del patch; *Used* = quelli **registrati in almeno un cue** + quelli modificati a mano (giallo).
**Slider / Tile**: *Slider* = una riga per strumento/gruppo, ordinata alfabeticamente, campo testo + slider; riga di gruppo con segni gialli per i livelli dei membri; **disclosure** (a destra = solo parametro default, tipicamente intensity; aperto = tutti i parametri; i gruppi contengono tutti i parametri dei membri). *Tile* = una tessera per parametro (livello grande sopra, "strumento · parametro" sotto; contorno più luminoso = valore più alto), divise in gruppi / strumenti semplici (1 parametro) / strumenti "fancy" (multi-parametro).
**Pannello virtuale** (sidebar, per lo strumento selezionato): *additive picker* (triangolo con pip trascinabile o swipe a due dita; Shift = lento/preciso; uno slider per componente che si aggiorna in tempo reale; lo sfondo del triangolo simula i colori ottenibili; slider **%** scala proporzionalmente **tutte** le componenti — utile per luci senza intensity), *subtractive picker* (solo C/M/Y, capovolto), *HSI picker* (circolare; lo slider intensity è collegato **direttamente** al parametro intensity reale, a differenza del % dell'additive), *Pan/Tilt* (pan orizzontale, tilt verticale, griglia ogni 10%). Click destro nella sidebar = mostra slider aggiuntivi del parametro default e di tutti gli altri parametri.
**Latest Light cue**: etichetta con l'ultimo Light cue eseguito (QLab non è "dentro" un cue: i cue sono parziali, il live può essere somma di più cue).
**Revert Changes (Ctrl+R)**: ripristina i parametri modificati nel Dashboard all'ultimo valore impostato, **in `panic duration`**; undo/redo per modifiche singole. **Clear All**: annulla le modifiche e porta **tutti** i parametri di tutte le luci a **home** (di norma blackout = "Go To Cue Out"; i parcheggiati **non** sono toccati).
**Registrare/aggiornare cue** (nuovi cue **dopo la selezione**, o in fondo se nessuna; lista o cart corrente):
| Azione | Effetto |
|---|---|
| **Record All…** → *Latest Cue* / *Selected Cue(s)* / *New Cue* | registra **tutti** i parametri di **tutti** gli strumenti (quelli mai toccati = **home**, tipicamente 0) → cue **blocking**; sovrascrive i livelli già presenti. *Latest* non disponibile se nessun Light cue eseguito; *Selected* se nessun Light cue selezionato |
| **Update…** (attivo se ci sono valori gialli) → *Latest* (Ctrl+U) / *Selected* (Ctrl+Shift+U) / *Originating* (Ctrl+Alt+U) | copia **solo i livelli modificati**: sovrascrive quelli già nel cue, **aggiunge** gli altri, lascia il resto |
| **New Cue with All** (Ctrl+Shift+N) | = Record All → New Cue |
| **New Cue with Changes** (Ctrl+N nel Dashboard) | registra **solo** i livelli modificati → cue **tracking** (es. modificati 2=36, 3=50 → il cue contiene solo `2 = 36`, `3 = 50`) |
**Update Originating**: ogni livello modificato va nel cue che **ne ha originato** il valore corrente (≈ "record track"); il pulsante riporta "Update *N* Originating Cues" (N = numero di cue d'origine distinti).
**Parking**: *Park Selected Lights* / *Unpark Selected Lights* (menu Tools; solo in vista Slider; selezionare il cursore dello strumento o singoli parametri; Cmd-click multiplo). Un parametro parcheggiato: **né cue né Dashboard** ne alterano l'uscita; il valore parcheggiato **non si registra**; si può comunque editare (l'uscita DMX resta bloccata; il valore parcheggiato è mostrato come "luce" gialla sulla traccia); è disegnato con **strisce diagonali** (come un cue disarmato). **Conferma** richiesta sia al park sia all'unpark: allo unpark il valore live cambia **subito** (può dare sorprese: es. strobo parcheggiato a 0, cue lo porta a 100, unpark → scatta). Usi: house light a glow durante il fuoco, impedire strobo/fog durante la programmazione.
**Menu Tools** (con Dashboard in primo piano): New Cue with Changes, New Cue with All, Update Latest/Selected/Originating, Record All to Latest/Selected, Clear All, Revert Changes, Park/Unpark.
**Altri riferimenti**: MIDI del Dashboard (tab *Light Dashboard MIDI*: canale = workspace | 1–16 | any; riga per strumento/gruppo + righe speciali **subcontrollers** e **selected**; cattura messaggio; **MIDI feedback** per fader motorizzati) → SPEC-protocolli-qlab §3; comandi OSC `dashboard/…` (clear, mode, newCueWithAll/Changes, recordAllToLatest/Selected, update…) e `settings/light/patch|undo|redo` → SPEC-osc-qlab §6–§7.

## C8. Curve (fade curve; Light cue e Fade cue)
Stesso componente per **Light cue** (tab Curve) e **Fade cue** (SPEC-cue-tipi §D). Quattro tipi (menu in alto a sinistra):
| Tipo | Comportamento |
|---|---|
| **S-Curve** | fissa "ease-in, ease-out": fade uniforme senza inizio/fine bruschi; **default dei Fade** (da cue template) |
| **Custom** | **default dei Light cue**; clic sulla curva = nuovo punto di controllo; il punto **piega dolcemente** la curva verso di sé; selezionare + Delete = rimuovere |
| **Linear** | come Custom ma i punti creano **spigoli netti** (segmenti lineari) |
| **Parametric** | curva matematicamente precisa regolata da **Intensity** (campo di testo) |
- **Rising** (sinistra) per i valori che **aumentano**, **Falling** (destra) per quelli che **diminuiscono**. Asse x = tempo (etichette dipendono dalla durata del cue), asse y = **percentuale della variazione totale**. Rising: angolo basso-sinistra = t=0, 0%; angolo alto-destra = fine, 100%. Falling: alto-sinistra = inizio; basso-destra = fine. Tipo **uguale** per le due curve, ma con Custom/Linear le **forme sono indipendenti**.
- **Reset to Default Shape**. Campo **Duration** nel tab (stesso valore del tab Basics). **Audio Domain** (slider/decibel/linear) vale solo per i livelli **audio** fadati (SPEC-cue-tipi §D).
- **Equal power** = Parametric + dominio linear; **equal gain** = Linear + dominio linear.
- **Rappresentazione [ShowSuite]**: `Curve{type, rising:{pts:[(t,y)…]}, falling:{pts}, intensity}`, `t,y ∈ [0,1]`. Progresso per un parametro: crescente `p(t)=y_rise(t)`; decrescente `p(t)=1−y_fall(t)`; valore `v(t)=v0+(v1−v0)·p(t)`. **[ipotesi]** S-Curve = smoothstep `3t²−2t³`; Custom = spline monotona (PCHIP) sui punti, Linear = poligonale; Parametric: **formula non pubblicata** — vincolo di accettazione: con dominio linear e intensity di default, `g(t)²+g(1−t)²=1` (rising `sin(πt/2)`, falling `cos(πt/2)`) = equal power; la parametrizzazione di `intensity` va scelta/misurata su QLab reale. Vincoli per tutti: `p(0)=0`, `p(1)=1`, continuità; Custom/S non devono oscillare (nessun overshoot).

## C9. Test (luce)
1. **Tracking**: look 1 (tutti 100) + cue 2 (1–3=15) → 15,15,15,100,100,100; solo cue 2 da buio → 15,15,15,0,0,0. 2. **Originating**: cue1 `100×6`; cue2 `1,2,3=15`; cue3 `2=80`; cue4 `4,5=25`; cue5 `3=50`; live = 15,80,50,25,25,100; portare tutti a 75 + **Update Originating** → "Update 5 Originating Cues"; cue1 → solo strumento 6=75; cue2 → 1=75 (2 e 3 = 15); cue3 → 2=75; cue4 → 4=75,5=75; cue5 → 3=75. 3. **Range**: `1 - 3 = 50` → 3 comandi; `[1 - 3] = 50` → 1 comando. 4. **Pass/group**: `backlight=75`, `12=pass` → 12 intatto. 5. **Pull**: `group1=cue A`, `3=pass`, `4=75`; **Expand** rompe il link; `10 = cue A * .5` = metà. 6. **Arrotondamento**: `1=10.7` → DMX 27 → 10.59%; 16-bit `round(p·65535/100)`. 7. **Default parameter**: `20=75` ≡ `20.intensity=75`. 8. **home**: dimmer → 0, iris → 100. 9. **HTP**: sub 20% + cue "tutto 0" = 20; cue "tutto 100" = 100; sub vs Dashboard = LTP. 10. **Park**: cue e Dashboard non cambiano l'uscita; unpark applica il valore live; Clear All non tocca i parcheggiati; il valore parcheggiato non entra in Record/Update. 11. **Over Time** si azzera dopo ogni uso. 12. **Record All** mette home sui non toccati; **New Cue with Changes** solo i gialli. 13. **Audition**: nessun pacchetto Art-Net/DMX; Reset from Live copia il live. 14. **Patch**: indirizzi duplicati → entrambi rotti; non patchato non appare nel Dashboard; Auto-patch non cambia nomi/definizioni/gruppi; Art-Net net/sub/uni ↔ port-address 15 bit; USB device = spazio indirizzi separato. 15. **Cue rotto**: comando non valido / nessuno strumento patchato / definizione rotta / device USB mancante; rispetta pre-wait/duration/continue. 16. **Curva**: rising per valori in salita, falling per valori in discesa nello **stesso** cue; durata 0 = istantaneo. 17. **Collate**: eseguire cue 5 da buio con collate = stesso stato che eseguendo 1…5. 18. **Safe Sort** non cambia mai il risultato (testare con coppie commutanti e non). 19. **Definizione**: 16-bit usa 2 indirizzi adiacenti; `use %` non cambia l'uscita DMX; Delete di definizione in uso rifiutato.

---
# D. LACUNE DEL MANUALE E DECISIONI APERTE
Il manuale è una guida utente, non una specifica formale. Da verificare/decidere **prima** della Fase di implementazione (ordine = impatto):
1. **Sintassi dei valori per parametri virtuali** nei comandi luce (colore RGB/CMY/HSI, pan/tilt, One-to-Many) e se il parser è case-sensitive. Senza questo il Light cue non è compatibile al 100% con file QLab.
2. **Formule delle curve** (S-Curve, Parametric/intensity, spline Custom, forma di default) e **delle blend mode / compositing** (B7). Servono confronti visivi/numerici con QLab reale.
3. **Comportamento di Light cue su Stop/Pause/Panic/Reset** e di Dashboard Revert vs cue in corso; **tempo** di fade di `collate`.
4. **Schema reale** di `.qlablight` e del tipo `hsi` nel JSON; **formato** di salvataggio workspace di stage/region/route/patch.
5. **Edge blend**: unità dell'ampiezza, default del gamma, formula del fall-off, composizione di region sovrapposte sulla stessa route; ordine esatto rotazione/rear/scaling.
6. **Indici numerici** (`warpType`, `scalingMode`) = ordine del menu (ipotesi).
7. **Patch matrix**: esistenza di input/output level per riga/colonna oltre al main.
8. **16-bit**: ordine coarse/fine dei due canali; **auto-patch** a cavallo di universo; mix di range (`1-3, 10`); nomi riservati; cicli di pull.
9. **Interpolazione** di parametri enumerati/booleani/colore nei Fade video.
10. **Sub-controller multipli** sullo stesso parametro (il manuale dice solo "non interagiscono per HTP").
Errori nel manuale già corretti in questa spec: DMX 25 vs 27 (C3), mDNS TCP vs UDP (B6), `Light_Points_Z` etichettato X (B8).

# E. ORDINE DI IMPLEMENTAZIONE SUGGERITO (per STATO.md)
1. **Audio**: patch/matrici/clock (A) — alimenta tutti i cue con audio. 2. **Stage/region/route** con layout (B2–B3, B5) e rendering senza warping; poi **warping/edge blend** (B4) e **blend mode** (B7). 3. **Video FX** per priorità (B8), con test visivi. 4. **Light**: patch + definizioni Generic + linguaggio comandi + motore tracking/HTP/parking + uscita Art-Net/Enttec (C1–C5), poi **Dashboard** (C7). 5. Curve (C8) condivise con Fade. Ogni punto con i test di A4, B11, C9.
