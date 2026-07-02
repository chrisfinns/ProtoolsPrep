-- Create new Pro Tools session from Dashboard
-- Placeholders: {session_name}, {sample_rate}, {bit_depth}, {save_path}
-- NOTE: After clicking Create, a Save dialog opens - we navigate to {save_path}

tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true
		
		-- Verify Dashboard window exists, open it if needed
		if not (exists window "Dashboard") then
			keystroke "o" using {command down, option down}
			delay 1.5
			
			-- Wait for Dashboard to appear
			set dashboardAttempts to 0
			repeat while dashboardAttempts < 10
				if exists window "Dashboard" then
					exit repeat
				end if
				delay 0.5
				set dashboardAttempts to dashboardAttempts + 1
			end repeat
			
			if not (exists window "Dashboard") then
				error "Dashboard window did not appear after Cmd+Option+O"
			end if
		end if
		tell window "Dashboard"
			-- Bring Dashboard to front
			--set index to 1
			delay 0.5
			
			-- Set session name
			-- The name field is already in focus with "Untitled" selected
			-- Just select all and type the new name
			keystroke "a" using {command down}
			delay 0.1
			keystroke "{session_name}"
			delay 0.3
			
			-- Set sample rate using AXIdentifier "samp"
			-- Pro Tools displays as "48 kHz", "44.1 kHz", "96 kHz"
			set sampleRateValue to "{sample_rate}"
			set sampButton to (first pop up button whose value of attribute "AXIdentifier" is "samp")
			delay 0.3
			perform action "AXPress" of sampButton
			-- Reset selection to top
			repeat 10 times
				key code 126 -- Up arrow
			end repeat
			
			-- Now move down to desired rate
			if sampleRateValue is "44.1 kHz" then
				-- already at top (44.1 is usually first)
			else if sampleRateValue is "48 kHz" then
				key code 125 -- Down
			else if sampleRateValue is "88.2 kHz" then
				repeat 2 times
					key code 125
				end repeat
			else if sampleRateValue is "96 kHz" then
				repeat 3 times
					key code 125
				end repeat
			else
				key code 53
				error "Unsupported sample rate: " & sampleRateValue
			end if
			
			key code 36 -- Return
			
			-- Set bit depth using AXIdentifier "bitd"
			set bitDepthValue to "{bit_depth}"
			set bitPopup to (first pop up button whose value of attribute "AXIdentifier" is "bitd")
			delay 0.3
			perform action "AXPress" of bitPopup
			delay 0.3
			
			if bitDepthValue is "16" then
				keystroke "16"
				key code 36
			else if bitDepthValue is "24" then
				keystroke "24"
				key code 36
			else if bitDepthValue is "32" then
				keystroke "32"
				key code 36
			else
				key code 53 -- Escape to close popup
				error "Unsupported bit depth: " & bitDepthValue
			end if
			delay 0.3
			
			-- Click Create button
			delay 0.5
			click button "Create"
		end tell
		
		-- Wait for Save dialog to appear (poll for up to 10 seconds)
		set saveDialogFound to false
		set saveDialogAttempts to 0
		repeat while saveDialogAttempts < 10
			if exists (window 1 whose name contains "Save") then
				set saveDialogFound to true
				exit repeat
			end if
			delay 1
			set saveDialogAttempts to saveDialogAttempts + 1
		end repeat
		
		if not saveDialogFound then
			error "Save dialog did not appear after clicking Create"
		end if
		
		-- Handle Save dialog - navigate to the target save path
		tell window 1
			-- Navigate to target folder using Cmd+Shift+G
			keystroke "g" using {command down, shift down}
			delay 1.5
			
			-- Wait for "Go to the folder" sheet to appear
			delay 0.5
			
			-- Type the save path
			keystroke "{save_path}"
			delay 0.5
			keystroke return
			delay 1.5
			
			-- Click Save button (or press Enter since it's the default)
			key code 36
			delay 10
		end tell
		
		-- Wait for initialization progress bar to appear (usually shows "Initializing Hardware" etc.)
		delay 2
		
		-- Wait for progress/initialization to complete (look for progress indicator to disappear)
		set maxProgressAttempts to 15
		set progressAttemptCount to 0
		repeat while progressAttemptCount < maxProgressAttempts
			-- Check if there's still a progress indicator or sheet
			if not (exists sheet 1 of window 1) then
				-- Progress indicator gone, initialization complete
				exit repeat
			end if
			delay 1
			set progressAttemptCount to progressAttemptCount + 1
		end repeat
		
		-- Extra delay to ensure session is fully loaded
		delay 2
		
		-- Wait for session window to appear
		set maxAttempts to {window_timeout}
		set attemptCount to 0
		set sessionFound to false
		
		repeat while attemptCount < maxAttempts
			-- Use partial match since Pro Tools may append " - Edit" or other suffixes
			if exists (window 1 whose name contains "{session_name}") then
				set sessionFound to true
				exit repeat
			end if
			
			delay 1
			set attemptCount to attemptCount + 1
		end repeat
		
		if not sessionFound then
			error "Session window did not appear within " & maxAttempts & " seconds"
		end if
	end tell
end tell

return "Session created successfully"
