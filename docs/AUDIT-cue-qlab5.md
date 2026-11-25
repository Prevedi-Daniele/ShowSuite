# Audit sezione Cue contro il manuale QLab 5 (5.6, 16 giugno 2026)

Data: 2026-11-25. Test: 314 verdi. Nessuna funzione di questo documento è stata provata su hardware reale.

## Metodo e limiti dell'audit
- **Cap. 9.1 (dizionario OSC)**: verifica automatica. Ho estratto dal manuale 1047 indirizzi (modelli con `{parametri}`) e li ho inviati
  a `QLabApi` con tutti i permessi, usando un cue Audio. Un indirizzo è "gestito" se non risponde "sconosciuto".
  Lo script è riproducibile; l'elenco completo dei non riconosciuti è in `docs/osc_non_riconosciuti.txt`.
  Limite: molte proprietà sono specifiche di un tipo di cue (es. `hours` è del Timecode cue); testate su un cue Audio risultano
  "non riconosciute" anche se esistono per il tipo giusto. I numeri sono quindi un **limite inferiore** per `/cue`.
- **Altri capitoli**: NON letti riga per riga. Il giudizio si basa sui titoli di sezione del manuale e sul codice. Va considerato
  una stima, non una verifica.

## Copertura OSC (aggiornata a fine giornata: 849/1047, 81%)
Stessa misura automatica di prima (indirizzo "gestito" = non risponde "sconosciuto"; errori di valore/permesso contano come gestiti).
Partenza: 459/1047 (44%). Aggiunti oggi: show control broadcast, patch audio, impostazioni video, audio map, object audio per cue.
Ancora non riconosciuti: 198 (elenco in `docs/osc_non_riconosciuti.txt`): `/cue/.../` per slice marker, playlist, mute/solo per canale/oggetto,
effetti video, `liveAverageLevel`, `rotate`, `gang`, `*PatchID/Name/Number`, `objectLevel(s)`, `/update/...`, `/workingDirectory`, `/udpReplyPort`,
`/overrideWindow`, `/timecodeWindow`.

## Fatto (e coperto da test)
Modello workspace/liste/cart/cue; numerazione; pre-wait/durata/post-wait; continue; armed; colori; second trigger; GO e playhead;
gruppi (Start First, Start First and Enter, Start Random, Timeline, Playlist con crossfade/loop/shuffle); cue di controllo
(Start, Stop, Pause, Load, Reset, Arm, Disarm, GoTo, Target, Devamp, Wait, Memo); Fade (assoluto/relativo, curve, revert, stop target);
Script in Python; panic; undo/redo; salvataggio; UI base (lista, Inspector, cart, impostazioni, patch, Active Cues, Avvisi);
server OSC UDP/TCP SLIP/testo con sessioni, permessi, wildcard, `/+` `/-`, `/live`, push; query nei Network cue; protocolli MIDI/MSC/SysEx/MTC/LTC/SMF;
trigger hotkey/MIDI/MSC/wall clock/timecode; audio (matrice, slice/loop, rate, envelope, EQ, delay, panic, mute/solo);
video compositor (stage/regioni/route, maschere, edge blend, warp a 4 angoli, layer, testo); ponte Cue↔Light.

## Manca
- **Audio Map / object audio**: modello, indirizzi e instradamento fatti, ma con algoritmo APPROSSIMATO (QLab non pubblica la formula di gravity/shadow/filtri): i livelli intermedi non coincidono con QLab. Mancano Audio Map Editor grafico, heatmap, test object reale (solo stato), fade degli oggetti con Fade cue.
- **Show control broadcast MSC (8.7)**: la parte OSC è fatta, l'invio MSC ai dispositivi MIDI no.
- Liste di OSC `/cue/.../` mancanti per tutti i tipi: marker di slice (`sliceMarker`, `addSliceMarker`...), `playlist`, `mute/solo` per canale/oggetto,
  `liveAverageLevel`, `videoEffect*`, `rotate`, `gang`, `expand/collapse`, `tempDuration`, `soloCueInTime`, `fadeEntries`, `parameterValue(s)`,
  `valuesForKeysWithArguments`, `surface*`/`stage*`, `*PatchID/Name/Number`.
- UI: editor matrice/envelope/slice, editor Fade/Network/MIDI dedicati, editor Timeline, Light Dashboard, Workspace Status e Timecode Status (cap. 4),
  Find e Paste Cue Properties (3.2-3.3), finestra Monitor e Audition (3.5-3.6) in UI, Override Controls in UI, Launcher (3.4), tasti rapidi completi (1.5).
- Video: effetti video (6.7), warp a griglia/Bézier, Mic cue e ingressi, preserve pitch, plugin effetti audio (solo EQ/filtri/delay), uscita LTC reale su scheda audio.
- Collaborazione multiutente (8.1) e Workspace Templates (2.3).
- Le impostazioni OSC del workspace (porte) non governano ancora il server (usa 53000/53001/53535 fissi).

## Approssimato
- Warp video prospettico a 4 angoli, non mesh.
- Testo con font OpenCV semplice, senza font reali né formattazione per range.
- Script Python con builtins ristretti: non è una sandbox di sicurezza.
- Fade MIDI/Network a fps fissi con interpolazione lineare.

## Solo macOS: equivalente proposto
| Funzione QLab | Stato | Equivalente |
|---|---|---|
| Syphon (video) | non implementato | `FrameSink` (memoria/PNG) già presente; proposto Spout su Windows, NDI su entrambe |
| NDI (6.6) | non implementato | libreria NDI SDK via binding Python |
| AppleScript Dictionary (9.4) | non implementato | equivalenti già disponibili: API Python dei Script cue + OSC |
| Core Audio / Audio Units | non applicabile | `sounddevice` (PortAudio: WASAPI/ASIO/ALSA/JACK); plugin VST3 non fatti |
| Bonjour/mDNS | non implementato | `zeroconf` |
| Licenze (1.6, 1.7) | non applicabile | tutte le funzioni sono sempre attive |

## Non provato su hardware
`MidoBackend` e ingresso MIDI, `sounddevice`, Camera (`cv2.VideoCapture`), LTC su scheda audio, server OSC da client reali (QLab Remote, TouchOSC),
Arturia MiniLab 3, cavo DSD TECH SH-RS09B, proiettori e uscite video multiple.
