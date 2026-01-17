-- Import audio files with Apply SRC DISABLED
-- Placeholders: {audio_folder_path}, {dialog_wait}, {import_timeout}
-- CRITICAL: Must disable "Apply SRC" checkbox (if available) to prevent quality degradation
-- NOTE: Must use "Copy All ->" to copy files into session, not just link them

tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true

		-- Verify menu bar is accessible before attempting menu navigation
		log "Waiting for Pro Tools menu bar..."
		repeat 10 times
			if exists menu bar 1 then exit repeat
			delay 0.5
		end repeat
		if not (exists menu bar 1) then error "Menu bar not accessible"

		-- Open File -> Import -> Audio
		log "Opening Import Audio dialog"
		click menu item "Audio..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1

		-- Allow file chooser to appear
		delay {dialog_wait}

		-- ================= FILE CHOOSER =================
		tell window 1

			-- Jump directly to target folder (Cmd+Shift+G)
			log "Navigating to audio folder"
			keystroke "g" using {command down, shift down}
			delay 1
			keystroke "{audio_folder_path}"
			keystroke return
			delay 1

			-- Select all audio files in folder
			log "Selecting all audio files"
			keystroke "a" using command down
			delay 0.5

			-- Explicitly disable Apply SRC to prevent silent resampling
			-- NOTE: Checkbox may be grayed out when sample rates match
			log "Ensuring Apply SRC is disabled"
			if exists checkbox "Apply SRC" then
				set value of checkbox "Apply SRC" to 0
				delay 0.3

				if value of checkbox "Apply SRC" is not 0 then
					error "Failed to disable Apply SRC"
				end if
				log "Apply SRC checkbox disabled and verified"
			else
				log "Apply SRC checkbox not found (continuing)"
			end if

			-- Choose Copy or Convert depending on session/sample-rate state
			-- CRITICAL: Must copy files into session folder, not just link
			if exists button "Copy All ->" then
				log "Using Copy All"
				click button "Copy All ->"
			else if exists button "Convert All ->" then
				log "Using Convert All"
				click button "Convert All ->"
			else
				log "No Copy/Convert button found"
			end if

			delay 0.5

			-- Confirm file selection
			log "Confirming import selection"
			click button "Open"

		end tell

		-- ================= DESTINATION FOLDER =================
		-- A second dialog appears to confirm the Audio Files destination
		delay 1
		log "Confirming Audio Files destination"
		set frontmost to true
		if exists window 1 then
			click button "Open" of window 1
		end if

		-- ================= IMPORT COMPLETION =================
		-- Import work finishes BEFORE Audio Import Options appears
		log "Waiting for Audio Import Options window"

		set elapsed to 0
		repeat
			delay 0.5
			set elapsed to elapsed + 0.5

			if exists window "Audio Import Options" then exit repeat
			if elapsed >= {import_timeout} then error "Timed out waiting for Audio Import Options"
		end repeat

		-- Accept defaults (no settings are ever changed here)
		log "Accepting Audio Import Options"
		tell window "Audio Import Options"
			click button "OK"
		end tell

		log "Audio import completed successfully"

	end tell
end tell

return "Audio import completed successfully with SRC disabled"
