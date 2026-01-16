"""Immutable data model for Pro Tools session specifications."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SessionSpec:
    """
    Immutable specification for a Pro Tools session.

    Contains all parameters needed to create and configure a session:
    - Audio specs (sample rate, bit depth)
    - File lists (audio files, MIDI files)
    - Output paths (session directory, session file)
    - Metadata (artist, song name, project name)
    - Template path (optional)
    """

    # Audio specifications
    sample_rate: int
    bit_depth: int

    # File lists
    audio_files: tuple[Path, ...]
    midi_files: tuple[Path, ...]

    # Output paths
    output_dir: Path
    session_file: Path

    # Metadata
    artist: str
    song_name: str
    project_name: Optional[str] = None  # Only for album/EP mode

    # Template
    template_path: Optional[Path] = None

    @property
    def has_audio(self) -> bool:
        """Check if session has audio files."""
        return len(self.audio_files) > 0

    @property
    def has_midi(self) -> bool:
        """Check if session has MIDI files."""
        return len(self.midi_files) > 0

    @property
    def has_template(self) -> bool:
        """Check if session uses a template."""
        return self.template_path is not None

    @property
    def is_album_mode(self) -> bool:
        """Check if session is part of an album/EP."""
        return self.project_name is not None

    @property
    def session_name(self) -> str:
        """Get the Pro Tools session name (without extension)."""
        return self.session_file.stem

    def __post_init__(self):
        """Validate SessionSpec after initialization."""
        # Ensure file lists are tuples (immutable)
        if not isinstance(self.audio_files, tuple):
            object.__setattr__(self, 'audio_files', tuple(self.audio_files))
        if not isinstance(self.midi_files, tuple):
            object.__setattr__(self, 'midi_files', tuple(self.midi_files))

        # Validate sample rate
        valid_sample_rates = {44100, 48000, 88200, 96000, 176400, 192000}
        if self.sample_rate not in valid_sample_rates:
            raise ValueError(f"Invalid sample rate: {self.sample_rate}")

        # Validate bit depth
        valid_bit_depths = {16, 24, 32}
        if self.bit_depth not in valid_bit_depths:
            raise ValueError(f"Invalid bit depth: {self.bit_depth}")

        # Validate paths
        if not self.output_dir:
            raise ValueError("Output directory is required")

        if not self.session_file:
            raise ValueError("Session file path is required")

        # Validate metadata
        if not self.artist or not self.artist.strip():
            raise ValueError("Artist name is required")

        if not self.song_name or not self.song_name.strip():
            raise ValueError("Song name is required")

        # Validate at least one file type present
        if not self.has_audio and not self.has_midi:
            raise ValueError("Session must have at least one audio or MIDI file")

        # Validate template exists if specified
        if self.template_path and not self.template_path.exists():
            raise ValueError(f"Template file not found: {self.template_path}")
