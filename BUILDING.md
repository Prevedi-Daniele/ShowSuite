# Compilazione ed Esecuzione Nativa di ShowSuite

ShowSuite è un'applicazione desktop **completamente nativa e autonoma**, progettata per essere installata ed eseguita direttamente su **Windows** e **Linux** senza alcun browser web.

L'applicazione si compila in:
- **Windows**:
  - `ShowSuite-Setup-1.0.0.exe`: Installer classico con wizard di installazione Windows, scelta cartella, scorciatoia sul Desktop e nel Menu Start.
  - `ShowSuite-1.0.0.exe`: Versione **Portable** (un singolo file eseguibile autonomo, ideale per chiavette USB di regia e tour teatrali).
- **Linux**:
  - `ShowSuite-1.0.0.AppImage`: Eseguibile universale per qualsiasi distribuzione Linux (Ubuntu, Debian, Fedora, Arch).
  - `ShowSuite-1.0.0.deb`: Pacchetto per distribuzioni basate su Debian/Ubuntu.

---

## 1. Compilazione Automatica su GitHub (Consigliata)

Poiché questo progetto è un repository Git, è già configurata una **GitHub Action** (`.github/workflows/build.yml`) per la compilazione continua in cloud.

### Come generare gli eseguibili con GitHub:
1. Esegui il push del codice sul tuo repository GitHub:
   ```bash
   git add .
   git commit -m "Compilazione ShowSuite"
   git push origin master
   ```
2. Vai nella scheda **Actions** del tuo repository GitHub: vedrai partire automaticamente il workflow `Build & Release ShowSuite Native`.
3. Al termine (circa 3-4 minuti), troverai nella sezione **Artifacts** i pacchetti già compilati e pronti al download:
   - `ShowSuite-Windows` (.exe installer e portable)
   - `ShowSuite-Linux` (.AppImage e .deb)
4. Se vuoi creare una Release formale, crea un tag Git (es. `v1.0.0`):
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   GitHub pubblicherà automaticamente la Release con i file scaricabili allegati.

---

## 2. Compilazione Locale sul tuo PC

Se desideri compilare direttamente sul tuo computer senza passare da GitHub:

### Prerequisiti
- Node.js versione 20 o 22 LTS installato.

### Compilazione per Windows (eseguibile `.exe`)
Apri PowerShell nella cartella del progetto ed esegui:
```powershell
npm run package:win
```
Troverai i file `.exe` generati nella cartella `release/`:
- `release/ShowSuite-Setup-1.0.0.exe`
- `release/ShowSuite-1.0.0.exe`

### Compilazione per Linux (`.AppImage` / `.deb`)
Su una macchina o macchina virtuale Linux (o tramite WSL2 / CI):
```bash
npm run package:linux
```
Troverai i pacchetti generati nella cartella `release/`:
- `release/ShowSuite-1.0.0.AppImage`
- `release/ShowSuite-1.0.0.deb`

---

## 3. Esecuzione del Software Compilato

- **Su Windows**: Fai doppio clic su `ShowSuite-Setup-1.0.0.exe` per installarlo nel sistema, oppure avvia direttamente la versione portable.
- **Su Linux**: Rendi eseguibile l'AppImage (`chmod +x ShowSuite-1.0.0.AppImage`) e fai doppio clic per avviarlo.
