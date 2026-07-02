# Pro Tools Session Builder — Rebuild Plan & Improvement Proposals

**Date**: 2026-07-03
**Status**: PTSL approach validated live against Pro Tools 2024.3 (PTSL v3) on this machine
**Audience**: Developer implementing the next version of the app

---

## 1. Executive Summary

This app batch-creates Pro Tools sessions from song folders: it scans audio files,
detects sample rate/bit depth, queues jobs, then drives Pro Tools to create a session,
import audio/MIDI, import a session template, and save — one job at a time.

The original implementation drives Pro Tools entirely through AppleScript UI scripting
(System Events), which is inherently fragile: keystrokes go to whatever has focus,
dialogs race the script, and exit code 0 is the only success signal. In practice the
automation drifted out of sync with Pro Tools ("a step behind"), stalled in polling
loops, and reported steps complete that never ran.

**The core proposal: rebuild the Pro Tools automation layer on PTSL** — Avid's official
gRPC scripting API built into Pro Tools (2022.4+, v3 in Pro Tools 2024.3) — and demote
AppleScript to two small, well-guarded fallback roles. Everything above the automation
layer (scanning, analysis, path resolution, queue, job executor, UI) is already
automation-agnostic, tested (~100 unit tests), and carries over.

**Validated on 2026-07-03, live against this machine's Pro Tools 2024.3:**

| Operation | Result |
|---|---|
| Connect + version handshake | ✅ PTSL v3, typed errors |
| Create session (48 kHz / 24-bit WAV, named, at target path) | ✅ `.ptx` verified on disk |
| Import Session Data from a `.ptx` template | ✅ **87 tracks** imported from "Speed Mix Template" (groups, routing, inserts) |
| Save session / Close session / Reopen session | ✅ |
| Audio import (`import_audio`) | ⚠️ Command exists in v3; **not yet live-tested** |
| MIDI import | ❌ No PTSL v3 equivalent — keep AppleScript fallback |

Test artifacts: `prototypes/ptsl_probe.py` (read-only connection probe) and
`prototypes/ptsl_prototype.py` (end-to-end create→import→save→close).

---

## 2. Why PTSL (what it eliminates)

Each row was a hand-tuned, brittle AppleScript mechanism. With PTSL it is a request
parameter or simply not needed:

| Old AppleScript mechanism | PTSL replacement |
|---|---|
| Dashboard form fill: Cmd+A, typed session name, arrow-key counting through sample-rate popup, typeahead into bit-depth popup | `create_session(name, path)` builder: `.wave_format()`, `.sample_rate(48000)`, `.bit_depth(24)` |
| Save dialog navigation (Cmd+Shift+G, typed path, fixed `delay 10`) | Path is a parameter of create |
| "Apply SRC" checkbox hunt + verify (audio + template imports) | Import behavior is a parameter (`link_to_source_audio()` / `force_audio_to_session_format()`); no SRC ever applied implicitly |
| Track mapping hack (`AXPress` row 1 + Cmd+A to select all source tracks) | `import_as_new_tracks()` |
| "Session Start Time" warning dismissal | `maintain_absolute_timecode()` — no warning raised |
| Polling for windows named "Importing" to detect completion | Synchronous command completion + typed errors |
| stderr string-parsing to classify errors | Typed error codes (e.g. `PT_NoOpenedSession` = 106, `PT_InvalidParameter` = 126) |
| Launch: poll for Dashboard window, Cmd+N fallback | Not needed — just probe the gRPC endpoint |

---

## 3. Critical PTSL v3 Quirks (discovered in live testing — MUST handle)

These four findings cost a debugging session to discover. Bake them in from day one.

### 3.1 `import_data` requires an explicit timecode start
py-ptsl 301's builder defaults `timecode_mapping_start_time` to `""`, which Pro Tools
2024.3 rejects with `PT_InvalidParameter` (126). Always set `"00:00:00:00"` (or the
session start) even when using `maintain_absolute_timecode()`.

```python
imp = engine.import_data(str(template_path))
imp.import_as_new_tracks()
imp.link_to_source_audio()
imp.maintain_absolute_timecode()
imp.import_clips_and_media()
imp._timecode_mapping_start_time = "00:00:00:00"   # REQUIRED on PTSL v3
imp.import_data()
```

