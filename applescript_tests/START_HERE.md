# AppleScript Testing - START HERE

## What We're Doing

The Pro Tools automation scripts were written based on assumptions about the UI. We need to validate each script against the actual Pro Tools interface to ensure they work correctly.

## What's in This Directory

```
applescript_tests/
├── START_HERE.md                           ← You are here
├── README.md                               ← Testing strategy and script documentation
├── ACCESSIBILITY_INSPECTOR_GUIDE.md        ← How to use Accessibility Inspector
├── TESTING_CHECKLIST.md                    ← Detailed checklist for each script
│
├── test_launch.applescript                 ← Test: Launch Pro Tools
├── test_create_session.applescript         ← Test: Create session
├── test_save_session.applescript           ← Test: Save (Cmd+S)
├── test_close_session.applescript          ← Test: Close (Cmd+W)
├── test_save_session_as.applescript        ← Test: Save to location
├── test_import_audio.applescript           ← Test: Import audio (CRITICAL - SRC)
├── test_import_midi.applescript            ← Test: Import MIDI
└── test_import_template.applescript        ← Test: Import template (CRITICAL - SRC + warning)
```

## Quick Start

### 1. Setup (One Time)

#### Enable Accessibility Permissions
1. Open System Settings
2. Go to Privacy & Security → Accessibility
3. Add Terminal (or your terminal app) to the list
4. Enable the checkbox
5. **Restart your terminal**

#### Install Accessibility Inspector
```bash
# Launch Accessibility Inspector
open /System/Library/CoreServices/Applications/Accessibility\ Inspector.app
```

If not found, it's included with Xcode Developer Tools:
```bash
xcode-select --install
```

#### Create Test Files/Folders
```bash
# Create test directories
mkdir -p ~/Desktop/test_audio
mkdir -p ~/Desktop/test_midi
mkdir -p ~/Desktop/test_sessions

# Copy some WAV files to ~/Desktop/test_audio
# Copy a MIDI file to ~/Desktop/test_midi
# Have a .ptx template file ready
```

### 2. Testing Workflow (For Each Script)

#### A. Read the docs
1. Open `README.md` - find the section for the script you're testing
2. Understand what it's supposed to do
3. Note what to verify

#### B. Prepare
1. Set up Pro Tools in the required state (see "Before Running" in README)
2. Update any paths in the test script (marked with `TODO:`)
3. Have Accessibility Inspector open

#### C. Run the test
```bash
cd /Users/chris/Workspace/Pro\ Tools\ Prepper/applescript_tests
osascript test_launch.applescript
```

#### D. Observe
- Watch what happens in Pro Tools
- Note any errors in terminal
- Check Console.app for AppleScript logs (use `log` statements)

#### E. Inspect with Accessibility Inspector
1. Click the "Target" button (crosshair icon)
2. Hover over UI elements mentioned in the script
3. Verify actual names match script assumptions
4. Write down exact names

#### F. Fix if needed
1. Edit the test script with correct element names
2. Run again
3. Repeat until it works

#### G. Document
1. Use `TESTING_CHECKLIST.md` to check off what works
2. Write down exact UI element names in the checklist
3. Note any issues/gotchas

### 3. Recommended Testing Order

**Start simple, build up to complex:**

```
1. test_launch.applescript          (Simple - just launch)
   ↓
2. test_create_session.applescript  (Medium - UI interaction)
   ↓
3. test_save_session.applescript    (Simple - keyboard shortcut)
   ↓
4. test_close_session.applescript   (Simple - keyboard shortcut)
   ↓
5. test_save_session_as.applescript (Medium - dialog navigation)
   ↓
6. test_import_audio.applescript    (Complex - CRITICAL for SRC)
   ↓
7. test_import_midi.applescript     (Medium - similar to audio)
   ↓
8. test_import_template.applescript (Complex - CRITICAL for SRC + warning)
```

## Critical Questions to Answer

These are the most important unknowns we need to verify:

### 1. Apply SRC Checkbox (HIGHEST PRIORITY)
**In Audio Import Dialog:**
- [ ] Does "Apply SRC" checkbox exist?
- [ ] What is its exact name?
- [ ] What value means unchecked (0 or 1)?
- [ ] Can it be set via AppleScript?

**In Session Data Import Dialog:**
- [ ] Does "Apply SRC" checkbox exist here too?
- [ ] Same name as audio import, or different?

**Why critical**: If we can't disable SRC, audio quality degrades. This is a deal-breaker.

### 2. Session Start Time Warning (HIGH PRIORITY)
**When importing template with different start time:**
- [ ] Does the warning dialog appear?
- [ ] What is the exact window name?
- [ ] What button dismisses it (OK, Continue, Yes)?

**Why critical**: If we can't dismiss this, automation hangs forever.

