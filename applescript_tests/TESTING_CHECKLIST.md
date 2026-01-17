# AppleScript Testing Checklist

Use this checklist while testing each script. Check off items as you verify them.

## Setup

- [ ] Accessibility permissions enabled for Terminal
- [ ] Pro Tools installed and launches successfully
- [ ] Accessibility Inspector installed and working
- [ ] Test files prepared (audio, MIDI, template as needed)
- [ ] Test output directory created (`~/Desktop/test_sessions` or similar)

---

## 1. test_launch.applescript

**Goal**: Launch Pro Tools and open Dashboard window

### Before Running
- [X] Pro Tools is quit (not running)
- [X] Script is ready to run: `osascript test_launch.applescript`

### Run Test
- [X] Script executes without errors
- [X] Pro Tools application launches
- [X] Pro Tools becomes active/frontmost
- [X] Menu bar becomes accessible

### Verify with Accessibility Inspector
- [X] Dashboard window appears
- [X] Window name is exactly: Dashboard (write down actual name)
- [X] If Dashboard doesn't auto-open, Cmd+N opens it successfully

### Issues Found
```
(Document any problems, timing issues, or unexpected behavior)



```

### Script Status
- [X] ✅ Works perfectly as-is
- [ ] ⚠️  Works but needs timing adjustments
- [ ] ❌ Needs fixes (see Issues Found above)

---

## 2. test_create_session.applescript

**Goal**: Create new 48kHz/24-bit session named "Test Session"

### Before Running
- [x] Dashboard is open (run test_launch.applescript first if needed)
- [x] Script ready to run

### Run Test
- [x] Script executes
- [x] Session name field gets filled with "Test Session"
- [x] Sample rate changes to 48kHz
- [ ] Bit depth changes to 24-bit
- [ ] Create button gets clicked
- [ ] Session window appears

### Verify with Accessibility Inspector

#### Session Name Field
- [ ] Field exists
- [ ] Field type: AXTextField
- [ ] Field identifier: _____________ (write down actual name/title)

Does not exist but is already in focus when dashboard is open can just input name set value doesn't work

#### Sample Rate Popup
- [ ] Popup button name: name is whatever last loaded sample rate (write down)
- [ ] Menu item for 48kHz: 48 kHz (exact text)
- [ ] Menu item for 44.1kHz: 44.1 kHz (exact text)
- [ ] Menu item for 96kHz: 96 kHz (exact text)

			log "Attempting to set sample rate to 48 kHz..."
			try
				set sampButton to (first pop up button whose value of attribute "AXIdentifier" is "samp")
				delay 0.5
				-- TODO: Verify exact menu item text
				perform action "AXPress" of sampButton
				keystroke "48"
				log "Sample rate set to 48 kHz"
				key code 36


#### Bit Depth Popup
- [ ] Popup button name: name is whatever is selected on load (write down)
- [ ] Menu item for 24-bit: 24-bit (exact text)
- [ ] Menu item for 16-bit: 16-bit (exact text)
- [ ] Menu item for 32-bit: 32-bit float (exact text)

set bitPopup to (first pop up button whose value of attribute "AXIdentifier" is "bitd")
				delay 0.5
				--TODO: Verify exact menu item text
				perform action "AXPress" of bitPopup
				keystroke "24"
				key code 36
				
				
				delay 0.5
				
				-- Select the specific menu item directly
				-- Note: Try "24-bit" if "24 Bit" (with a space) fails
				click menu item "24-Bit" of menu 1 of bitPopup


#### Create Button
- [X] Button name: Create (should be "Create")

#### Session Window
- [ ] Window appears after Create is clicked
- [ ] Window name format: _____________ (e.g., "Test Session", "Test Session - Edit", etc.)

No another window opens. this seems to be a dialog about where to save the session. window name is "Save"   maybe we can use shift+command+g to paste the filepath hit enter and then click save
### Issues Found
```
The name section is automatically in focus with the "Untitled" highlighted if we just input the name here it should work

I edited the script "popup button" doesn't work it should be "pop up button"
When Dashboard is open it always has focus


I made adjustments in the file.

```

### Script Status
- [ ] ✅ Works perfectly as-is
- [X] ⚠️  Works but needs adjustments
- [ ] ❌ Needs fixes

---

## 3. test_save_session.applescript

**Goal**: Save session with Cmd+S

### Before Running
- [ ] Session is open (created with test_create_session)
- [ ] Updated script paths if needed