### 3.2 Modal dialogs poison every PTSL response
While ANY modal dialog is up (observed: "Missing AAX Plugins", "Save changes before
closing?"), **all** PTSL commands return `PT_NoOpenedSession` (106) — even when a
session is open. Commands issued during a modal appear to queue and execute after
dismissal. Consequences:

- Error 106 does NOT reliably mean "no session"; treat it as *"no session OR a modal
  is blocking"* and invoke the dialog supervisor (§5) before concluding anything.
- The user's mix template references plugins not installed natively on this machine
  (Altiverb 7, C4, PuigTec EQP1A, S1 Imager), so **"Missing AAX Plugins" appears on
  every template import/open here**. This is the normal path, not an edge case.

### 3.3 Rapid command cycling can wedge/crash Pro Tools 2024.3
Back-to-back create/import/close cycles with no settling time hung Pro Tools hard
enough to require a force-quit. Rules:
- Call `engine.host_ready_check()` before each operation.
- Sleep ~5–10 s after create/import/open before the next command (make configurable).
- One job at a time (the queue is already strictly serial — keep it that way).

### 3.4 py-ptsl 301 + modern protobuf compatibility shim
`py-ptsl==301.0.0` matches PTSL v3 exactly, but calls protobuf's `json_format` with the
pre-protobuf-5 kwarg `including_default_value_fields`. On Python ≥3.13 protobuf 5+ is
required, so install the shim before importing `ptsl` (working copy in
`prototypes/ptsl_probe.py`): wrap `MessageToJson`/`MessageToDict` and rename the kwarg
to `always_print_fields_with_no_presence`. Alternatively pin Python 3.12 and
protobuf 4.25.x and drop the shim. When Pro Tools is upgraded, bump py-ptsl to the
matching release (401→2024.6, 500→2024.10, 60x→2025.6+).

---

## 4. Target Architecture

Unchanged layers are marked ✓ (keep, with the small bug fixes in §8).

```
FolderScanner ✓ → AudioAnalyzer ✓ → SessionSpec ✓ → Job ✓ → QueueManager ✓ (serial)
                                                              ↓
                                                        JobExecutor ✓ (step order updated, §6)
                                                              ↓
                                              ProToolsWorkflowProtocol (existing interface)
                                                    ↓                      ↓
                                            PTSLWorkflow (NEW)     AppleScript fallback (kept for:)
                                              gRPC :31416           • MIDI import
                                                                     • Dialog supervisor
```

### 4.1 `PTSLWorkflow` (new module: `src/protools/ptsl_workflow.py`)

Implements the existing `ProToolsWorkflowProtocol`, so `JobExecutor`, the queue, and
the UI require **zero changes** to adopt it.

```python
class PTSLWorkflow:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._engine = None            # lazy; reconnect on ChannelError

    # -- connection management -------------------------------------------
    def _ensure_engine(self):
        """Connect (or reconnect) and host_ready_check. Retry with backoff.
        Pro Tools restarts must be survivable: a dead channel invalidates
        the cached engine, next call reconnects."""

    def _settle(self):
        time.sleep(self.settings.ptsl_settle_time)   # default 5–10 s

    # -- protocol methods --------------------------------------------------
    def launch(self):
        # open -a "Pro Tools" if endpoint down, then poll endpoint (~15 s
        # warm start; allow minutes for cold start). No Dashboard handling.

    def create_session(self, name, sample_rate, bit_depth, output_dir):
        # parent_dir.mkdir(); builder: wave_format/sample_rate/bit_depth;
        # sample rate stays an int Hz — no "48 kHz" string formatting.
        # settle; verify session_path() matches expectation.

    def import_template(self, template_path):
        # §3.1 exactly. After import: run dialog supervisor (§5) to clear
        # "Missing AAX Plugins", then settle, then verify via track_list().

    def import_audio(self, files):
        # engine.import_audio(file_list=[...], audio_operations=Copy, ...)
        # ⚠️ UNTESTED on v3 — validate first (§7). Fallback: hardened
        # import_audio.applescript if v3's implementation proves unusable.

    def import_midi(self, files):
        # AppleScript fallback (no PTSL v3 equivalent). Precondition-guarded
        # version of import_midi.applescript.

    def save_session(self, session_file):
        # engine.save_session(); poll (not fixed-sleep) for .ptx mtime/existence.

    def close_session(self):
        # engine.close_session(save_on_close=True); then dialog supervisor
        # sweep — "Save changes?" can still appear and must be cleared.
```

### 4.2 Error taxonomy

| Signal | Meaning | Action |
|---|---|---|
| gRPC `UNAVAILABLE` / channel error | Pro Tools not running or crashed | Relaunch + reconnect; retry job step from a checkpoint, not blindly |
| `PT_NoOpenedSession` (106) | No session **or modal dialog up** | Run dialog supervisor; re-query; only then treat as "no session" |
| `PT_InvalidParameter` (126) | Bad/missing request field | Non-retryable; fix parameters (check §3.1 first) |
| Command timeout | Pro Tools busy/stuck | host_ready_check loop; dialog supervisor; then fail the job cleanly |

Retries must be **state-aware**: verify current state (session open? correct name?)
before re-issuing any command. Never blindly re-run a whole step. (The old
controller's "retry the entire script by default" design caused the out-of-sync
behavior and must not be replicated.)

---

## 5. Dialog Supervisor (small AppleScript that remains)

One focused script, not a general automation layer. Called at defined checkpoints
(after import, after close, on any 106) and optionally as a lightweight watchdog
between job steps:

1. List Pro Tools' windows via System Events.
2. If a window matches a **whitelist** of known informational dialogs, dismiss it
   with its safe button and log which one:
   - "Missing AAX Plugins" → `OK`
   - "Save changes … before closing?" → `Save` (sessions are ours; never "Don't Save")
   - Session Notes / playback-engine notices → `OK`
3. Anything not whitelisted: do NOT touch it — report its name/text back to Python
   so the job fails with a *diagnosable* message ("blocked by dialog: <name>").

Return a structured result (e.g. `dismissed=Missing AAX Plugins` / `none` /
`unknown=<title>`); Python parses it. Never dismiss blind, never send bare Return.

Requires Accessibility permission for the app's process (existing startup check
stays; System Settings → Privacy & Security → Accessibility).