### 3. UI Element Names (MEDIUM PRIORITY)
- Dashboard window actual name
- Sample rate popup and menu items
- Bit depth popup and menu items
- Import dialog window names
- Progress indicator window names

**Why important**: Scripts fail if names don't match exactly.

## How to Run a Test Script

### From Terminal
```bash
# Navigate to this directory
cd /Users/chris/Workspace/Pro\ Tools\ Prepper/applescript_tests

# Run a script
osascript test_launch.applescript

# Check exit code
echo $?  # 0 = success, non-zero = error
```

### From Script Editor (Better for Debugging)
1. Open Script Editor app (in /Applications/Utilities/)
2. File → Open → Select test script
3. Click "Run" button (or Cmd+R)
4. View results and errors in bottom panel
5. Can step through line by line

### Viewing Logs
AppleScript `log` statements appear in:
- Script Editor's "Messages" panel
- Console.app (filter by "osascript")

```bash
# Watch Console logs in real-time
log stream --predicate 'process == "osascript"' --level debug
```

## What Success Looks Like

### For Each Script
- ✅ Runs without errors
- ✅ Pro Tools UI responds as expected
- ✅ All `log` statements show success messages
- ✅ Operation completes (session created, file imported, etc.)
- ✅ Timing is reasonable (not too slow)

### For Apply SRC Verification
```applescript
log "Apply SRC checkbox successfully disabled and verified"
```
You should see this in Console/Script Editor. If not, the checkbox handling failed.

### For Session Start Time Warning
```applescript
log "Dismissed Session Start Time warning (OK)"
```
You should see this if the warning appeared and was dismissed.

## Troubleshooting

### "Permission denied" or "Not authorized"
→ Accessibility permissions not enabled. Restart terminal after enabling.

### "Window not found" or "Element not found"
→ UI element name doesn't match. Use Accessibility Inspector to find correct name.

### Script hangs/never completes
→ Waiting for element that never appears. Check window names, add shorter timeouts.

### "Can't get checkbox 'Apply SRC'"
→ Either:
  - Checkbox doesn't exist in this Pro Tools version
  - Checkbox has different name
  - Dialog is in different state

Use Accessibility Inspector to verify.

### Script works sometimes, fails other times
→ Timing issue. Add longer delays before checking for elements.

## After All Tests Pass

1. **Document findings** in `TESTING_CHECKLIST.md`
2. **Update production scripts** in `src/protools/scripts/` with correct element names
3. **Update `CLAUDE.md`** with any UI quirks discovered
4. **Test full workflow** - run all scripts in sequence:
   ```bash
   osascript test_launch.applescript && \
   osascript test_create_session.applescript && \
   osascript test_import_audio.applescript && \
   osascript test_save_session.applescript && \
   osascript test_close_session.applescript
   ```
5. **Test with different sample rates** - Repeat with 44.1kHz, 48kHz, 96kHz audio
6. **Run app** - Try the full Python app with real Pro Tools
7. **Update TODO.md** - Mark manual testing tasks complete

## Getting Help

If you get stuck:

1. **Check Console.app** for detailed error messages
2. **Use Accessibility Inspector** to verify element names
3. **Add more logging** to scripts to see where it fails
4. **Test in Script Editor** for better debugging
5. **Simplify** - comment out parts to isolate the problem
6. **Search** - AppleScript System Events documentation

## Key Files to Update Later

After testing completes, these production files need updates:

```
src/protools/scripts/
├── launch_protools.applescript          ← Update with correct Dashboard name
├── create_session.applescript           ← Update field/popup/menu names
├── import_audio.applescript             ← Update with SRC checkbox findings
├── import_midi.applescript              ← Update dialog/checkbox names
├── import_template.applescript          ← Update SRC + warning handling
├── save_session.applescript             ← Probably fine as-is (uses Cmd+S)
└── close_session.applescript            ← Probably fine as-is (uses Cmd+W)
```

## Timeline Estimate

**Don't rush this** - accuracy is more important than speed.

- Setup: 15-30 minutes
- Each simple script (launch, save, close): 10-20 minutes
- Each medium script (create, save as, MIDI): 20-40 minutes
- Each complex script (audio, template): 30-60 minutes

**Total**: 3-5 hours of focused testing

Take breaks. Test carefully. Document everything.

---

## Ready to Start?

1. [ ] Read this document completely
2. [ ] Enable Accessibility permissions
3. [ ] Install Accessibility Inspector
4. [ ] Create test files/folders
5. [ ] Open `README.md` to understand first script
6. [ ] Open `TESTING_CHECKLIST.md` to track progress
7. [ ] Open `ACCESSIBILITY_INSPECTOR_GUIDE.md` for reference
8. [ ] Run `test_launch.applescript` and begin!

**Good luck!** Take your time and document everything you discover.
