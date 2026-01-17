"""9-step workflow coordinator for job execution."""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Protocol

from src.core.exceptions import JobExecutionError, ValidationError
from .job import Job, JobStatus


class ProToolsWorkflowProtocol(Protocol):
    """
    Interface for Pro Tools automation (can be mocked for testing).

    This protocol defines the contract for Pro Tools operations without
    requiring the actual implementation. Enables testing JobExecutor
    without Pro Tools installed.
    """

    def launch(self) -> None:
        """Launch Pro Tools and wait for ready state."""
        ...

    def create_session(
        self, name: str, sample_rate: int, bit_depth: int, output_dir: Path
    ) -> None:
        """Create new session with specified parameters."""
        ...

    def import_audio(self, files: list[Path]) -> None:
        """Import audio files (with Apply SRC disabled)."""
        ...

    def import_midi(self, files: list[Path]) -> None:
        """Import MIDI files with tempo/key import enabled."""
        ...

    def import_template(self, template_path: Path) -> None:
        """Import session data from template (with Apply SRC disabled)."""
        ...

    def save_session(self, session_file: Path) -> None:
        """Save session to specified file path."""
        ...

    def close_session(self) -> None:
        """Close current session."""
        ...


# Type alias for progress callback
ProgressCallback = Callable[[int, str], None]


