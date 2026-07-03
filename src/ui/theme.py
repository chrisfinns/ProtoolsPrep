"""Application theme: dark studio utility.

Design intent (PRODUCT.md): the tool sits next to Pro Tools at a mixing desk
in low light. Neutral dark grays, a single restrained accent for actions /
selection / progress, semantic colors reserved for job status. Quiet, dense,
engineered - the tool disappears into the task.

Implementation: Fusion style (consistent cross-control rendering; also fixes
macOS's native style clipping QFormLayout fields) + one QSS sheet + a matching
QPalette so native pieces (menus, dialogs) blend in.
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

WINDOW = "#1d1f22"      # app background
SURFACE = "#25272b"     # group boxes, panels
FIELD = "#2b2e33"       # inputs, table base
RAISED = "#34383e"      # buttons
RAISED_HOVER = "#3d424a"
BORDER = "#3d4148"
BORDER_SOFT = "#33373d"

INK = "#e6e8eb"         # primary text (12.9:1 on SURFACE)
MUTED = "#a7adb5"       # secondary text (6.6:1 on SURFACE)
DISABLED = "#6b7077"

ACCENT = "#5b9dd9"          # primary action / selection / progress
ACCENT_HOVER = "#6faee5"
ACCENT_PRESSED = "#4b8ac2"
ACCENT_DIM = "#2c4257"      # selection background

# Job status (semantic - status is also always conveyed by label text)
STATUS_PENDING = MUTED
STATUS_RUNNING = ACCENT
STATUS_COMPLETED = "#6fbf73"
STATUS_FAILED = "#e07b6a"

STATUS_COLORS = {
    "pending": STATUS_PENDING,
    "running": STATUS_RUNNING,
    "completed": STATUS_COMPLETED,
    "failed": STATUS_FAILED,
}

MONO_FONT = "Menlo, Monaco, 'Courier New', monospace"

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

QSS = f"""
QMainWindow, QDialog {{
    background: {WINDOW};
}}

QWidget {{
    color: {INK};
    font-size: 13px;
}}

/* ---- Group boxes: quiet panels, title as section label ---- */
QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 12px 12px 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {MUTED};
    font-weight: 600;
}}

/* ---- Text inputs: roomy enough that descenders never clip ---- */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    min-height: 20px;
    selection-background-color: {ACCENT_DIM};
    selection-color: {INK};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {DISABLED};
    background: {SURFACE};
    border-color: {BORDER_SOFT};
}}
QLineEdit[placeholderText] {{
    /* Qt renders placeholder via palette; set there (see apply_theme) */
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {RAISED};
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {RAISED_HOVER};
}}

/* ---- Buttons ---- */
QPushButton {{
    background: {RAISED};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    min-height: 20px;
}}
QPushButton:hover {{
    background: {RAISED_HOVER};
}}
QPushButton:pressed {{
    background: {BORDER};
}}
QPushButton:focus {{
    border-color: {ACCENT};
}}
QPushButton:disabled {{
    color: {DISABLED};
    background: {SURFACE};
    border-color: {BORDER_SOFT};
}}

/* Primary action (Add to Queue, Start Queue) */
QPushButton[primary="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #10151a;
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton[primary="true"]:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton[primary="true"]:disabled {{
    background: {RAISED};
    border-color: {BORDER_SOFT};
    color: {DISABLED};
}}

/* ---- Checkboxes ---- */
QCheckBox {{
    spacing: 7px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {FIELD};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ---- Queue table ---- */
QTableWidget {{
    background: {FIELD};
    alternate-background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    gridline-color: transparent;
    selection-background-color: {ACCENT_DIM};
    selection-color: {INK};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QHeaderView::section {{
    background: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background: {SURFACE};
    border: none;
}}

/* ---- Progress bars (bottom bar + table cells) ---- */
QProgressBar {{
    background: {FIELD};
    border: 1px solid {BORDER_SOFT};
    border-radius: 4px;
    text-align: center;
    color: {INK};
    min-height: 14px;
    max-height: 16px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

/* ---- Log output ---- */
QTextEdit#logOutput {{
    background: #17181b;
    color: {MUTED};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    font-family: {MONO_FONT};
    font-size: 11px;
    padding: 4px;
}}

/* ---- Secondary / hint labels ---- */
QLabel[hint="true"] {{
    color: {MUTED};
    font-size: 11px;
}}

/* ---- Tabs (settings dialog) ---- */
QTabWidget::pane {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 6px 16px;
    border: 1px solid transparent;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {INK};
    border-color: {BORDER_SOFT};
    border-bottom-color: {SURFACE};
}}
QTabBar::tab:hover:!selected {{
    color: {INK};
}}

/* ---- Splitter ---- */
QSplitter::handle {{
    background: transparent;
    height: 6px;
}}
QSplitter::handle:hover {{
    background: {BORDER_SOFT};
}}

QToolTip {{
    background: {RAISED};
    color: {INK};
    border: 1px solid {BORDER};
    padding: 4px 6px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the dark studio theme to the whole application."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(WINDOW))
    palette.setColor(QPalette.WindowText, QColor(INK))
    palette.setColor(QPalette.Base, QColor(FIELD))
    palette.setColor(QPalette.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.Text, QColor(INK))
    palette.setColor(QPalette.PlaceholderText, QColor(MUTED))
    palette.setColor(QPalette.Button, QColor(RAISED))
    palette.setColor(QPalette.ButtonText, QColor(INK))
    palette.setColor(QPalette.Highlight, QColor(ACCENT_DIM))
    palette.setColor(QPalette.HighlightedText, QColor(INK))
    palette.setColor(QPalette.ToolTipBase, QColor(RAISED))
    palette.setColor(QPalette.ToolTipText, QColor(INK))
    palette.setColor(QPalette.Link, QColor(ACCENT))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(DISABLED))
    app.setPalette(palette)

    app.setStyleSheet(QSS)
