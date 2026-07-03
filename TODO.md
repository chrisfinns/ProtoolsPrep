# Pro Tools Session Builder - TODO

**Last Updated**: 2026-07-03 (PTSL rebuild implemented)
**Current Phase**: ✅ PTSL REBUILD COMPLETE (code) — ⏳ awaiting live validation with Pro Tools

---

## 🏗️ What just happened (2026-07-03)

The automation layer was rebuilt on **PTSL** (official Pro Tools gRPC API) per
[docs/DEVELOPER_IMPROVEMENT_PLAN.md](docs/DEVELOPER_IMPROVEMENT_PLAN.md), phases 0–4:

- **Phase 0**: debris pruned; status-label stuck-red bug fixed; QueueWorker now uses
  `AppSettings.load()` (was silently ignoring all saved settings); `.gitattributes`
  pins `*.applescript` to UTF-8
- **Phase 1**: `ptsl_compat` (protobuf-5 shim), `PTSLClient` (connect/reconnect,
  ensure_ready, settle, typed error translation), new exception subtree
  (`PTSLError` → `ProToolsNotRunningError` / `SessionBlockedError` /
  `PTSLParameterError` / `DialogBlockedError`), new settings knobs
  (`ptsl_settle_time`, `ptsl_connect_timeout`, `save_poll_timeout`,
  `midi_import_timeout`), settings dialog updated
- **Phase 2**: `PTSLWorkflow` (implements `ProToolsWorkflowProtocol` — JobExecutor/UI
  unchanged), dialog supervisor (whitelist-only AppleScript + Python wrapper),
  `AppleScriptRunner` (escaped substitution, derived timeouts, no blind retry),
  hardened `import_midi.applescript`, QueueWorker wired to `PTSLWorkflow`
- **Phase 3**: deleted old layer — `workflow.py`, `applescript_controller.py`,
  `ui_scripting_utils.py`, and 7 obsolete .applescript files. Survivors:
  `import_midi.applescript` + `dialog_supervisor.applescript`
- **Phase 4**: unit tests for the new modules (mocked engine — no Pro Tools needed)

**Architecture, quirks, and retry policy are documented in CLAUDE.md** (rewritten).

---

## 🎯 Next Up — Live validation with real Pro Tools (manual)

Run these in order, with Pro Tools 2024.3 open and idle:

1. [ ] **Connection probe** (read-only, safe any time)
       `venv/bin/python prototypes/ptsl_probe.py`
2. [ ] **⚠️ import_audio spike** — the ONE PTSL v3 command never live-tested.
       `venv/bin/python prototypes/ptsl_audio_import_spike.py`
       PASS = files copied into Audio Files + new tracks created.
       FAIL = revive an AppleScript audio-import fallback (old script is in git
       history: `git show 0244397^:src/protools/scripts/import_audio.applescript`)
3. [ ] **Dialog supervisor dry run** — import the Speed Mix Template (raises
       "Missing AAX Plugins" on this machine every time) and confirm the
       supervisor dismisses it and the job continues
4. [ ] **One real job end-to-end from the UI** — audio + template into `testing/`
5. [ ] **Restart recovery** — quit Pro Tools mid-idle, verify next job relaunches
       and reconnects
6. [ ] **MIDI import** — job with .mid files; verify hardened script + tempo/key options
7. [ ] **Multi-job soak** — 3+ jobs, mixed sample rates, with/without template/MIDI

## 🎨 Later — UI modernization (plan §9, independent pass)

- [ ] Native macOS menu bar (remove `setNativeMenuBar(False)` properly)
- [ ] Application-wide QSS theme
- [ ] Real progress-bar cells + status chips in queue table
- [ ] QSplitter layout, empty-state hint, toolbar icons
- [ ] Per-job error tooltips; double-click completed job → reveal in Finder
- [ ] Surface dialog-supervisor/PTSL step results in the log (structured results make this nearly free)

## 📌 Maintenance notes

- **py-ptsl is pinned to 301.0.0** (matches Pro Tools 2024.3 / PTSL v3). When Pro
  Tools is upgraded, bump in lockstep: 401=2024.6, 500=2024.10, 60x=2025.6+ — and
  re-check whether the `ptsl_compat` shim is still needed.
- **Template path pre-flight**: the saved template path broke once when the file
  moved (iCloud). Consider a "template missing" check in the UI before queueing.
- `applescript_tests/` contains the old UI-scripting test harness — historical
  reference only; delete when confident.

> **Historical context**: [progress.md](progress.md) logs work before the PTSL pivot.
> The old AppleScript layer is recoverable from git history (commit `0244397^`).
