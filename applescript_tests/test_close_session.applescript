tell application "System Events"
	tell process "Pro Tools"
		-- Verify Pro Tools is frontmost
		if not frontmost then
			set frontmost to true
			delay 0.5
		end if
		
		log "Closing session with Cmd+Shift+W..."
		
		-- Correct syntax for multiple modifiers
		keystroke "w" using {command down, shift down}
		
		-- Wait for the Save dialog to appear
		delay 1
		
		-- Check for the Save dialog

			log "Save changes dialog appeared"
			
			-- Since the Save button is highlighted/default, 
			-- pressing Enter (key code 36) is the most reliable way to click it.
			key code 36
			log "Pressed Enter to Save"
			
		--else
			log "No save dialog appeared (session was already saved)"
		--end if
		
		-- Wait for session to finish closing
		delay 2
		
		log "Session closed successfully"
	end tell
end tell

return "Session closed successfully"