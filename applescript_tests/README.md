# AppleScript Testing Guide

This directory contains standalone test scripts for validating Pro Tools UI automation.

## Prerequisites

1. **Enable Accessibility Permissions**:
   - System Settings → Privacy & Security → Accessibility
   - Add Terminal (or your terminal app) to the list
   - Enable the checkbox

2. **Pro Tools Installed**: Ensure Pro Tools is installed and can launch

## Testing Strategy

Work through scripts in order from simplest to most complex. For each script:

1. **Read the script** - Understand what it's trying to do
2. **Run it** - Execute with `osascript script_name.applescript`
3. **Observe** - Watch what happens in Pro Tools
4. **Inspect UI** - Use Accessibility Inspector to verify element names
5. **Fix** - Update script based on actual UI behavior
6. **Retest** - Run again until it works reliably
7. **Document** - Note any discoveries/gotchas

## Using Accessibility Inspector

macOS includes Accessibility Inspector for examining UI elements:

```bash
# Launch Accessibility Inspector
open /System/Library/CoreServices/Applications/Accessibility\ Inspector.app
```

**How to use**:
1. Click the "Target" button (crosshair icon)
2. Hover over UI elements in Pro Tools
3. Inspector shows: element type, name, role, attributes
4. Verify our AppleScript references match actual names

**Key things to check**:
- Window names (e.g., "Dashboard", "Import Audio")
- Button labels (e.g., "Create", "Open")
- Checkbox names (e.g., "Apply SRC")
- Text field identifiers
- Popup button names

## Testing Order

### 1. Launch (`test_launch.applescript`)
**What it does**: Launches Pro Tools and waits for Dashboard

**Manual steps**:
1. Quit Pro Tools if running
2. Run: `osascript test_launch.applescript`
3. Watch Pro Tools launch

**What to verify**:
- [ ] Pro Tools activates
- [ ] Dashboard window appears (or Cmd+N opens it)
- [ ] Script completes without error
- [ ] Check window name is actually "Dashboard"

**Common issues**:
- Dashboard might be called "Quick Start" in some versions
- May need different menu path to open Dashboard
- Timing might be too short for cold starts

---

### 2. Create Session (`test_create_session.applescript`)
**What it does**: Creates a new 48kHz/24-bit session named "Test Session"

**Manual steps**:
1. Launch Pro Tools manually (or use test_launch first)
2. Ensure Dashboard is open (Cmd+N)
3. Run: `osascript test_create_session.applescript`
4. Watch session creation

**What to verify**:
- [ ] Session name field gets populated
- [ ] Sample rate popup works (check menu item names)
- [ ] Bit depth popup works (check menu item names)
- [ ] Create button works
- [ ] Session window appears

**Common issues**:
- Field names might be different ("Name" vs "Session Name")
- Popup button names might not be "Sample Rate"/"Bit Depth"
- Menu item names might vary ("48 kHz" vs "48000" vs "48.0 kHz")
- Session window title format unknown

**Use Accessibility Inspector to find**:
- Exact text field identifier for session name
- Exact popup button names
- Exact menu item text for each sample rate
- How to identify the session window appeared

---

### 3. Save Session As (`test_save_session_as.applescript`)
**What it does**: Saves current session to specific location

**Manual steps**:
1. Have a session open (create one with test_create_session)
2. Update `{save_path}` in script to actual test directory
3. Run: `osascript test_save_session_as.applescript`

**What to verify**:
- [ ] Save As dialog appears (Cmd+Shift+S)
- [ ] Go to folder works (Cmd+Shift+G)
- [ ] Path navigation works
- [ ] Save button clicks
- [ ] File appears in target directory

**Common issues**:
- Save dialog window name might vary
- Text field for filename might have different identifier
- Replace dialog might not appear as "sheet 1"

---

### 4. Save Session (`test_save_session.applescript`)
**What it does**: Saves session with Cmd+S

**Manual steps**:
1. Have unsaved session open (make a change)
2. Run: `osascript test_save_session.applescript`

**What to verify**:
- [ ] Save happens (session no longer has unsaved indicator)
- [ ] No error dialogs appear
- [ ] Script completes quickly

**This is the simplest script - should work as-is**

---

### 5. Close Session (`test_close_session.applescript`)
**What it does**: Closes current session with Cmd+W

**Manual steps**:
1. Have a session open (saved or unsaved)
2. Run: `osascript test_close_session.applescript`

**What to verify**:
- [ ] Session closes
- [ ] If unsaved, save dialog handled correctly
- [ ] Pro Tools returns to Dashboard or empty state

**Common issues**:
- Save dialog might have different button names
- Might need to handle "Save As" for never-saved sessions

---

### 6. Import Audio (`test_import_audio.applescript`)
**What it does**: Imports all audio files from a folder with SRC disabled

**Manual steps**:
1. Create test folder with a few WAV files
2. Have a session open
3. Update `{audio_folder_path}` in script to your test folder
4. Run: `osascript test_import_audio.applescript`
5. Watch import process

