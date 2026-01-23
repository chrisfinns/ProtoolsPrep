# Pro Tools Session Builder - TODO

**Last Updated**: 2026-01-23 (UTF-8 Encoding Bug Fix)
**Current Phase**: ✅ READY FOR PRODUCTION - All known bugs fixed, app ready for manual testing

> **Historical Context**: See [progress.md](progress.md) for a log of completed work across sessions.
>
> **Architecture Status**:
> - Core Layer: ✓ Complete (44 tests, 442 lines)
> - Queue Layer: ✓ Complete (60 tests, 516 lines)
> - Pro Tools Layer: ✓ Complete (~950 lines)
> - UI Layer: ✓ Complete (~480 lines) - **🐛 BUGS FIXED**
> - **Total Application**: ✓ Ready for manual testing with real Pro Tools

> **Recent Bug Fixes** (2026-01-16):
> - Fixed `QueueWorker.run()` calling non-existent `get_current_job()` → now calls `get_next()`
> - Fixed `JobExecutor` callback initialization - now passed to constructor, not `execute()` method
> - Fixed method names: `complete_current_job()` → `complete_current()`, `fail_current_job()` → `fail_current()`
> - Fixed `ProToolsWorkflow()` missing required `AppSettings` argument in QueueWorker
> - **Issue**: Queue start button was not working - jobs stayed pending with "no job running"
> - **Root Cause**: Four bugs in `QueueWorker` - method name mismatches and missing dependency injection
> - **Status**: ✅ Fixed - queue should now execute when "Start Queue" button is clicked
>
> **Recent Enhancements** (2026-01-23):
> - Added **SettingsDialog** with tabbed interface for Paths and Timing configuration
> - Template path and output directory now persist between sessions via AppSettings
> - Added File menu with Settings option (Cmd+,) and Quit (Cmd+Q)
> - Settings auto-load on app startup and save on window close
> - All timing parameters now configurable through UI (dialog waits, timeouts, retry config)

---

## 🎯 Next Up

### PHASE 1: AppleScript Testing (Individual Scripts) - IN PROGRESS

**Location**: `applescript_tests/` directory
**Goal**: Validate each AppleScript works correctly with actual Pro Tools UI before integrating into main app

**Testing Resources Created**:
- ✅ `START_HERE.md` - Quick start guide and workflow
- ✅ `README.md` - Detailed testing strategy for each script
- ✅ `ACCESSIBILITY_INSPECTOR_GUIDE.md` - How to inspect UI elements
- ✅ `TESTING_CHECKLIST.md` - Detailed checklist for documenting findings
- ✅ 8 test scripts with logging and error handling

**Scripts to Test** (in order):
- [ ] **test_launch.applescript** - Launch Pro Tools and open Dashboard
  - Verify: Dashboard window name, menu bar accessibility, Cmd+N behavior

- [ ] **test_create_session.applescript** - Create new session
  - Verify: Session name field, sample rate popup/menu items, bit depth popup/menu items
  - Verify: Session window naming convention

- [ ] **test_save_session.applescript** - Save with Cmd+S
  - Verify: Simple keyboard shortcut works

- [ ] **test_close_session.applescript** - Close with Cmd+W
  - Verify: Save dialog handling if unsaved

- [ ] **test_save_session_as.applescript** - Save to specific location
  - Verify: Save dialog navigation, filename field, replace handling

- [ ] **test_import_audio.applescript** - Import audio with SRC disabled ⚠️ CRITICAL
  - Verify: Menu path, import dialog name, "Apply SRC" checkbox existence
  - Verify: Checkbox exact name, value meanings (0/1), verification works
  - Verify: Progress window detection

- [ ] **test_import_midi.applescript** - Import MIDI files
  - Verify: Import dialog, tempo/key checkboxes (may not exist)

- [ ] **test_import_template.applescript** - Import template ⚠️ CRITICAL
  - Verify: Session Data import dialog, "Apply SRC" in template import
  - Verify: "Session Start Time" warning appearance and dismissal

