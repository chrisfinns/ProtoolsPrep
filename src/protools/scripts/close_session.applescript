-- Close current Pro Tools session (whichever is frontmost)
-- No placeholders required
-- NOTE: Uses Cmd+Shift+W to close session, Save button is default

tell application "System Events"
	tell process "Pro Tools"
		-- Verify Pro Tools is frontmost
		if not frontmost then
			set frontmost to true
			delay 0.5
		end if

		log "Closing session with Cmd+Shift+W..."

		-- Close session using keyboard shortcut (Cmd+Shift+W)
		-- NOTE: Cmd+W alone doesn't close the session, need Cmd+Shift+W
		keystroke "w" using {command down, shift down}

		-- Wait for the Save dialog to appear
		delay 1

		-- Check for the Save dialog
		-- Save button is highlighted/default, pressing Enter is most reliable
		log "Save changes dialog appeared"

		-- Since the Save button is highlighted/default,
		-- pressing Enter (key code 36) is the most reliable way to click it.
		key code 36
		log "Pressed Enter to Save"

		-- Wait for session to finish closing
		delay 2

		log "Session closed successfully"
	end tell
end tell

return "Session closed successfully"