### Run Test
- [ ] Script executes
- [ ] Cmd+S is pressed
- [ ] Session saves (no unsaved indicator)
- [ ] No error dialogs appear

### Verify
- [ ] Session file exists on disk
- [ ] File has .ptx extension
- [ ] Script completes quickly (should be fast)

### Issues Found
```

I don't think we need this script because once I click create in the previous script it opens save dialog and asks me for location to save it. 





```

### Script Status
- [ ] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## 4. test_close_session.applescript

**Goal**: Close session with Cmd+W

### Before Running
- [x] Session is open

### Run Test
- [ ] Script executes
- [ ] Cmd+W is pressed 
- [ ] Session closes
- [ ] Pro Tools returns to Dashboard or empty state

### Verify
- [ ] If session was saved: closes immediately
- [ ] If session unsaved: save dialog appears
- [ ] Save dialog gets dismissed correctly

### Verify with Accessibility Inspector (if save dialog appears)
- [ ] Save dialog window name: _____________
- [ ] "Don't Save" button name: _____________
- [ ] Alternative button names: _____________

### Issues Found
```
I updated the applescript with the correct key command and a window pops up without a name but the save button is on focus so we can just hit enter. We want it to save.


```

### Script Status
- [ ] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## 5. test_save_session_as.applescript

**Goal**: Save session to specific location

### Before Running
- [ ] Updated `savePath` in script to actual test directory
- [ ] Updated `sessionName` if desired
- [ ] Test directory exists
- [ ] Session is open

### Run Test
- [ ] Script executes
- [ ] Save As dialog appears (Cmd+Shift+S)
- [ ] Go to folder works (Cmd+Shift+G)
- [ ] Path is entered and accepted
- [ ] Filename is set correctly
- [ ] Save button clicks
- [ ] File saves to correct location

### Verify with Accessibility Inspector

#### Save As Dialog
- [ ] Window name: _____________ (contains "Save"?)

#### Filename Field
- [ ] Text field identifier: _____________
- [ ] Which text field (1, 2, or other): _____________

#### If file exists
- [ ] Replace sheet appears: Yes / No
- [ ] Sheet is `sheet 1`: Yes / No / Other: _____________
- [ ] Replace button name: _____________

### Verify on Disk
- [ ] File exists at specified path
- [ ] Filename is correct
- [ ] File can be opened in Pro Tools

### Issues Found
```
We don't need this applescript.. The Session is already named correctly from the create session.


```

### Script Status
- [ ] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## 6. test_import_audio.applescript

**Goal**: Import audio files with Apply SRC disabled

### Before Running
- [X] Created test folder with WAV files (e.g., `~/Desktop/test_audio`)
- [X] Updated `audioFolderPath` in script to actual test folder path
- [X] Session is open (created one with test_create_session)

### Run Test
- [X] Script executes
- [X] File → Import → Audio menu works
- [X] Import Audio dialog appears
- [X] Go to folder navigation works
- [X] Files are selected (Cmd+A)
- [ ] "Apply SRC" checkbox is found
- [ ] "Apply SRC" checkbox gets unchecked
- [ ] Verification confirms checkbox value is 0
- [ ] Open/Import button clicks
- [ ] Files import into session
- [ ] Script detects import completion

### Verify with Accessibility Inspector

#### Menu Path
- [X] Menu: File → Import → Audio...
- [X] Menu item name:  Audio (likely "Audio...")

#### Import Dialog
- [X] Window name: Import Audio (contains "Import Audio"?)
but it on forced focus. I Tried to get the name with inspector but couldn't find it.

#### Apply SRC Checkbox
- [x] **CRITICAL**: Checkbox exists: Yes / No
- [x] Checkbox name: Apply SRC (should be "Apply SRC")
- [ ] Checked value: _____________ (should be 1)
- [ ] Unchecked value: _____________ (should be 0)
- [ ] Can be set via script: No

It is grayed out and no option to change (disabled)
#### Open/Import Button
- [ ] Button name: _____________ ("Open" or "Import"?)

#### Progress Indication
- [ ] Progress window appears during import: Yes / No
- [ ] Progress window name: _____________ (contains "Importing"?)
- [ ] Progress window closes when done: Yes / No

### Verify in Pro Tools
- [ ] Audio files appear in session
- [ ] Files are in Clips list
- [ ] No sample rate conversion occurred (verify audio quality)

