# Accessibility Inspector Guide

## What is Accessibility Inspector?

Accessibility Inspector is a macOS developer tool that lets you examine the accessibility attributes of UI elements in any application. This is essential for writing accurate AppleScript UI automation.

## How to Launch

```bash
open /System/Library/CoreServices/Applications/Accessibility\ Inspector.app
```

Or: Xcode → Open Developer Tool → Accessibility Inspector

## How to Use

### 1. Enable Inspection Mode
- Click the **"Target"** button (crosshair icon) in the toolbar
- Or press: `Cmd + F7`

### 2. Inspect Elements
- Move your mouse over any UI element in Pro Tools
- The Inspector window shows live information about that element
- Click to lock inspection on that element

### 3. Key Information to Note

#### For Windows/Dialogs:
- **Title** - The exact name (e.g., "Dashboard", "Import Audio")
- **Role** - Should be "AXWindow" or "AXDialog"
- **Subrole** - May provide additional context

#### For Buttons:
- **Title** - Button label (e.g., "Create", "Open", "Save")
- **Role** - Should be "AXButton"

#### For Text Fields:
- **Title** or **Description** - Field label
- **Role** - "AXTextField"
- **Value** - Current text content

#### For Checkboxes:
- **Title** - Checkbox label (e.g., "Apply SRC")
- **Role** - "AXCheckBox"
- **Value** - 0 (unchecked) or 1 (checked)

#### For Popup Buttons (Dropdowns):
- **Title** - Popup label (e.g., "Sample Rate", "Bit Depth")
- **Role** - "AXPopUpButton"
- **Menu Items** - Expand hierarchy to see menu structure

### 4. Navigate Hierarchy
- Use the **Hierarchy** view (bottom panel)
- Shows parent-child relationships
- Example: Window → PopUpButton → Menu → MenuItem

## Practical Examples for Pro Tools

### Example 1: Finding the Session Name Field

1. Launch Pro Tools and open Dashboard (Cmd+N)
2. Launch Accessibility Inspector
3. Click Target button
4. Hover over the session name input field
5. Note what the Inspector shows:
   ```
   Title: "Name"  OR  "Session Name"  OR something else
   Role: AXTextField
   ```
6. Use this exact title in AppleScript:
   ```applescript
   set value of text field "Name" to "My Session"
   ```

### Example 2: Finding Sample Rate Menu Items

1. In Dashboard, click the Sample Rate popup
2. In Accessibility Inspector, click Target
3. Hover over "48 kHz" menu item
4. Note the exact text:
   ```
   Title: "48 kHz"  OR  "48.0 kHz"  OR  "48000"
   ```
5. Use exact text in AppleScript:
   ```applescript
   click menu item "48 kHz" of menu 1 of popup button "Sample Rate"
   ```

### Example 3: Finding the "Apply SRC" Checkbox

1. Open File → Import → Audio in Pro Tools
2. In Accessibility Inspector, click Target
3. Hover over the SRC checkbox
4. Note the exact title:
   ```
   Title: "Apply SRC"  OR  "SRC"  OR  "Sample Rate Conversion"
   ```
5. Also note the **value** when checked vs unchecked:
   ```
   Value: 0 (unchecked)
   Value: 1 (checked)
   ```
6. Use in AppleScript:
   ```applescript
   set value of checkbox "Apply SRC" to 0
   ```

## Common AppleScript Patterns

### Windows
```applescript
-- Check if window exists
if exists window "Dashboard" then
    -- ...
end if

-- Check by partial match
if exists window 1 whose name contains "Import" then
    -- ...
end if
```

### Buttons
```applescript
-- Click by name
click button "Create"

-- Click by position (fallback)
click button 1
```

### Text Fields
```applescript
-- Set value
set value of text field "Name" to "My Text"

-- By position if name unknown
set value of text field 1 to "My Text"
```

### Checkboxes
```applescript
-- Set to unchecked
set value of checkbox "Apply SRC" to 0

-- Set to checked
set value of checkbox "Import Tempo" to 1

-- Read current value
set currentValue to value of checkbox "Apply SRC"
```

### Popup Buttons
```applescript
-- Click popup to open menu
click popup button "Sample Rate"

-- Click menu item
click menu item "48 kHz" of menu 1 of popup button "Sample Rate"
```

### Menu Bar
```applescript
-- Full menu path
click menu item "Audio..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1
```

## Troubleshooting

### "Element not found" error
- Element name might be slightly different (check Inspector)
- Element might not exist yet (add delay)
- Element might be in a different window/sheet
- Try using position instead: `button 1`, `text field 1`

### Can't access element
- Make sure Pro Tools is frontmost
- Verify Accessibility permissions are enabled
- Element might be disabled/hidden
- Try clicking parent window first to focus it

### Value doesn't change
- Some elements don't respond to `set value`
- Try clicking instead: `click checkbox "..."`
- Or use keyboard: `keystroke space` to toggle checkbox

### Hierarchy issues
- Some elements are nested: window → sheet → button
- Use `tell window 1` → `tell sheet 1` → `click button`
- Sheets are child dialogs (like "Replace" confirmation)

## Tips

1. **Always verify element names** - Don't assume, always check
2. **Test immediately** - Run script right after inspecting
3. **Check different states** - Elements may change based on dialog state
4. **Document as you go** - Note findings in comments
5. **Use logs** - Add `log "message"` statements for debugging
6. **Test timing** - Some elements appear after delays
7. **Handle variations** - Pro Tools versions may differ

## What to Look For

When testing each script, use Accessibility Inspector to verify:

✅ Window/dialog exact names
✅ Button exact labels
✅ Text field identifiers
✅ Checkbox exact names
✅ Checkbox value meanings (0 vs 1)
✅ Popup button names
✅ Menu item exact text
✅ Menu hierarchy structure
✅ Sheet (child dialog) structure

## Example Workflow

1. **Open Pro Tools** to the state you want to automate
2. **Launch Inspector** and enable Target mode
3. **Hover over elements** you need to interact with
4. **Write down exact names** in a notes file
5. **Test in Script Editor** with hardcoded values
6. **Iterate** until script works reliably
7. **Update production scripts** with correct values

---

**Remember**: Every UI element name, button label, and menu item text must match EXACTLY what Accessibility Inspector shows. Even extra spaces or different capitalization will cause failures.
