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
    QSpinBox,
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

        # Dialog Timing
        dialog_group = QGroupBox("Dialog Timing")
        dialog_layout = QFormLayout()

        dialog_help = QLabel("Adjust these if Pro Tools UI interactions are unreliable")
        dialog_help.setStyleSheet("color: gray; font-size: 10pt;")
        dialog_layout.addRow("", dialog_help)

        self.dialog_wait_input = QDoubleSpinBox()
        self.dialog_wait_input.setRange(0.5, 10.0)
        self.dialog_wait_input.setSingleStep(0.5)
        self.dialog_wait_input.setSuffix(" seconds")
        self.dialog_wait_input.setDecimals(1)
        dialog_layout.addRow("Dialog Wait Time:", self.dialog_wait_input)

        self.window_timeout_input = QDoubleSpinBox()
        self.window_timeout_input.setRange(5.0, 60.0)
        self.window_timeout_input.setSingleStep(5.0)
        self.window_timeout_input.setSuffix(" seconds")
        self.window_timeout_input.setDecimals(1)
        dialog_layout.addRow("Window Appearance Timeout:", self.window_timeout_input)

        dialog_group.setLayout(dialog_layout)
        layout.addWidget(dialog_group)

        # Import Timing
        import_group = QGroupBox("Import Timing")
        import_layout = QFormLayout()

        import_help = QLabel("Maximum time to wait for audio/MIDI/template imports to complete")
        import_help.setStyleSheet("color: gray; font-size: 10pt;")
        import_layout.addRow("", import_help)

        self.import_timeout_input = QDoubleSpinBox()
        self.import_timeout_input.setRange(10.0, 300.0)
        self.import_timeout_input.setSingleStep(10.0)
        self.import_timeout_input.setSuffix(" seconds")
        self.import_timeout_input.setDecimals(1)
        import_layout.addRow("Import Completion Timeout:", self.import_timeout_input)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        # Retry Configuration
        retry_group = QGroupBox("Retry Configuration")
        retry_layout = QFormLayout()

        retry_help = QLabel("AppleScript retry behavior for transient failures")
        retry_help.setStyleSheet("color: gray; font-size: 10pt;")
        retry_layout.addRow("", retry_help)

        self.retry_attempts_input = QSpinBox()
        self.retry_attempts_input.setRange(1, 10)
        self.retry_attempts_input.setSingleStep(1)
        self.retry_attempts_input.setSuffix(" attempts")
        retry_layout.addRow("Retry Attempts:", self.retry_attempts_input)

        self.retry_delay_input = QDoubleSpinBox()
        self.retry_delay_input.setRange(0.5, 10.0)
        self.retry_delay_input.setSingleStep(0.5)
        self.retry_delay_input.setSuffix(" seconds")
        self.retry_delay_input.setDecimals(1)
        retry_layout.addRow("Base Retry Delay:", self.retry_delay_input)

        retry_note = QLabel("Uses exponential backoff: 2s → 4s → 8s")
        retry_note.setStyleSheet("color: gray; font-size: 10pt; font-style: italic;")
        retry_layout.addRow("", retry_note)

        retry_group.setLayout(retry_layout)
        layout.addWidget(retry_group)

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
        self.settings.dialog_wait_time = self.dialog_wait_input.value()
        self.settings.window_appearance_timeout = self.window_timeout_input.value()
        self.settings.import_completion_timeout = self.import_timeout_input.value()
        self.settings.applescript_retry_attempts = self.retry_attempts_input.value()
        self.settings.applescript_retry_delay = self.retry_delay_input.value()

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
        self.dialog_wait_input.setValue(defaults.dialog_wait_time)
        self.window_timeout_input.setValue(defaults.window_appearance_timeout)
        self.import_timeout_input.setValue(defaults.import_completion_timeout)
        self.retry_attempts_input.setValue(defaults.applescript_retry_attempts)
        self.retry_delay_input.setValue(defaults.applescript_retry_delay)

    def _load_settings(self):
        """Load current settings into UI."""
        # Load paths
        if self.settings.root_output_dir:
            self.output_dir_input.setText(self.settings.root_output_dir)

        if self.settings.last_template_path:
            self.template_file_input.setText(self.settings.last_template_path)

        # Load timing settings
        self.dialog_wait_input.setValue(self.settings.dialog_wait_time)
        self.window_timeout_input.setValue(self.settings.window_appearance_timeout)
        self.import_timeout_input.setValue(self.settings.import_completion_timeout)
        self.retry_attempts_input.setValue(self.settings.applescript_retry_attempts)
        self.retry_delay_input.setValue(self.settings.applescript_retry_delay)
