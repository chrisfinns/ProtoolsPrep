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
4. [x] **PACE/iLok activation windows CAN be automated** (2026-07-04): they
       looked invisible only because they live in their own short-lived
       `PACEEdenExperience` helper process (one per unlicensed plugin,
       spawned serially), not in Pro Tools. Their AX tree is fully readable —
       `button "Quit" of group 1 of window 1`. Supervisor pass 0 now Quits
       each automatically (validated live: EchoBoy, MicroShift, Little Plate,
       plus the Missing AAX dialog after). Batches run unattended without the
       iLok. Also fixed earlier: supervisor no longer crashes on AX -10000
       ("ax-error:"), blocked track queries never read as "zero tracks".
5. [x] Transient 106 "Session state is already changing" right after Pro Tools
       startup — handled with patient state-checked retry.

## 🎯 Next Up — remaining live tests (manual)

1. [ ] **One real job end-to-end from the app UI** — audio + template into `testing/`
       (PACE activation windows now auto-Quit; verify hands-off) — use the
       **bundled app** now so the test covers distribution
2. [ ] **Restart recovery** — quit Pro Tools mid-idle, verify next job relaunches
       and reconnects
3. [ ] **MIDI import** — job with .mid files; verify hardened script + tempo/key options
4. [ ] **Multi-job soak** — 3+ jobs, mixed sample rates, with/without template/MIDI

## 📦 App bundle (2026-07-04) — built & smoke-tested

`venv/bin/pyinstaller "Pro Tools Session Builder.spec" --noconfirm` →
`dist/Pro Tools Session Builder.app` (~131 MB, arm64). Launches from Finder,
logs to `~/Library/Logs/Pro Tools Session Builder.log`.

Bundle-readiness fixes that made it work:
- log file moved from cwd (unwritable `/` when Finder-launched) to ~/Library/Logs
- default output dir: `./testing` in a dev checkout, else `~/Documents/Pro Tools Sessions`
- **sox dependency removed entirely** — AudioAnalyzer now uses `soundfile`
  (libsndfile ships inside the wheel/bundle). No brew installs needed by users.
- spec bundles the two .applescript files; Info.plist has bundle name/ID +
  NSAppleEventsUsageDescription (proper Automation permission prompt)

Handing to another user — they need:
- Apple Silicon Mac (this build is arm64-only)
- Pro Tools **2024.3 or newer** (the PTSL server is backward compatible with
  the bundled v3 client; the app probes the server version at connect and
  shows a readable error only if Pro Tools is *older*). Their first run on a
  newer Pro Tools doubles as the live backward-compat validation — typed
  error handling fails loudly and safely if a command shifted.
- First run: right-click → Open (app is ad-hoc signed, not notarized), then
  grant Accessibility + Automation (System Events) when prompted
- Their own template path + output dir in Settings

## 🎨 UI modernization (plan §9) — ✅ done (commit af9d42f + follow-ups)

- [x] Native macOS menu bar (Settings pinned to File menu with explicit
      menu role; in-window Settings… button added — Qt otherwise relocates
      it to the app menu, titled "Python" when unbundled)
- [x] Application-wide dark studio theme (`src/ui/theme.py`: Fusion + QSS +
      palette; also fixes macOS native style clipping form fields)
- [x] Progress-bar cells + colored status labels in queue table
- [x] QSplitter layout, empty-state hint
- [x] Per-job error tooltips; double-click completed job → reveal in Finder
- [ ] Surface dialog-supervisor/PTSL step results in the log (structured results make this nearly free)

## 📌 Maintenance notes

- **py-ptsl is pinned to 301.0.0** (PTSL v3 = Pro Tools 2024.3). The pin is
  one-directional: newer Pro Tools accepts v3 commands (backward compatible);
  only *older* Pro Tools is rejected — with a clear message via the connect-time
  version probe in `ptsl_client.py`. Bump py-ptsl only to gain new commands
  (401=2024.6, 500=2024.10, 60x=2025.6+) and re-check the `ptsl_compat` shim.
- **Template path pre-flight**: the saved template path broke once when the file
  moved (iCloud). Consider a "template missing" check in the UI before queueing.
- `applescript_tests/` contains the old UI-scripting test harness — historical
  reference only; delete when confident.

> **Historical context**: [progress.md](progress.md) logs work before the PTSL pivot.
> The old AppleScript layer is recoverable from git history (commit `0244397^`).
