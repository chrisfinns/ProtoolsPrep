"""Tests for FolderScanner."""

import pytest
from pathlib import Path
from src.core.folder_scanner import FolderScanner


class TestFolderScanner:
    """Test suite for FolderScanner."""

    @pytest.fixture
    def scanner(self):
        """Create FolderScanner instance."""
        return FolderScanner()

    @pytest.fixture
    def temp_folder(self, tmp_path):
        """Create temporary folder with test files."""
        # Create audio files
        (tmp_path / "track1.wav").touch()
        (tmp_path / "track2.aif").touch()
        (tmp_path / "track3.aiff").touch()

        # Create MIDI files
        (tmp_path / "melody.mid").touch()
        (tmp_path / "drums.midi").touch()

        # Create hidden file (should be ignored)
        (tmp_path / ".DS_Store").touch()

        # Create unsupported file (should be ignored)
        (tmp_path / "notes.txt").touch()

        # Create subdirectory (should be ignored)
        (tmp_path / "subfolder").mkdir()

        return tmp_path

    def test_scan_folder_not_found(self, scanner):
        """Test scanning non-existent folder raises error."""
        fake_folder = Path("/nonexistent/folder")
        with pytest.raises(FileNotFoundError):
            scanner.scan_folder(fake_folder)

    def test_scan_folder_not_directory(self, scanner, tmp_path):
        """Test scanning a file instead of directory raises error."""
        test_file = tmp_path / "test.wav"
        test_file.touch()

        with pytest.raises(NotADirectoryError):
            scanner.scan_folder(test_file)

    def test_scan_folder_finds_audio_files(self, scanner, temp_folder):
        """Test scanning folder finds all audio files."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        assert len(audio_files) == 3
        assert any(f.name == "track1.wav" for f in audio_files)
        assert any(f.name == "track2.aif" for f in audio_files)
        assert any(f.name == "track3.aiff" for f in audio_files)

    def test_scan_folder_finds_midi_files(self, scanner, temp_folder):
        """Test scanning folder finds all MIDI files."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        assert len(midi_files) == 2
        assert any(f.name == "melody.mid" for f in midi_files)
        assert any(f.name == "drums.midi" for f in midi_files)

    def test_scan_folder_ignores_hidden_files(self, scanner, temp_folder):
        """Test scanning folder ignores hidden files."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        all_files = audio_files + midi_files
        assert not any(f.name.startswith(".") for f in all_files)

    def test_scan_folder_ignores_unsupported_files(self, scanner, temp_folder):
        """Test scanning folder ignores unsupported file types."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        all_files = audio_files + midi_files
        assert not any(f.name == "notes.txt" for f in all_files)

    def test_scan_folder_ignores_subdirectories(self, scanner, temp_folder):
        """Test scanning folder ignores subdirectories."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        all_files = audio_files + midi_files
        assert not any(f.name == "subfolder" for f in all_files)

    def test_scan_folder_returns_sorted_lists(self, scanner, temp_folder):
        """Test scanning folder returns sorted file lists."""
        audio_files, midi_files = scanner.scan_folder(temp_folder)

        # Check audio files are sorted
        audio_names = [f.name for f in audio_files]
        assert audio_names == sorted(audio_names)

        # Check MIDI files are sorted
        midi_names = [f.name for f in midi_files]
        assert midi_names == sorted(midi_names)

    def test_get_supported_extensions(self, scanner):
        """Test getting all supported extensions."""
        extensions = scanner.get_supported_extensions()

        assert ".wav" in extensions
        assert ".aif" in extensions
        assert ".aiff" in extensions
        assert ".mid" in extensions
        assert ".midi" in extensions
        assert len(extensions) == 5
