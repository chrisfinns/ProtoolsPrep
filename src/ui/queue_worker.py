"""Queue worker thread for executing Pro Tools session jobs in background.

This QThread runs the queue execution loop, emitting signals for UI updates.
All UI updates must happen via signals to ensure thread safety.
"""

import logging
from typing import Callable

from PySide6.QtCore import QThread, Signal

from src.core.exceptions import PTSessionBuilderError
from src.protools.settings import AppSettings
from src.protools.workflow import ProToolsWorkflow
from src.queue.job import Job
from src.queue.job_executor import JobExecutor
from src.queue.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class QueueWorker(QThread):
    """Worker thread for executing jobs from the queue.

    Runs in background and emits signals for thread-safe UI updates.
    """

    # Signals for UI updates
    job_started = Signal(str)  # job_name
    job_progress = Signal(str, int, str)  # job_name, progress_percent, status_message
    job_completed = Signal(str)  # job_name
    job_failed = Signal(str, str)  # job_name, error_message
    queue_finished = Signal()
    log_message = Signal(str)

    def __init__(self, queue_manager: QueueManager):
        super().__init__()
        self.queue_manager = queue_manager
        self.settings = AppSettings()
        self.workflow = ProToolsWorkflow(self.settings)
        self._should_stop = False

    def run(self):
        """Execute jobs from queue until empty or stopped."""
        self._should_stop = False
        self.log_message.emit("Queue execution started")

        try:
            while not self._should_stop:
                # Get next job from queue
                current_job = self.queue_manager.get_next()

                if current_job is None:
                    # Queue is empty
                    self.log_message.emit("Queue is empty")
                    break

                # Execute the job
                self._execute_job(current_job)

                # Check if we should stop between jobs
                if self._should_stop:
                    self.log_message.emit("Queue execution paused by user")
                    break

            # Queue finished normally
            if not self._should_stop:
                self.log_message.emit("All jobs completed")
                self.queue_finished.emit()

        except Exception as e:
            logger.exception("Unexpected error in queue worker")
            self.log_message.emit(f"FATAL ERROR: {str(e)}")

    def _execute_job(self, job: Job):
        """Execute a single job with progress callbacks."""
        job_name = job.display_name
        self.log_message.emit(f"Starting: {job_name}")
        self.job_started.emit(job_name)

        try:
            # Create progress callback
            def progress_callback(progress: int, message: str):
                if not self._should_stop:
                    self.job_progress.emit(job_name, progress, message)
                    self.log_message.emit(f"[{progress}%] {message}")

            # Create executor with progress callback for this job
            executor = JobExecutor(self.workflow, progress_callback)

            # Execute the job
            executor.execute(job)

            # Mark as completed
            self.queue_manager.complete_current()
            self.log_message.emit(f"Completed: {job_name}")
            self.job_completed.emit(job_name)

        except PTSessionBuilderError as e:
            # Known error - user-friendly message
            error_msg = str(e)
            self.queue_manager.fail_current(error_msg)
            self.log_message.emit(f"Failed: {job_name} - {error_msg}")
            self.job_failed.emit(job_name, error_msg)

        except Exception as e:
            # Unexpected error - log full details
            logger.exception(f"Unexpected error executing job: {job_name}")
            error_msg = f"Unexpected error: {str(e)}"
            self.queue_manager.fail_current(error_msg)
            self.log_message.emit(f"Failed: {job_name} - {error_msg}")
            self.job_failed.emit(job_name, error_msg)

    def stop(self):
        """Request worker to stop after current job."""
        self._should_stop = True
        self.log_message.emit("Stop requested - will pause after current job")