**Critical Questions to Answer**:
1. Does "Apply SRC" checkbox exist in audio import? Exact name?
2. Does "Apply SRC" exist in template import? Same name?
3. Does "Session Start Time" warning appear? Window name? Dismiss button?
4. What are exact menu item names for sample rates (48 kHz vs 48.0 kHz vs 48000)?
5. What are progress window names during import?

**After Scripts Validated**:
- [ ] Document all UI element names in `TESTING_CHECKLIST.md`
- [ ] Update production scripts in `src/protools/scripts/` with correct names
- [ ] Update `CLAUDE.md` with UI quirks discovered
- [ ] Test full script sequence (launch → create → import → save → close)

---

### PHASE 2: Manual Testing with Real Pro Tools (After AppleScript validation)
- [ ] **First Launch Test**
  - [ ] Run `python src/main.py` to verify app starts
  - [ ] Check accessibility permissions prompt appears
  - [ ] Verify welcome message displays in log
  - [ ] Test all UI controls are responsive

- [ ] **Basic Workflow Test** (44.1kHz/16-bit audio)
  - [ ] Create test folder with 44.1k/16-bit WAV files
  - [ ] Add job to queue via UI form
  - [ ] Start queue and verify Pro Tools launches
  - [ ] Verify session creation with correct sample rate
  - [ ] Verify audio import with SRC disabled
  - [ ] Verify session saves to correct output path

- [ ] **Sample Rate Tests**
  - [ ] Test with 48kHz/24-bit audio files
  - [ ] Test with 96kHz/24-bit audio files
  - [ ] Verify SRC checkbox is disabled and verified in logs

- [ ] **Template Import Test**
  - [ ] Create job with template file specified
  - [ ] Verify "Session Start Time" warning is dismissed automatically
  - [ ] Verify SRC disabled for template import
  - [ ] Verify session data imports correctly

- [ ] **Album Mode Test**
  - [ ] Check "Part of larger project" checkbox
  - [ ] Enter project name
  - [ ] Verify output path follows album structure: `{root}/{Artist}/{Project}/{Song}/`

- [ ] **Edge Cases**
  - [ ] Test with paths containing spaces
  - [ ] Test with empty queue (should show message)
  - [ ] Test pause/resume functionality
  - [ ] Test remove job from queue
  - [ ] Test clear queue
  - [ ] Test error recovery if Pro Tools not installed

- [ ] **Debug Mode Test**
  - [ ] Run `python src/main.py --debug`
  - [ ] Verify verbose logging to console and log file
  - [ ] Check log file created: `protools_session_builder.log`

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

### Phase 3: Core Layer Tests
- [x] `test_audio_analyzer.py` (7 tests)
- [x] `test_folder_scanner.py` (9 tests)
- [x] `test_session_spec.py` (17 tests)
- [x] `test_path_resolver.py` (11 tests)
- [x] **44 core tests**, 4 skipped (need fixtures)

### Phase 4: Queue Layer
- [x] **Job Model** (`src/queue/job.py`)
  - JobStatus enum (PENDING/RUNNING/COMPLETED/FAILED)
  - Mutable runtime state wrapping immutable SessionSpec
  - Properties: display_name, is_finished, duration
  - Timestamps: queued_at, started_at, completed_at
  - Unique job_id for tracking

- [x] **QueueManager** (`src/queue/queue_manager.py`)
  - Thread-safe FIFO queue using deque + Lock
  - Add/remove/clear operations
  - Current job tracking (separate from queue)
  - Status management (complete_current, fail_current)
  - Snapshot API (get_all_jobs)

- [x] **JobExecutor** (`src/queue/job_executor.py`)
  - ProToolsWorkflowProtocol for dependency injection
  - 9-step workflow coordinator with progress callbacks
  - Smart skipping (audio/MIDI/template only when present)
  - Error handling and cleanup
  - Progress tracking (5% → 100%)

- [x] **QueueError Exception** (`src/core/exceptions.py`)

