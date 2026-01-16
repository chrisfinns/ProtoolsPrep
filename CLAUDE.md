# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pro Tools Session Builder - A macOS desktop application (Python 3.11+ with PySide6) that batch-processes song folders, analyzes audio specs using sox/soxi, and automates Pro Tools session creation via AppleScript UI scripting.

**Critical Design Constraint**: All Pro Tools automation uses AppleScript + System Events (no Pro Tools SDK). This is intentionally brittle - reliability comes from configurable timing, polling over fixed delays, and retry logic.

## Architecture

### Data Flow
```
FolderScanner → AudioAnalyzer → SessionSpec → Job → JobExecutor
                                                        ↓
                                                  ProToolsWorkflow
                                                        ↓
                                                  AppleScript
```

### Layer Responsibilities

**Core Layer** (`src/core/`)
- `AudioAnalyzer`: Wraps sox/soxi shell commands, validates all audio files in folder have matching sample rate/bit depth
- `FolderScanner`: Filters files by extension (.wav/.aif for audio, .mid for MIDI), skips hidden/unsupported files
- `PathResolver`: Computes output paths - Single song: `{root}/{Artist}/{Song}/` vs Album: `{root}/{Artist}/{Project}/{Song}/`
- `SessionSpec`: Immutable data model holding all session parameters (detected sample rate, file lists, output paths)

**Queue Layer** (`src/queue/`)
- `QueueManager`: Orchestrates serial job execution (Pro Tools can only be automated one session at a time)
- `JobExecutor`: Coordinates 9-step workflow with progress callbacks (5% validate → 30% create → 50% audio → 70% MIDI → 85% template → 100%)
- Jobs are **never** executed in parallel - queue is strictly serial

**Pro Tools Layer** (`src/protools/`)
- `AppleScriptController`: Template substitution + osascript execution with stderr parsing and exponential backoff retry
- `ProToolsWorkflow`: High-level operations (launch, create, import, save) - each method encapsulates a multi-step AppleScript sequence
- `UIScriptingUtils`: Reliability helpers - polling for windows, detecting import completion, dismissing warnings

**UI Layer** (`src/ui/`)
- PySide6 with Qt Signals for thread-safe updates from background queue execution
- MainWindow layout: Top (job form) → Middle (queue table) → Bottom (progress/logs)

## Critical AppleScript Requirements

### MUST Disable "Apply SRC" (Sample Rate Conversion)
**Why**: Pro Tools' SRC corrupts audio quality. Since we pre-validate sample rates match, SRC must be disabled.

**Where**:
1. `import_audio.applescript` - Audio import dialog
2. `import_template.applescript` - Session Data import dialog

**Pattern**:
```applescript
set value of checkbox "Apply SRC" to 0
-- VERIFY it worked
set srcValue to value of checkbox "Apply SRC"
if srcValue is not 0 then
    error "Failed to disable Apply SRC"
end if
```

### MUST Dismiss "Session Start Time" Warning
When importing templates with different start times, Pro Tools shows a warning dialog. This MUST be dismissed automatically or workflow hangs.

Location: `import_template.applescript` after selecting template file.

### MUST Wait for Import Completion
Never proceed until imports finish. Poll for progress indicators to disappear, don't use fixed delays.

## Development Commands

### Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install external dependency
brew install sox

# Generate test audio fixtures
cd tests/fixtures
sox -n -r 44100 -b 16 44100_16bit.wav trim 0 5
sox -n -r 48000 -b 24 48000_24bit.wav trim 0 5
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_audio_analyzer.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_analyze"
```

### Running
```bash
# Run application
python src/main.py

