"""Una sola QApplication per tutta la sessione di test, tenuta viva fino alla fine del processo.

Se ogni test ne creasse una propria senza riferimenti, verrebbe distrutta con widget ancora vivi
e il processo andrebbe in crash allo spegnimento (heap corruption intermittente)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    _APP = QApplication.instance() or QApplication([])
except Exception:     # PySide6 assente: i test non-UI girano comunque
    _APP = None


def pytest_sessionfinish(session, exitstatus):
    """Chiude e distrugge i widget in ordine prima dello spegnimento di Python/Qt."""
    if _APP is None:
        return
    import gc
    for w in _APP.topLevelWidgets():
        try:
            w.close(); w.deleteLater()
        except RuntimeError:
            pass
    _APP.processEvents()
    gc.collect()
    _APP.processEvents()