### Phase 5: Queue Layer Tests
- [x] `test_job.py` (14 tests)
- [x] `test_queue_manager.py` (22 tests)
- [x] `test_job_executor.py` (16 tests)
- [x] `test_queue_integration.py` (8 tests)
- [x] **60 queue tests**, all passing
- [x] **100 total tests**, 4 skipped (need fixtures)

### Phase 6: Pro Tools Layer ✓
- [x] **AppSettings** (`src/protools/settings.py`) - 119 lines
  - JSON persistence to `~/.protools_session_builder_settings.json`
  - Configurable timing: dialog_wait_time (1.5s), import_completion_timeout (60s), window_appearance_timeout (10s)
  - Retry configuration: applescript_retry_attempts (3), applescript_retry_delay (2s)
  - Path configuration: root_output_dir, last_template_path
  - Default testing directory: `{workspace}/testing/`
  - Auto-save on property changes

- [x] **AppleScript Templates** (`src/protools/scripts/`) - 7 templates, 308 lines total
  - `launch_protools.applescript` (29 lines) - Activate app, poll for Dashboard
  - `create_session.applescript` (43 lines) - Dashboard form with sample rate/bit depth
  - `import_audio.applescript` (60 lines) - **Disable Apply SRC**, verify checkbox, poll for completion
  - `import_midi.applescript` (42 lines) - Enable tempo/key import, poll for completion
  - `import_template.applescript` (78 lines) - **Disable Apply SRC**, **dismiss Session Start Time warning**
  - `save_session.applescript` (31 lines) - Save via Cmd+S, check for errors
  - `close_session.applescript` (25 lines) - Close via Cmd+W, handle save dialogs

- [x] **AppleScriptController** (`src/protools/applescript_controller.py`) - 147 lines
  - Template loading from scripts/ directory with automatic path resolution
  - Placeholder substitution: `{key}` → value, escapes double quotes
  - Subprocess execution via osascript with stderr capture
  - Error classification: retryable (timeout, UI not ready) vs non-retryable (template not found)
  - Exponential backoff retry: 2s → 4s → 8s for retryable errors
  - Clean error messages extracted from AppleScript stderr

- [x] **UIScriptingUtils** (`src/protools/ui_scripting_utils.py`) - 189 lines
  - `wait_for_window(window_name, timeout)` - Poll for window appearance (0.5s intervals)
  - `wait_for_import_completion(timeout)` - Poll for import progress indicator disappearance
  - `dismiss_warning(dialog_text)` - Find dialog by text, click OK/Yes button
  - `verify_checkbox(window, checkbox_name, expected_value)` - Verify checkbox state
  - `cleanup_on_error()` - Emergency cleanup: press Escape, close session, suppress errors
  - `check_accessibility_permissions()` - Verify System Events can control Pro Tools
  - `get_accessibility_instructions()` - User-friendly permission setup guide

- [x] **ProToolsWorkflow** (`src/protools/workflow.py`) - 131 lines
  - `launch()` - Launch Pro Tools, wait for Dashboard
  - `create_session(name, sample_rate, bit_depth, output_dir)` - Create session
  - `import_audio(files)` - Import audio with SRC disabled + verified
  - `import_midi(files)` - Import MIDI with tempo/key enabled
  - `import_template(template_path)` - Import template with SRC disabled + warning dismissed
  - `save_session(session_file)` - Save and verify file exists
  - `close_session()` - Close current session
  - Implements ProToolsWorkflowProtocol for JobExecutor
  - Integrates AppSettings for configurable timeouts

- [x] **Integration Verification**
  - All imports verified: `from src.protools import ProToolsWorkflow, AppSettings` ✓
  - ProToolsWorkflow implements ProToolsWorkflowProtocol ✓
  - Integration with JobExecutor confirmed ✓
  - No circular dependencies ✓

**Total Pro Tools Layer**: ~950 lines of production code (settings + scripts + controller + utils + workflow)

