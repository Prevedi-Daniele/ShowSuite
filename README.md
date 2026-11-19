# ShowSuite

Cue (stile QLab 5) + Light (stile Lightkey) per Windows/Linux. Python 3.12+, PySide6.
Spec in `specs/`. Branch di lavoro: `main` (il codice Electron su `master` è separato e non usato).

```
pip install -e .[dev]
pytest
```

## Avvio (sezione Light)
```
pip install -e .[ui,dev]
python -m showsuite.light            # finestra Light
python -m showsuite.light.tools.dmx_test opendmx COM3 1   # prova interfaccia USB (Linux: /dev/ttyUSB0)
```
