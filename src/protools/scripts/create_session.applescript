-- Create new Pro Tools session from Dashboard
-- Placeholders: {session_name}, {sample_rate}, {bit_depth}, {save_path}
-- NOTE: After clicking Create, a Save dialog opens - we navigate to {save_path}

tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true

		-- Verify Dashboard window exists
		if not (exists window "Dashboard") then
			error "Dashboard window not found"
		end if

		tell window "Dashboard"
			-- Bring Dashboard to front
			set index to 1
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
			delay 0.3

			if sampleRateValue is "44100" then
				keystroke "44"
				key code 36
			else if sampleRateValue is "48000" then
				keystroke "48"
				key code 36
			else if sampleRateValue is "96000" then
				keystroke "96"
				key code 36
			else if sampleRateValue is "88200" then
				keystroke "88"
				key code 36
			else if sampleRateValue is "192000" then
				keystroke "192"
				key code 36
			else
				key code 53 -- Escape to close popup
				error "Unsupported sample rate: " & sampleRateValue
			end if
			delay 0.3

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

		-- Wait for Save dialog to appear
		delay 1

		-- Handle Save dialog - navigate to the target save path
		if exists window 1 whose name contains "Save" then
			tell window 1
				-- Navigate to target folder using Cmd+Shift+G
				keystroke "g" using {command down, shift down}
				delay 1

				-- Type the save path
				keystroke "{save_path}"
				delay 0.5
				keystroke return
				delay 1

				-- Click Save button (or press Enter since it's the default)
				key code 36
			end tell
		end if

		-- Wait for session window to appear
		set maxAttempts to {window_timeout}
		set attemptCount to 0
		set sessionFound to false

		repeat while attemptCount < maxAttempts
			-- Use partial match since Pro Tools may append " - Edit" or other suffixes
			if exists window 1 whose name contains "{session_name}" then
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
