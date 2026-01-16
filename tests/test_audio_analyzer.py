"""Tests for AudioAnalyzer."""

import pytest
from pathlib import Path
from src.core.audio_analyzer import AudioAnalyzer, AudioSpec
from src.core.exceptions import AudioAnalysisError, SampleRateMismatchError


class TestAudioAnalyzer:
    """Test suite for AudioAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create AudioAnalyzer instance."""
        return AudioAnalyzer()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_sox_installed(self, analyzer):
        """Test that sox is installed and detected."""
        assert analyzer._is_sox_installed()

    def test_analyze_file_not_found(self, analyzer):
        """Test analyzing non-existent file raises error."""
        fake_file = Path("/nonexistent/file.wav")
        with pytest.raises(AudioAnalysisError, match="File not found"):
            analyzer.analyze_file(fake_file)

    def test_analyze_file_44100_16bit(self, analyzer, fixtures_dir):
        """Test analyzing 44.1kHz 16-bit file."""
        test_file = fixtures_dir / "44100_16bit.wav"
        if not test_file.exists():
            pytest.skip(f"Test fixture not found: {test_file}")

        spec = analyzer.analyze_file(test_file)

        assert spec.sample_rate == 44100
        assert spec.bit_depth == 16
        assert spec.channels >= 1
        assert spec.duration > 0

    def test_analyze_file_48000_24bit(self, analyzer, fixtures_dir):
        """Test analyzing 48kHz 24-bit file."""
        test_file = fixtures_dir / "48000_24bit.wav"
        if not test_file.exists():
            pytest.skip(f"Test fixture not found: {test_file}")

        spec = analyzer.analyze_file(test_file)

        assert spec.sample_rate == 48000
        assert spec.bit_depth == 24
        assert spec.channels >= 1
        assert spec.duration > 0

    def test_validate_folder_empty_list(self, analyzer):
        """Test validating empty file list raises error."""
        with pytest.raises(AudioAnalysisError, match="No audio files"):
            analyzer.validate_folder([])

    def test_validate_folder_matching_files(self, analyzer, fixtures_dir):
        """Test validating files with matching specs succeeds."""
        # This test would need multiple files with same specs
        # For now, test with single file
        test_file = fixtures_dir / "44100_16bit.wav"
        if not test_file.exists():
            pytest.skip(f"Test fixture not found: {test_file}")

        result = analyzer.validate_folder([test_file])

        assert result["sample_rate"] == 44100
        assert result["bit_depth"] == 16

    def test_validate_folder_mismatched_sample_rates(self, analyzer, fixtures_dir):
        """Test validating files with different sample rates raises error."""
        file1 = fixtures_dir / "44100_16bit.wav"
        file2 = fixtures_dir / "48000_24bit.wav"

        if not file1.exists() or not file2.exists():
            pytest.skip("Test fixtures not found")

        with pytest.raises(SampleRateMismatchError, match="mismatch"):
            analyzer.validate_folder([file1, file2])
