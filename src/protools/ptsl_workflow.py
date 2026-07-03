"""Pro Tools automation via PTSL (official gRPC API) - the primary workflow.

Implements ProToolsWorkflowProtocol (src/queue/job_executor.py), replacing the
AppleScript UI-scripting workflow. Two operations still fall back to guarded
AppleScript because PTSL v3 has no equivalent:

- MIDI import (import_midi.applescript)
- Dialog dismissal (dialog_supervisor.applescript) - modal dialogs poison
  every PTSL response with PT_NoOpenedSession (106), so the supervisor runs
  after imports/close and whenever a 106 is seen.

Retry policy is state-aware (docs/DEVELOPER_IMPROVEMENT_PLAN.md section 4.2):
on a 106 the workflow sweeps dialogs and verifies actual session state before
re-issuing anything. Whole steps are never blindly re-run.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

from src.protools import ptsl_compat  # noqa: F401  (must precede ptsl import)

from ptsl import PTSL_pb2 as pt

from src.core.exceptions import (
    PTSLError,
    ProToolsNotRunningError,
    SessionBlockedError,
)
from src.protools.applescript_runner import AppleScriptRunner
from src.protools.dialog_supervisor import DialogSupervisor
from src.protools.ptsl_client import PTSLClient
from src.protools.settings import AppSettings

logger = logging.getLogger(__name__)


class PTSLWorkflow:
    """High-level Pro Tools operations over PTSL.

    Satisfies ProToolsWorkflowProtocol, so JobExecutor, the queue, and the
    UI are unchanged from the AppleScript era.
    """

    def __init__(
        self,
        settings: AppSettings,
        client: Optional[PTSLClient] = None,
        runner: Optional[AppleScriptRunner] = None,
        supervisor: Optional[DialogSupervisor] = None,
    ):
        self.settings = settings
        self.client = client or PTSLClient(settings)
        self.runner = runner or AppleScriptRunner()
        self.supervisor = supervisor or DialogSupervisor(self.runner)

    # ------------------------------------------------------------------
    # Protocol: launch
    # ------------------------------------------------------------------

    def launch(self) -> None:
        """Ensure Pro Tools is running and the PTSL endpoint answers.

        No Dashboard handling - PTSL does not need any window state.

        Raises:
            ProToolsNotRunningError: Endpoint never came up within
                ptsl_connect_timeout (cold starts can take minutes).
        """
        if self.client.is_endpoint_up():
            self.client.ensure_ready()
            return

        logger.info("PTSL endpoint down; launching Pro Tools")
        try:
            subprocess.run(["open", "-a", "Pro Tools"], check=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            raise ProToolsNotRunningError(f"Failed to launch Pro Tools: {e}") from e

        deadline = time.monotonic() + self.settings.ptsl_connect_timeout
        while time.monotonic() < deadline:
            if self.client.is_endpoint_up():
                self.client.ensure_ready()
                return
            time.sleep(3.0)

        raise ProToolsNotRunningError(
            f"Pro Tools PTSL endpoint did not come up within "
            f"{self.settings.ptsl_connect_timeout:.0f}s of launch"
        )

    # ------------------------------------------------------------------
    # Protocol: create_session
    # ------------------------------------------------------------------

    def create_session(
        self, name: str, sample_rate: int, bit_depth: int, output_dir: Path
    ) -> None:
        """Create a new session.

        Pro Tools creates `{parent}/{name}/{name}.ptx`, which matches
        PathResolver's layout exactly when parent = output_dir.parent
        (output_dir's basename equals the session name).

        Sample rate stays an integer in Hz - no "48 kHz" string formatting.
        """
        parent_dir = output_dir.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        self.client.ensure_ready()

        def _create() -> None:
            with self.client.translate_errors():
                builder = self.client.engine().create_session(name, str(parent_dir))
                builder.wave_format()
                builder.sample_rate(sample_rate)
                builder.bit_depth(bit_depth)
                builder.create()

        self._run_blocked_tolerant(
            _create,
            verified_done=lambda: self._session_open_with_name(name),
            step_name=f"Session creation ({name})",
        )

        self.client.settle()

        # Verify: the right session must actually be open.
        open_name = self._query_session_name()
        if open_name != name:
            raise PTSLError(
                f"Session creation verification failed: expected {name!r} open, "
                f"found {open_name!r}"
            )
        logger.info("Created session %r at %s", name, output_dir)

    # ------------------------------------------------------------------
    # Protocol: import_audio
    # ------------------------------------------------------------------

    def import_audio(self, files: list[Path]) -> None:
        """Import audio files, copied into the session (never linked).

        Copy semantics are a hard project requirement; SRC is never applied
        implicitly - the queue pre-validates that file sample rates match the
        session.

        NOTE: PTSL v3's import_audio has not yet been validated live on this
        machine (see prototypes/ptsl_audio_import_spike.py). A parameter
        rejection surfaces as PTSLParameterError with a clear message rather
        than silently misimporting.
        """
        if not files:
            raise ValueError("No audio files to import")

        self.client.ensure_ready()

        def _import() -> None:
            with self.client.translate_errors():
                self.client.engine().import_audio(
                    file_list=[str(f) for f in files],
                    audio_operations=pt.CopyAudio,
                    audio_destination=pt.MD_NewTrack,
                    audio_location=pt.ML_SessionStart,
                )

        try:
            _import()
        except SessionBlockedError:
            self.supervisor.sweep()
            _import()

        self.supervisor.sweep()
        self.client.settle()
        logger.info("Imported %d audio file(s)", len(files))

    # ------------------------------------------------------------------
    # Protocol: import_midi (AppleScript fallback - no PTSL v3 equivalent)
    # ------------------------------------------------------------------

    def import_midi(self, files: list[Path]) -> None:
        """Import MIDI files via the guarded AppleScript fallback."""
        if not files:
            raise ValueError("No MIDI files to import")

        # Precondition: nothing may be blocking the UI before we script it.
        self.supervisor.sweep()

        midi_folder = files[0].parent
        result = self.runner.run(
            "import_midi",
            placeholders={
                "midi_folder_path": str(midi_folder),
                "dialog_wait": str(self.settings.dialog_wait_time),
                "import_timeout": str(int(self.settings.midi_import_timeout)),
            },
            max_internal_wait=self.settings.midi_import_timeout
            + self.settings.dialog_wait_time
            + 15.0,
        )
        logger.info("MIDI import result: %s", result)

        self.supervisor.sweep()
        self.client.settle()

    # ------------------------------------------------------------------
    # Protocol: import_template
    # ------------------------------------------------------------------

    def import_template(self, template_path: Path) -> None:
        """Import session data (tracks, routing, inserts) from a .ptx template.

        Replaces the old import_template.applescript entirely: no SRC
        checkbox, no track-selection hack, no Session Start Time warning -
        all request parameters.
        """
        if not template_path.exists():
            raise ValueError(f"Template file not found: {template_path}")

        self.client.ensure_ready()

        def _import() -> None:
            with self.client.translate_errors():
                imp = self.client.engine().import_data(str(template_path))
                imp.import_as_new_tracks()
                imp.link_to_source_audio()        # no copy/SRC of template media
                imp.maintain_absolute_timecode()  # no Session Start Time warning
                imp.import_clips_and_media()
                # REQUIRED on PTSL v3: the builder's empty-string default is
                # rejected with PT_InvalidParameter (126). Set the private
                # field directly - map_start_timecode() would also switch the
                # mapping option away from MaintainAbsoluteTimeCodeValues.
                imp._timecode_mapping_start_time = "00:00:00:00"
                imp.import_data()

        # Template plugins trigger dialogs during import: "Missing AAX
        # Plugins" (auto-dismissed) and PACE/iLok activation windows, which
        # are invisible to automation and must be Quit by hand. The helper
        # waits for the user, verifying track count before any re-issue.
        self._run_blocked_tolerant(
            _import,
            verified_done=lambda: self._query_track_count() > 0,
            step_name=f"Template import ({template_path.name})",
        )

        # Missing AAX Plugins fires after every import of a template whose
        # plugins aren't installed - the normal path on this machine.
        self.supervisor.sweep()
        self.client.settle()

        # Postcondition the old system never had: tracks actually arrived.
        # Must be blocked-aware: PACE/iLok activation windows keep every
        # query returning 106 until the user Quits them, and a blocked
        # query must NOT be read as "zero tracks".
        track_count = self._wait_for_track_count()
        if track_count == 0:
            raise PTSLError(
                f"Template import verification failed: no tracks in session "
                f"after importing {template_path.name}"
            )
        logger.info(
            "Imported template %s (%d tracks)", template_path.name, track_count
        )

    # ------------------------------------------------------------------
    # Protocol: save_session
    # ------------------------------------------------------------------

    def save_session(self, session_file: Path) -> None:
        """Save the session and poll until the .ptx exists on disk.

        Polling (not a fixed sleep) because large sessions save slower.
        """
        self.client.ensure_ready()

        try:
            with self.client.translate_errors():
                self.client.engine().save_session()
        except SessionBlockedError:
            self.supervisor.sweep()
            with self.client.translate_errors():
                self.client.engine().save_session()

        deadline = time.monotonic() + self.settings.save_poll_timeout
        while True:
            if session_file.exists():
                logger.info("Session saved: %s", session_file)
                return
            if time.monotonic() >= deadline:
                break
            time.sleep(0.5)

        raise PTSLError(
            f"Session file did not appear at {session_file} within "
            f"{self.settings.save_poll_timeout:.0f}s of save"
        )

    # ------------------------------------------------------------------
    # Protocol: close_session
    # ------------------------------------------------------------------

    def close_session(self) -> None:
        """Close the session (saving), then sweep any Save-changes dialog."""
        try:
            with self.client.translate_errors():
                self.client.engine().close_session(save_on_close=True)
        except SessionBlockedError:
            # Either a modal is up, or there is no session to close.
            self.supervisor.sweep()
            try:
                with self.client.translate_errors():
                    self.client.engine().close_session(save_on_close=True)
            except SessionBlockedError:
                # 106 with no dialogs left = no open session = already closed.
                logger.info("close_session: no open session (already closed)")
        except ProToolsNotRunningError:
            # Nothing to close if Pro Tools is gone (cleanup path).
            logger.warning("close_session: Pro Tools not running")
            return

        # "Save changes?" can still appear after a close command.
        self.supervisor.sweep()
        self.client.settle()

    # ------------------------------------------------------------------
    # Blocked-operation handling
    # ------------------------------------------------------------------

    def _run_blocked_tolerant(self, operation, verified_done, step_name: str) -> None:
        """Run a PTSL operation, tolerating 106s caused by dialogs.

        Handles three live-observed causes of SessionBlockedError:
        - whitelisted dialogs (Missing AAX Plugins...): swept automatically
        - transient "session state is already changing": resolved by waiting
        - PACE/iLok activation windows: INVISIBLE to accessibility (DRM) -
          nothing can dismiss them but the user. We log clear instructions
          and wait up to settings.user_dialog_timeout.

        verified_done() is checked before every re-issue: commands rejected
        during a modal can queue and execute after dismissal, so blind
        re-runs would double-execute.
        """
        deadline = time.monotonic() + self.settings.user_dialog_timeout
        delay = 2.0
        warned = False
        while True:
            try:
                operation()
                return
            except SessionBlockedError as e:
                self.supervisor.sweep()
                if verified_done():
                    logger.info("%s: verified complete after being blocked", step_name)
                    return
                if time.monotonic() >= deadline:
                    raise PTSLError(
                        f"{step_name} stayed blocked for "
                        f"{self.settings.user_dialog_timeout:.0f}s: {e}"
                    ) from e
                if not warned:
                    logger.warning(
                        "%s is blocked by Pro Tools (%s). If an iLok/PACE "
                        "'Activation is required' window is showing, press "
                        "Quit on each one - the job resumes automatically "
                        "(waiting up to %.0fs).",
                        step_name, e, self.settings.user_dialog_timeout,
                    )
                    warned = True
                time.sleep(delay)
                delay = min(delay * 2, 10.0)

    # ------------------------------------------------------------------
    # State queries (used by state-aware retry)
    # ------------------------------------------------------------------

    def _query_session_name(self) -> Optional[str]:
        """Name of the open session, or None if none/blocked."""
        try:
            with self.client.translate_errors():
                return self.client.engine().session_name()
        except SessionBlockedError:
            return None

    def _session_open_with_name(self, name: str) -> bool:
        return self._query_session_name() == name

    def _query_track_count(self) -> int:
        """Track count of the open session, or 0 if none/blocked.

        Only for pre-re-issue state checks, where "blocked" and "nothing
        imported" both mean "do not skip the operation". For verification
        use _wait_for_track_count, which waits out blockage instead.
        """
        try:
            with self.client.translate_errors():
                return len(self.client.engine().track_list())
        except SessionBlockedError:
            return 0

    def _wait_for_track_count(self) -> int:
        """Track count once Pro Tools answers definitively.

        While a PACE/iLok activation window is up every query returns 106;
        wait for the user to dismiss them (up to user_dialog_timeout) and
        only trust an actual track_list response.
        """
        deadline = time.monotonic() + self.settings.user_dialog_timeout
        warned = False
        while True:
            try:
                with self.client.translate_errors():
                    return len(self.client.engine().track_list())
            except SessionBlockedError as e:
                self.supervisor.sweep()
                if time.monotonic() >= deadline:
                    raise PTSLError(
                        f"Could not verify track count - Pro Tools stayed "
                        f"blocked for {self.settings.user_dialog_timeout:.0f}s: {e}"
                    ) from e
                if not warned:
                    logger.warning(
                        "Track verification blocked (%s). If iLok/PACE "
                        "'Activation is required' windows are showing, press "
                        "Quit on each - verification resumes automatically.", e,
                    )
                    warned = True
                time.sleep(3.0)
