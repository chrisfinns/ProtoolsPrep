-- Import MIDI files with tempo and key signature import enabled.
-- One of two surviving AppleScripts (PTSL v3 has no MIDI import command).
--
-- Placeholders: {midi_folder_path}, {dialog_wait}, {import_timeout}
-- Returns: "midi-import:ok:with-options" or "midi-import:ok:no-options"
-- Errors (non-zero exit) on any unmet precondition - no blind keystrokes.

tell application "System Events"
	if not (exists process "Pro Tools") then
		error "Pro Tools is not running"
	end if

	tell process "Pro Tools"
		set frontmost to true

		------------------------------------------------------------
		-- Preconditions: menu bar reachable, a session window open
		------------------------------------------------------------
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

		if not (exists menu item "Import" of menu "File" of menu bar 1) then
			error "File > Import menu not available (no session open?)"
		end if

		------------------------------------------------------------
		-- File -> Import -> MIDI...
		------------------------------------------------------------
		click menu item "MIDI..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1

		------------------------------------------------------------
		-- Wait for the Open dialog (poll, not a single fixed delay)
		------------------------------------------------------------
		set dialogReady to false
		set waited to 0
		repeat
			delay 0.5
			set waited to waited + 0.5
			if exists window 1 then
				set dialogReady to true
				exit repeat
			end if
			if waited is greater than or equal to {dialog_wait} + 5 then exit repeat
		end repeat
		if not dialogReady then
			error "MIDI Open dialog did not appear"
		end if

		tell window 1
			--------------------------------------------------------
			-- Navigate to the MIDI folder via Go To Folder sheet.
			-- Only press Return once the sheet is confirmed present,
			-- so the keystroke cannot land somewhere unexpected.
			--------------------------------------------------------
			keystroke "g" using {command down, shift down}

			set sheetReady to false
			repeat 10 times
				delay 0.3
				if exists sheet 1 then
					set sheetReady to true
					exit repeat
				end if
			end repeat
			if not sheetReady then
				error "Go To Folder sheet did not appear in Open dialog"
			end if

			keystroke "{midi_folder_path}"
			delay 0.3
			keystroke return -- confirms the Go To Folder sheet (verified present)
			delay 1

			--------------------------------------------------------
			-- Select all MIDI files and open
			--------------------------------------------------------
			keystroke "a" using command down
			delay 0.3

			if not (exists button "Open") then
				error "Open button not found in file dialog"
			end if
			click button "Open"
		end tell

		------------------------------------------------------------
		-- MIDI Import Options may or may not appear
		------------------------------------------------------------
		set elapsed to 0
		set optionsHandled to false

		repeat
			delay 0.5
			set elapsed to elapsed + 0.5

			if exists window "MIDI Import Options" then
				tell window "MIDI Import Options"
					if exists checkbox "Import Tempo" then
						if enabled of checkbox "Import Tempo" then
							set value of checkbox "Import Tempo" to 1
						end if
					end if
					if exists checkbox "Import Key Signature" then
						if enabled of checkbox "Import Key Signature" then
							set value of checkbox "Import Key Signature" to 1
						end if
					end if
					if not (exists button "OK") then
						error "MIDI Import Options has no OK button"
					end if
					click button "OK"
				end tell
				set optionsHandled to true
				exit repeat
			end if

			-- Fallback: options window detected via static text (window
			-- name is unreliable on some Pro Tools builds)
			if exists window 1 then
				if exists (static text "MIDI Import Options" of window 1) then
					tell window 1
						if exists checkbox "Import Tempo" then
							if enabled of checkbox "Import Tempo" then
								set value of checkbox "Import Tempo" to 1
							end if
						end if
						if exists checkbox "Import Key Signature" then
							if enabled of checkbox "Import Key Signature" then
								set value of checkbox "Import Key Signature" to 1
							end if
						end if
						if not (exists button "OK") then
							error "MIDI Import Options has no OK button"
						end if
						click button "OK"
					end tell
					set optionsHandled to true
					exit repeat
				end if
			end if

			-- No options window within the timeout: import completed silently
			if elapsed is greater than or equal to {import_timeout} then
				exit repeat
			end if
		end repeat

		delay 0.5
	end tell
end tell

if optionsHandled then
	return "midi-import:ok:with-options"
else
	return "midi-import:ok:no-options"
end if
