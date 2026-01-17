"""Main entry point for Pro Tools Session Builder.

Usage:
    python src/main.py          # Normal mode
    python src/main.py --debug  # Debug mode (verbose logging)
"""

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from src.protools.ui_scripting_utils import UIScriptingUtils
from src.ui import AppController, MainWindow


def setup_logging(debug: bool = False):
    """Configure logging for the application.

    Args:
        debug: If True, set log level to DEBUG, otherwise INFO
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("protools_session_builder.log"),
        ],
    )

    logger = logging.getLogger(__name__)
    if debug:
        logger.info("Debug mode enabled - verbose logging active")


def check_permissions() -> bool:
    """Check if accessibility permissions are granted.

    Returns:
        True if permissions are granted, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        has_permissions = UIScriptingUtils.check_accessibility_permissions()

        if not has_permissions:
            logger.warning("Accessibility permissions not granted")
            instructions = UIScriptingUtils.get_accessibility_instructions()

            # Show instructions dialog
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Accessibility Permissions Required")
            msg.setText(
                "Pro Tools Session Builder requires accessibility permissions to automate Pro Tools."
            )
            msg.setInformativeText(instructions)
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.setDefaultButton(QMessageBox.Ok)

            result = msg.exec()

            if result == QMessageBox.Cancel:
                logger.info("User cancelled - exiting")
                return False

            # User clicked OK - recheck permissions
            has_permissions = UIScriptingUtils.check_accessibility_permissions()

            if not has_permissions:
                logger.warning("Permissions still not granted")
                QMessageBox.critical(
                    None,
                    "Permissions Not Granted",
                    "Accessibility permissions are required. Please grant permissions and restart the application.",
                )
                return False

        logger.info("Accessibility permissions verified")
        return True

    except Exception as e:
        logger.exception("Error checking accessibility permissions")
        QMessageBox.critical(
            None,
            "Permission Check Failed",
            f"Failed to verify accessibility permissions: {str(e)}",
        )
        return False


def show_welcome_message(window: MainWindow):
    """Show welcome message with usage tips."""
    welcome_text = """
Welcome to Pro Tools Session Builder!

Quick Start:
1. Fill in Artist and Song name
2. Select source folder with audio/MIDI files
3. Select output directory (where sessions will be created)
4. Click "Add to Queue"
5. Click "Start Queue" to begin automation

Tips:
- For albums/EPs, check "Part of larger project" and enter Project name
- Template import is optional - leave blank to create empty session
- Pro Tools must be installed and you must have accessibility permissions
- Queue executes serially (one session at a time)

Settings are saved automatically.
"""
    window.log_message(welcome_text.strip())


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Pro Tools Session Builder")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (verbose logging)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    logger.info("Starting Pro Tools Session Builder")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Pro Tools Session Builder")
    app.setOrganizationName("Pro Tools Prepper")

    # Check accessibility permissions
    if not check_permissions():
        logger.error("Accessibility permissions not granted - exiting")
        return 1


    # Create main window and controller
    window = MainWindow()
    controller = AppController(window)

    # Show welcome message
    show_welcome_message(window)

    # Show window
    window.show()

    # Start event loop
    logger.info("Application started")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