---

## 6. End-to-End Job Pipeline (revised)

Queue behavior is unchanged: multiple jobs queued in the UI, executed strictly
serially. Per-job steps become:

| # | Step | % | Implementation |
|---|---|---|---|
| 1 | Validate spec | 5 | unchanged (Python) |
| 2 | Ensure parent dir | 10 | unchanged (Python) |
| 3 | Ensure Pro Tools + PTSL endpoint | 20 | launch if needed; poll endpoint; host_ready_check |
| 4 | Create session | 30 | PTSL builder; settle; verify `session_path()` |
| 5 | Import audio | 50 | PTSL `import_audio` (after §7 validation) or hardened AppleScript |
| 6 | Import MIDI | 70 | AppleScript fallback (skip if no MIDI) |
| 7 | Import template | 85 | PTSL `import_data` (§3.1) + dialog supervisor + track-count verify |
| 8 | Save | 95 | PTSL save; poll `.ptx` on disk |
| 9 | Close | 100 | PTSL close + dialog supervisor sweep |

Between steps: `host_ready_check()` + configurable settle. Step 7's verification
(`track_list()` count > 0) is the postcondition that the old system never had.

**Settings changes** (`AppSettings`): add `ptsl_settle_time` (default 8 s),
`ptsl_connect_timeout` (default 240 s, cold starts are slow), `ptsl_port` (31416).
Keep `dialog_wait_time`/retry settings only for the two surviving AppleScripts.
Remove obsolete AppleScript timing knobs from the Settings UI as scripts are deleted.

---

## 7. Open Items to Validate Before Building (½ day, in this order)

1. **`import_audio` on PTSL v3** — one prototype run importing 2–3 WAVs from
   `tests/fixtures/` into a scratch session with `audio_operations=Copy`. Verify the
   files are *copied* into the session's Audio Files folder (project requirement:
   copy, never link) and land on new tracks vs. clip list only. This determines
   whether step 5 is PTSL or AppleScript.
2. **Dialog supervisor dry run** — trigger the Missing AAX Plugins dialog via a
   template import and confirm the whitelist script sees and dismisses it.
3. **Pro Tools restart recovery** — kill Pro Tools mid-idle, confirm reconnect logic
   revives the engine and the next queued job proceeds.

---

## 8. Bug Fixes Owed to the Existing Code (regardless of migration)

Found in code review 2026-07-02; fix the ones that survive the migration:

