"""Job model for queue execution."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from src.core.session_spec import SessionSpec


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """
    Runtime state for queued job (wraps immutable SessionSpec).

    Job represents mutable runtime execution state (status, progress, timestamps)
    while SessionSpec represents immutable specification (what to build).

    This follows the Core Layer pattern: SessionSpec is frozen (immutable facts),
    but Job is mutable (runtime state that changes during execution).
    """

    # Immutable reference to session specification
    spec: SessionSpec

    # Mutable execution state
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100 percentage

    # Error tracking
    error_message: Optional[str] = None

    # Timestamps
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Unique identifier
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_name(self) -> str:
        """Get formatted display name for UI (Artist - Song)."""
        return f"{self.spec.artist} - {self.spec.song_name}"

    @property
    def is_finished(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    @property
    def duration(self) -> Optional[float]:
        """
        Get execution duration in seconds.

        Returns:
            Duration in seconds if job has started, None otherwise.
            For running jobs, returns elapsed time so far.
        """
        if not self.started_at:
            return None

        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
