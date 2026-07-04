"""MainWindow for Pro Tools Session Builder.

PySide6 desktop application with three main sections:
1. Top: Job creation form (artist, song, project, folders, settings)
2. Middle: Queue table (song name, artist, status, progress)
3. Bottom: Progress bar and real-time log output
"""

import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QEvent, QUrl
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent
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
    QSplitter,
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
from src.ui import theme
from src.ui.settings_dialog import SettingsDialog

# Human-readable status labels (status is conveyed by text AND color)
STATUS_LABELS = {
    JobStatus.PENDING: "Pending",
    JobStatus.RUNNING: "● Running",
    JobStatus.COMPLETED: "✓ Completed",
    JobStatus.FAILED: "✕ Failed",
}


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
        self.settings = AppSettings.load()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Pro Tools Session Builder")
        self.setMinimumSize(900, 700)
        self.resize(980, 880)

        # Create menu bar
        self._create_menu_bar()

        # Central widget with vertical layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Form on top; queue and progress/log share a draggable splitter
        layout.addWidget(self._create_job_form_section())

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._create_queue_section())
        splitter.addWidget(self._create_progress_section())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 210])  # queue gets the room by default
        layout.addWidget(splitter, stretch=1)

    def _create_menu_bar(self):
        """Create application menu bar (native macOS menu bar).

        On macOS, Qt relocates Settings/Quit into the application menu
        (titled "Python" when running unbundled), which would leave File
        empty and hidden. Set the roles explicitly and keep a File menu
        entry for Settings so it stays discoverable.
        """
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        settings_action = file_menu.addAction("&Settings...")
        settings_action.setShortcut("Cmd+,")
        settings_action.setMenuRole(QAction.MenuRole.NoRole)
        settings_action.triggered.connect(self._open_settings_dialog)

        file_menu.addSeparator()

        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Cmd+Q")
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        quit_action.triggered.connect(self.close)

    def _create_job_form_section(self) -> QGroupBox:
        """Create the top section: job creation form."""
        group = QGroupBox("New Session")
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(10)

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
        self.source_folder_input.setPlaceholderText("Drag folder here or browse...")
        self.source_folder_input.setAcceptDrops(True)
        self.source_folder_input.dragEnterEvent = self._drag_enter_event
        self.source_folder_input.dropEvent = self._drop_event
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

        # Add to queue button (primary action - styled by theme)
        self.add_to_queue_btn = QPushButton("Add to Queue")
        self.add_to_queue_btn.setProperty("primary", True)
        self.add_to_queue_btn.clicked.connect(self._on_add_to_queue)
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
        self.start_queue_btn.setProperty("primary", True)
        self.start_queue_btn.clicked.connect(self.start_queue_requested.emit)
        self.pause_queue_btn = QPushButton("Pause Queue")
        self.pause_queue_btn.clicked.connect(self.pause_queue_requested.emit)
        self.pause_queue_btn.setEnabled(False)
        self.clear_queue_btn = QPushButton("Clear All")
        self.clear_queue_btn.clicked.connect(self._on_clear_queue)
        self.remove_job_btn = QPushButton("Remove Selected")
        self.remove_job_btn.clicked.connect(self._on_remove_job)
        self.settings_btn = QPushButton("Settings…")
        self.settings_btn.clicked.connect(self._open_settings_dialog)

        button_layout.addWidget(self.start_queue_btn)
        button_layout.addWidget(self.pause_queue_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.remove_job_btn)
        button_layout.addWidget(self.clear_queue_btn)
        button_layout.addWidget(self.settings_btn)

        layout.addLayout(button_layout)

        # Queue table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Song", "Artist", "Status", "Progress"])
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SingleSelection)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setShowGrid(False)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.cellDoubleClicked.connect(self._on_job_double_clicked)

        # Configure column widths
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Song
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Artist
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Progress
        header.resizeSection(3, 140)

        # Empty-state hint, shown until the first job is queued
        self.queue_empty_label = QLabel(
            "No sessions queued\nFill in the form above and click “Add to Queue”",
            self.queue_table.viewport(),
        )
        self.queue_empty_label.setAlignment(Qt.AlignCenter)
        self.queue_empty_label.setProperty("hint", True)
        self.queue_table.viewport().installEventFilter(self)

        layout.addWidget(self.queue_table)

        group.setLayout(layout)
        return group

    def eventFilter(self, obj, event):
        """Keep the queue empty-state hint centered over the table."""
        if obj is self.queue_table.viewport() and event.type() == QEvent.Resize:
            self.queue_empty_label.setGeometry(self.queue_table.viewport().rect())
        return super().eventFilter(obj, event)

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

        # Log output (height managed by the splitter)
        log_label = QLabel("Log Output")
        log_label.setProperty("hint", True)
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
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
        # Preserve the selected job across the refresh
        selected_job_id = None
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if selected_rows:
            item = self.queue_table.item(selected_rows[0].row(), 0)
            if item:
                selected_job_id = item.data(Qt.UserRole)

        self.queue_table.setRowCount(len(jobs))
        self.queue_empty_label.setVisible(len(jobs) == 0)

        for row, job in enumerate(jobs):
            status_color = QColor(theme.STATUS_COLORS[job.status.value])
            # Failed rows explain themselves on hover
            tooltip = job.error_message if job.status == JobStatus.FAILED else ""
            # Completed rows can be revealed in Finder
            if job.status == JobStatus.COMPLETED:
                tooltip = "Double-click to reveal the session in Finder"

            # Song name (store job_id and session file in item data)
            song_item = QTableWidgetItem(job.spec.song_name)
            song_item.setData(Qt.UserRole, job.job_id)
            song_item.setData(Qt.UserRole + 1, str(job.spec.session_file))
            song_item.setData(Qt.UserRole + 2, job.status.value)
            self.queue_table.setItem(row, 0, song_item)

            # Artist
            artist_item = QTableWidgetItem(job.spec.artist)
            self.queue_table.setItem(row, 1, artist_item)

            # Status: label + semantic color (text carries the state too)
            status_item = QTableWidgetItem(STATUS_LABELS[job.status])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(status_color)
            self.queue_table.setItem(row, 2, status_item)

            # Progress: a real progress bar for running jobs, quiet text otherwise
            if job.status == JobStatus.RUNNING:
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(job.progress)
                bar.setFormat(f"{job.progress}%")
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(8, 2, 8, 2)
                cell_layout.addWidget(bar)
                self.queue_table.setCellWidget(row, 3, cell)
                self.queue_table.setItem(row, 3, QTableWidgetItem(""))
            else:
                self.queue_table.removeCellWidget(row, 3)
                progress_text = "100%" if job.status == JobStatus.COMPLETED else (
                    f"{job.progress}%" if job.progress > 0 else "–"
                )
                progress_item = QTableWidgetItem(progress_text)
                progress_item.setTextAlignment(Qt.AlignCenter)
                progress_item.setForeground(QColor(theme.MUTED))
                self.queue_table.setItem(row, 3, progress_item)

            # Row tooltip
            for col in range(4):
                cell_item = self.queue_table.item(row, col)
                if cell_item:
                    cell_item.setToolTip(tooltip)

            # Restore selection
            if job.job_id == selected_job_id:
                self.queue_table.selectRow(row)

    @Slot(int, int)
    def _on_job_double_clicked(self, row: int, column: int):
        """Reveal a completed job's session in Finder."""
        item = self.queue_table.item(row, 0)
        if not item:
            return
        if item.data(Qt.UserRole + 2) != JobStatus.COMPLETED.value:
            return
        session_file = Path(item.data(Qt.UserRole + 1))
        if session_file.exists():
            subprocess.run(["open", "-R", str(session_file)])
        else:
            self._log_message(f"Session file not found: {session_file}")

    @Slot(str, int)
    def update_job_progress(self, job_name: str, progress: int):
        """Update progress bar and current job label."""
        self.current_job_label.setText(f"Processing: {job_name}")
        self.progress_bar.setValue(progress)

    @Slot(str)
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.setText(message)
        # Reset any error styling applied by _show_error
        self.status_label.setStyleSheet("")

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

    # Drag and drop event handlers

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Accept drag events if they contain file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _drop_event(self, event: QDropEvent):
        """Handle dropped folders and extract the path."""
        urls = event.mimeData().urls()
        if urls:
            # Get the first URL (file path)
            file_path = urls[0].toLocalFile()

            # Check if it's a directory
            path = Path(file_path)
            if path.is_dir():
                self.source_folder_input.setText(str(path))
                self._log_message(f"Source folder set via drag-and-drop: {path}")
                event.acceptProposedAction()
            else:
                # If user dropped a file, use its parent directory
                parent_dir = path.parent
                self.source_folder_input.setText(str(parent_dir))
                self._log_message(f"Using parent directory of dropped file: {parent_dir}")
                event.acceptProposedAction()
        else:
            event.ignore()

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
        self.status_label.setStyleSheet(f"color: {theme.STATUS_FAILED}; font-weight: bold;")
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

        # Set template path from settings
        if self.settings.last_template_path:
            self.template_file_input.setText(str(self.settings.last_template_path))

    @Slot()
    def _open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            # Settings were saved, reload them into main window
            self._load_settings()
            self._log_message("Settings updated and saved")

    def closeEvent(self, event):
        """Handle window close event."""
        # Save current output directory to settings
        output_dir = self.output_dir_input.text().strip()
        if output_dir and Path(output_dir).is_dir():
            self.settings.set_root_output_dir(Path(output_dir))

        # Save current template path to settings
        template_path = self.template_file_input.text().strip()
        if template_path and Path(template_path).is_file():
            self.settings.set_last_template_path(Path(template_path))
        elif not template_path:
            # Clear template if field is empty
            self.settings.set_last_template_path(None)

        event.accept()
