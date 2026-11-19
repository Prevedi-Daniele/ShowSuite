# SPEC-architettura.md (ShowSuite, Python)

Stack: **Python 3.12+**, **PySide6** (UI), **pyserial** (interfacce USB), **pytest**. Il codice Electron su `master` è ignorato: tutto il lavoro è su `main`.

## 1. Struttura del repo
```
pyproject.toml
src/showsuite/
  common/            # utilità condivise (clock, eventi, serializzazione)
  light/             # sezione Light (Lightkey)
    dmx/             # Universe, mixer, OutputManager, driver
    fixtures/        # FixtureProfile, FixtureInstance, Patch
    (poi) engine/ effects/ live/ control/
  cue/               # sezione Cue (QLab) — dopo Light Fase 1
  ui/                # PySide6, nessuna logica di dominio
tests/
specs/
```
Light e Cue sono pacchetti separati, installabili e avviabili da soli; possono comunicare via OSC ma non si importano a vicenda.

## 2. Regole
1. `light/` e `cue/` non importano PySide6: il motore gira anche headless (test, CLI).
2. L'UI parla col motore solo tramite API pubbliche e segnali.
3. Ogni driver di uscita implementa `OutputDriver` (`open`, `send(universe, data)`, `close`).
4. Un universo può avere 0..N destinazioni; ogni destinazione è un driver configurato. Nessun limite artificiale sul numero di interfacce.
5. Il file progetto ha `schema_version` e migrazioni.
6. Output a 44 Hz di default, configurabile; thread dedicato per l'output, mai nel thread UI.

## 3. Interfacce DMX (hardware reale: cinesi ~15 €)
Le interfacce USB economiche sono quasi sempre **Open DMX / FT232R** senza microcontrollore: il PC genera break, MAB e dati.
- Seriale 250000 baud, 8 bit, 2 stop, nessuna parità.
- Break ≥ 88 µs (usiamo ~120–200 µs), MAB ≥ 8 µs, start code 0x00 + 512 byte.
- Break via `break_condition` di pyserial. Su Windows e Linux il timing non è preciso (jitter di ~1 ms): di solito i dimmer/fixture lo tollerano, ma possono comparire sfarfallii. Mitigazioni: thread dedicato a priorità alta, frame sempre da 512 slot, rate più basso (30–40 Hz) se serve.
- Alcune "cinesi" sono cloni Enttec Pro (con microcontrollore): stesso VID/PID FTDI ma protocollo diverso. Il driver deve poter essere scelto a mano e fare un test di auto-rilevamento (opzionale).
- Linux: servono permessi su `/dev/ttyUSB*` (gruppo `dialout`) e il kernel `ftdi_sio`. Windows: driver FTDI VCP.
Ordine driver: Art-Net, sACN, Open DMX (FT232R), Enttec Pro, poi altri.

## 4. Fasi
- **Fase 1 (in corso)**: Universe, profili/patch, mixer (LTP per priorità), driver Art-Net/sACN/Open DMX, OutputManager, test automatici.
- Fase 2: salvataggio progetto, proprietà fixture, Preview 2D.
- Fase 3: preset, sequenze, Palette, effetti, beat.
- Fase 4: Live view (pagine, cue, cuelist, modificatori, blind/freeze/lock).
- Fase 5: controllo esterno (MIDI, OSC, DMX-In, tastiera).
- Fase 6: sezione Cue e extra.
