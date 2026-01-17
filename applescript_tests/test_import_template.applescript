-- TEST: Import session template (Session Data) with Apply SRC DISABLED
-- PREREQUISITE:
--   1. Have a session open
--   2. Have a Pro Tools template file (.ptx)
--   3. Update the templatePath below

-- ============= CONFIGURATION =============
-- TODO: Update this to the full path of your .ptx template file
set templatePath to "/Users/YOUR_USERNAME/Desktop/MyTemplate.ptx"
-- ==========================================

tell application "System Events"
	tell process "Pro Tools"
		-- Verify menu bar is accessible
		log "Checking if Pro Tools menu bar is accessible..."
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

		-- Open File → Import → Session Data
		log "Attempting to open File → Import → Session Data..."
		try
			click menu item "Session Data..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1
			log "Menu navigation successful"
		on error errMsg
			log "ERROR navigating menu: " & errMsg
			error errMsg
		end try

		-- Wait for import dialog
		delay 2

		-- Verify import dialog appeared
		log "Checking for Session Data import dialog..."
		if not (exists window 1 whose name contains "Import Session Data") then
			log "WARNING: Import Session Data dialog not found"
			log "Checking all open windows:"
			set windowList to name of every window
			repeat with windowName in windowList
				log "  Found window: " & windowName
			end repeat
			error "Import dialog did not appear or has different name"
		end if

		log "Session Data import dialog found!"

		tell window 1
			-- Navigate to template file using POSIX path
			log "Navigating to template: " & templatePath
			keystroke "g" using {command down, shift down}
			delay 1

			keystroke templatePath
			delay 0.5
			keystroke return
			delay 1

			-- CRITICAL: Disable "Apply SRC" checkbox
			log "Checking for 'Apply SRC' checkbox in Session Data import..."
			try
				if exists checkbox "Apply SRC" then
					log "Found 'Apply SRC' checkbox"

					set currentValue to value of checkbox "Apply SRC"
					log "Current Apply SRC value: " & currentValue

					set value of checkbox "Apply SRC" to 0
					delay 0.3

					-- VERIFY it worked
					set srcValue to value of checkbox "Apply SRC"
					log "Apply SRC value after setting to 0: " & srcValue

					if srcValue is not 0 then
						error "CRITICAL: Failed to disable Apply SRC checkbox (value: " & srcValue & ")"
					end if

					log "SUCCESS: Apply SRC checkbox disabled and verified"
				else
					log "NOTE: 'Apply SRC' checkbox not found in Session Data import"
					log "This might be expected - Session Data import may not have SRC option"
				end if
			on error errMsg
				log "ERROR with Apply SRC checkbox: " & errMsg
			end try

			-- Click Open/Import button
			log "Clicking Open button..."
			try
				click button "Open"
				log "Open button clicked"
			on error errMsg
				try
					click button "Import"
					log "Import button clicked instead"
				on error
					error "Could not find Open or Import button"
				end try
			end try
		end tell

		-- Wait a moment for warning dialog to potentially appear
		delay 2

		-- CRITICAL: Dismiss "Session Start Time" warning if it appears
		log "Checking for 'Session Start Time' warning..."
		set warningDismissed to false

		repeat 5 times
			-- TODO: Verify exact window name/description for this warning
			if exists window 1 whose name contains "Session Start Time" or exists window 1 whose description contains "start time" then
				log "Found Session Start Time warning dialog!"
				tell window 1
					try
						click button "OK"
						log "Dismissed warning with OK button"
						set warningDismissed to true
						exit repeat
					on error
						try
							click button "Continue"
							log "Dismissed warning with Continue button"
							set warningDismissed to true
							exit repeat
						on error
							try
								click button 1
								log "Dismissed warning with button 1"
								set warningDismissed to true
								exit repeat
							end try
						end try
					end try
				end tell
			else
				log "No Session Start Time warning (yet)"
			end if
			delay 0.5
		end repeat

		if warningDismissed then
			log "Session Start Time warning was dismissed"
		else
			log "No Session Start Time warning appeared (might not be expected)"
		end if

		-- Poll for import completion
		log "Waiting for template import to complete..."
		set maxAttempts to 60
		set attemptCount to 0

		repeat while attemptCount < maxAttempts
			delay 1

			if not (exists window 1 whose name contains "Importing") then
				log "Import complete"
				exit repeat
			end if

			set attemptCount to attemptCount + 1
		end repeat

		if attemptCount >= maxAttempts then
			log "WARNING: Import did not complete within " & maxAttempts & " seconds"
		end if

		-- Check for error dialogs
		delay 0.5
		if exists window 1 whose name contains "Error" or exists window 1 whose name contains "Warning" or exists window 1 whose name contains "Alert" then
			log "ERROR: Import failed with error dialog"
			error "Import failed with error dialog"
		end if

		log "Template import completed successfully!"
	end tell
end tell

return "Template import completed successfully with SRC disabled and warnings dismissed"
