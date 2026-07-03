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

## ✅ Live validation results (2026-07-03, Pro Tools 2024.3)

1. [x] **Connection probe** — PTSL v3, all workflow commands available
2. [x] **⚠️ import_audio spike** — **VALIDATED**: files copied into Audio Files
       (not linked) + new tracks created. Step 5 is PTSL, no fallback needed.
3. [x] **Template import E2E via production PTSLWorkflow** — 87 tracks imported
       from Speed Mix Template, saved, .ptx verified on disk, closed.
       **Major discovery**: PACE/iLok "Activation is required" dialogs (one per
       unlicensed plugin when the iLok isn't plugged in) are INVISIBLE to
       accessibility (DRM) — they cannot be auto-dismissed. The workflow now
       waits up to `user_dialog_timeout` (600 s) with logged instructions while
       the user presses Quit on each, then resumes and verifies. Also fixed:
       supervisor no longer crashes on PACE-poisoned AX queries (-10000 →
       "ax-error:"), and blocked track queries are never read as "zero tracks".
4. [x] Transient 106 "Session state is already changing" right after Pro Tools
       startup — handled with patient state-checked retry.

## 🎯 Next Up — remaining live tests (manual)

1. [ ] **One real job end-to-end from the app UI** — audio + template into `testing/`
       (best with iLok plugged in, or expect to Quit activation windows once)
2. [ ] **Restart recovery** — quit Pro Tools mid-idle, verify next job relaunches
       and reconnects
3. [ ] **MIDI import** — job with .mid files; verify hardened script + tempo/key options
4. [ ] **Multi-job soak** — 3+ jobs, mixed sample rates, with/without template/MIDI
5. [ ] Tip for batches without the iLok: consider iLok Cloud sessions for the
       licensed plugins, so activation windows never appear

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
