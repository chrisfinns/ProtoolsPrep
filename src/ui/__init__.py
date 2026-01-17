"""UI layer for Pro Tools Session Builder.

PySide6-based desktop application with:
- MainWindow: Three-section layout (form, queue, progress)
- QueueWorker: Background thread for job execution
- AppController: Signal/slot wiring between components
"""

from src.ui.app_controller import AppController
from src.ui.main_window import MainWindow
from src.ui.queue_worker import QueueWorker

__all__ = ["MainWindow", "QueueWorker", "AppController"]
