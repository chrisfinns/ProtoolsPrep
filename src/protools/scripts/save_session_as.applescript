-- DEPRECATED: This script is no longer needed
-- The create_session.applescript now handles saving to a specific location
-- via the Save dialog that appears after clicking Create. Keeping for reference only.
--
-- Save current Pro Tools session to a specific location using Save As
-- Placeholders: {save_path}, {session_name}, {dialog_wait}

tell application "System Events"
	tell process "Pro Tools"
		-- Verify Pro Tools is frontmost
		if not frontmost then
			set frontmost to true
			delay 0.5
		end if

		-- Verify menu bar is accessible
		set menuReady to false
		repeat 10 times
			if exists menu bar 1 then
				set menuReady to true
				exit repeat
			end if
			delay 0.5
		end repeat

		if not menuReady then
			error "Pro Tools menu bar not accessible"
		end if

		-- Open File → Save As (Cmd+Shift+S)
		keystroke "s" using {command down, shift down}
		delay {dialog_wait}

		-- Verify Save As dialog appeared
		if not (exists window 1 whose name contains "Save") then
			error "Save As dialog did not appear"
		end if

		tell window 1
			-- Navigate to target folder using POSIX path
			-- Press Cmd+Shift+G to open "Go to folder" dialog
			keystroke "g" using {command down, shift down}
			delay 1

			-- Type the path
			keystroke "{save_path}"
			delay 0.5
			keystroke return
			delay 1

			-- Ensure session name is correct in the filename field
			-- The name field should already have the session name, but let's verify
			try
				set value of text field 1 to "{session_name}"
			end try

			delay 0.5

			-- Click Save button
			click button "Save"
			delay 1

			-- Handle "Replace" dialog if file already exists
			repeat 3 times
				if exists sheet 1 then
					tell sheet 1
						if exists button "Replace" then
							click button "Replace"
							exit repeat
						end if
					end tell
				end if
				delay 0.3
			end repeat
		end tell

		-- Wait for save to complete
		delay 2

		-- Check for any error dialogs
		if exists window 1 whose name contains "Error" or exists window 1 whose name contains "Warning" then
			error "Save operation encountered an error or warning dialog"
		end if
	end tell
end tell

return "Session saved successfully to specified location"
