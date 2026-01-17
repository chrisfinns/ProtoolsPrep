"""High-level Pro Tools automation workflow operations."""

from pathlib import Path
from typing import Optional

from src.core.session_spec import SessionSpec
from src.core.exceptions import AppleScriptError
from src.protools.applescript_controller import AppleScriptController
from src.protools.settings import AppSettings
from src.protools.ui_scripting_utils import UIScriptingUtils


class ProToolsWorkflow:
    """High-level Pro Tools automation operations.

    Coordinates multi-step workflows using AppleScriptController and
    UIScriptingUtils. Each method encapsulates a complete operation
    (launch, create, import, save, close) with proper error handling.

    Example:
        settings = AppSettings.load()
        workflow = ProToolsWorkflow(settings)
        workflow.launch()
        workflow.create_session(
            name=spec.song_name,
            sample_rate=spec.sample_rate,
            bit_depth=spec.bit_depth,
            output_dir=spec.output_dir
        )
        workflow.import_audio(list(spec.audio_files))
        workflow.save_session(spec.session_file)
        workflow.close_session()
    """

    def __init__(self, settings: AppSettings):
        """Initialize workflow with settings.

        Args:
            settings: Application settings with timing configuration
        """
        self.settings = settings
        self.controller = AppleScriptController(settings)

    def launch(self) -> None:
        """Launch Pro Tools and wait for Dashboard window.

        Raises:
            AppleScriptError: If Pro Tools fails to launch or Dashboard doesn't appear
        """
        self.controller.execute(
            "launch_protools",
            placeholders={
                "window_timeout": str(int(self.settings.window_appearance_timeout))
            }
        )

    def create_session(
        self, name: str, sample_rate: int, bit_depth: int, output_dir: Path
    ) -> None:
        """Create new Pro Tools session from Dashboard.

        Note: Session is initially created in Pro Tools' default location.
        Use save_session() afterward to save it to the desired output_dir.

        Args:
            name: Session name
            sample_rate: Sample rate in Hz (e.g., 44100, 48000)
            bit_depth: Bit depth (e.g., 16, 24)
            output_dir: Directory where session should be saved (used for validation only)

        Raises:
            AppleScriptError: If session creation fails
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        self.controller.execute(
            "create_session",
            placeholders={
                "session_name": name,
                "sample_rate": str(sample_rate),
                "bit_depth": str(bit_depth),
                "window_timeout": str(int(self.settings.window_appearance_timeout))
            }
        )

    def import_audio(self, files: list[Path]) -> None:
        """Import audio files with Apply SRC disabled.

        CRITICAL: This operation disables and verifies the "Apply SRC" checkbox
        to prevent sample rate conversion and audio quality degradation.

        Args:
            files: List of audio file paths to import

        Raises:
            AppleScriptError: If import fails or Apply SRC cannot be disabled
            ValueError: If files is empty
        """
        if not files:
            raise ValueError("No audio files to import")

        # Get parent folder (assumes all files in same directory)
        audio_folder = files[0].parent

        self.controller.execute(
            "import_audio",
            placeholders={
                "audio_folder_path": str(audio_folder),
                "dialog_wait": str(self.settings.dialog_wait_time),
                "import_timeout": str(int(self.settings.import_completion_timeout))
            }
        )

    def import_midi(self, files: list[Path]) -> None:
        """Import MIDI files with tempo and key signature import enabled.

        Args:
            files: List of MIDI file paths to import

        Raises:
            AppleScriptError: If import fails
            ValueError: If files is empty
        """
        if not files:
            raise ValueError("No MIDI files to import")

        # Get parent folder (assumes all files in same directory)
        midi_folder = files[0].parent

        self.controller.execute(
            "import_midi",
            placeholders={
                "midi_folder_path": str(midi_folder),
                "dialog_wait": str(self.settings.dialog_wait_time),
                "import_timeout": str(int(self.settings.import_completion_timeout))
            }
        )

    def import_template(self, template_path: Path) -> None:
        """Import session template (Session Data) with Apply SRC disabled.

        CRITICAL: This operation:
        1. Disables and verifies "Apply SRC" checkbox
        2. Dismisses "Session Start Time" warning dialog

        Args:
            template_path: Path to template session file (.ptx)

        Raises:
            AppleScriptError: If import fails, SRC cannot be disabled, or warning not dismissed
            ValueError: If template_path doesn't exist
        """
        if not template_path.exists():
            raise ValueError(f"Template file not found: {template_path}")

        self.controller.execute(
            "import_template",
            placeholders={
                "template_posix_path": str(template_path),
                "dialog_wait": str(self.settings.dialog_wait_time),
                "import_timeout": str(int(self.settings.import_completion_timeout))
            }
        )

    def save_session(self, session_file: Path) -> None:
        """Save current Pro Tools session to specific location.

        Args:
            session_file: Path where session should be saved

        Raises:
            AppleScriptError: If save operation fails
        """
        # Use Save As to save to specific location
        self.controller.execute(
            "save_session_as",
            placeholders={
                "save_path": str(session_file.parent),
                "session_name": session_file.stem,
                "dialog_wait": str(self.settings.dialog_wait_time)
            }
        )

        # Verify session file was created
        # Pro Tools creates the .ptx file, but we need to wait a moment
        import time
        time.sleep(1)

        if not session_file.exists():
            # Check if it exists with different extension (.ptf for older versions)
            ptf_file = session_file.with_suffix('.ptf')
            if not ptf_file.exists():
                raise AppleScriptError(
                    f"Session file was not created at {session_file} or {ptf_file}"
                )

    def close_session(self) -> None:
        """Close current Pro Tools session.

        Uses keyboard shortcut (Cmd+W) to close the frontmost session.
        Handles save dialogs automatically by clicking "Don't Save"
        (session should already be saved at this point).

        Raises:
            AppleScriptError: If close operation fails
        """
        self.controller.execute("close_session")
