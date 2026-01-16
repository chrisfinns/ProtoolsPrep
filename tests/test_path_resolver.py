"""Tests for PathResolver."""

import pytest
from pathlib import Path
from src.core.path_resolver import PathResolver


class TestPathResolver:
    """Test suite for PathResolver."""

    @pytest.fixture
    def root_dir(self, tmp_path):
        """Create temporary root directory."""
        root = tmp_path / "sessions"
        root.mkdir()
        return root

    @pytest.fixture
    def resolver(self, root_dir):
        """Create PathResolver instance."""
        return PathResolver(root_dir)

    def test_resolve_paths_single_song_mode(self, resolver, root_dir):
        """Test resolving paths for single song mode."""
        output_dir, session_file = resolver.resolve_paths(
            artist="Artist Name",
            song_name="Song Name"
        )

        expected_dir = root_dir / "Artist Name" / "Song Name"
        expected_file = expected_dir / "Song Name.ptx"

        assert output_dir == expected_dir
        assert session_file == expected_file

    def test_resolve_paths_album_mode(self, resolver, root_dir):
        """Test resolving paths for album/EP mode."""
        output_dir, session_file = resolver.resolve_paths(
            artist="Artist Name",
            song_name="Song Name",
            project_name="Album Name"
        )

        expected_dir = root_dir / "Artist Name" / "Album Name" / "Song Name"
        expected_file = expected_dir / "Song Name.ptx"

        assert output_dir == expected_dir
        assert session_file == expected_file

    def test_sanitize_name_slashes(self, resolver):
        """Test sanitizing names with slashes."""
        result = resolver._sanitize_name("AC/DC")
        assert result == "AC-DC"

    def test_sanitize_name_colons(self, resolver):
        """Test sanitizing names with colons."""
        result = resolver._sanitize_name("Song: Version 2")
        assert result == "Song- Version 2"

    def test_sanitize_name_special_chars(self, resolver):
        """Test sanitizing names with various special characters."""
        result = resolver._sanitize_name('Song "Name" <Version>')
        assert '"' not in result
        assert '<' not in result
        assert '>' not in result

    def test_sanitize_name_whitespace(self, resolver):
        """Test sanitizing names with extra whitespace."""
        result = resolver._sanitize_name("  Song   Name  ")
        assert result == "Song Name"
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_sanitize_name_asterisk_question_mark(self, resolver):
        """Test sanitizing names with wildcards."""
        result = resolver._sanitize_name("Song*Name?")
        assert "*" not in result
        assert "?" not in result

    def test_get_audio_files_dir(self, resolver, root_dir):
        """Test getting Audio Files directory path."""
        output_dir = root_dir / "Artist" / "Song"
        audio_dir = resolver.get_audio_files_dir(output_dir)

        expected = output_dir / "Audio Files"
        assert audio_dir == expected

    def test_validate_root_writable_creates_directory(self, tmp_path):
        """Test validating root creates directory if needed."""
        new_root = tmp_path / "new_sessions"
        resolver = PathResolver(new_root)

        assert resolver.validate_root_writable()
        assert new_root.exists()
        assert new_root.is_dir()

    def test_validate_root_writable_existing_directory(self, resolver):
        """Test validating root with existing directory."""
        assert resolver.validate_root_writable()

    def test_resolve_paths_with_complex_names(self, resolver, root_dir):
        """Test resolving paths with complex artist/song names."""
        output_dir, session_file = resolver.resolve_paths(
            artist="The Artist: Special Edition",
            song_name="Song / Remix (2025)",
            project_name="Album <Deluxe>"
        )

        # Verify no problematic characters in path
        path_str = str(output_dir)
        assert "/" not in output_dir.name
        assert ":" not in output_dir.name
        assert "<" not in output_dir.name
        assert ">" not in output_dir.name

        # Verify structure is correct
        parts = output_dir.relative_to(root_dir).parts
        assert len(parts) == 3  # Artist/Project/Song