# Run with debug mode (verbose logging, screenshots)
python src/main.py --debug
```

## Testing Notes

**Unit Tests**: Core logic only (AudioAnalyzer, FolderScanner, PathResolver, Validator)

**Integration Tests**: Queue management with mocked Pro Tools workflow

**Manual Tests Required**: All AppleScript automation must be tested with real Pro Tools. Cannot be automated due to UI scripting nature.

**Test Data Location**: `tests/fixtures/` - Contains sample WAV files at different sample rates for testing validation

**Testing Output**: `testing/` directory in project root - prevents accidentally creating sessions in production audio drives

## Key Design Decisions

1. **Serial Queue Execution**: Pro Tools UI scripting is stateful - only one session can be automated at a time. Parallel execution would cause race conditions and click wrong UI elements.

2. **Python Owns Logic**: All validation, path resolution, queue management in Python (testable). Pro Tools only does minimum (create, import, save).

3. **Fail-Safe Over Fast**: Generous timeouts, explicit waits, verification steps. Corrupted sessions worse than slow execution.

4. **Configurable Timing**: `AppSettings` has tunable delays (`dialog_wait_time`, `import_completion_timeout`) because different systems have different speeds.

5. **No Track Manipulation (v1)**: Track naming, routing, color coding explicitly out of scope. Focus on core workflow reliability first.

## Error Handling

### Exception Hierarchy
```
PTSessionBuilderError (base)
├── AudioAnalysisError
│   └── SampleRateMismatchError  # Different sample rates in folder
├── AppleScriptError              # UI scripting failed
├── JobExecutionError             # Workflow step failed
└── ValidationError               # Invalid session spec
```

### Error Recovery
- **User Errors** (sample rate mismatch): Friendly message, mark job failed, continue queue
- **System Errors** (sox missing): Technical instructions, halt queue
- **Pro Tools Errors** (timeout): Retry with backoff OR mark job failed, continue queue
- **Cleanup**: `workflow_steps.cleanup_on_error()` presses Escape to close dialogs, then closes session

## Critical Risks

| Risk | Why Critical | Mitigation |
|------|-------------|-----------|
| "Apply SRC" checkbox | Degrades audio quality | Verify checkbox value after setting, log it, fail if can't disable |
| Timing issues | AppleScript races | Poll for conditions (never fixed delays), configurable timeouts |
| Path with spaces | AppleScript breaks | POSIX paths, proper escaping, test edge cases |
| Accessibility perms | All automation fails silently | Check on startup, show instructions |
| User touches Pro Tools | Automation clicks wrong thing | Warning in UI, focus lock, state verification |

## Folder Structure Logic

Two modes based on "Is this part of a larger project?" checkbox:

**Single Song Mode**: One-off track or learning project
```
{root}/
  {Artist}/
    {Song}/
      {Song}.ptx
      Audio Files/
      Session File Backups/
      ...
```

**Album/EP Mode**: Multiple songs in same project
```
{root}/
  {Artist}/
    {Project}/
      {Song1}/
        {Song1}.ptx
        ...
      {Song2}/
        {Song2}.ptx
        ...
```

Pro Tools auto-creates: Audio Files, Bounced Files, Clip Groups, Session File Backups, Video Files, WaveCache.wfm

## Settings Persistence

`AppSettings` saves to JSON in user home directory (`~/.protools_session_builder_settings.json`).

For testing: Default root output is `{workspace}/testing/` to prevent polluting production audio drives.

## Workflow Execution Order (MUST NOT CHANGE)

The JobExecutor follows this exact 9-step sequence:

1. **Validate** (5%): Check SessionSpec for errors
2. **Create Output Dir** (10%): Make folder structure
3. **Launch Pro Tools** (20%): Activate app, wait for Dashboard
4. **Create Session** (30%): Use Dashboard with detected sample rate/bit depth
5. **Import Audio** (50%): File → Import → Audio, disable SRC
6. **Import MIDI** (70%): File → Import → MIDI, enable tempo/key import
7. **Import Template** (85%): File → Import → Session Data, disable SRC, dismiss warning
8. **Save Session** (95%): File → Save Session
9. **Complete** (100%): Close session

Each step has progress callback for UI updates. Steps cannot be reordered - MIDI must come after audio to prevent dialog overlap.

## AppleScript Script Templates

Location: `src/protools/scripts/*.applescript`

Templates use `{placeholder}` syntax that AppleScriptController substitutes before execution:
```applescript
tell application "System Events"
    tell process "Pro Tools"
        tell window "Dashboard"
            set value of text field "Name" to "{session_name}"
            set value of popup button "Sample Rate" to "{sample_rate}"
        end tell
    end tell
end tell
```

Controller substitutes: `{session_name}` → actual song name, `{sample_rate}` → detected rate.
