"""Tests for SessionSpec."""

import pytest
from pathlib import Path
from src.core.session_spec import SessionSpec


class TestSessionSpec:
    """Test suite for SessionSpec."""

    @pytest.fixture
    def valid_params(self, tmp_path):
        """Create valid SessionSpec parameters."""
        output_dir = tmp_path / "Artist" / "Song"
        session_file = output_dir / "Song.ptx"

        audio_file = tmp_path / "audio.wav"
        audio_file.touch()

        return {
            "sample_rate": 44100,
            "bit_depth": 16,
            "audio_files": [audio_file],
            "midi_files": [],
            "output_dir": output_dir,
            "session_file": session_file,
            "artist": "Artist Name",
            "song_name": "Song Name",
        }

    def test_create_valid_session_spec(self, valid_params):
        """Test creating valid SessionSpec."""
        spec = SessionSpec(**valid_params)

        assert spec.sample_rate == 44100
        assert spec.bit_depth == 16
        assert spec.artist == "Artist Name"
        assert spec.song_name == "Song Name"

    def test_audio_files_converted_to_tuple(self, valid_params):
        """Test audio files list is converted to tuple."""
        spec = SessionSpec(**valid_params)

        assert isinstance(spec.audio_files, tuple)

    def test_midi_files_converted_to_tuple(self, valid_params):
        """Test MIDI files list is converted to tuple."""
        spec = SessionSpec(**valid_params)

        assert isinstance(spec.midi_files, tuple)

    def test_has_audio_property(self, valid_params, tmp_path):
        """Test has_audio property."""
        spec = SessionSpec(**valid_params)
        assert spec.has_audio

        # Test without audio
        valid_params["audio_files"] = []
        midi_file = tmp_path / "test.mid"
        midi_file.touch()
        valid_params["midi_files"] = [midi_file]

        spec_no_audio = SessionSpec(**valid_params)
        assert not spec_no_audio.has_audio

    def test_has_midi_property(self, valid_params, tmp_path):
        """Test has_midi property."""
        spec = SessionSpec(**valid_params)
        assert not spec.has_midi

        # Test with MIDI
        midi_file = tmp_path / "test.mid"
        midi_file.touch()
        valid_params["midi_files"] = [midi_file]

        spec_with_midi = SessionSpec(**valid_params)
        assert spec_with_midi.has_midi

    def test_has_template_property(self, valid_params, tmp_path):
        """Test has_template property."""
        spec = SessionSpec(**valid_params)
        assert not spec.has_template

        # Test with template
        template = tmp_path / "template.ptx"
        template.touch()
        valid_params["template_path"] = template

        spec_with_template = SessionSpec(**valid_params)
        assert spec_with_template.has_template

    def test_is_album_mode_property(self, valid_params):
        """Test is_album_mode property."""
        spec = SessionSpec(**valid_params)
        assert not spec.is_album_mode

        # Test with project name
        valid_params["project_name"] = "Album Name"
        spec_album = SessionSpec(**valid_params)
        assert spec_album.is_album_mode

    def test_session_name_property(self, valid_params):
        """Test session_name property."""
        spec = SessionSpec(**valid_params)
        assert spec.session_name == "Song"

    def test_invalid_sample_rate(self, valid_params):
        """Test invalid sample rate raises error."""
        valid_params["sample_rate"] = 22050  # Invalid rate

        with pytest.raises(ValueError, match="Invalid sample rate"):
            SessionSpec(**valid_params)

    def test_invalid_bit_depth(self, valid_params):
        """Test invalid bit depth raises error."""
        valid_params["bit_depth"] = 8  # Invalid depth

        with pytest.raises(ValueError, match="Invalid bit depth"):
            SessionSpec(**valid_params)

    def test_empty_artist(self, valid_params):
        """Test empty artist name raises error."""
        valid_params["artist"] = ""

        with pytest.raises(ValueError, match="Artist name is required"):
            SessionSpec(**valid_params)

    def test_empty_song_name(self, valid_params):
        """Test empty song name raises error."""
        valid_params["song_name"] = "   "

        with pytest.raises(ValueError, match="Song name is required"):
            SessionSpec(**valid_params)

    def test_no_files(self, valid_params):
        """Test SessionSpec with no files raises error."""
        valid_params["audio_files"] = []
        valid_params["midi_files"] = []

        with pytest.raises(ValueError, match="at least one audio or MIDI file"):
            SessionSpec(**valid_params)

    def test_nonexistent_template(self, valid_params):
        """Test nonexistent template path raises error."""
        valid_params["template_path"] = Path("/nonexistent/template.ptx")

        with pytest.raises(ValueError, match="Template file not found"):
            SessionSpec(**valid_params)

    def test_immutability(self, valid_params):
        """Test SessionSpec is immutable."""
        spec = SessionSpec(**valid_params)

        with pytest.raises(Exception):  # FrozenInstanceError
            spec.sample_rate = 48000

    def test_valid_sample_rates(self, valid_params):
        """Test all valid sample rates are accepted."""
        valid_rates = [44100, 48000, 88200, 96000, 176400, 192000]

        for rate in valid_rates:
            valid_params["sample_rate"] = rate
            spec = SessionSpec(**valid_params)
            assert spec.sample_rate == rate

    def test_valid_bit_depths(self, valid_params):
        """Test all valid bit depths are accepted."""
        valid_depths = [16, 24, 32]

        for depth in valid_depths:
            valid_params["bit_depth"] = depth
            spec = SessionSpec(**valid_params)
            assert spec.bit_depth == depth
