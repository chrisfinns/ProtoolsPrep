"""Reliability helpers for Pro Tools UI scripting."""

import subprocess
import time
from typing import Optional

from src.core.exceptions import AppleScriptError


class UIScriptingUtils:
    """Utility functions for reliable Pro Tools UI automation.

    These helpers provide polling-based operations that are more reliable
    than fixed delays. They handle common scenarios like waiting for
    windows to appear, checking for import completion, and error cleanup.
    """

    @staticmethod
    def wait_for_window(window_name: str, timeout: int = 10) -> bool:
        """Poll for window appearance with timeout.

        Args:
            window_name: Name of window to wait for
            timeout: Maximum seconds to wait

        Returns:
            True if window appeared, False if timeout

        Example:
            if UIScriptingUtils.wait_for_window("Dashboard", 10):
                print("Dashboard ready")
        """
        script = f"""
        tell application "System Events"
            tell process "Pro Tools"
                set maxAttempts to {timeout}
                set attemptCount to 0

                repeat while attemptCount < maxAttempts
                    if exists window "{window_name}" then
                        return true
                    end if
                    delay 1
                    set attemptCount to attemptCount + 1
                end repeat

                return false
            end tell
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            return result.stdout.strip() == "true"
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def wait_for_import_completion(timeout: int = 60) -> bool:
        """Poll for import operation completion.

        Checks for "Importing" progress window to disappear.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if import completed, False if timeout

        Example:
            if UIScriptingUtils.wait_for_import_completion(60):
                print("Import finished")
        """
        script = f"""
        tell application "System Events"
            tell process "Pro Tools"
                set maxAttempts to {timeout}
                set attemptCount to 0

                repeat while attemptCount < maxAttempts
                    -- Import is complete when progress window closes
                    if not (exists window 1 whose name contains "Importing") then
                        return true
                    end if
                    delay 1
                    set attemptCount to attemptCount + 1
                end repeat

                return false
            end tell
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            return result.stdout.strip() == "true"
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def dismiss_warning(text_pattern: str, timeout: int = 5) -> bool:
        """Find and dismiss a warning dialog by text pattern.

        Args:
            text_pattern: Text to search for in dialog name/description
            timeout: Maximum seconds to wait for dialog

        Returns:
            True if dialog was found and dismissed, False otherwise

        Example:
            UIScriptingUtils.dismiss_warning("Session Start Time", 5)
        """
        script = f"""
        tell application "System Events"
            tell process "Pro Tools"
                set maxAttempts to {timeout}
                set attemptCount to 0

                repeat while attemptCount < maxAttempts
                    -- Look for dialog containing the text pattern
                    if exists window 1 whose name contains "{text_pattern}" then
                        tell window 1
                            -- Try different button names
                            try
                                click button "OK"
                                return true
                            on error
                                try
                                    click button "Continue"
                                    return true
                                on error
                                    try
                                        click button 1
                                        return true
                                    end try
                                end try
                            end try
                        end tell
                    end if

                    delay 1
                    set attemptCount to attemptCount + 1
                end repeat

                return false
            end tell
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            return result.stdout.strip() == "true"
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def verify_checkbox(checkbox_name: str, expected_value: int) -> bool:
        """Verify a checkbox has the expected value.

        Args:
            checkbox_name: Name of checkbox to verify
            expected_value: Expected value (0 = unchecked, 1 = checked)

        Returns:
            True if checkbox has expected value, False otherwise

        Raises:
            AppleScriptError: If checkbox cannot be found

        Example:
            if not UIScriptingUtils.verify_checkbox("Apply SRC", 0):
                raise AppleScriptError("Apply SRC is still checked!")
        """
        script = f"""
        tell application "System Events"
            tell process "Pro Tools"
                tell window 1
                    set actualValue to value of checkbox "{checkbox_name}"
                    if actualValue is {expected_value} then
                        return true
                    else
                        return false
                    end if
                end tell
            end tell
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                raise AppleScriptError(
                    f"Could not find checkbox '{checkbox_name}': {result.stderr}"
                )

            return result.stdout.strip() == "true"
        except subprocess.TimeoutExpired as e:
            raise AppleScriptError(f"Timeout verifying checkbox '{checkbox_name}'") from e
        except OSError as e:
            raise AppleScriptError(f"Failed to execute verification: {e}") from e

    @staticmethod
    def cleanup_on_error() -> None:
        """Emergency cleanup: Press Escape and attempt to close session.

        Call this when workflow fails to reset Pro Tools to a clean state.
        Does not raise exceptions - best effort cleanup only.

        Example:
            try:
                workflow.import_audio(files)
            except Exception:
                UIScriptingUtils.cleanup_on_error()
                raise
        """
        script = """
        tell application "System Events"
            tell process "Pro Tools"
                -- Press Escape multiple times to close any dialogs
                repeat 3 times
                    key code 53  -- Escape key
                    delay 0.5
                end repeat

                -- Try to close current session (Cmd+W)
                keystroke "w" using command down
                delay 1

                -- If save dialog appears, click "Don't Save"
                if exists window 1 whose name contains "Save" then
                    tell window 1
                        try
                            click button "Don't Save"
                        on error
                            try
                                click button "No"
                            end try
                        end try
                    end tell
                end if
            end tell
        end tell
        """

        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
        except (subprocess.TimeoutExpired, OSError):
            # Best effort - don't raise if cleanup fails
            pass

    @staticmethod
    def check_accessibility_permissions() -> bool:
        """Check if accessibility permissions are granted for Terminal/IDE.

        Returns:
            True if permissions are granted, False otherwise

        Example:
            if not UIScriptingUtils.check_accessibility_permissions():
                print("Please enable accessibility permissions in System Preferences")
        """
        script = """
        tell application "System Events"
            try
                -- Try to access any running process (Finder is always running)
                tell process "Finder"
                    get name
                    return true
                end tell
            on error
                return false
            end try
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "true"
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def get_accessibility_instructions() -> str:
        """Get user-friendly instructions for enabling accessibility permissions.

        Returns:
            Formatted instructions string
        """
        return """
Accessibility Permissions Required
===================================

Pro Tools Session Builder requires accessibility permissions to automate Pro Tools.

To enable:
1. Open System Preferences → Security & Privacy → Privacy
2. Select "Accessibility" in the left sidebar
3. Click the lock icon to make changes
4. Add your terminal app (Terminal.app, iTerm, or your IDE)
5. Check the box next to the app to enable permissions
6. Restart this application

Without these permissions, UI automation will not work.
"""