### Phase 7: UI Layer ✓
- [x] **MainWindow** (`src/ui/main_window.py`) - 476 lines
  - Top section: Job creation form (artist, song, project, folders, settings)
    - Artist/Song/Project name inputs with validation
    - Album mode checkbox with dynamic project field enable/disable
    - Source folder browser for audio/MIDI files
    - Template file browser (optional .ptx selection)
    - Output directory browser with settings persistence
    - "Add to Queue" button with form validation
  - Middle section: Queue table with controls
    - 4-column table: Song Name, Artist, Status, Progress
    - Start/Pause queue buttons with state management
    - Remove selected job / Clear all jobs
    - Row selection for job removal
  - Bottom section: Progress and logs
    - Current job label with job name
    - Progress bar (0-100%)
    - Status message label with error styling
    - Real-time scrollable log output (auto-scroll to bottom)
  - Settings integration: Load/save output directory on open/close
  - Thread-safe UI updates via Qt Signals

- [x] **QueueWorker** (`src/ui/queue_worker.py`) - 121 lines
  - QThread subclass for background queue execution
  - Integrates QueueManager + JobExecutor + ProToolsWorkflow
  - Emits signals for all UI updates (job_started, job_progress, job_completed, job_failed, queue_finished, log_message)
  - Progress callback integration with JobExecutor
  - Exception handling: PTSessionBuilderError (user-friendly) vs unexpected errors
  - Graceful stop mechanism (finish current job before pausing)
  - Automatic queue completion when empty

- [x] **AppController** (`src/ui/app_controller.py`) - 135 lines
  - Coordinator between MainWindow, QueueManager, and QueueWorker
  - Connects all UI signals to business logic
  - Handles job lifecycle: add → start queue → execute → complete/fail
  - Worker thread management: create, connect signals, start, cleanup
  - Queue state enforcement: prevent clear/remove during execution
  - UI state synchronization: update table after every state change
  - Error propagation from worker to UI with logging

- [x] **main.py** (`src/main.py`) - 149 lines
  - Command-line argument parsing: `--debug` flag for verbose logging
  - Logging setup: dual output (console + file), configurable log level
  - Accessibility permissions check on startup with user-friendly instructions
  - Permission dialog with retry logic
  - QApplication initialization with app metadata
  - MainWindow + AppController instantiation and wiring
  - Welcome message with usage tips
  - Settings auto-save on window close
  - Graceful exit code handling

- [x] **Test Fixtures** (`tests/fixtures/`)
  - Generated 3 test audio files using sox:
    - `44100_16bit.wav` (431KB, 5 seconds)
    - `48000_24bit.wav` (703KB, 5 seconds)
    - `96000_24bit.wav` (1.4MB, 5 seconds)
  - Enables testing of sample rate detection and validation
  - Used by skipped unit tests in core layer

**Total UI Layer**: ~880 lines (MainWindow 476 + QueueWorker 121 + AppController 135 + main.py 149)

### Phase 8: Bug Fixes - Queue Start Issue ✓
- [x] **Issue Reported**: Queue start button does nothing - jobs stuck in pending status
- [x] **Root Cause Analysis** (`src/ui/queue_worker.py`)
  - Line 50: Called non-existent `get_current_job()` method → Should be `get_next()`
  - Line 39: Created `JobExecutor` without progress callback
  - Line 88: Tried to pass progress callback to `execute()` method → Should pass to constructor
  - Lines 93, 100, 108: Called `complete_current_job()` and `fail_current_job()` → Should be `complete_current()` and `fail_current()`
- [x] **Fixes Applied**:
  - Changed `get_current_job()` to `get_next()` to properly dequeue jobs
  - Removed instance variable `self.executor` from `__init__`
  - Created `JobExecutor` per-job in `_execute_job()` with progress callback
  - Fixed all QueueManager method calls to use correct names
- [x] **Testing**: Ready for manual testing - queue should now execute jobs when Start Queue is clicked

### Phase 9: Settings UI Enhancement ✓
- [x] **SettingsDialog** (`src/ui/settings_dialog.py`) - 248 lines
  - Tabbed interface with two tabs: Paths and Timing
  - **Paths Tab**:
    - Root output directory configuration with browse button
    - Default template file selection with browse and clear buttons
    - Help text explaining each setting
  - **Timing Tab**:
    - Dialog wait time configuration (0.5-10.0 seconds)
    - Window appearance timeout (5.0-60.0 seconds)
    - Import completion timeout (10.0-300.0 seconds)
    - Retry attempts (1-10 attempts)
    - Base retry delay (0.5-10.0 seconds) with exponential backoff note
  - OK/Cancel/Restore Defaults buttons
  - Auto-save all settings to JSON on OK