### Issues Found
```
CRITICAL: Document if "Apply SRC" checkbox exists and exact name

Big problem there wasn't a "Copy All" step in the script we need to copy all because it will just link the files instead of importing to that location.

It seems like most of the logging doesn't work window the UI names for windows is misnammed 

CRITICAL: I fix the script and it works completely for now


```

### Script Status
- [X] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## 7. test_import_midi.applescript

**Goal**: Import MIDI files with tempo/key import

### Before Running
- [ ] Created test folder with MIDI file (e.g., `~/Desktop/test_midi`)
- [ ] Updated `midiFolderPath` in script
- [ ] Session is open

### Run Test
- [X] Script executes
- [X] File → Import → MIDI menu works
- [X] Import MIDI dialog appears
- [X] Navigation works
- [X] Files selected
- [ ] Tempo/key checkboxes handled
- [X] Import completes

### Verify with Accessibility Inspector

#### Import Dialog
- [ ] Window name: _____________ (contains "Import MIDI"?)

#### Import Tempo Checkbox
- [X] Checkbox exists: Yes / No
- [ ] Checkbox name: _____________

#### Import Key Signature Checkbox
- [X] Checkbox exists: Yes / No
- [ ] Checkbox name: _____________

#### Button
- [ ] Button name: _____________ ("Open" or "Import"?)

### Verify in Pro Tools
- [ ] MIDI appears in session
- [ ] Tempo imported (if enabled)
- [ ] Key signature imported (if enabled)

### Issues Found
```
I didn't check all the boxes on here but it works correctly. The check boxes are grayed out in this base when I worked on it. We don't need to add it to so the script right now


```

### Script Status
- [ ] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## 8. test_import_template.applescript

**Goal**: Import template with SRC disabled and warning dismissed

### Before Running
- [ ] Have a Pro Tools template file (.ptx)
- [ ] Updated `templatePath` in script to actual .ptx file
- [ ] Session is open
- [ ] Template has different start time than session (to trigger warning)

### Run Test
- [ ] Script executes
- [ ] File → Import → Session Data menu works
- [ ] Import Session Data dialog appears
- [ ] Navigation to template file works
- [ ] "Apply SRC" checkbox handling (if exists)
- [ ] Open button clicks
- [ ] "Session Start Time" warning appears (expected)
- [ ] Warning gets dismissed automatically
- [ ] Template data imports

### Verify with Accessibility Inspector

#### Import Dialog
- [ ] Window name: _____________ (contains "Import Session Data"?)

#### Apply SRC Checkbox
- [ ] Checkbox exists in Session Data import: Yes / No
- [ ] If yes, checkbox name: _____________

#### Session Start Time Warning
- [ ] **CRITICAL**: Warning appears: Yes / No
- [ ] Window name: _____________ (contains "Session Start Time"?)
- [ ] Window description contains "start time": Yes / No

#### Warning Dismiss Button
- [ ] Button name to dismiss: _____________ ("OK", "Continue", other?)
- [ ] Button position: _____________ (button 1, button 2?)

### Verify in Pro Tools
- [ ] Template data imported
- [ ] Tracks appear
- [ ] No sample rate conversion occurred

### Issues Found
```
CRITICAL: Document Session Start Time warning details


```

### Script Status
- [ ] ✅ Works perfectly
- [ ] ❌ Needs fixes

---

## Summary

### Scripts Working
- [ ] test_launch.applescript
- [ ] test_create_session.applescript
- [ ] test_save_session.applescript
- [ ] test_close_session.applescript
- [ ] test_save_session_as.applescript
- [ ] test_import_audio.applescript
- [ ] test_import_midi.applescript
- [ ] test_import_template.applescript

### Critical Findings

**Apply SRC in Audio Import**:
- Checkbox exists: _______
- Exact name: _______
- Works as expected: _______

**Apply SRC in Template Import**:
- Checkbox exists: _______
- Exact name: _______

**Session Start Time Warning**:
- Warning appears: _______
- Window name: _______
- Dismiss button: _______

### Next Steps

After all scripts work individually:

1. [ ] Update production scripts in `src/protools/scripts/` with findings
2. [ ] Test full workflow sequence (launch → create → import → save → close)
3. [ ] Test with different sample rates (44.1kHz, 48kHz, 96kHz)
4. [ ] Test error cases (wrong paths, missing files)
5. [ ] Document final UI element names in CLAUDE.md
6. [ ] Run manual testing checklist from TODO.md

---

**Date tested**: _______________
**Pro Tools version**: _______________
**macOS version**: _______________
**Tester**: _______________
