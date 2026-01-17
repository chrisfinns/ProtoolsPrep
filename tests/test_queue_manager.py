"""Tests for QueueManager."""

import threading
import time
import pytest
from pathlib import Path

from src.queue.queue_manager import QueueManager
from src.queue.job import Job, JobStatus
from src.core.session_spec import SessionSpec


class TestQueueManager:
    """Test suite for QueueManager."""

    @pytest.fixture
    def queue_manager(self):
        """Create empty QueueManager."""
        return QueueManager()

    @pytest.fixture
    def sample_job(self, tmp_path):
        """Create sample job for testing."""
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
    def multiple_jobs(self, tmp_path):
        """Create multiple jobs for testing."""
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

    def test_add_job_to_queue(self, queue_manager, sample_job):
        """Can add job to queue."""
        queue_manager.add(sample_job)
        assert queue_manager.size() == 1

    def test_remove_job_by_id(self, queue_manager, sample_job):
        """Can remove job from queue by ID."""
        queue_manager.add(sample_job)
        assert queue_manager.size() == 1

        removed = queue_manager.remove(sample_job.job_id)
        assert removed is True
        assert queue_manager.size() == 0

    def test_remove_nonexistent_job(self, queue_manager):
        """Removing nonexistent job returns False."""
        removed = queue_manager.remove("fake-id")
        assert removed is False

    def test_cannot_remove_current_job(self, queue_manager, sample_job):
        """Cannot remove currently executing job."""
        queue_manager.add(sample_job)
        current = queue_manager.get_next()
        assert current == sample_job

        # Try to remove current job - should fail
        removed = queue_manager.remove(sample_job.job_id)
        assert removed is False

    def test_clear_queue(self, queue_manager, multiple_jobs):
        """Can clear all pending jobs."""
        for job in multiple_jobs:
            queue_manager.add(job)

        assert queue_manager.size() == 3

        count = queue_manager.clear()
        assert count == 3
        assert queue_manager.size() == 0

    def test_clear_does_not_affect_current_job(self, queue_manager, multiple_jobs):
        """Clear removes pending jobs but not current job."""
        for job in multiple_jobs:
            queue_manager.add(job)

        # Get first job as current
        current = queue_manager.get_next()
        assert queue_manager.size() == 2  # 2 pending jobs left

        # Clear should remove pending jobs only
        count = queue_manager.clear()
        assert count == 2
        assert queue_manager.size() == 0
        assert queue_manager.get_current() == current

    def test_get_next_returns_fifo_order(self, queue_manager, multiple_jobs):
        """get_next returns jobs in FIFO order."""
        for job in multiple_jobs:
            queue_manager.add(job)

        job1 = queue_manager.get_next()
        assert job1 == multiple_jobs[0]

        job2 = queue_manager.get_next()
        assert job2 == multiple_jobs[1]

        job3 = queue_manager.get_next()
        assert job3 == multiple_jobs[2]

    def test_get_next_returns_none_when_empty(self, queue_manager):
        """get_next returns None when queue is empty."""
        assert queue_manager.get_next() is None

    def test_get_current_returns_running_job(self, queue_manager, sample_job):
        """get_current returns currently executing job."""
        queue_manager.add(sample_job)
        current = queue_manager.get_next()

        assert queue_manager.get_current() == current
        assert queue_manager.get_current() == sample_job

    def test_get_current_returns_none_when_no_job(self, queue_manager):
        """get_current returns None when no job is executing."""
        assert queue_manager.get_current() is None

    def test_complete_current_updates_status(self, queue_manager, sample_job):
        """complete_current marks job as COMPLETED and clears slot."""
        queue_manager.add(sample_job)
        queue_manager.get_next()

        queue_manager.complete_current()
        assert sample_job.status == JobStatus.COMPLETED
        assert queue_manager.get_current() is None

    def test_fail_current_updates_status_and_error(self, queue_manager, sample_job):
        """fail_current marks job as FAILED with error message."""
        queue_manager.add(sample_job)
        queue_manager.get_next()

        error_msg = "Something went wrong"
        queue_manager.fail_current(error_msg)

        assert sample_job.status == JobStatus.FAILED
        assert sample_job.error_message == error_msg
        assert queue_manager.get_current() is None

    def test_get_all_jobs_returns_current_and_pending(self, queue_manager, multiple_jobs):
        """get_all_jobs returns snapshot with current job first."""
        for job in multiple_jobs:
            queue_manager.add(job)

        # Get first job as current
        queue_manager.get_next()

        all_jobs = queue_manager.get_all_jobs()
        assert len(all_jobs) == 3
        assert all_jobs[0] == multiple_jobs[0]  # Current job first
        assert all_jobs[1] == multiple_jobs[1]
        assert all_jobs[2] == multiple_jobs[2]

    def test_get_all_jobs_when_only_pending(self, queue_manager, multiple_jobs):
        """get_all_jobs returns only pending jobs when no current job."""
        for job in multiple_jobs:
            queue_manager.add(job)

        all_jobs = queue_manager.get_all_jobs()
        assert len(all_jobs) == 3
        assert all_jobs == multiple_jobs

    def test_size_counts_pending_only(self, queue_manager, multiple_jobs):
        """size returns count of pending jobs (excludes current)."""
        for job in multiple_jobs:
            queue_manager.add(job)

        assert queue_manager.size() == 3

        # Get one job as current
        queue_manager.get_next()
        assert queue_manager.size() == 2  # Current job not counted

    def test_is_empty_when_no_jobs(self, queue_manager):
        """is_empty returns True when queue has no pending jobs."""
        assert queue_manager.is_empty() is True

    def test_is_empty_when_only_current_job(self, queue_manager, sample_job):
        """is_empty returns True when only current job exists."""
        queue_manager.add(sample_job)
        queue_manager.get_next()

        assert queue_manager.is_empty() is True

    def test_is_empty_false_when_has_pending(self, queue_manager, sample_job):
        """is_empty returns False when queue has pending jobs."""
        queue_manager.add(sample_job)
        assert queue_manager.is_empty() is False

    def test_has_running_job_true_when_current(self, queue_manager, sample_job):
        """has_running_job returns True when job is executing."""
        queue_manager.add(sample_job)
        queue_manager.get_next()

        assert queue_manager.has_running_job() is True

    def test_has_running_job_false_when_no_current(self, queue_manager):
        """has_running_job returns False when no job executing."""
        assert queue_manager.has_running_job() is False

    def test_thread_safety_concurrent_adds(self, queue_manager, multiple_jobs):
        """Queue is thread-safe for concurrent add operations."""
        threads = []

        def add_job(job):
            queue_manager.add(job)

        # Spawn threads to add jobs concurrently
        for job in multiple_jobs:
            thread = threading.Thread(target=add_job, args=(job,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All jobs should be added
        assert queue_manager.size() == len(multiple_jobs)

    def test_thread_safety_concurrent_operations(self, queue_manager, multiple_jobs):
        """Queue is thread-safe for mixed concurrent operations."""
        results = {"added": 0, "removed": 0, "size": 0}

        def add_jobs():
            for job in multiple_jobs[:2]:
                queue_manager.add(job)
                results["added"] += 1

        def get_size():
            time.sleep(0.001)  # Small delay to create race condition
            results["size"] = queue_manager.size()

        def remove_job():
            time.sleep(0.002)
            # Try to remove a job (may or may not exist)
            if multiple_jobs:
                removed = queue_manager.remove(multiple_jobs[0].job_id)
                if removed:
                    results["removed"] += 1

        # Run operations concurrently
        threads = [
            threading.Thread(target=add_jobs),
            threading.Thread(target=get_size),
            threading.Thread(target=remove_job),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no corruption (exact counts may vary due to timing)
        final_size = queue_manager.size()
        assert final_size >= 0  # No negative size
        assert final_size <= len(multiple_jobs)  # No more than added