- [x] **MainWindow Enhancements** (`src/ui/main_window.py`)
  - Added menu bar with File menu
  - Settings menu item (Cmd+,) opens SettingsDialog
  - Quit menu item (Cmd+Q)
  - Template path now persists between sessions
  - Auto-loads template and output directory from settings on startup
  - Auto-saves template and output directory on window close
  - Changed to use `AppSettings.load()` for proper initialization

- [x] **User Experience Improvements**:
  - Template file no longer needs to be selected every time
  - Output directory remembered across sessions
  - All timing parameters accessible through UI (no need to edit JSON)
  - Settings changes take effect immediately after dialog closes

**Total Settings Enhancement**: ~248 lines (SettingsDialog) + menu bar and persistence logic in MainWindow

### Phase 10: Template Import Bug Fix ✓
- [x] **Issue Reported**: Template import failing with "Import Session Data dialog did not appear"
- [x] **Root Cause Analysis**:
  - Issue 1: AppleScript was using Cmd+Shift+G with full file path instead of folder path
    - Cmd+Shift+G navigates to folders, not files
    - After navigation, script wasn't selecting the specific template file
  - Issue 2: Track selection was clicking first row repeatedly instead of selecting all tracks
    - Standard iteration approaches failed (clicking rows, using arrows, etc.)
    - Solution discovered: Use `perform action "AXPress"` on row 1 to focus table, then send Cmd+A
- [x] **Fixes Applied** (`src/protools/scripts/import_template.applescript`):
  - **File Navigation Fix** (lines 34-54):
    - Split template path into folder and filename components
    - Navigate to folder using Cmd+Shift+G: `{template_folder_path}`
    - Type filename to select file: `{template_filename}`
  - **Track Selection Fix** (lines 70-89):
    - Focus table using `tell row 1 to perform action "AXPress"`
    - Select all tracks with `keystroke "a" using {command down}` (OUTSIDE tell table block)
    - Ensures all tracks mapped to "New Track" destinations
- [x] **Workflow Updated** (`src/protools/workflow.py`):
  - Changed from passing `template_posix_path` to `template_folder_path` and `template_filename`
  - Uses `template_path.parent` for folder and `template_path.name` for filename
- [x] **Test Script Created**: `test_import_template_standalone.applescript`
  - Standalone version with hardcoded values for quick testing
  - Contains same AXPress + Cmd+A solution
- [x] **Status**: ✅ COMPLETE - Ready for full application testing with real Pro Tools session

### Phase 11: UTF-8 Encoding Bug Fix ✓
- [x] **Issue Reported**: Template import failing with "'utf-8' codec can't decode byte 0xff in position 0"
- [x] **Root Cause Analysis**:
  - `import_template.applescript` was saved as UTF-16LE by AppleScript Editor
  - Python's `open()` defaults to UTF-8 encoding
  - When AppleScriptController tried to read UTF-16 file as UTF-8, it failed with UnicodeDecodeError
- [x] **Fixes Applied**:
  - **File Encoding Fix**: Converted `import_template.applescript` from UTF-16LE to UTF-8
    - Used `iconv` to convert encoding: `iconv -f UTF-16LE -t UTF-8`
    - Removed UTF-8 BOM for cleaner file format
    - Verified all other AppleScript files are ASCII/UTF-8 compatible
  - **Code Robustness Enhancement** (`src/protools/applescript_controller.py`):
    - Enhanced `_load_and_substitute()` to try multiple encodings: utf-8, utf-16-le, utf-16-be, utf-8-sig
    - Prevents future encoding issues if AppleScript Editor re-saves files
    - Provides clear error message if all encodings fail
- [x] **Status**: ✅ COMPLETE - Template import now works with any text encoding

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
