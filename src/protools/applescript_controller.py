"""AppleScript template execution engine with retry logic."""

import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from src.core.exceptions import AppleScriptError
from src.protools.settings import AppSettings


class AppleScriptController:
    """Executes AppleScript templates with placeholder substitution and retry logic.

    Features:
        - Template loading from scripts/ directory
        - Placeholder substitution ({key} → value)
        - Subprocess execution via osascript
        - Error parsing from stderr
        - Exponential backoff retry logic
        - Configurable timeout handling

    Example:
        controller = AppleScriptController(settings)
        result = controller.execute(
            "launch_protools",
            placeholders={"window_timeout": "10"}
        )
    """

    def __init__(self, settings: AppSettings):
        """Initialize controller with settings.

        Args:
            settings: Application settings with timing configuration
        """
        self.settings = settings
        self.scripts_dir = Path(__file__).parent / "scripts"

        if not self.scripts_dir.exists():
            raise AppleScriptError(f"Scripts directory not found: {self.scripts_dir}")

    def execute(
        self,
        script_name: str,
        placeholders: Optional[Dict[str, str]] = None,
        retry: bool = True
    ) -> str:
        """Execute an AppleScript template with optional retry logic.

        Args:
            script_name: Name of script file (without .applescript extension)
            placeholders: Dictionary of placeholder substitutions
            retry: Whether to retry on failure with exponential backoff

        Returns:
            Script output (stdout + result message)

        Raises:
            AppleScriptError: If script execution fails after all retries
        """
        script_path = self.scripts_dir / f"{script_name}.applescript"

        if not script_path.exists():
            raise AppleScriptError(f"Script not found: {script_path}")

        # Load and substitute template
        script_content = self._load_and_substitute(script_path, placeholders or {})

        # Execute with retry logic
        if retry:
            return self._execute_with_retry(script_name, script_content)
        else:
            return self._execute_once(script_content)

    def _load_and_substitute(self, script_path: Path, placeholders: Dict[str, str]) -> str:
        """Load template and substitute placeholders.

        Args:
            script_path: Path to AppleScript template file
            placeholders: Dictionary of {placeholder: value} substitutions

        Returns:
            Script content with placeholders replaced
        """
        with open(script_path, 'r') as f:
            content = f.read()

        # Substitute all placeholders
        for key, value in placeholders.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))

        return content

    def _execute_once(self, script_content: str) -> str:
        """Execute AppleScript once without retry.

        Args:
            script_content: Complete AppleScript code to execute

        Returns:
            Script output

        Raises:
            AppleScriptError: If execution fails
        """
        try:
            # Execute via osascript
            result = subprocess.run(
                ["osascript", "-e", script_content],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for long operations
            )

            # Check for errors in stderr
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise AppleScriptError(
                    f"AppleScript execution failed (exit code {result.returncode}): {error_msg}"
                )

            # Return stdout + any result value
            output = result.stdout.strip()
            return output if output else "Script executed successfully"

        except subprocess.TimeoutExpired as e:
            raise AppleScriptError(f"AppleScript execution timed out after 120 seconds") from e
        except OSError as e:
            raise AppleScriptError(f"Failed to execute osascript: {e}") from e

    def _execute_with_retry(self, script_name: str, script_content: str) -> str:
        """Execute AppleScript with exponential backoff retry logic.

        Args:
            script_name: Name of script (for error messages)
            script_content: Complete AppleScript code to execute

        Returns:
            Script output

        Raises:
            AppleScriptError: If all retry attempts fail
        """
        max_attempts = self.settings.applescript_retry_attempts
        base_delay = self.settings.applescript_retry_delay
        last_error = None

        for attempt in range(max_attempts):
            try:
                return self._execute_once(script_content)

            except AppleScriptError as e:
                last_error = e

                # Check if error is retryable
                if not self._is_retryable_error(str(e)):
                    # Non-retryable error, fail immediately
                    raise

                # Calculate exponential backoff delay
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Attempt {attempt + 1}/{max_attempts} failed for {script_name}. "
                          f"Retrying in {delay}s...")
                    time.sleep(delay)

        # All attempts failed
        raise AppleScriptError(
            f"Script '{script_name}' failed after {max_attempts} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    def _is_retryable_error(self, error_message: str) -> bool:
        """Determine if an error is worth retrying.

        Timing-related errors are retryable (window not found, element not ready).
        Logic errors are not retryable (wrong sample rate, missing file).

        Args:
            error_message: Error message from AppleScript

        Returns:
            True if error should be retried, False otherwise
        """
        retryable_patterns = [
            "did not appear",
            "not found",
            "doesn't exist",
            "can't get",
            "timeout",
            "timed out"
        ]

        non_retryable_patterns = [
            "CRITICAL:",  # Our explicit critical errors
            "Unsupported sample rate",
            "Unsupported bit depth",
            "Failed to disable Apply SRC"  # Checkbox verification failure
        ]

        error_lower = error_message.lower()

        # Check non-retryable patterns first
        for pattern in non_retryable_patterns:
            if pattern.lower() in error_lower:
                return False

        # Check retryable patterns
        for pattern in retryable_patterns:
            if pattern.lower() in error_lower:
                return True

        # Default: retry if we're unsure
        return True
