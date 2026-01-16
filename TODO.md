# Pro Tools Session Builder - TODO

**Last Updated**: 2026-01-16
**Current Phase**: Core Layer Complete ✓

---

## 🎯 Next Up

### Queue Layer (`src/queue/`)
- [ ] **QueueManager**: Serial job execution orchestration
  - Queue data structure (FIFO)
  - Add/remove/clear operations
  - Status tracking (pending/running/completed/failed)
  - Thread-safe operations for UI updates

- [ ] **JobExecutor**: 9-step workflow coordinator
  - Step 1: Validate SessionSpec (5%)
  - Step 2: Create output directory (10%)
  - Step 3: Launch Pro Tools (20%)
  - Step 4: Create session (30%)
  - Step 5: Import audio (50%)
  - Step 6: Import MIDI (70%)
  - Step 7: Import template (85%)
  - Step 8: Save session (95%)
  - Step 9: Complete (100%)
  - Progress callbacks for UI
  - Error handling and cleanup

- [ ] **Job Model**: Data class for queue items
  - SessionSpec reference
  - Status (pending/running/completed/failed)
  - Progress percentage
  - Error messages
  - Timestamps (queued/started/completed)

### Pro Tools Layer (`src/protools/`)
- [ ] **AppleScript Templates** (`src/protools/scripts/`)
  - [ ] `launch_protools.applescript` - Activate app, wait for Dashboard
  - [ ] `create_session.applescript` - Dashboard → New Session with sample rate/bit depth
  - [ ] `import_audio.applescript` - File → Import → Audio, **disable Apply SRC**, verify
  - [ ] `import_midi.applescript` - File → Import → MIDI, enable tempo/key import
  - [ ] `import_template.applescript` - File → Import → Session Data, **disable Apply SRC**, **dismiss Session Start Time warning**
  - [ ] `save_session.applescript` - File → Save Session
  - [ ] `close_session.applescript` - File → Close Session

- [ ] **AppleScriptController**: Template execution engine
  - Load templates from `scripts/` directory
  - Placeholder substitution (`{session_name}`, `{sample_rate}`, etc.)
  - Execute via `osascript` subprocess
  - Parse stderr for errors
  - Exponential backoff retry logic
  - Timeout handling

- [ ] **ProToolsWorkflow**: High-level operations
  - `launch()` - Launch Pro Tools and wait for ready state
  - `create_session(spec: SessionSpec)` - Create new session with specs
  - `import_audio(files: list[Path])` - Import audio, disable SRC
  - `import_midi(files: list[Path])` - Import MIDI with tempo/key
  - `import_template(template: Path)` - Import session data, handle warnings
  - `save_session(path: Path)` - Save session file
  - `close_session()` - Close current session

- [ ] **UIScriptingUtils**: Reliability helpers
  - `wait_for_window(name: str, timeout: int)` - Poll for window appearance
  - `wait_for_import_completion(timeout: int)` - Detect import progress completion
  - `dismiss_warning(text: str)` - Find and dismiss dialog by text
  - `verify_checkbox(name: str, expected_value: int)` - Verify checkbox state
  - `cleanup_on_error()` - Press Escape, close session

- [ ] **AppSettings**: Configuration management
  - JSON persistence to `~/.protools_session_builder_settings.json`
  - Configurable timing:
    - `dialog_wait_time` (default: 2s)
    - `import_completion_timeout` (default: 60s)
    - `window_appearance_timeout` (default: 10s)
  - Default root output directory
  - Last used template path
  - Accessibility permission check on startup

### UI Layer (`src/ui/`)
- [ ] **MainWindow**: PySide6 main application window
  - Top section: Job creation form
    - Artist name input
    - Song name input
    - Project name input (optional, for album mode)
    - "Is part of larger project?" checkbox
    - Source folder selector (browse button)
    - Template file selector (optional, browse button)
    - Root output directory selector
    - "Add to Queue" button
  - Middle section: Queue table
    - Columns: Song Name, Artist, Status, Progress
    - Remove/Clear queue buttons
    - Start/Pause queue buttons
  - Bottom section: Progress and logs
    - Current job progress bar
    - Real-time log output (scrollable)
    - Status message display

- [ ] **Signal/Slot Connections**
  - Qt Signals for thread-safe updates from background executor
  - Progress updates → progress bar + table
  - Log messages → log output area
  - Job completion → update table status
  - Error handling → show dialog with user-friendly message

