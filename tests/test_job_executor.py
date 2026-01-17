"""Tests for JobExecutor."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.queue.job_executor import JobExecutor
from src.queue.job import Job, JobStatus
from src.core.session_spec import SessionSpec
from src.core.exceptions import JobExecutionError, ValidationError, AppleScriptError


class MockProToolsWorkflow:
    """Test double for ProToolsWorkflow (implements ProToolsWorkflowProtocol)."""

    def __init__(self):
        """Initialize mock workflow with call tracking."""
        self.calls = []  # Track method calls
        self.should_fail_on: str | None = None  # Inject failures at specific steps

    def launch(self) -> None:
        """Mock launch Pro Tools."""
        self.calls.append("launch")
        if self.should_fail_on == "launch":
            raise AppleScriptError("Mock launch failure")

    def create_session(
        self, name: str, sample_rate: int, bit_depth: int, output_dir: Path
    ) -> None:
        """Mock create session."""
        self.calls.append(("create_session", name, sample_rate, bit_depth, output_dir))
        if self.should_fail_on == "create_session":
            raise AppleScriptError("Mock create session failure")

    def import_audio(self, files: list[Path]) -> None:
        """Mock import audio."""
        self.calls.append(("import_audio", files))
        if self.should_fail_on == "import_audio":
            raise AppleScriptError("Mock import audio failure")

    def import_midi(self, files: list[Path]) -> None:
        """Mock import MIDI."""
        self.calls.append(("import_midi", files))
        if self.should_fail_on == "import_midi":
            raise AppleScriptError("Mock import MIDI failure")

    def import_template(self, template_path: Path) -> None:
        """Mock import template."""
        self.calls.append(("import_template", template_path))
        if self.should_fail_on == "import_template":
            raise AppleScriptError("Mock import template failure")

    def save_session(self, session_file: Path) -> None:
        """Mock save session."""
        self.calls.append(("save_session", session_file))
        if self.should_fail_on == "save_session":
            raise AppleScriptError("Mock save session failure")

    def close_session(self) -> None:
        """Mock close session."""
        self.calls.append("close_session")
        if self.should_fail_on == "close_session":
            raise AppleScriptError("Mock close session failure")


class TestJobExecutor:
    """Test suite for JobExecutor."""

    @pytest.fixture
    def mock_workflow(self):
        """Create mock workflow."""
        return MockProToolsWorkflow()

    @pytest.fixture
    def progress_callback(self):
        """Create mock progress callback."""
        return MagicMock()

    @pytest.fixture
    def executor(self, mock_workflow, progress_callback):
        """Create JobExecutor with mock workflow and callback."""
        return JobExecutor(workflow=mock_workflow, progress_callback=progress_callback)

    @pytest.fixture
    def full_job(self, tmp_path):
        """Create job with audio, MIDI, and template."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        midi_file = tmp_path / "midi.mid"
        midi_file.touch()

        template_file = tmp_path / "template.ptx"
        template_file.touch()

        spec = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[midi_file],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
            template_path=template_file,
        )
        return Job(spec=spec)

    @pytest.fixture
    def audio_only_job(self, tmp_path):
        """Create job with only audio files."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        spec = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
        )
        return Job(spec=spec)

    @pytest.fixture
    def midi_only_job(self, tmp_path):
        """Create job with only MIDI files."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        midi_file = tmp_path / "midi.mid"
        midi_file.touch()

        spec = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[],
            midi_files=[midi_file],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
        )
        return Job(spec=spec)

    def test_execute_all_steps_successfully(self, executor, mock_workflow, full_job):
        """Execute all 9 steps successfully with full job."""
        executor.execute(full_job)

        # Verify job status
        assert full_job.status == JobStatus.COMPLETED
        assert full_job.progress == 100
        assert full_job.started_at is not None
        assert full_job.completed_at is not None

        # Verify all workflow methods called
        assert "launch" in mock_workflow.calls
        assert any("create_session" in str(call) for call in mock_workflow.calls)
        assert any("import_audio" in str(call) for call in mock_workflow.calls)
        assert any("import_midi" in str(call) for call in mock_workflow.calls)
        assert any("import_template" in str(call) for call in mock_workflow.calls)
        assert any("save_session" in str(call) for call in mock_workflow.calls)
        assert "close_session" in mock_workflow.calls

    def test_execute_audio_only_skips_midi(self, executor, mock_workflow, audio_only_job):
        """Execute with audio only skips MIDI import."""
        executor.execute(audio_only_job)

        assert audio_only_job.status == JobStatus.COMPLETED
        assert audio_only_job.progress == 100

        # Verify MIDI import was NOT called
        assert not any("import_midi" in str(call) for call in mock_workflow.calls)

        # Verify audio import WAS called
        assert any("import_audio" in str(call) for call in mock_workflow.calls)

    def test_execute_midi_only_skips_audio(self, executor, mock_workflow, midi_only_job):
        """Execute with MIDI only skips audio import."""
        executor.execute(midi_only_job)

        assert midi_only_job.status == JobStatus.COMPLETED
        assert midi_only_job.progress == 100

        # Verify audio import was NOT called
        assert not any("import_audio" in str(call) for call in mock_workflow.calls)

        # Verify MIDI import WAS called
        assert any("import_midi" in str(call) for call in mock_workflow.calls)

    def test_execute_skips_template_if_none(self, executor, mock_workflow, audio_only_job):
        """Execute skips template import if no template provided."""
        executor.execute(audio_only_job)

        assert audio_only_job.status == JobStatus.COMPLETED

        # Verify template import was NOT called
        assert not any("import_template" in str(call) for call in mock_workflow.calls)

    def test_validate_step_catches_missing_audio(self, executor, tmp_path):
        """Validate step detects missing audio files."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        # Create spec with non-existent audio file
        nonexistent_file = tmp_path / "missing.wav"

        spec = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[nonexistent_file],
            midi_files=[],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
        )
        job = Job(spec=spec)

        # Execute should fail during validation
        with pytest.raises(JobExecutionError):
            executor.execute(job)

        assert job.status == JobStatus.FAILED
        assert "not found" in job.error_message.lower()

    def test_validate_step_catches_missing_midi(self, executor, tmp_path):
        """Validate step detects missing MIDI files."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        # Create spec with non-existent MIDI file
        nonexistent_midi = tmp_path / "missing.mid"

        spec = SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[nonexistent_midi],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
        )
        job = Job(spec=spec)

        # Execute should fail during validation
        with pytest.raises(JobExecutionError):
            executor.execute(job)

        assert job.status == JobStatus.FAILED

    def test_progress_callback_invoked_at_each_step(
        self, mock_workflow, progress_callback, full_job
    ):
        """Progress callback is invoked at each workflow step."""
        executor = JobExecutor(workflow=mock_workflow, progress_callback=progress_callback)
        executor.execute(full_job)

        # Verify callback was called multiple times
        assert progress_callback.call_count >= 9  # At least 9 steps

        # Verify progress percentages increase
        call_args = [call[0] for call in progress_callback.call_args_list]
        progress_values = [args[0] for args in call_args]

        # Progress should increase monotonically
        for i in range(len(progress_values) - 1):
            assert progress_values[i] <= progress_values[i + 1]

        # Final progress should be 100
        assert progress_values[-1] == 100

    def test_cleanup_on_error_attempts_close(self, mock_workflow, full_job):
        """Cleanup on error attempts to close session."""
        # Make workflow fail at create_session step
        mock_workflow.should_fail_on = "create_session"

        executor = JobExecutor(workflow=mock_workflow)

        with pytest.raises(JobExecutionError):
            executor.execute(full_job)

        # Verify job marked as failed
        assert full_job.status == JobStatus.FAILED
        assert full_job.error_message is not None

        # Verify close_session was called during cleanup
        assert "close_session" in mock_workflow.calls

    def test_job_status_updated_throughout_execution(self, executor, full_job):
        """Job status transitions through PENDING -> RUNNING -> COMPLETED."""
        assert full_job.status == JobStatus.PENDING

        executor.execute(full_job)

        assert full_job.status == JobStatus.COMPLETED

    def test_error_at_launch_step(self, mock_workflow, full_job):
        """Error at launch step marks job as failed."""
        mock_workflow.should_fail_on = "launch"
        executor = JobExecutor(workflow=mock_workflow)

        with pytest.raises(JobExecutionError):
            executor.execute(full_job)

        assert full_job.status == JobStatus.FAILED
        assert "launch" in full_job.error_message.lower()

    def test_error_at_import_audio_step(self, mock_workflow, full_job):
        """Error at import audio step marks job as failed."""
        mock_workflow.should_fail_on = "import_audio"
        executor = JobExecutor(workflow=mock_workflow)

        with pytest.raises(JobExecutionError):
            executor.execute(full_job)

        assert full_job.status == JobStatus.FAILED

    def test_error_at_save_step(self, mock_workflow, full_job):
        """Error at save step marks job as failed."""
        mock_workflow.should_fail_on = "save_session"
        executor = JobExecutor(workflow=mock_workflow)

        with pytest.raises(JobExecutionError):
            executor.execute(full_job)

        assert full_job.status == JobStatus.FAILED

    def test_step_progress_percentages(self):
        """Verify step progress percentages are correctly defined."""
        assert JobExecutor.STEP_PROGRESS["validate"] == 5
        assert JobExecutor.STEP_PROGRESS["create_dir"] == 10
        assert JobExecutor.STEP_PROGRESS["launch"] == 20
        assert JobExecutor.STEP_PROGRESS["create_session"] == 30
        assert JobExecutor.STEP_PROGRESS["import_audio"] == 50
        assert JobExecutor.STEP_PROGRESS["import_midi"] == 70
        assert JobExecutor.STEP_PROGRESS["import_template"] == 85
        assert JobExecutor.STEP_PROGRESS["save"] == 95
        assert JobExecutor.STEP_PROGRESS["complete"] == 100

    def test_create_session_receives_correct_params(
        self, executor, mock_workflow, full_job
    ):
        """create_session receives correct parameters from SessionSpec."""
        executor.execute(full_job)

        # Find the create_session call
        create_call = next(
            call for call in mock_workflow.calls if isinstance(call, tuple) and call[0] == "create_session"
        )

        _, name, sample_rate, bit_depth, output_dir = create_call

        assert name == "Song"  # session_name is the file stem
        assert sample_rate == 44100
        assert bit_depth == 16
        assert output_dir == full_job.spec.output_dir

    def test_import_audio_receives_correct_files(
        self, executor, mock_workflow, full_job
    ):
        """import_audio receives correct file list from SessionSpec."""
        executor.execute(full_job)

        # Find the import_audio call
        audio_call = next(
            call for call in mock_workflow.calls if isinstance(call, tuple) and call[0] == "import_audio"
        )

        _, files = audio_call
        assert files == list(full_job.spec.audio_files)

    def test_save_session_receives_correct_path(
        self, executor, mock_workflow, full_job
    ):
        """save_session receives correct session file path."""
        executor.execute(full_job)

        # Find the save_session call
        save_call = next(
            call for call in mock_workflow.calls if isinstance(call, tuple) and call[0] == "save_session"
        )

        _, session_file = save_call
        assert session_file == full_job.spec.session_file
