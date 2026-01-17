"""MainWindow for Pro Tools Session Builder.

PySide6 desktop application with three main sections:
1. Top: Job creation form (artist, song, project, folders, settings)
2. Middle: Queue table (song name, artist, status, progress)
3. Bottom: Progress bar and real-time log output
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.audio_analyzer import AudioAnalyzer
from src.core.folder_scanner import FolderScanner
from src.core.path_resolver import PathResolver
from src.core.session_spec import SessionSpec
from src.protools.settings import AppSettings
from src.queue.job import Job, JobStatus


class MainWindow(QMainWindow):
    """Main application window for Pro Tools Session Builder."""

    # Signals
    add_job_requested = Signal(SessionSpec)
    start_queue_requested = Signal()
    pause_queue_requested = Signal()
    clear_queue_requested = Signal()
    remove_job_requested = Signal(str)  # job_id

    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Pro Tools Session Builder")
        self.setMinimumSize(900, 700)

        # Central widget with vertical layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add three main sections
        layout.addWidget(self._create_job_form_section())
        layout.addWidget(self._create_queue_section())
        layout.addWidget(self._create_progress_section())

        # Set stretch factors (form: 0, queue: 2, progress: 1)
        layout.setStretch(0, 0)  # Fixed height for form
        layout.setStretch(1, 2)  # Queue table gets most space
        layout.setStretch(2, 1)  # Progress/logs get less space

    def _create_job_form_section(self) -> QGroupBox:
        """Create the top section: job creation form."""
        group = QGroupBox("New Session")
        form_layout = QFormLayout()

        # Artist name
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Enter artist name")
        form_layout.addRow("Artist:", self.artist_input)

        # Song name
        self.song_input = QLineEdit()
        self.song_input.setPlaceholderText("Enter song name")
        form_layout.addRow("Song:", self.song_input)

        # Project name (for album mode)
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("Leave empty for single song mode")
        self.project_input.setEnabled(False)  # Disabled until checkbox checked
        form_layout.addRow("Project:", self.project_input)

        # Album mode checkbox
        self.album_mode_checkbox = QCheckBox("Part of larger project (Album/EP)")
        self.album_mode_checkbox.stateChanged.connect(self._on_album_mode_changed)
        form_layout.addRow("", self.album_mode_checkbox)

        # Source folder selector
        source_layout = QHBoxLayout()
        self.source_folder_input = QLineEdit()
        self.source_folder_input.setPlaceholderText("Select folder containing audio/MIDI files")
        source_browse_btn = QPushButton("Browse...")
        source_browse_btn.clicked.connect(self._browse_source_folder)
        source_layout.addWidget(self.source_folder_input)
        source_layout.addWidget(source_browse_btn)
        form_layout.addRow("Source Folder:", source_layout)

        # Template file selector (optional)
        template_layout = QHBoxLayout()
        self.template_file_input = QLineEdit()
        self.template_file_input.setPlaceholderText("Optional: Select .ptx template file")
        template_browse_btn = QPushButton("Browse...")
        template_browse_btn.clicked.connect(self._browse_template_file)
        template_clear_btn = QPushButton("Clear")
        template_clear_btn.clicked.connect(lambda: self.template_file_input.clear())
        template_layout.addWidget(self.template_file_input)
        template_layout.addWidget(template_browse_btn)
        template_layout.addWidget(template_clear_btn)
        form_layout.addRow("Template:", template_layout)

        # Root output directory selector
        output_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Select root output directory")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(output_browse_btn)
        form_layout.addRow("Output Directory:", output_layout)

        # Add to queue button
        self.add_to_queue_btn = QPushButton("Add to Queue")
        self.add_to_queue_btn.clicked.connect(self._on_add_to_queue)
        self.add_to_queue_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }"
        )
        form_layout.addRow("", self.add_to_queue_btn)

        group.setLayout(form_layout)
        return group

    def _create_queue_section(self) -> QGroupBox:
        """Create the middle section: queue table."""
        group = QGroupBox("Queue")

        layout = QVBoxLayout()

        # Queue control buttons
        button_layout = QHBoxLayout()
        self.start_queue_btn = QPushButton("Start Queue")
        self.start_queue_btn.clicked.connect(self.start_queue_requested.emit)
        self.pause_queue_btn = QPushButton("Pause Queue")
        self.pause_queue_btn.clicked.connect(self.pause_queue_requested.emit)
        self.pause_queue_btn.setEnabled(False)
        self.clear_queue_btn = QPushButton("Clear All")
        self.clear_queue_btn.clicked.connect(self._on_clear_queue)
        self.remove_job_btn = QPushButton("Remove Selected")
        self.remove_job_btn.clicked.connect(self._on_remove_job)

        button_layout.addWidget(self.start_queue_btn)
        button_layout.addWidget(self.pause_queue_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.remove_job_btn)
        button_layout.addWidget(self.clear_queue_btn)

        layout.addLayout(button_layout)

        # Queue table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Song", "Artist", "Status", "Progress"])
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SingleSelection)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Configure column widths
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Song
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Artist
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Progress

        layout.addWidget(self.queue_table)

        group.setLayout(layout)
        return group

    def _create_progress_section(self) -> QGroupBox:
        """Create the bottom section: progress bar and logs."""
        group = QGroupBox("Progress")

        layout = QVBoxLayout()

        # Current job label
        self.current_job_label = QLabel("No job running")
        self.current_job_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.current_job_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status message
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Log output
        log_label = QLabel("Log Output:")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        layout.addWidget(self.log_output)

        group.setLayout(layout)
        return group

    # Slots for UI interactions

    @Slot()
    def _on_album_mode_changed(self):
        """Enable/disable project name input based on album mode checkbox."""
        is_album_mode = self.album_mode_checkbox.isChecked()
        self.project_input.setEnabled(is_album_mode)
        if not is_album_mode:
            self.project_input.clear()

    @Slot()
    def _browse_source_folder(self):
        """Open folder browser for source folder selection."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder", str(Path.home())
        )
        if folder:
            self.source_folder_input.setText(folder)

    @Slot()
    def _browse_template_file(self):
        """Open file browser for template selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Pro Tools Template",
            str(Path.home()),
            "Pro Tools Session (*.ptx);;All Files (*)",
        )
        if file_path:
            self.template_file_input.setText(file_path)

    @Slot()
    def _browse_output_dir(self):
        """Open folder browser for output directory selection."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", str(self.settings.root_output_dir)
        )
        if folder:
            self.output_dir_input.setText(folder)

    @Slot()
    def _on_add_to_queue(self):
        """Validate form and emit signal to add job to queue."""
        # Validate required fields
        artist = self.artist_input.text().strip()
        song = self.song_input.text().strip()
        source_folder = self.source_folder_input.text().strip()
        output_dir = self.output_dir_input.text().strip()

        if not artist:
            self._show_error("Artist name is required")
            return
        if not song:
            self._show_error("Song name is required")
            return
        if not source_folder:
            self._show_error("Source folder is required")
            return
        if not output_dir:
            self._show_error("Output directory is required")
            return

        # Validate paths exist
        if not Path(source_folder).is_dir():
            self._show_error(f"Source folder does not exist: {source_folder}")
            return
        if not Path(output_dir).is_dir():
            self._show_error(f"Output directory does not exist: {output_dir}")
            return

        # Get optional fields
        project = self.project_input.text().strip() if self.album_mode_checkbox.isChecked() else None
        template_path = self.template_file_input.text().strip() or None

        # Validate template if provided
        if template_path and not Path(template_path).is_file():
            self._show_error(f"Template file does not exist: {template_path}")
            return

        try:
            # Step 1: Scan source folder for audio and MIDI files
            scanner = FolderScanner()
            audio_files, midi_files = scanner.scan_folder(Path(source_folder))

            if not audio_files and not midi_files:
                self._show_error(f"No audio or MIDI files found in {source_folder}")
                return

            # Step 2: Analyze audio files to get sample rate and bit depth
            sample_rate = 44100  # Default
            bit_depth = 24  # Default

            if audio_files:
                analyzer = AudioAnalyzer()
                audio_specs = analyzer.validate_folder(audio_files)
                sample_rate = audio_specs["sample_rate"]
                bit_depth = audio_specs["bit_depth"]
                self._log_message(f"Detected: {sample_rate}Hz, {bit_depth}-bit from {len(audio_files)} audio file(s)")
            else:
                # MIDI-only session, use defaults
                self._log_message(f"MIDI-only session, using defaults: {sample_rate}Hz, {bit_depth}-bit")

            # Step 3: Resolve output paths
            path_resolver = PathResolver(Path(output_dir))
            resolved_output_dir, session_file = path_resolver.resolve_paths(
                artist=artist,
                song_name=song,
                project_name=project
            )

            # Step 4: Create SessionSpec with all required parameters
            spec = SessionSpec(
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                audio_files=tuple(audio_files),
                midi_files=tuple(midi_files),
                output_dir=resolved_output_dir,
                session_file=session_file,
                artist=artist,
                song_name=song,
                project_name=project,
                template_path=Path(template_path) if template_path else None,
            )

            # Emit signal to add job
            self.add_job_requested.emit(spec)

            # Clear form after successful add
            self._clear_form()
            self._log_message(f"Added to queue: {spec.song_name} by {spec.artist}")

        except Exception as e:
            self._show_error(f"Failed to create session: {str(e)}")

    @Slot()
    def _on_clear_queue(self):
        """Emit signal to clear the queue."""
        self.clear_queue_requested.emit()

    @Slot()
    def _on_remove_job(self):
        """Emit signal to remove selected job from queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            self._show_error("No job selected")
            return

        row = selected_rows[0].row()
        job_id_item = self.queue_table.item(row, 0)
        if job_id_item:
            job_id = job_id_item.data(Qt.UserRole)  # Stored in item data
            if job_id:
                self.remove_job_requested.emit(job_id)

    # Public methods for external updates (called by controller/worker)

    @Slot(list)
    def update_queue_table(self, jobs: list[Job]):
        """Update the queue table with current jobs."""
        self.queue_table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            # Song name (store job_id in UserRole)
            song_item = QTableWidgetItem(job.spec.song_name)
            song_item.setData(Qt.UserRole, job.job_id)
            self.queue_table.setItem(row, 0, song_item)

            # Artist
            artist_item = QTableWidgetItem(job.spec.artist)
            self.queue_table.setItem(row, 1, artist_item)

            # Status
            status_item = QTableWidgetItem(job.status.value)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.queue_table.setItem(row, 2, status_item)

            # Progress
            progress_text = f"{job.progress}%" if job.progress > 0 else "-"
            progress_item = QTableWidgetItem(progress_text)
            progress_item.setTextAlignment(Qt.AlignCenter)
            self.queue_table.setItem(row, 3, progress_item)

    @Slot(str, int)
    def update_job_progress(self, job_name: str, progress: int):
        """Update progress bar and current job label."""
        self.current_job_label.setText(f"Processing: {job_name}")
        self.progress_bar.setValue(progress)

    @Slot(str)
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.setText(message)

    @Slot(str)
    def log_message(self, message: str):
        """Append message to log output (thread-safe via signal)."""
        self._log_message(message)

    @Slot(bool)
    def set_queue_running(self, is_running: bool):
        """Update UI state based on queue running status."""
        self.start_queue_btn.setEnabled(not is_running)
        self.pause_queue_btn.setEnabled(is_running)
        self.add_to_queue_btn.setEnabled(not is_running)

    # Private helper methods

    def _clear_form(self):
        """Clear form inputs (only song and source folder).

        Persist artist, project, template, and output directory for batch processing.
        """
        # Only clear song name and source folder
        self.song_input.clear()
        self.source_folder_input.clear()

        # Keep these for next song in same project:
        # - artist_input
        # - project_input
        # - album_mode_checkbox
        # - template_file_input
        # - output_dir_input

    def _show_error(self, message: str):
        """Show error in status label and log."""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self._log_message(f"ERROR: {message}")

    def _log_message(self, message: str):
        """Append message to log output."""
        self.log_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _load_settings(self):
        """Load saved settings into UI."""
        # Set output directory from settings
        if self.settings.root_output_dir:
            self.output_dir_input.setText(str(self.settings.root_output_dir))

    def closeEvent(self, event):
        """Handle window close event."""
        # Save current output directory to settings
        output_dir = self.output_dir_input.text().strip()
        if output_dir and Path(output_dir).is_dir():
            self.settings.root_output_dir = Path(output_dir)

        event.accept()
