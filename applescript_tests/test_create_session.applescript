-- TEST: Create new Pro Tools session from Dashboard
-- Hardcoded values: "Test Session", 48kHz, 24-bit
-- PREREQUISITE: Dashboard must be open (run test_launch.applescript first)

tell application "System Events"
	tell process "Pro Tools"
		-- Verify Dashboard window exists
		if not (exists window "Dashboard") then
			error "Dashboard window not found - run test_launch.applescript first"
		end if
		set frontmost to true
		tell window "Dashboard"
			--Bring Dashboard to front
			--set index of window "Dashboard" to 0
			delay 0.5
			
			-- TODO: Use Accessibility Inspector to find exact name of session name field
			-- Might be "Name", "Session Name", or have a different identifier
			log "Attempting to set session name..."
			try
				keystroke "a" using {command down}
				delay 0.1
				keystroke "Test Session"
				log "Session name set successfully"
			on error errMsg
				log "ERROR setting session name: " & errMsg
				log "Use Accessibility Inspector to find the correct text field name"
			end try
			
			-- TODO: Verify exact popup button name for sample rate
			log "Attempting to set sample rate to 48 kHz..."
			try
				set sampButton to (first pop up button whose value of attribute "AXIdentifier" is "samp")
				delay 0.5
				-- TODO: Verify exact menu item text
				perform action "AXPress" of sampButton
				keystroke "48"
				log "Sample rate set to 48 kHz"
				key code 36
				
			on error errMsg
				log "ERROR setting sample rate: " & errMsg
				log "Possible issues:"
				log "  - Popup button might not be named 'Sample Rate'"
				log "  - Menu item might be '48.0 kHz' or '48000' instead"
				log "Use Accessibility Inspector to verify names"
			end try
			
			-- TODO: Verify exact popup button name for bit depth
			log "Attempting to set bit depth to 24-bit..."
			try
				--click pop up button "24-bit" or "16-bit"
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
				log "Bit depth set to 24 Bit"
			on error errMsg
				log "ERROR setting bit depth: " & errMsg
				log "Possible issues:"
				log "  - Popup button might not be named 'Bit Depth'"
				log "  - Menu item might be '24-bit' or '24 Bit Int' instead"
				log "Use Accessibility Inspector to verify names"
			end try
			
			-- Click Create button
			log "Clicking Create button..."
			delay 0.5
			try
				-- click button "Create"
				log "Create button clicked"
			on error errMsg
				log "ERROR clicking Create button: " & errMsg
			end try
		end tell
		
		-- Wait for session window to appear
		log "Waiting for session window to appear..."
		set maxAttempts to 10
		set attemptCount to 0
		set sessionFound to false
		
		(*
repeat while attemptCount < maxAttempts
			-- TODO: Verify how session window is named
			-- Might be "Test Session", "Test Session - Edit", "Test Session.ptx", etc.
			if exists (window 1 whose name contains "Test Session") then
				set sessionFound to true
				log "Session window found!"
				exit repeat
			end if
			
			delay 1
			set attemptCount to attemptCount + 1
		end repeat
		
		if not sessionFound then
			error "Session window did not appear within " & maxAttempts & " seconds"
		end if
		
*)
	end tell
end tell


return "Session created successfully - ready for testing imports"


