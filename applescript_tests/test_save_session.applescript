-- TEST: Save current Pro Tools session
-- Uses keyboard shortcut Cmd+S
-- PREREQUISITE: Have a session open (run test_create_session.applescript first)

tell application "System Events"
	tell process "Pro Tools"
		-- Verify Pro Tools is frontmost
		if not frontmost then
			set frontmost to true
			delay 0.5
		end if

		log "Saving session with Cmd+S..."

		-- Save using keyboard shortcut (Cmd+S)
		keystroke "s" using command down

		-- Wait for save to complete
		delay 2

		-- Check for any error dialogs
		if exists window 1 whose name contains "Error" or exists window 1 whose name contains "Warning" then
			error "Save operation encountered an error or warning dialog"
		end if

		log "Session saved successfully"
	end tell
end tell

return "Session saved successfully"
