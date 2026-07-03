"""Accessibility permission checks for the surviving UI-scripting steps.

PTSL needs no accessibility permission, but the MIDI import script and the
dialog supervisor still drive System Events, which does.
"""

import subprocess


def check_accessibility_permissions() -> bool:
    """Check if accessibility permissions are granted for this process.

    Returns:
        True if System Events can control other processes, False otherwise.
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
            timeout=5,
        )
        return result.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, OSError):
        return False


def get_accessibility_instructions() -> str:
    """User-friendly instructions for enabling accessibility permissions."""
    return """
Accessibility Permissions Required
===================================

Pro Tools Session Builder uses the official Pro Tools API for most automation,
but MIDI import and dialog dismissal still require accessibility permissions.

To enable:
1. Open System Settings → Privacy & Security → Accessibility
2. Add your terminal app (Terminal.app, iTerm, or your IDE)
3. Toggle the switch next to the app to enable permissions
4. Restart this application

Without these permissions, MIDI import and automatic dialog dismissal will fail.
"""
