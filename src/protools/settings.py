"""Application settings with JSON persistence."""

import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional


@dataclass
class AppSettings:
    """Application configuration with persistent storage.

    Settings are saved to ~/.protools_session_builder_settings.json
    and automatically loaded on next startup.

    PTSL Configuration (primary automation path):
        ptsl_port: gRPC port Pro Tools listens on (default: 31416)
        ptsl_settle_time: Seconds to pause after create/import/open - rapid
            command cycling can wedge Pro Tools 2024.3 (default: 8.0)
        ptsl_connect_timeout: Max seconds to wait for the PTSL endpoint after
            launching Pro Tools; cold starts are slow (default: 240.0)
        save_poll_timeout: Max seconds to poll for the .ptx on disk after
            save (default: 30.0)
        user_dialog_timeout: Max seconds to wait for the USER to manually
            dismiss dialogs automation cannot touch - PACE/iLok activation
            windows are invisible to accessibility (default: 600.0)

    AppleScript Configuration (two surviving scripts: MIDI import, dialog supervisor):
        dialog_wait_time: Seconds to wait after opening dialogs (default: 2.0)
        midi_import_timeout: Max seconds to wait for the MIDI Import Options
            dialog / silent completion (default: 60.0)

    Path Configuration:
        root_output_dir: Default root directory for created sessions
        last_template_path: Last used template file path (for UI convenience)

    System Configuration:
        check_accessibility_permissions: Whether to check permissions on startup (default: True)
    """

    # PTSL configuration
    ptsl_port: int = 31416
    ptsl_settle_time: float = 8.0
    ptsl_connect_timeout: float = 240.0
    save_poll_timeout: float = 30.0
    user_dialog_timeout: float = 600.0

    # AppleScript configuration (surviving scripts only)
    dialog_wait_time: float = 2.0
    midi_import_timeout: float = 60.0

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
                # Ignore unknown/legacy keys (e.g. removed AppleScript timing
                # knobs from earlier versions) instead of crashing.
                known = {f.name for f in fields(cls)}
                return cls(**{k: v for k, v in data.items() if k in known})
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