- [ ] **Worker Thread**
  - QThread for queue execution (keep UI responsive)
  - Emit signals for progress/status updates
  - Handle errors without blocking UI

### Testing
- [ ] **Unit Tests** for Queue Layer
  - `test_queue_manager.py` - Queue operations, thread safety
  - `test_job_executor.py` - Workflow steps with mocked ProToolsWorkflow

- [ ] **Integration Tests**
  - `test_queue_integration.py` - End-to-end queue execution with mocks

- [ ] **Manual Testing Checklist**
  - [ ] Test with real Pro Tools on different sample rates (44.1k, 48k, 96k)
  - [ ] Verify "Apply SRC" checkbox is disabled and verified
  - [ ] Test Session Start Time warning dismissal
  - [ ] Test import completion polling (don't use fixed delays)
  - [ ] Test with paths containing spaces
  - [ ] Verify accessibility permissions prompt
  - [ ] Test error recovery and cleanup
  - [ ] Test both single song and album modes

### Test Fixtures
- [ ] Generate audio test files
  ```bash
  cd tests/fixtures
  sox -n -r 44100 -b 16 44100_16bit.wav trim 0 5
  sox -n -r 48000 -b 24 48000_24bit.wav trim 0 5
  sox -n -r 96000 -b 24 96000_24bit.wav trim 0 5
  ```

### Main Entry Point
- [ ] **main.py**: Application launcher
  - Parse `--debug` flag for verbose logging/screenshots
  - Check accessibility permissions on startup
  - Show instructions if permissions missing
  - Initialize QApplication
  - Launch MainWindow
  - Handle graceful shutdown

---

## ✅ Completed

### Phase 1: Project Setup
- [x] Project directory structure (`src/`, `tests/`, etc.)
- [x] `requirements.txt` with dependencies
- [x] `pytest.ini` configuration
- [x] `.gitignore` for Python/macOS
- [x] Virtual environment setup
- [x] Git repository initialization
- [x] GitHub remote connection

### Phase 2: Core Layer
- [x] **AudioAnalyzer** (`src/core/audio_analyzer.py`)
  - sox/soxi wrapper for audio analysis
  - Validation for sample rate/bit depth consistency
  - Error handling for missing files

- [x] **FolderScanner** (`src/core/folder_scanner.py`)
  - Filter audio files (.wav, .aif, .aiff)
  - Filter MIDI files (.mid, .midi)
  - Skip hidden files and directories
  - Sorted file lists

- [x] **SessionSpec** (`src/core/session_spec.py`)
  - Immutable data model for session parameters
  - Validation for sample rate, bit depth, paths
  - Properties: has_audio, has_midi, has_template, is_album_mode
  - Support for both single song and album modes

- [x] **PathResolver** (`src/core/path_resolver.py`)
  - Single song mode: `{root}/{Artist}/{Song}/`
  - Album mode: `{root}/{Artist}/{Project}/{Song}/`
  - Filesystem name sanitization
  - Writable directory validation

- [x] **Exception Hierarchy** (`src/core/exceptions.py`)
  - PTSessionBuilderError (base)
  - AudioAnalysisError, SampleRateMismatchError
  - ValidationError
  - AppleScriptError
  - JobExecutionError

### Phase 3: Test Suite
- [x] `test_audio_analyzer.py` (7 tests)
- [x] `test_folder_scanner.py` (9 tests)
- [x] `test_session_spec.py` (17 tests)
- [x] `test_path_resolver.py` (11 tests)
- [x] **40 passing tests**, 4 skipped (need fixtures)

---

## 📝 Notes

### Critical Requirements to Remember
1. **MUST disable "Apply SRC"** in both audio and template imports - verify checkbox state
2. **MUST dismiss "Session Start Time" warning** when importing templates
3. **MUST poll for import completion** - never use fixed delays
4. **Serial execution only** - Pro Tools can only automate one session at a time
5. **Accessibility permissions** required for UI scripting - check on startup

### Design Principles
- **Fail-safe over fast**: Generous timeouts, explicit waits, verification steps
- **Configurable timing**: All delays/timeouts in AppSettings
- **Python owns logic**: All validation/paths/queue in Python (testable)
- **No track manipulation in v1**: Focus on core workflow reliability first

### Testing Strategy
- **Unit tests**: Core logic only (can be automated)
- **Integration tests**: Queue management with mocked Pro Tools
- **Manual tests**: All AppleScript automation (cannot be automated due to UI scripting)
- **Test output**: Use `testing/` directory to prevent polluting production drives
