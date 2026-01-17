"""Tests for Job model."""

import time
import pytest
from pathlib import Path
from datetime import datetime

from src.queue.job import Job, JobStatus
from src.core.session_spec import SessionSpec


class TestJob:
    """Test suite for Job model."""

    @pytest.fixture
    def valid_spec(self, tmp_path):
        """Create valid SessionSpec for job testing."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        return SessionSpec(
            sample_rate=44100,
            bit_depth=16,
            audio_files=[audio_file],
            midi_files=[],
            output_dir=output_dir,
            session_file=session_file,
            artist="Test Artist",
            song_name="Test Song",
        )

    def test_create_job_with_spec(self, valid_spec):
        """Job can be created with valid SessionSpec."""
        job = Job(spec=valid_spec)

        assert job.spec == valid_spec
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.job_id is not None
        assert job.queued_at is not None

    def test_default_status_is_pending(self, valid_spec):
        """New job has PENDING status by default."""
        job = Job(spec=valid_spec)
        assert job.status == JobStatus.PENDING

    def test_display_name_property(self, valid_spec):
        """display_name property formats as 'Artist - Song'."""
        job = Job(spec=valid_spec)
        assert job.display_name == "Test Artist - Test Song"

    def test_is_finished_detects_completed(self, valid_spec):
        """is_finished returns True for COMPLETED status."""
        job = Job(spec=valid_spec)
        job.status = JobStatus.COMPLETED

        assert job.is_finished is True

    def test_is_finished_detects_failed(self, valid_spec):
        """is_finished returns True for FAILED status."""
        job = Job(spec=valid_spec)
        job.status = JobStatus.FAILED

        assert job.is_finished is True

    def test_is_finished_false_for_pending(self, valid_spec):
        """is_finished returns False for PENDING status."""
        job = Job(spec=valid_spec)
        job.status = JobStatus.PENDING

        assert job.is_finished is False

    def test_is_finished_false_for_running(self, valid_spec):
        """is_finished returns False for RUNNING status."""
        job = Job(spec=valid_spec)
        job.status = JobStatus.RUNNING

        assert job.is_finished is False

    def test_duration_none_when_not_started(self, valid_spec):
        """duration returns None if job hasn't started."""
        job = Job(spec=valid_spec)
        assert job.duration is None

    def test_duration_calculated_for_running_job(self, valid_spec):
        """duration returns elapsed time for running job."""
        job = Job(spec=valid_spec)
        job.started_at = datetime.now()

        # Small delay to ensure measurable duration
        time.sleep(0.01)

        duration = job.duration
        assert duration is not None
        assert duration > 0

    def test_duration_calculated_for_completed_job(self, valid_spec):
        """duration returns total time for completed job."""
        job = Job(spec=valid_spec)
        job.started_at = datetime.now()
        time.sleep(0.01)
        job.completed_at = datetime.now()

        duration = job.duration
        assert duration is not None
        assert duration > 0

    def test_status_transitions(self, valid_spec):
        """Job status can transition through workflow states."""
        job = Job(spec=valid_spec)

        # PENDING -> RUNNING
        assert job.status == JobStatus.PENDING
        job.status = JobStatus.RUNNING
        assert job.status == JobStatus.RUNNING

        # RUNNING -> COMPLETED
        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED

    def test_status_transition_to_failed(self, valid_spec):
        """Job status can transition to FAILED with error message."""
        job = Job(spec=valid_spec)
        job.status = JobStatus.RUNNING
        job.error_message = "Something went wrong"
        job.status = JobStatus.FAILED

        assert job.status == JobStatus.FAILED
        assert job.error_message == "Something went wrong"

    def test_job_id_is_unique(self, valid_spec):
        """Each job gets a unique job_id."""
        job1 = Job(spec=valid_spec)
        job2 = Job(spec=valid_spec)

        assert job1.job_id != job2.job_id

    def test_spec_reference_is_immutable(self, valid_spec):
        """Job holds reference to immutable SessionSpec."""
        job = Job(spec=valid_spec)

        # SessionSpec is frozen, so this should fail
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            job.spec.artist = "Modified Artist"