**What to verify**:
- [ ] File → Import → Audio menu path works
- [ ] Import dialog appears
- [ ] Go to folder navigation works (Cmd+Shift+G)
- [ ] Select all works (Cmd+A)
- [ ] "Apply SRC" checkbox exists and can be unchecked
- [ ] Checkbox value verification works
- [ ] Open button starts import
- [ ] Import completion detection works

**CRITICAL**:
- [ ] Verify "Apply SRC" is the actual checkbox name (use Inspector!)
- [ ] Test that checkbox value = 0 means unchecked
- [ ] Check import progress window name ("Importing..." exact text)

**Common issues**:
- Menu path might be different
- Import dialog window name might vary
- "Apply SRC" might be named differently or not exist
- Progress window name might be different
- Import might be too fast to detect progress window

**This is the most critical script to get right!**

---

### 7. Import MIDI (`test_import_midi.applescript`)
**What it does**: Imports MIDI files with tempo/key import enabled

**Manual steps**:
1. Create test folder with a MIDI file
2. Have a session open
3. Update `{midi_folder_path}` in script
4. Run: `osascript test_import_midi.applescript`

**What to verify**:
- [ ] File → Import → MIDI menu path works
- [ ] Import dialog appears
- [ ] Navigation works
- [ ] File selection works
- [ ] Tempo/key checkboxes exist (might not in all versions)
- [ ] Import completes

**Common issues**:
- MIDI import dialog might be simpler (no SRC option)
- Tempo/key checkboxes might not exist
- Progress indication might be different

---

### 8. Import Template (`test_import_template.applescript`)
**What it does**: Imports session data with SRC disabled and dismisses warning

**Manual steps**:
1. Create or find a Pro Tools template (.ptx file)
2. Have a session open
3. Update `{template_posix_path}` in script
4. Run: `osascript test_import_template.applescript`

**What to verify**:
- [ ] File → Import → Session Data menu path works
- [ ] Import dialog appears
- [ ] Navigation to template file works
- [ ] "Apply SRC" checkbox exists and disables
- [ ] Open button works
- [ ] "Session Start Time" warning appears (expected)
- [ ] Warning gets dismissed automatically

**CRITICAL**:
- [ ] Test if "Session Start Time" warning actually appears
- [ ] Find exact window name/description for the warning
- [ ] Test which button dismisses it (OK, Continue, Yes?)

**Common issues**:
- Session Data import might not have SRC option
- Warning dialog might have different name
- Warning might not appear if template matches session start time
- Button to dismiss might vary

---

## Script Testing Checklist

For each script, verify:

1. **Window/Dialog Names**: Match exactly what Accessibility Inspector shows
2. **Element Names**: Buttons, checkboxes, fields match actual UI
3. **Menu Paths**: Full menu hierarchy is correct
4. **Timing**: Delays are long enough but not excessive
5. **Error Cases**: Script handles errors gracefully
6. **Completion Detection**: Knows when operation finishes
7. **Verification**: Critical operations are verified (like SRC checkbox)

## Debugging Tips

**Script won't run**:
```bash
# Check for syntax errors
osascript -s s script.applescript
```

**Need to see what's happening**:
- Add `log "Step description"` statements
- Check Console.app for AppleScript logs
- Run script line by line in Script Editor

**Elements not found**:
- Use Accessibility Inspector to find exact names
- Check if UI is in different state than expected
- Add longer delays before accessing elements
- Verify Pro Tools is frontmost

**Script hangs**:
- Might be waiting for dialog that didn't appear
- Might be waiting for element that has different name
- Use timeout values to fail gracefully

## After All Scripts Work

Once all scripts are validated:

1. **Document findings** - Create a reference of actual UI element names
2. **Update main scripts** - Apply fixes to scripts in `src/protools/scripts/`
3. **Update CLAUDE.md** - Document any UI differences from assumptions
4. **Test workflow** - Run full sequence: launch → create → import → save → close
5. **Test edge cases** - Different sample rates, missing files, etc.

## Common Pro Tools UI Quirks to Watch For

- Window names may vary by Pro Tools version
- Dialog titles might be localized (if not English)
- Checkbox names might differ (e.g., "Apply SRC" vs "SRC" vs "Sample Rate Conversion")
- Menu items might have keyboard shortcuts in text (e.g., "Save⌘S")
- Progress dialogs might appear/disappear too fast to detect
- Some dialogs are sheets (child windows) vs separate windows
- Button order might vary (OK vs Cancel position)

## Questions to Answer During Testing

1. What is the exact name of the Dashboard window?
2. Does "Apply SRC" checkbox exist in audio import? Exact name?
3. Does "Apply SRC" exist in template import?
4. What is the exact text of sample rate menu items?
5. What is the exact window name for import progress?
6. Does "Session Start Time" warning appear? Exact name?
7. What button dismisses the start time warning?
8. How fast do imports complete (affects polling logic)?
9. Are there any unexpected dialogs/warnings we need to handle?
10. What happens if user clicks on Pro Tools during automation?

---

Good luck! Take your time with each script and document everything you discover.
