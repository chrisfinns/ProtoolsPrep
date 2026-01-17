-- Import MIDI files with tempo and key signature import enabled
-- Placeholders: {midi_folder_path}, {dialog_wait}, {import_timeout}
-- NOTE: MIDI Import Options window detected via static text, not window name

tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true

		------------------------------------------------------------
		-- Ensure menu bar is accessible
		------------------------------------------------------------
		log "Checking Pro Tools menu bar accessibility..."
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

		------------------------------------------------------------
		-- File -> Import -> MIDI
		------------------------------------------------------------
		log "Opening File -> Import -> MIDI..."
		click menu item "MIDI..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1

		------------------------------------------------------------
		-- Wait for Open dialog
		------------------------------------------------------------
		delay {dialog_wait}

		if not (exists window 1) then
			error "Open dialog did not appear"
		end if

		tell window 1
			--------------------------------------------------------
			-- Navigate to MIDI folder
			--------------------------------------------------------
			log "Navigating to MIDI folder..."
			keystroke "g" using {command down, shift down}
			delay 0.5
			keystroke "{midi_folder_path}"
			delay 0.3
			keystroke return
			delay 1

			--------------------------------------------------------
			-- Select all MIDI files
			--------------------------------------------------------
			log "Selecting all files..."
			keystroke "a" using command down
			delay 0.3

			--------------------------------------------------------
			-- Confirm import
			--------------------------------------------------------
			log "Clicking Open..."
			click button "Open"
		end tell

		------------------------------------------------------------
		-- Wait for MIDI Import Options (if it appears)
		-- IMPORTANT: detected via static text, not window name
		------------------------------------------------------------
		log "Waiting for MIDI Import Options (if required)..."
		set elapsed to 0
		set optionsHandled to false

		repeat
			delay 0.5
			set elapsed to elapsed + 0.5

			if exists (static text "MIDI Import Options" of window 1) then
				log "MIDI Import Options detected"

				set optionsWindow to window "MIDI Import Options"

				tell optionsWindow
					------------------------------------------------
					-- Import Tempo
					------------------------------------------------
					if exists checkbox "Import Tempo" then
						if enabled of checkbox "Import Tempo" then
							set value of checkbox "Import Tempo" to 1
							log "Enabled Import Tempo"
						else
							log "Import Tempo checkbox is disabled"
						end if
					else
						log "No Import Tempo checkbox found"
					end if

					------------------------------------------------
					-- Import Key Signature
					------------------------------------------------
					if exists checkbox "Import Key Signature" then
						if enabled of checkbox "Import Key Signature" then
							set value of checkbox "Import Key Signature" to 1
							log "Enabled Import Key Signature"
						else
							log "Import Key Signature checkbox is disabled"
						end if
					else
						log "No Import Key Signature checkbox found"
					end if

					------------------------------------------------
					-- Accept options
					------------------------------------------------
					click button "OK"
				end tell

				set optionsHandled to true
				exit repeat
			end if

			-- If no options window appears quickly, import completed silently
			if elapsed >= {import_timeout} then
				exit repeat
			end if
		end repeat

		if optionsHandled then
			log "MIDI import completed with options dialog"
		else
			log "MIDI import completed without options dialog"
		end if

		------------------------------------------------------------
		-- Final safety delay
		------------------------------------------------------------
		delay 0.5

		log "MIDI import completed successfully"
	end tell
end tell

return "MIDI import completed successfully"
