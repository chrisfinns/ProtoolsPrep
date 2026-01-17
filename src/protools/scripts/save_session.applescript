-- DEPRECATED: This script is no longer needed
-- The create_session.applescript now handles saving via the Save dialog
-- that appears after clicking Create. Keeping for reference only.
--
-- Save current Pro Tools session
-- Uses keyboard shortcut Cmd+S for reliability

tell application "System Events"
	tell process "Pro Tools"
		-- Verify Pro Tools is frontmost
		if not frontmost then
			set frontmost to true
			delay 0.5
		end if

		-- Save using keyboard shortcut (Cmd+S)
		-- This is more reliable than menu navigation
		keystroke "s" using command down

		-- Wait for save to complete
		delay 2

		-- Check for any error dialogs
		if exists window 1 whose name contains "Error" or exists window 1 whose name contains "Warning" then
			error "Save operation encountered an error or warning dialog"
		end if
	end tell
end tell

return "Session saved successfully"
