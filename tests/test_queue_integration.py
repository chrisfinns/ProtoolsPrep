"""Integration tests for queue layer components."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.queue import QueueManager, JobExecutor, Job, JobStatus
from src.core.session_spec import SessionSpec
from src.core.exceptions import AppleScriptError


class MockProToolsWorkflow:
    """Mock workflow for integration testing."""

    def __init__(self):
        self.calls = []
        self.fail_job_index: int | None = None  # Fail specific job by index

    def launch(self) -> None:
        self.calls.append("launch")

    def create_session(
        self, name: str, sample_rate: int, bit_depth: int, output_dir: Path
    ) -> None:
        self.calls.append(("create_session", name))
        # Check if should fail for this job
        if self.fail_job_index is not None:
            session_count = sum(1 for call in self.calls if isinstance(call, tuple) and call[0] == "create_session")
            if session_count - 1 == self.fail_job_index:
                raise AppleScriptError(f"Mock failure for job {self.fail_job_index}")

    def import_audio(self, files: list[Path]) -> None:
        self.calls.append("import_audio")

    def import_midi(self, files: list[Path]) -> None:
        self.calls.append("import_midi")

    def import_template(self, template_path: Path) -> None:
        self.calls.append("import_template")

    def save_session(self, session_file: Path) -> None:
        self.calls.append("save_session")

    def close_session(self) -> None:
        self.calls.append("close_session")


@pytest.mark.integration
class TestQueueIntegration:
    """Integration tests for queue and executor working together."""

    @pytest.fixture
    def queue_manager(self):
        """Create queue manager."""
        return QueueManager()

    @pytest.fixture
    def mock_workflow(self):
        """Create mock workflow."""
        return MockProToolsWorkflow()

    @pytest.fixture
    def executor(self, mock_workflow):
        """Create job executor with mock workflow."""
        return JobExecutor(workflow=mock_workflow)

    @pytest.fixture
    def three_jobs(self, tmp_path):
        """Create three test jobs."""
        jobs = []
        for i in range(3):
            output_dir = tmp_path / f"Artist{i}" / f"Song{i}"
            session_file = output_dir / f"Song{i}.ptx"

            audio_file = tmp_path / f"audio{i}.wav"
            audio_file.touch()

            spec = SessionSpec(
                sample_rate=44100,
                bit_depth=16,
                audio_files=[audio_file],
                midi_files=[],
                output_dir=output_dir,
                session_file=session_file,
                artist=f"Artist {i}",
                song_name=f"Song {i}",
            )
            jobs.append(Job(spec=spec))

        return jobs

    def test_queue_to_executor_serial_flow(
        self, queue_manager, executor, mock_workflow, three_jobs
    ):
        """Add multiple jobs to queue and execute serially."""
        # Add all jobs to queue
        for job in three_jobs:
            queue_manager.add(job)

        assert queue_manager.size() == 3

        # Execute jobs one at a time
        executed_jobs = []

        while not queue_manager.is_empty():
            # Get next job
            job = queue_manager.get_next()
            assert job is not None
            assert queue_manager.has_running_job()

            # Execute job
            executor.execute(job)
            executed_jobs.append(job)

            # Mark as completed
            queue_manager.complete_current()
            assert not queue_manager.has_running_job()

        # Verify all jobs completed
        assert len(executed_jobs) == 3
        assert all(job.status == JobStatus.COMPLETED for job in executed_jobs)
        assert all(job.progress == 100 for job in executed_jobs)

        # Verify serial execution (each job went through full workflow)
        create_session_calls = [
            call for call in mock_workflow.calls
            if isinstance(call, tuple) and call[0] == "create_session"
        ]
        assert len(create_session_calls) == 3

        # Verify jobs executed in FIFO order
        assert executed_jobs[0] == three_jobs[0]
        assert executed_jobs[1] == three_jobs[1]
        assert executed_jobs[2] == three_jobs[2]

    def test_error_recovery_continues_queue(
        self, queue_manager, mock_workflow, three_jobs
    ):
        """Queue continues after job failure."""
        # Make second job fail
        mock_workflow.fail_job_index = 1

        executor = JobExecutor(workflow=mock_workflow)

        # Add all jobs to queue
        for job in three_jobs:
            queue_manager.add(job)

        executed_jobs = []
        failed_jobs = []

        # Execute jobs
        while not queue_manager.is_empty():
            job = queue_manager.get_next()

            try:
                executor.execute(job)
                executed_jobs.append(job)
                queue_manager.complete_current()
            except Exception:
                failed_jobs.append(job)
                queue_manager.fail_current(job.error_message or "Unknown error")

        # Verify job 0 completed
        assert three_jobs[0].status == JobStatus.COMPLETED
        assert three_jobs[0].progress == 100

        # Verify job 1 failed
        assert three_jobs[1].status == JobStatus.FAILED
        assert three_jobs[1].error_message is not None

        # Verify job 2 completed (queue continued after failure)
        assert three_jobs[2].status == JobStatus.COMPLETED
        assert three_jobs[2].progress == 100

        assert len(executed_jobs) == 2  # Jobs 0 and 2
        assert len(failed_jobs) == 1  # Job 1

    def test_progress_tracking_through_workflow(
        self, queue_manager, mock_workflow, three_jobs
    ):
        """Progress is tracked correctly throughout execution."""
        progress_updates = []

        def track_progress(progress_pct: int, message: str):
            progress_updates.append((progress_pct, message))

        executor = JobExecutor(
            workflow=mock_workflow, progress_callback=track_progress
        )

        # Add first job only
        queue_manager.add(three_jobs[0])
        job = queue_manager.get_next()

        executor.execute(job)
        queue_manager.complete_current()

        # Verify progress updates
        assert len(progress_updates) > 0

        # Extract progress percentages
        progress_values = [update[0] for update in progress_updates]

        # Progress should start at 5% (validate step)
        assert progress_values[0] == 5

        # Progress should end at 100%
        assert progress_values[-1] == 100

        # Progress should be monotonically increasing
        for i in range(len(progress_values) - 1):
            assert progress_values[i] <= progress_values[i + 1]

    def test_get_all_jobs_during_execution(
        self, queue_manager, executor, three_jobs
    ):
        """get_all_jobs returns current + pending during execution."""
        # Add all jobs
        for job in three_jobs:
            queue_manager.add(job)

        # Get first job as current
        job = queue_manager.get_next()

        # Check all jobs snapshot
        all_jobs = queue_manager.get_all_jobs()
        assert len(all_jobs) == 3
        assert all_jobs[0] == three_jobs[0]  # Current job first
        assert all_jobs[1] == three_jobs[1]  # Pending
        assert all_jobs[2] == three_jobs[2]  # Pending

        # Complete first job
        executor.execute(job)
        queue_manager.complete_current()

        # Check remaining jobs
        all_jobs = queue_manager.get_all_jobs()
        assert len(all_jobs) == 2
        assert all_jobs[0] == three_jobs[1]
        assert all_jobs[1] == three_jobs[2]

    def test_clear_queue_during_execution(
        self, queue_manager, executor, three_jobs
    ):
        """Clear queue removes pending but not current job."""
        # Add all jobs
        for job in three_jobs:
            queue_manager.add(job)

        # Get first job as current
        current_job = queue_manager.get_next()
        assert queue_manager.size() == 2  # Two pending

        # Clear pending jobs
        removed = queue_manager.clear()
        assert removed == 2
        assert queue_manager.size() == 0
        assert queue_manager.has_running_job()

        # Current job can still execute
        executor.execute(current_job)
        queue_manager.complete_current()

        assert current_job.status == JobStatus.COMPLETED

    def test_remove_pending_job_during_execution(
        self, queue_manager, three_jobs
    ):
        """Can remove pending job while another is executing."""
        # Add all jobs
        for job in three_jobs:
            queue_manager.add(job)

        # Get first job as current
        queue_manager.get_next()

        # Try to remove pending job
        removed = queue_manager.remove(three_jobs[1].job_id)
        assert removed is True
        assert queue_manager.size() == 1

        # Try to remove current job (should fail)
        removed = queue_manager.remove(three_jobs[0].job_id)
        assert removed is False

    def test_job_timestamps_updated_correctly(
        self, queue_manager, executor, three_jobs
    ):
        """Job timestamps are set correctly during execution."""
        job = three_jobs[0]

        # Initial state
        assert job.queued_at is not None
        assert job.started_at is None
        assert job.completed_at is None

        # Add and execute
        queue_manager.add(job)
        queue_manager.get_next()
        executor.execute(job)

        # After execution
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.duration is not None
        assert job.duration > 0

        # Timestamps should be in order
        assert job.queued_at <= job.started_at
        assert job.started_at <= job.completed_at

    def test_mixed_job_types_execute_correctly(self, queue_manager, executor, tmp_path):
        """Jobs with different file types execute correctly."""
        # Job 1: Audio only
        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        spec1 = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[],
            output_dir=tmp_path / "Job1",
            session_file=tmp_path / "Job1" / "Song.ptx",
            artist="Artist",
            song_name="Audio Only",
        )
        job1 = Job(spec=spec1)

        # Job 2: MIDI only
        midi_file = tmp_path / "midi.mid"
        midi_file.touch()

        spec2 = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[],
            midi_files=[midi_file],
            output_dir=tmp_path / "Job2",
            session_file=tmp_path / "Job2" / "Song.ptx",
            artist="Artist",
            song_name="MIDI Only",
        )
        job2 = Job(spec=spec2)

        # Job 3: Both audio and MIDI
        spec3 = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[midi_file],
            output_dir=tmp_path / "Job3",
            session_file=tmp_path / "Job3" / "Song.ptx",
            artist="Artist",
            song_name="Both",
        )
        job3 = Job(spec=spec3)

        # Add all jobs
        for job in [job1, job2, job3]:
            queue_manager.add(job)

        # Execute all jobs
        while not queue_manager.is_empty():
            job = queue_manager.get_next()
            executor.execute(job)
            queue_manager.complete_current()

        # Verify all completed
        assert job1.status == JobStatus.COMPLETED
        assert job2.status == JobStatus.COMPLETED
        assert job3.status == JobStatus.COMPLETED
