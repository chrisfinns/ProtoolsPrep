"""Application settings with JSON persistence."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class AppSettings:
    """Application configuration with persistent storage.

    Settings are saved to ~/.protools_session_builder_settings.json
    and automatically loaded on next startup.

    Timing Configuration:
        dialog_wait_time: Seconds to wait after opening dialogs (default: 2.0)
        import_completion_timeout: Max seconds to wait for import completion (default: 60.0)
        window_appearance_timeout: Max seconds to wait for window to appear (default: 10.0)
        applescript_retry_attempts: Number of retry attempts for failed scripts (default: 3)
        applescript_retry_delay: Base delay in seconds for exponential backoff (default: 1.0)

    Path Configuration:
        root_output_dir: Default root directory for created sessions
        last_template_path: Last used template file path (for UI convenience)

    System Configuration:
        check_accessibility_permissions: Whether to check permissions on startup (default: True)
    """

    # Timing configuration
    dialog_wait_time: float = 2.0
    import_completion_timeout: float = 60.0
    window_appearance_timeout: float = 10.0
    applescript_retry_attempts: int = 3
    applescript_retry_delay: float = 1.0

    # Path configuration
    root_output_dir: Optional[str] = None
    last_template_path: Optional[str] = None

    # System configuration
    check_accessibility_permissions: bool = True

    @classmethod
    def get_settings_path(cls) -> Path:
        """Get the path to the settings file in user's home directory."""
        return Path.home() / ".protools_session_builder_settings.json"

    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from JSON file, or return defaults if file doesn't exist."""
        settings_path = cls.get_settings_path()

        if not settings_path.exists():
            # Return defaults with testing directory as root
            settings = cls()
            settings.root_output_dir = str(Path.cwd() / "testing")
            return settings

        try:
            with open(settings_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        except (json.JSONDecodeError, TypeError) as e:
            # If file is corrupted, return defaults
            print(f"Warning: Could not load settings from {settings_path}: {e}")
            print("Using default settings.")
            settings = cls()
            settings.root_output_dir = str(Path.cwd() / "testing")
            return settings

    def save(self) -> None:
        """Save settings to JSON file."""
        settings_path = self.get_settings_path()

        try:
            with open(settings_path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
        except (OSError, TypeError) as e:
            print(f"Warning: Could not save settings to {settings_path}: {e}")

    def get_root_output_dir(self) -> Path:
        """Get the root output directory as a Path object.

        Returns:
            Path to root output directory (defaults to ./testing if not set)
        """
        if self.root_output_dir:
            return Path(self.root_output_dir)
        return Path.cwd() / "testing"

    def get_last_template_path(self) -> Optional[Path]:
        """Get the last used template path as a Path object.

        Returns:
            Path to last template, or None if not set
        """
        if self.last_template_path:
            return Path(self.last_template_path)
        return None

    def set_root_output_dir(self, path: Path) -> None:
        """Set the root output directory and save settings.

        Args:
            path: Path to new root output directory
        """
        self.root_output_dir = str(path)
        self.save()

    def set_last_template_path(self, path: Optional[Path]) -> None:
        """Set the last used template path and save settings.

        Args:
            path: Path to template file, or None to clear
        """
        self.last_template_path = str(path) if path else None
        self.save()
