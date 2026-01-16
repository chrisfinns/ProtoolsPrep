"""Folder scanning and file filtering."""

from pathlib import Path
from typing import Tuple


class FolderScanner:
    """Filters files by extension, skips hidden/unsupported files."""

    AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff"}
    MIDI_EXTENSIONS = {".mid", ".midi"}

    def scan_folder(self, folder_path: Path) -> Tuple[list[Path], list[Path]]:
        """
        Scan folder for audio and MIDI files.

        Args:
            folder_path: Path to folder to scan

        Returns:
            Tuple of (audio_files, midi_files)

        Note:
            - Skips hidden files (starting with .)
            - Only includes supported extensions
            - Returns sorted lists for consistent ordering
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        if not folder_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        audio_files = []
        midi_files = []

        for file_path in folder_path.iterdir():
            # Skip hidden files
            if file_path.name.startswith("."):
                continue

            # Skip directories
            if not file_path.is_file():
                continue

            # Check extension
            ext = file_path.suffix.lower()

            if ext in self.AUDIO_EXTENSIONS:
                audio_files.append(file_path)
            elif ext in self.MIDI_EXTENSIONS:
                midi_files.append(file_path)

        # Sort for consistent ordering
        audio_files.sort()
        midi_files.sort()

        return audio_files, midi_files

    def get_supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return self.AUDIO_EXTENSIONS | self.MIDI_EXTENSIONS