class JobExecutor:
    """
    9-step workflow coordinator.

    Orchestrates the complete Pro Tools session creation workflow with
    progress callbacks for UI updates. Each step updates job status
    and progress percentage.

    Workflow Steps:
        1. Validate (5%): Check SessionSpec for errors
        2. Create Dir (10%): Make output folder structure
        3. Launch (20%): Activate Pro Tools, wait for Dashboard
        4. Create Session (30%): Use Dashboard with detected specs
        5. Import Audio (50%): File → Import → Audio, disable SRC
        6. Import MIDI (70%): File → Import → MIDI
        7. Import Template (85%): File → Import → Session Data
        8. Save (95%): File → Save Session
        9. Complete (100%): Close session

    Steps are skipped if not applicable (e.g., no audio files = skip step 5).
    Progress bar always reaches 100% even when steps are skipped.
    """

    # Progress percentage for each step
    STEP_PROGRESS = {
        "validate": 5,
        "create_dir": 10,
        "launch": 20,
        "create_session": 30,
        "import_audio": 50,
        "import_midi": 70,
        "import_template": 85,
        "save": 95,
        "complete": 100,
    }

    def __init__(
        self,
        workflow: ProToolsWorkflowProtocol,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        """
        Initialize executor with workflow implementation and callback.

        Args:
            workflow: Pro Tools workflow implementation (or mock for testing)
            progress_callback: Optional callback for progress updates (progress_pct, message)
        """
        self._workflow = workflow
        self._progress_callback = progress_callback

    def execute(self, job: Job) -> None:
        """
        Execute complete 9-step workflow (mutates job status/progress).

        Updates job.status, job.progress, job.started_at, job.completed_at.
        On error, calls cleanup and marks job as FAILED.

        Args:
            job: Job to execute (will be mutated)

        Raises:
            JobExecutionError: If any step fails
        """
        try:
            # Mark job as started
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()

            # Execute workflow steps
            self._step_validate(job)
            self._step_create_dir(job)
            self._step_launch(job)
            self._step_create_session(job)
            self._step_import_audio(job)
            self._step_import_midi(job)
            self._step_import_template(job)
            self._step_save(job)
            self._step_complete(job)

            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()

        except Exception as error:
            self._cleanup_on_error(job, error)
            raise JobExecutionError(f"Job execution failed: {error}") from error

    def _step_validate(self, job: Job) -> None:
        """
        Step 1: Validate SessionSpec (5%).

        Checks that all required files exist and are accessible.

        Raises:
            ValidationError: If validation fails
        """
        self._update_progress(job, self.STEP_PROGRESS["validate"], "Validating session specification")

        # Check audio files exist
        for audio_file in job.spec.audio_files:
            if not audio_file.exists():
                raise ValidationError(f"Audio file not found: {audio_file}")

        # Check MIDI files exist
        for midi_file in job.spec.midi_files:
            if not midi_file.exists():
                raise ValidationError(f"MIDI file not found: {midi_file}")

        # Check template exists if specified
        if job.spec.has_template and not job.spec.template_path.exists():
            raise ValidationError(f"Template file not found: {job.spec.template_path}")

    def _step_create_dir(self, job: Job) -> None:
        """Step 2: Create output directory (10%)."""
        self._update_progress(job, self.STEP_PROGRESS["create_dir"], "Creating output directory")

        try:
            job.spec.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise JobExecutionError(f"Failed to create output directory: {e}") from e

    def _step_launch(self, job: Job) -> None:
        """Step 3: Launch Pro Tools (20%)."""
        self._update_progress(job, self.STEP_PROGRESS["launch"], "Launching Pro Tools")
        self._workflow.launch()

    def _step_create_session(self, job: Job) -> None:
        """Step 4: Create session (30%)."""
        self._update_progress(
            job,
            self.STEP_PROGRESS["create_session"],
            f"Creating session: {job.spec.session_name}",
        )
        self._workflow.create_session(
            name=job.spec.session_name,
            sample_rate=job.spec.sample_rate,
            bit_depth=job.spec.bit_depth,
            output_dir=job.spec.output_dir,
        )

    def _step_import_audio(self, job: Job) -> None:
        """Step 5: Import audio files (50%) - skip if no audio."""
        if not job.spec.has_audio:
            self._update_progress(job, self.STEP_PROGRESS["import_audio"], "Skipping audio import (no audio files)")
            return

        self._update_progress(
            job,
            self.STEP_PROGRESS["import_audio"],
            f"Importing {len(job.spec.audio_files)} audio file(s)",
        )
        self._workflow.import_audio(list(job.spec.audio_files))

    def _step_import_midi(self, job: Job) -> None:
        """Step 6: Import MIDI files (70%) - skip if no MIDI."""
        if not job.spec.has_midi:
            self._update_progress(job, self.STEP_PROGRESS["import_midi"], "Skipping MIDI import (no MIDI files)")
            return

        self._update_progress(
            job,
            self.STEP_PROGRESS["import_midi"],
            f"Importing {len(job.spec.midi_files)} MIDI file(s)",
        )
        self._workflow.import_midi(list(job.spec.midi_files))

    def _step_import_template(self, job: Job) -> None:
        """Step 7: Import template (85%) - skip if no template."""
        if not job.spec.has_template:
            self._update_progress(job, self.STEP_PROGRESS["import_template"], "Skipping template import (no template)")
            return

        self._update_progress(
            job,
            self.STEP_PROGRESS["import_template"],
            f"Importing template: {job.spec.template_path.name}",
        )
        self._workflow.import_template(job.spec.template_path)

    def _step_save(self, job: Job) -> None:
        """Step 8: Save session (95%)."""
        self._update_progress(job, self.STEP_PROGRESS["save"], "Saving session")
        self._workflow.save_session(job.spec.session_file)

    def _step_complete(self, job: Job) -> None:
        """Step 9: Complete (100%)."""
        self._update_progress(job, self.STEP_PROGRESS["complete"], "Job complete")
        self._workflow.close_session()

    def _cleanup_on_error(self, job: Job, error: Exception) -> None:
        """
        Attempt cleanup after error, mark job as failed.

        Tries to close session gracefully. If cleanup fails, logs error
        but doesn't raise (original error is more important).

        Args:
            job: Job that failed
            error: Original exception that caused failure
        """
        job.status = JobStatus.FAILED
        job.error_message = str(error)
        job.completed_at = datetime.now()

        # Attempt to close session (best effort)
        try:
            self._workflow.close_session()
        except Exception:
            # Cleanup failure is secondary to original error
            pass

    def _update_progress(self, job: Job, progress: int, message: str) -> None:
        """
        Update job progress and invoke callback.

        Args:
            job: Job to update
            progress: Progress percentage (0-100)
            message: Status message describing current step
        """
        job.progress = progress

        if self._progress_callback:
            self._progress_callback(progress, message)
