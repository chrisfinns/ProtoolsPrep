"""Path resolution for Pro Tools session output."""

from pathlib import Path
from typing import Optional


class PathResolver:
    """
    Computes output paths based on folder structure mode.

    Single Song Mode: {root}/{Artist}/{Song}/
    Album/EP Mode: {root}/{Artist}/{Project}/{Song}/
    """

    def __init__(self, root_output_dir: Path):
        """
        Initialize path resolver.

        Args:
            root_output_dir: Root directory for all Pro Tools sessions
        """
        self.root_output_dir = root_output_dir

    def resolve_paths(
        self,
        artist: str,
        song_name: str,
        project_name: Optional[str] = None
    ) -> tuple[Path, Path]:
        """
        Resolve output directory and session file path.

        Args:
            artist: Artist name
            song_name: Song name
            project_name: Optional project name (for album/EP mode)

        Returns:
            Tuple of (output_dir, session_file_path)

        Examples:
            Single song mode:
            - output_dir: /path/to/root/Artist Name/Song Name/
            - session_file: /path/to/root/Artist Name/Song Name/Song Name.ptx

            Album mode:
            - output_dir: /path/to/root/Artist Name/Album Name/Song Name/
            - session_file: /path/to/root/Artist Name/Album Name/Song Name/Song Name.ptx
        """
        # Sanitize names for filesystem
        artist_clean = self._sanitize_name(artist)
        song_clean = self._sanitize_name(song_name)

        if project_name:
            # Album/EP mode: {root}/{Artist}/{Project}/{Song}/
            project_clean = self._sanitize_name(project_name)
            output_dir = self.root_output_dir / artist_clean / project_clean / song_clean
        else:
            # Single song mode: {root}/{Artist}/{Song}/
            output_dir = self.root_output_dir / artist_clean / song_clean

        # Session file path
        session_file = output_dir / f"{song_clean}.ptx"

        return output_dir, session_file

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize name for filesystem use.

        Replaces problematic characters with safe alternatives.

        Args:
            name: Original name

        Returns:
            Sanitized name safe for filesystem
        """
        # Strip leading/trailing whitespace
        name = name.strip()

        # Replace problematic characters
        replacements = {
            "/": "-",
            "\\": "-",
            ":": "-",
            "*": "",
            "?": "",
            '"': "",
            "<": "",
            ">": "",
            "|": "-",
        }

        for old, new in replacements.items():
            name = name.replace(old, new)

        # Collapse multiple spaces
        while "  " in name:
            name = name.replace("  ", " ")

        return name

    def get_audio_files_dir(self, output_dir: Path) -> Path:
        """
        Get the Audio Files directory path.

        Pro Tools auto-creates this directory, but we may need to reference it.

        Args:
            output_dir: Session output directory

        Returns:
            Path to Audio Files directory
        """
        return output_dir / "Audio Files"

    def validate_root_writable(self) -> bool:
        """
        Check if root output directory exists and is writable.

        Returns:
            True if directory exists and is writable

        Note:
            Creates directory if it doesn't exist
        """
        try:
            self.root_output_dir.mkdir(parents=True, exist_ok=True)
            return True
        except (PermissionError, OSError):
            return False
