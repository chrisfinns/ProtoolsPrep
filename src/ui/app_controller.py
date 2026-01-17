"""Application controller for Pro Tools Session Builder.

Coordinates between MainWindow, QueueManager, and QueueWorker.
Handles all signal/slot connections for thread-safe communication.
"""

import logging

from PySide6.QtCore import QObject, Slot

from src.core.exceptions import PTSessionBuilderError
from src.core.session_spec import SessionSpec
from src.queue.job import Job
from src.queue.queue_manager import QueueManager
from src.ui.main_window import MainWindow
from src.ui.queue_worker import QueueWorker

logger = logging.getLogger(__name__)


class AppController(QObject):
    """Controller that wires MainWindow, QueueManager, and QueueWorker together."""

    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.window = main_window
        self.queue_manager = QueueManager()
        self.worker: QueueWorker | None = None

        self._connect_signals()

    def _connect_signals(self):
        """Connect all signals and slots."""
        # Connect MainWindow signals to controller slots
        self.window.add_job_requested.connect(self._on_add_job)
        self.window.start_queue_requested.connect(self._on_start_queue)
        self.window.pause_queue_requested.connect(self._on_pause_queue)
        self.window.clear_queue_requested.connect(self._on_clear_queue)
        self.window.remove_job_requested.connect(self._on_remove_job)

    def _connect_worker_signals(self, worker: QueueWorker):
        """Connect QueueWorker signals to MainWindow slots."""
        worker.job_started.connect(self._on_job_started)
        worker.job_progress.connect(self._on_job_progress)
        worker.job_completed.connect(self._on_job_completed)
        worker.job_failed.connect(self._on_job_failed)
        worker.queue_finished.connect(self._on_queue_finished)
        worker.log_message.connect(self.window.log_message)

    # Slots for MainWindow signals

    @Slot(SessionSpec)
    def _on_add_job(self, spec: SessionSpec):
        """Add job to queue."""
        try:
            job = Job(spec)
            self.queue_manager.add(job)
            self._update_queue_display()
            self.window.update_status(f"Added: {spec.song_name}")
        except Exception as e:
            logger.exception("Failed to add job")
            self.window.update_status(f"Failed to add job: {str(e)}")

    @Slot()
    def _on_start_queue(self):
        """Start queue execution in background thread."""
        if self.worker is not None and self.worker.isRunning():
            self.window.log_message("Queue is already running")
            return

        if self.queue_manager.is_empty():
            self.window.log_message("Queue is empty - add jobs first")
            return

        # Create and start worker thread
        self.worker = QueueWorker(self.queue_manager)
        self._connect_worker_signals(self.worker)

        self.worker.start()
        self.window.set_queue_running(True)
        self.window.update_status("Queue running")
        self.window.log_message("Started queue execution")

    @Slot()
    def _on_pause_queue(self):
        """Pause queue execution after current job."""
        if self.worker is None or not self.worker.isRunning():
            self.window.log_message("Queue is not running")
            return

        self.worker.stop()
        self.window.update_status("Pausing after current job...")

    @Slot()
    def _on_clear_queue(self):
        """Clear all jobs from queue."""
        if self.worker is not None and self.worker.isRunning():
            self.window.log_message("Cannot clear queue while running - pause first")
            return

        self.queue_manager.clear()
        self._update_queue_display()
        self.window.update_status("Queue cleared")
        self.window.log_message("Cleared all jobs from queue")

    @Slot(str)
    def _on_remove_job(self, job_id: str):
        """Remove job from queue by ID."""
        if self.worker is not None and self.worker.isRunning():
            self.window.log_message("Cannot remove jobs while running - pause first")
            return

        removed = self.queue_manager.remove(job_id)
        if removed:
            self._update_queue_display()
            self.window.update_status(f"Removed job: {job_id}")
            self.window.log_message(f"Removed job from queue")
        else:
            self.window.log_message(f"Failed to remove job: not found or is current job")

    # Slots for QueueWorker signals

    @Slot(str)
    def _on_job_started(self, job_name: str):
        """Handle job started event."""
        self._update_queue_display()
        self.window.update_status(f"Running: {job_name}")

    @Slot(str, int, str)
    def _on_job_progress(self, job_name: str, progress: int, message: str):
        """Handle job progress update."""
        self.window.update_job_progress(job_name, progress)
        self.window.update_status(message)
        self._update_queue_display()

    @Slot(str)
    def _on_job_completed(self, job_name: str):
        """Handle job completed event."""
        self._update_queue_display()
        self.window.update_job_progress("", 0)
        self.window.update_status(f"Completed: {job_name}")

    @Slot(str, str)
    def _on_job_failed(self, job_name: str, error_message: str):
        """Handle job failed event."""
        self._update_queue_display()
        self.window.update_job_progress("", 0)
        self.window.update_status(f"Failed: {job_name}")
        # Error already logged by worker

    @Slot()
    def _on_queue_finished(self):
        """Handle queue finished event."""
        self.window.set_queue_running(False)
        self.window.update_status("All jobs completed")
        self.window.update_job_progress("", 0)
        self._update_queue_display()

    # Helper methods

    def _update_queue_display(self):
        """Update the queue table with current jobs."""
        jobs = self.queue_manager.get_all_jobs()
        self.window.update_queue_table(jobs)
