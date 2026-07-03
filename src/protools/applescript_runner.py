"""Minimal AppleScript template runner for the two surviving scripts.

Replaces the old AppleScriptController. Deliberate differences:

- Placeholder values are escaped (backslash and double-quote) before
  substitution, so artist/song names and paths containing quotes cannot
  break the generated script.
- NO automatic retry. UI-scripting steps are not idempotent; callers decide
  whether re-running is safe based on verified Pro Tools state.
- The subprocess timeout is derived per-call from the script's own maximum
  internal wait plus a margin, instead of a fixed global timeout that could
  undercut a script still legitimately polling.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from src.core.exceptions import AppleScriptError

logger = logging.getLogger(__name__)

# Margin added on top of a script's own maximum internal wait.
TIMEOUT_MARGIN = 30.0
# Timeout used when the script has no internal waits to speak of.
DEFAULT_TIMEOUT = 60.0


def escape_applescript_string(value: str) -> str:
    """Escape a value for inclusion inside an AppleScript string literal.

    Backslashes must be escaped first, then double quotes.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


class AppleScriptRunner:
    """Loads, substitutes, and executes AppleScript templates once (no retry)."""

    def __init__(self, scripts_dir: Optional[Path] = None):
        self.scripts_dir = scripts_dir or Path(__file__).parent / "scripts"
        if not self.scripts_dir.exists():
            raise AppleScriptError(f"Scripts directory not found: {self.scripts_dir}")

    def run(
        self,
        script_name: str,
        placeholders: Optional[Dict[str, str]] = None,
        max_internal_wait: float = 0.0,
    ) -> str:
        """Execute an AppleScript template once.

        Args:
            script_name: Script file name without the .applescript extension.
            placeholders: {key: value} substitutions for {key} tokens. Values
                are escaped for AppleScript string literals.
            max_internal_wait: The longest the script itself may legitimately
                wait/poll (seconds). The subprocess timeout is this plus a
                margin, so the script's own timeout always fires first.

        Returns:
            The script's stdout (its `return` value), stripped.

        Raises:
            AppleScriptError: On non-zero exit, timeout, or osascript failure.
        """
        script_path = self.scripts_dir / f"{script_name}.applescript"
        if not script_path.exists():
            raise AppleScriptError(f"Script not found: {script_path}")

        content = self._load(script_path)
        for key, value in (placeholders or {}).items():
            content = content.replace(f"{{{key}}}", escape_applescript_string(str(value)))

        timeout = max(max_internal_wait + TIMEOUT_MARGIN, DEFAULT_TIMEOUT)

        try:
            result = subprocess.run(
                ["osascript", "-e", content],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise AppleScriptError(
                f"AppleScript '{script_name}' exceeded {timeout:.0f}s subprocess timeout"
            ) from e
        except OSError as e:
            raise AppleScriptError(f"Failed to execute osascript: {e}") from e

        # AppleScript `log` output lands on stderr even on success - keep it
        # visible instead of discarding it.
        if result.stderr.strip():
            logger.debug("AppleScript '%s' log: %s", script_name, result.stderr.strip())

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            raise AppleScriptError(
                f"AppleScript '{script_name}' failed (exit {result.returncode}): {error_msg}"
            )

        return result.stdout.strip()

    @staticmethod
    def _load(script_path: Path) -> str:
        """Read a script, tolerating Script Editor's UTF-16 re-saves."""
        encodings = ["utf-8", "utf-16-le", "utf-16-be", "utf-8-sig"]
        last_error: Optional[Exception] = None
        for encoding in encodings:
            try:
                with open(script_path, "r", encoding=encoding) as f:
                    content = f.read()
            except UnicodeDecodeError as e:
                last_error = e
                continue
            # BOM-less UTF-16 decodes "successfully" as UTF-8 because NUL
            # bytes are valid UTF-8 - detect the garbage and try the next
            # encoding instead.
            if "\x00" in content:
                continue
            return content
        raise AppleScriptError(
            f"Failed to read script {script_path.name} with any supported encoding. "
            f"Last error: {last_error}"
        )
