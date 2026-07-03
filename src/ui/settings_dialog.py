"""Settings dialog for Pro Tools Session Builder.

Provides a tabbed interface for configuring:
1. Paths: Output directory, template file
2. Timing: Dialog waits, import timeouts, retry configuration
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.protools.settings import AppSettings


class SettingsDialog(QDialog):
    """Settings dialog with tabs for path and timing configuration."""

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = settings
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_paths_tab(), "Paths")
        tabs.addTab(self._create_timing_tab(), "Timing")
        layout.addWidget(tabs)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._on_restore_defaults)
        layout.addWidget(button_box)

    def _create_paths_tab(self) -> QWidget:
        """Create the Paths configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Output Directory
        output_group = QGroupBox("Output Directory")
        output_layout = QFormLayout()

        output_row = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Root directory for all sessions")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self._browse_output_dir)
        output_row.addWidget(self.output_dir_input)
        output_row.addWidget(output_browse_btn)

        output_help = QLabel("All sessions will be created under this directory")
        output_help.setStyleSheet("color: gray; font-size: 10pt;")

        output_layout.addRow("Root Directory:", output_row)
        output_layout.addRow("", output_help)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Template File
        template_group = QGroupBox("Default Template")
        template_layout = QFormLayout()

        template_row = QHBoxLayout()
        self.template_file_input = QLineEdit()
        self.template_file_input.setPlaceholderText("Optional: Default .ptx template")
        template_browse_btn = QPushButton("Browse...")
        template_browse_btn.clicked.connect(self._browse_template_file)
        template_clear_btn = QPushButton("Clear")
        template_clear_btn.clicked.connect(lambda: self.template_file_input.clear())
        template_row.addWidget(self.template_file_input)
        template_row.addWidget(template_browse_btn)
        template_row.addWidget(template_clear_btn)

        template_help = QLabel("This template will be automatically loaded when creating new sessions")
        template_help.setStyleSheet("color: gray; font-size: 10pt;")

        template_layout.addRow("Template File:", template_row)
        template_layout.addRow("", template_help)
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        layout.addStretch()
        return widget

    def _create_timing_tab(self) -> QWidget:
        """Create the Timing configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # PTSL Timing (primary automation path)
        ptsl_group = QGroupBox("Pro Tools Scripting (PTSL)")
        ptsl_layout = QFormLayout()

        ptsl_help = QLabel(
            "Pacing for the official Pro Tools API. Increase settle time if "
            "Pro Tools becomes unresponsive during batches."
        )
        ptsl_help.setStyleSheet("color: gray; font-size: 10pt;")
        ptsl_help.setWordWrap(True)
        ptsl_layout.addRow("", ptsl_help)

        self.ptsl_settle_input = QDoubleSpinBox()
        self.ptsl_settle_input.setRange(1.0, 60.0)
        self.ptsl_settle_input.setSingleStep(1.0)
        self.ptsl_settle_input.setSuffix(" seconds")
        self.ptsl_settle_input.setDecimals(1)
        ptsl_layout.addRow("Settle Time After Operations:", self.ptsl_settle_input)

        self.ptsl_connect_timeout_input = QDoubleSpinBox()
        self.ptsl_connect_timeout_input.setRange(30.0, 600.0)
        self.ptsl_connect_timeout_input.setSingleStep(30.0)
        self.ptsl_connect_timeout_input.setSuffix(" seconds")
        self.ptsl_connect_timeout_input.setDecimals(1)
        ptsl_layout.addRow("Launch/Connect Timeout:", self.ptsl_connect_timeout_input)

        self.save_poll_timeout_input = QDoubleSpinBox()
        self.save_poll_timeout_input.setRange(5.0, 300.0)
        self.save_poll_timeout_input.setSingleStep(5.0)
        self.save_poll_timeout_input.setSuffix(" seconds")
        self.save_poll_timeout_input.setDecimals(1)
        ptsl_layout.addRow("Save Verification Timeout:", self.save_poll_timeout_input)

        self.user_dialog_timeout_input = QDoubleSpinBox()
        self.user_dialog_timeout_input.setRange(60.0, 3600.0)
        self.user_dialog_timeout_input.setSingleStep(60.0)
        self.user_dialog_timeout_input.setSuffix(" seconds")
        self.user_dialog_timeout_input.setDecimals(0)
        ptsl_layout.addRow("Wait for Manual Dialog Dismissal:", self.user_dialog_timeout_input)

        user_dialog_note = QLabel(
            "iLok/PACE activation windows can't be dismissed automatically - "
            "jobs wait this long for you to click Quit on them."
        )
        user_dialog_note.setStyleSheet("color: gray; font-size: 10pt; font-style: italic;")
        user_dialog_note.setWordWrap(True)
        ptsl_layout.addRow("", user_dialog_note)

        ptsl_group.setLayout(ptsl_layout)
        layout.addWidget(ptsl_group)

        # AppleScript Timing (surviving scripts: MIDI import, dialog supervisor)
        applescript_group = QGroupBox("AppleScript (MIDI Import / Dialogs)")
        applescript_layout = QFormLayout()

        applescript_help = QLabel(
            "Used only by the remaining UI-scripting steps: MIDI import and "
            "dialog dismissal."
        )
        applescript_help.setStyleSheet("color: gray; font-size: 10pt;")
        applescript_help.setWordWrap(True)
        applescript_layout.addRow("", applescript_help)

        self.dialog_wait_input = QDoubleSpinBox()
        self.dialog_wait_input.setRange(0.5, 10.0)
        self.dialog_wait_input.setSingleStep(0.5)
        self.dialog_wait_input.setSuffix(" seconds")
        self.dialog_wait_input.setDecimals(1)
        applescript_layout.addRow("Dialog Wait Time:", self.dialog_wait_input)

        self.midi_import_timeout_input = QDoubleSpinBox()
        self.midi_import_timeout_input.setRange(10.0, 300.0)
        self.midi_import_timeout_input.setSingleStep(10.0)
        self.midi_import_timeout_input.setSuffix(" seconds")
        self.midi_import_timeout_input.setDecimals(1)
        applescript_layout.addRow("MIDI Import Timeout:", self.midi_import_timeout_input)

        applescript_group.setLayout(applescript_layout)
        layout.addWidget(applescript_group)

        layout.addStretch()
        return widget

    @Slot()
    def _browse_output_dir(self):
        """Open folder browser for output directory selection."""
        current_dir = self.output_dir_input.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current_dir
        )
        if folder:
            self.output_dir_input.setText(folder)

    @Slot()
    def _browse_template_file(self):
        """Open file browser for template selection."""
        current_template = self.template_file_input.text() or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Pro Tools Template",
            current_template,
            "Pro Tools Session (*.ptx);;All Files (*)",
        )
        if file_path:
            self.template_file_input.setText(file_path)

    @Slot()
    def _on_accept(self):
        """Save settings and close dialog."""
        # Save path settings
        output_dir = self.output_dir_input.text().strip()
        if output_dir and Path(output_dir).is_dir():
            self.settings.set_root_output_dir(Path(output_dir))

        template_path = self.template_file_input.text().strip()
        if template_path:
            if Path(template_path).is_file():
                self.settings.set_last_template_path(Path(template_path))
        else:
            # Clear template if input is empty
            self.settings.set_last_template_path(None)

        # Save timing settings
        self.settings.ptsl_settle_time = self.ptsl_settle_input.value()
        self.settings.ptsl_connect_timeout = self.ptsl_connect_timeout_input.value()
        self.settings.save_poll_timeout = self.save_poll_timeout_input.value()
        self.settings.user_dialog_timeout = self.user_dialog_timeout_input.value()
        self.settings.dialog_wait_time = self.dialog_wait_input.value()
        self.settings.midi_import_timeout = self.midi_import_timeout_input.value()

        # Persist to disk
        self.settings.save()

        self.accept()

    @Slot()
    def _on_restore_defaults(self):
        """Restore default settings."""
        defaults = AppSettings()
        defaults.root_output_dir = str(Path.cwd() / "testing")

        # Load defaults into UI
        self.output_dir_input.setText(defaults.root_output_dir or "")
        self.template_file_input.clear()
        self.ptsl_settle_input.setValue(defaults.ptsl_settle_time)
        self.ptsl_connect_timeout_input.setValue(defaults.ptsl_connect_timeout)
        self.save_poll_timeout_input.setValue(defaults.save_poll_timeout)
        self.user_dialog_timeout_input.setValue(defaults.user_dialog_timeout)
        self.dialog_wait_input.setValue(defaults.dialog_wait_time)
        self.midi_import_timeout_input.setValue(defaults.midi_import_timeout)

    def _load_settings(self):
        """Load current settings into UI."""
        # Load paths
        if self.settings.root_output_dir:
            self.output_dir_input.setText(self.settings.root_output_dir)

        if self.settings.last_template_path:
            self.template_file_input.setText(self.settings.last_template_path)

        # Load timing settings
        self.ptsl_settle_input.setValue(self.settings.ptsl_settle_time)
        self.ptsl_connect_timeout_input.setValue(self.settings.ptsl_connect_timeout)
        self.save_poll_timeout_input.setValue(self.settings.save_poll_timeout)
        self.user_dialog_timeout_input.setValue(self.settings.user_dialog_timeout)
        self.dialog_wait_input.setValue(self.settings.dialog_wait_time)
        self.midi_import_timeout_input.setValue(self.settings.midi_import_timeout)
