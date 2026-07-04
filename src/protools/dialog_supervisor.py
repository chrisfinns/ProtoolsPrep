"""Python wrapper around the dialog supervisor AppleScript.

The supervisor dismisses only whitelisted informational dialogs and reports
anything else. It exists because modal dialogs poison every PTSL response:
while one is up, all commands return PT_NoOpenedSession (106) even when a
session is open (docs/DEVELOPER_IMPROVEMENT_PLAN.md section 3.2).
"""

import logging
import time
from typing import List

from src.core.exceptions import AppleScriptError, DialogBlockedError
from src.protools.applescript_runner import AppleScriptRunner

logger = logging.getLogger(__name__)


class DialogSupervisor:
    """Runs the whitelist dialog-dismissal script and parses its result."""

    SCRIPT_NAME = "dialog_supervisor"

    def __init__(self, runner: AppleScriptRunner):
        self._runner = runner

    def check(self) -> str:
        """Run one supervisor pass.

        Returns:
            The dismissed dialog's label, or "" if no dialog was present.

        Raises:
            DialogBlockedError: A non-whitelisted dialog is blocking Pro Tools.
            AppleScriptError: The supervisor script itself failed.
        """
        result = self._runner.run(self.SCRIPT_NAME)

        if result == "none":
            return ""
        if result.startswith("dismissed:"):
            label = result[len("dismissed:"):]
            logger.info("Dialog supervisor dismissed: %s", label)
            return label
        if result.startswith("unknown:"):
            raise DialogBlockedError(result[len("unknown:"):])
        if result.startswith("ax-error:"):
            # An AX query failed mid-pass (-10000 has been observed while a
            # PACE window is mid-spawn). Transient - treat as "nothing to do
            # right now"; the next sweep pass will see whatever settled.
            logger.warning(
                "Dialog supervisor could not inspect windows this pass: %s",
                result[len("ax-error:"):],
            )
            return ""

        raise AppleScriptError(f"Dialog supervisor returned unparseable result: {result!r}")

    def sweep(self, max_dismissals: int = 40, pause: float = 1.0) -> List[str]:
        """Dismiss whitelisted dialogs until none remain.

        Dialogs can stack: Missing AAX Plugins behind Session Notes, and PACE
        activation windows arrive one per unlicensed plugin (each a fresh
        helper process, spawned a couple of seconds apart - hence the high
        default bound and the longer pause after a PACE dismissal).

        Returns:
            Labels of all dialogs dismissed (may be empty).

        Raises:
            DialogBlockedError: A non-whitelisted dialog is blocking Pro Tools.
        """
        dismissed: List[str] = []
        for _ in range(max_dismissals):
            label = self.check()
            if not label:
                return dismissed
            dismissed.append(label)
            # The next PACE helper process takes ~2-3s to spawn; a plain
            # dialog just needs a beat for Pro Tools to surface the next one.
            time.sleep(3.0 if label.startswith("PACE") else pause)
        logger.warning(
            "Dialog supervisor hit dismissal limit (%d); last: %s",
            max_dismissals,
            dismissed[-1] if dismissed else "-",
        )
        return dismissed
