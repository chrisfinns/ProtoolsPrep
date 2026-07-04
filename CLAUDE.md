# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Progress Tracking

**IMPORTANT**: This project uses `TODO.md` to track progress between sessions.

- **First action in new session**: Read `TODO.md` to understand current status and next tasks
- **After completing work**: Update `TODO.md` to reflect what was done and what's next
- **When creating new coding projects**: Always create a `TODO.md` file with:
  - Current phase/status
  - Next up tasks (prioritized)
  - Completed items
  - Important notes/constraints

This ensures continuity across sessions and prevents lost context.

## Project Overview

Pro Tools Session Builder - A macOS desktop application (Python 3.11+ with PySide6) that batch-processes song folders, analyzes audio specs via libsndfile (soundfile package), and automates Pro Tools session creation via **PTSL** (Pro Tools Scripting Library, Avid's official gRPC API — v3 in Pro Tools 2024.3).

**Automation strategy**: PTSL is the primary path (typed commands, typed errors, no UI races). Exactly **two** guarded AppleScripts survive because PTSL v3 has no equivalent:
1. `import_midi.applescript` — MIDI import
2. `dialog_supervisor.applescript` — whitelist-only dismissal of modal dialogs

The full rationale, validated behaviors, and quirk list live in `docs/DEVELOPER_IMPROVEMENT_PLAN.md`.

## Architecture

### Data Flow
```
FolderScanner → AudioAnalyzer → SessionSpec → Job → JobExecutor
                                                        ↓
                                          ProToolsWorkflowProtocol
                                                        ↓
                                                  PTSLWorkflow
                                            ↓ (gRPC :31416)   ↓ (fallbacks)
                                             py-ptsl      AppleScriptRunner
                                                          (MIDI import, dialog supervisor)
```

### Layer Responsibilities

**Core Layer** (`src/core/`)
- `AudioAnalyzer`: Reads specs via libsndfile (`soundfile` — bundled in the wheel, no external tools), validates all audio files in folder have matching sample rate/bit depth
- `FolderScanner`: Filters files by extension (.wav/.aif for audio, .mid for MIDI), skips hidden/unsupported files
- `PathResolver`: Computes output paths - Single song: `{root}/{Artist}/{Song}/` vs Album: `{root}/{Artist}/{Project}/{Song}/`
- `SessionSpec`: Immutable data model holding all session parameters (detected sample rate, file lists, output paths)

**Queue Layer** (`src/queue/`)
- `QueueManager`: Orchestrates serial job execution (Pro Tools can only be automated one session at a time)
- `JobExecutor`: Coordinates 9-step workflow with progress callbacks; depends only on `ProToolsWorkflowProtocol`
- Jobs are **never** executed in parallel - queue is strictly serial

**Pro Tools Layer** (`src/protools/`)
- `ptsl_compat`: protobuf-5 shim for py-ptsl 301 — **must be imported before `ptsl`** (all modules here do)
- `PTSLClient` (`ptsl_client.py`): engine lifecycle — lazy connect/reconnect (survives Pro Tools restarts), `ensure_ready()` (host_ready_check + backoff), `settle()` pacing, typed error translation
- `PTSLWorkflow` (`ptsl_workflow.py`): implements the protocol — launch, create, import audio/template (PTSL), import MIDI (AppleScript fallback), save (polls for .ptx), close
- `DialogSupervisor` (`dialog_supervisor.py` + script): dismisses only whitelisted dialogs, returns structured results, raises `DialogBlockedError` on anything unknown
- `AppleScriptRunner` (`applescript_runner.py`): minimal osascript runner — escaped substitution, per-call derived timeouts, **no automatic retry**
- `accessibility.py`: permission check for the two surviving scripts

**UI Layer** (`src/ui/`)
- PySide6 with Qt Signals for thread-safe updates from background queue execution
- MainWindow layout: Top (job form) → Middle (queue table) → Bottom (progress/logs)

## Critical PTSL v3 Quirks (discovered in live testing — MUST handle)

1. **`import_data` requires an explicit timecode start**: py-ptsl 301's empty-string default is rejected with `PT_InvalidParameter` (126). Set `imp._timecode_mapping_start_time = "00:00:00:00"` directly — do NOT use `map_start_timecode()`, which silently switches the mapping option away from MaintainAbsoluteTimeCodeValues.
2. **Modal dialogs poison every PTSL response**: while ANY modal is up, all commands return `PT_NoOpenedSession` (106) even with a session open. 106 means "no session OR modal blocking" — always run the dialog supervisor before concluding. "Missing AAX Plugins" fires on **every** template import on this machine (normal path).
3. **Rapid command cycling can wedge/crash Pro Tools 2024.3**: `ensure_ready()` before operations, `settle()` (configurable, default 8 s) after create/import/open. Keep the queue serial.
4. **py-ptsl 301 + protobuf 5**: needs the `ptsl_compat` shim on Python ≥3.13. The version pin is **one-directional**: the PTSL server is backward compatible with older clients (each request carries the client's protocol version), so py-ptsl 301 works against Pro Tools 2024.3 *and newer* — `PTSLClient` probes the server version at connect and gates only on "Pro Tools older than the client" (see `PTSL_VERSION_RELEASES` in `ptsl_client.py`). Bump py-ptsl only to gain new commands (401=2024.6, 500=2024.10, 60x=2025.6+) and drop the shim when possible.
5. **PACE/iLok "Activation is required" windows live in their OWN process, not Pro Tools**: each one is a short-lived `PACEEdenExperience` helper process (one per unlicensed iLok plugin, spawned serially ~2–3 s apart, launched from `/Library/Frameworks/PACEEdenExperience.framework`). Querying the *Pro Tools* process finds 0 windows (and can fail with -10000 → supervisor reports `ax-error:`) — that made them look "invisible to accessibility" for a long time, but they are NOT: the helper's own AX tree is fully readable, with `button "Quit" of group 1 of window 1`. The dialog supervisor's pass 0 answers **Quit** on each (never Activate/Try). They appear at Pro Tools startup and during template import when the user's iLok isn't plugged in. A blocked query must never be read as "no session"/"zero tracks" — use the patient variants (`_run_blocked_tolerant`, `_wait_for_track_count`), which sweep on every 106 and wait up to `user_dialog_timeout` (default 600 s).
6. **106 detail messages observed live**: "Unable to complete the command..." (idle/no session or dialog up) and "Session state is already changing" (transient — Pro Tools mid-startup or mid-transition; wait and retry).

## Error Handling

### Exception Hierarchy
```
PTSessionBuilderError (base)
├── AudioAnalysisError
│   └── SampleRateMismatchError   # Different sample rates in folder
├── ValidationError                # Invalid session spec
├── AppleScriptError               # Surviving scripts failed
├── PTSLError                      # PTSL operation failed
│   ├── ProToolsNotRunningError    # endpoint unreachable/crashed
│   ├── SessionBlockedError        # 106: no session OR modal dialog up
│   ├── PTSLParameterError         # 126: bad request field (non-retryable)
│   └── DialogBlockedError         # unknown dialog blocking (not whitelisted)
├── JobExecutionError              # Workflow step failed
└── QueueError
```

### Retry Policy (state-aware — never blind)
On `SessionBlockedError` (106): run dialog supervisor sweep → verify actual state (session open? tracks imported?) → only re-issue if the operation demonstrably didn't happen. Commands issued during a modal can queue and execute after dismissal, so blind re-runs cause double execution. The old "retry the entire script by default" design caused out-of-sync behavior and must not be reintroduced.

## Development Commands

### Setup
```bash
pip install -r requirements.txt   # includes py-ptsl==301.0.0 and soundfile

# Regenerate test audio fixtures if ever needed (sox only used for this)
cd tests/fixtures
sox -n -r 44100 -b 16 44100_16bit.wav trim 0 5
sox -n -r 48000 -b 24 48000_24bit.wav trim 0 5
```

### Testing
```bash
pytest                      # all tests
pytest tests/test_ptsl_workflow.py
pytest -v -k "test_analyze"
```

### Running
```bash
python3 src/main.py           # run application
python3 src/main.py --debug   # verbose logging
```

### Live validation prototypes (require running Pro Tools)
```bash
venv/bin/python prototypes/ptsl_probe.py              # read-only connection probe
venv/bin/python prototypes/ptsl_prototype.py          # create→import template→save→close
venv/bin/python prototypes/ptsl_audio_import_spike.py # validate import_audio (untested on v3)
```

## Testing Notes

**Unit Tests**: Core logic, queue, and the PTSL workflow with a mocked engine — no Pro Tools needed.

**Manual Tests Required**: Live PTSL behavior and the two AppleScripts must be tested with real Pro Tools.

**Test Data Location**: `tests/fixtures/` — sample WAVs at different rates.

**Testing Output**: `testing/` directory in project root — prevents accidentally creating sessions in production audio drives.

## Key Design Decisions

1. **Serial Queue Execution**: One session at a time; parallel PTSL commands wedge Pro Tools.
2. **Python Owns Logic**: All validation, path resolution, queue management in Python (testable). Pro Tools does the minimum (create, import, save).
3. **Fail-Safe Over Fast**: `ensure_ready()` + settle pacing between steps; postcondition verification (e.g. track count after template import) over optimistic success.
4. **Configurable Timing**: `AppSettings` — `ptsl_settle_time`, `ptsl_connect_timeout`, `save_poll_timeout`, plus `dialog_wait_time`/`midi_import_timeout` for the surviving scripts.
5. **No Track Manipulation (v1)**: Track naming, routing, color coding out of scope.

## Critical Risks

| Risk | Why Critical | Mitigation |
|------|-------------|-----------|
| Modal dialog blocks PTSL | Every command returns 106 | Dialog supervisor at checkpoints and on any 106 |
| Rapid cycling wedges PT | Force-quit required | ensure_ready + settle between steps |
| Unknown dialog | Automation stalls | Supervisor never dismisses blind; fails with a diagnosable `DialogBlockedError` |
| Accessibility perms | MIDI import + supervisor fail | Check on startup, show instructions |
| Sample-rate conversion | Degrades audio | Pre-validated rates; PTSL import parameters never apply SRC implicitly |

## Folder Structure Logic

Two modes based on "Is this part of a larger project?" checkbox:

**Single Song Mode**: `{root}/{Artist}/{Song}/{Song}.ptx`
**Album/EP Mode**: `{root}/{Artist}/{Project}/{Song}/{Song}.ptx`

PTSL's `create_session(name, parent)` creates `{parent}/{name}/{name}.ptx`, which matches PathResolver's layout exactly (output_dir basename == session name). Pro Tools auto-creates: Audio Files, Bounced Files, Clip Groups, Session File Backups, Video Files, WaveCache.wfm.

## Settings Persistence

`AppSettings` saves to JSON in user home directory (`~/.protools_session_builder_settings.json`). `load()` tolerates unknown/legacy keys. Default root output is `{workspace}/testing/` to prevent polluting production audio drives.

## Workflow Execution Order (MUST NOT CHANGE)

The JobExecutor follows this exact 9-step sequence:

1. **Validate** (5%): Check SessionSpec for errors (Python)
2. **Create Output Dir** (10%): Ensure parent directory (Python)
3. **Launch Pro Tools** (20%): Probe/launch, poll PTSL endpoint, ensure_ready
4. **Create Session** (30%): PTSL builder (int Hz sample rate); verify open session name
5. **Import Audio** (50%): PTSL import_audio, CopyAudio + MD_NewTrack (⚠️ validate live via spike before first production batch)
6. **Import MIDI** (70%): AppleScript fallback (skipped if no MIDI)
7. **Import Template** (85%): PTSL import_data + timecode quirk + supervisor sweep + track-count verify
8. **Save Session** (95%): PTSL save; poll for .ptx on disk
9. **Complete** (100%): PTSL close + supervisor sweep

## AppleScript (surviving scripts only)

Location: `src/protools/scripts/` — `import_midi.applescript`, `dialog_supervisor.applescript`.

Templates use `{placeholder}` syntax; `AppleScriptRunner` escapes `"` and `\` in values before substitution. Scripts return structured results (`midi-import:ok:*`, `dismissed:*`/`none`/`unknown:*`) parsed by Python — exit code alone is never trusted. `.gitattributes` pins these files to UTF-8 (Script Editor re-saves as UTF-16, which breaks template loading).
