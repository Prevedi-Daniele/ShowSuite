"""Tema scuro per luce bassa, controlli grandi e cliccabili."""

ACCENT = "#3a8bff"
BG = "#16171b"
PANEL = "#1f2127"
PANEL_2 = "#272a32"
TEXT = "#d6d9e0"
MUTED = "#8b90a0"

STYLESHEET = f"""
* {{ font-size: 13px; color: {TEXT}; }}
QMainWindow, QDialog, QWidget {{ background: {BG}; }}
QMenuBar, QMenu, QToolBar {{ background: {PANEL}; border: none; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {ACCENT}; }}
QToolBar {{ spacing: 8px; padding: 6px; }}
QLabel {{ background: transparent; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid #33363f; border-radius: 6px; padding: 8px 14px; min-height: 20px; }}
QPushButton:hover {{ background: #30343e; }}
QPushButton:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
QPushButton#danger:checked {{ background: #c0392b; border-color: #c0392b; }}
QListWidget, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {PANEL}; border: 1px solid #33363f; border-radius: 4px; padding: 4px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}
QSlider::groove:horizontal {{ height: 6px; background: #33363f; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 18px; margin: -7px 0; border-radius: 9px; background: #e8eaf0; }}
QTabBar::tab {{ background: {PANEL}; padding: 8px 16px; border: 1px solid #33363f; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:selected {{ background: {PANEL_2}; border-color: {ACCENT}; }}
QSplitter::handle {{ background: #0e0f12; }}
QScrollArea {{ border: none; }}
QStatusBar {{ background: {PANEL}; }}
"""


def apply(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