1. **No escaping in AppleScript placeholder substitution**
   (`applescript_controller.py:107`) — a `"` or `\` in artist/song/paths breaks the
   generated script. Affects the two surviving scripts. Escape both characters.
2. **Blind `keystroke return`** in `import_template.applescript` — script is being
   deleted; do not replicate the pattern in the MIDI fallback.
3. **Retry-by-default of non-idempotent scripts** (`_is_retryable_error` returns
   `True` when unsure) — replace with state-aware retry (§4.2).
4. **Subprocess timeout (120 s) can undercut script-internal timeouts (up to 300 s)**
   (`applescript_controller.py:131`) — compute subprocess timeout from the script's
   own maximum + margin.
5. **`import_template.applescript` keeps reverting to UTF-16** when edited in Script
   Editor — moot after deletion; add a `.gitattributes`/CI check for the survivors.
6. **Status label stays red forever after one error** (`main_window.py:508–512`) —
   `update_status` never resets the stylesheet set by `_show_error`.
7. **`save_session` verification uses a fixed 1 s sleep** (`workflow.py:199–201`) —
   poll with timeout; large sessions save slower.
8. **AppleScript `log` output goes to stderr and is discarded on success** — the
   surviving scripts should return structured results parsed by Python (§5).
9. **Housekeeping** — commit the in-progress Dashboard-save work; delete
   `create_session.applescript.bak`, `debug_create_session.applescript`, root-level
   `test_*.applescript`, `fix_accessibility.sh`; move ad-hoc test scripts under
   `applescript_tests/`.

---

## 9. UI Modernization Proposals (independent pass)

Current UI is stock unstyled PySide6 with an in-window Windows-style menu bar.
Proposals, cheapest-first:

1. **Native macOS menu bar** — remove `setNativeMenuBar(False)`; fix the original
   disappearing-menu issue properly (it's typically an app-activation/parenting issue,
   and `setApplicationDisplayName` is already being set).
2. **Application-wide QSS theme** — dark theme with consistent spacing, rounded
   controls, one accent color; replaces the single inline-styled green button.
   Hand-rolled QSS (~150 lines) or `qt-material`/`pyqtdarktheme`.
3. **Queue table upgrades** — real `QProgressBar` cell widgets instead of "45%" text;
   colored status chips (pending/running/completed/failed); preserve selection across
   table refreshes.
4. **Layout** — `QSplitter` between queue and log sections; empty-state hint in the
   queue ("Drag a song folder to get started"); toolbar with Start/Pause icons.
5. **Job detail affordances** — per-job error tooltip on failed rows; double-click a
   completed job to reveal the session in Finder.
6. **Live automation status** — surface the dialog-supervisor and PTSL step results in
   the log with timestamps (the structured results from §4/§5 make this nearly free).

---

## 10. Suggested Delivery Phases

| Phase | Scope | Exit criterion |
|---|---|---|
| 0 | Housekeeping: commit WIP, prune debris, pin `py-ptsl==301.0.0` + shim (or Python 3.12), fix §8 items 1, 6, 7 | Clean repo, green tests |
| 1 | §7 validation spikes (audio import, dialog supervisor, restart recovery) | Go/no-go per step 5 |
| 2 | `PTSLWorkflow` + dialog supervisor + settings additions; wire behind protocol via a settings flag (AppleScript workflow kept as escape hatch) | One real job end-to-end from the UI |
| 3 | Multi-job queue soak (3+ jobs, mixed sample rates, with/without template/MIDI); state-aware retry + restart recovery | Unattended batch completes; induced PT crash recovers |
| 4 | Delete obsolete AppleScripts + their settings; harden the two survivors | AppleScript surface = 2 guarded scripts |
| 5 | UI modernization (§9) | — |

---

## Appendix A: Environment

- Pro Tools 2024.3 (PTSL v3), gRPC on `localhost:31416`
- `py-ptsl==301.0.0` (+ grpcio, protobuf ≥5 with shim — §3.4); Python 3.14 venv at `venv/`
- Template used in validation: `.../BIOMES/Audio/_TEMPLATES/Mix Templates/Speed Mix TEmplate/Speed Mix Template.ptx` (path is user-configurable in Settings; note it previously moved and broke the saved setting — consider a "template missing" pre-flight check in the UI)
- Working prototypes: `prototypes/ptsl_probe.py`, `prototypes/ptsl_prototype.py`
- Validation scratch output: `testing/ptsl_prototype/` (safe to delete)

## Appendix B: References

- py-ptsl: https://github.com/iluvcapra/py-ptsl · docs: https://py-ptsl.readthedocs.io/
- PTSL/Pro Tools version map: https://py-ptsl.readthedocs.io/en/latest/ptsl_versions.html
- Avid PTSL SDK (protobuf source, official docs): Avid Developer site
