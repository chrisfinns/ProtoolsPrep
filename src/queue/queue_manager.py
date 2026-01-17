"""Thread-safe queue manager for serial job execution."""

from collections import deque
from threading import Lock
from typing import Optional

from .job import Job, JobStatus


class QueueManager:
    """
    Serial job execution queue (Pro Tools constraint: one at a time).

    Uses deque + Lock instead of queue.Queue for simpler, more explicit control.
    No blocking operations needed since execution is strictly serial.

    Thread Safety: All public methods use lock for atomic operations.
    """

    def __init__(self):
        """Initialize empty queue."""
        self._queue: deque[Job] = deque()
        self._lock = Lock()
        self._current_job: Optional[Job] = None  # Separate from queue

    def add(self, job: Job) -> None:
        """
        Add job to end of queue (FIFO).

        Args:
            job: Job to add to queue
        """
        with self._lock:
            self._queue.append(job)

    def remove(self, job_id: str) -> bool:
        """
        Remove pending job from queue.

        Cannot remove currently executing job.

        Args:
            job_id: Unique identifier of job to remove

        Returns:
            True if job was removed, False if not found or is current job
        """
        with self._lock:
            # Cannot remove current job
            if self._current_job and self._current_job.job_id == job_id:
                return False

            # Search and remove from pending queue
            for i, job in enumerate(self._queue):
                if job.job_id == job_id:
                    del self._queue[i]
                    return True

            return False

    def clear(self) -> int:
        """
        Clear all pending jobs (not current).

        Returns:
            Number of jobs removed
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def get_next(self) -> Optional[Job]:
        """
        Pop next job from queue and mark as current.

        Returns:
            Next job to execute, or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None

            job = self._queue.popleft()
            self._current_job = job
            return job

    def get_current(self) -> Optional[Job]:
        """
        Get currently executing job.

        Returns:
            Current job or None if no job is executing
        """
        with self._lock:
            return self._current_job

    def complete_current(self) -> None:
        """Mark current job as completed and clear current slot."""
        with self._lock:
            if self._current_job:
                self._current_job.status = JobStatus.COMPLETED
                self._current_job = None

    def fail_current(self, error_message: str) -> None:
        """
        Mark current job as failed and clear current slot.

        Args:
            error_message: Error description to store in job
        """
        with self._lock:
            if self._current_job:
                self._current_job.status = JobStatus.FAILED
                self._current_job.error_message = error_message
                self._current_job = None

    def get_all_jobs(self) -> list[Job]:
        """
        Get snapshot of all jobs (pending + current).

        Returns:
            List of all jobs in order: [current] + [pending...]
        """
        with self._lock:
            all_jobs = []
            if self._current_job:
                all_jobs.append(self._current_job)
            all_jobs.extend(self._queue)
            return all_jobs

    def size(self) -> int:
        """
        Count pending jobs (excludes current).

        Returns:
            Number of jobs in queue
        """
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """
        Check if queue has no pending jobs.

        Returns:
            True if no pending jobs, False otherwise
        """
        with self._lock:
            return len(self._queue) == 0

    def has_running_job(self) -> bool:
        """
        Check if job currently executing.

        Returns:
            True if a job is running, False otherwise
        """
        with self._lock:
            return self._current_job is not None
