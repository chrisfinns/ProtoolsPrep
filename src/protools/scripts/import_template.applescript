-- Import session template (Session Data) with Apply SRC DISABLED
-- Placeholders: {template_folder_path}, {template_filename}, {dialog_wait}, {import_timeout}
-- CRITICAL: Must disable "Apply SRC" and dismiss "Session Start Time" warning

tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true
		
		-- Verify menu bar is accessible before attempting menu navigation
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
		click menu item "Session Data..." of menu "Import" of menu item "Import" of menu "File" of menu bar 1
		
		-- Wait for file chooser dialog to appear
		delay 2
		
		-- Ensure Pro Tools file chooser stays in focus
		set frontmost to true
		
		-- ================= FILE CHOOSER =================
		tell window 1
			-- Navigate to template folder using POSIX path
			-- Press Cmd+Shift+G to open "Go to folder" dialog
			keystroke "g" using {command down, shift down}
			delay 1
			
			-- Type the folder path (not the full file path)
			keystroke "{template_folder_path}"
			delay 0.5
			keystroke return
			delay 1
			
			-- Type the template filename to select it
			keystroke "{template_filename}"
			delay 0.5
			
			-- Press Return to confirm file selection
			keystroke return
			delay 0.5
			
		end tell
		
		-- Wait for Import Session Data options dialog (if it appears)
		delay 2
		
		-- ================= IMPORT OPTIONS DIALOG =================
		-- Check if there's a second dialog with SRC checkbox
		if exists window "Import Session Data" then
			tell window "Import Session Data"
				-- CRITICAL: Ensure all tracks are mapped to "New Track"
				-- Click on the Tracks tab to ensure we're on the right tab
				if exists table 1 then
					tell table 1
						-- 1. Click the first row to ensure the table is the active UI element
						-- We use AXPress because it's the most reliable "focus" click in PT
						tell row 1 to perform action "AXPress"
					end tell
					
					delay 0.1 -- Short pause for PT to register focus
					
					-- 2. Send the Select All command
					keystroke "a" using {command down}
					
					log "Sent Command+A to table"
				else
					log "Table not found in Import Session Data window"
				end if
				
				
				delay 0.5
				
				-- CRITICAL: Disable "Apply SRC" checkbox if it exists
				-- This checkbox converts sample rates and degrades audio quality
				if exists checkbox "Apply SRC" then
					set value of checkbox "Apply SRC" to 0
					delay 0.3
					
					-- VERIFY the checkbox is actually disabled
					set srcValue to value of checkbox "Apply SRC"
					if srcValue is not 0 then
						error "CRITICAL: Failed to disable Apply SRC checkbox (value: " & srcValue & ")"
					end if
					
					log "Apply SRC checkbox successfully disabled and verified"
				else
					log "Apply SRC checkbox not found in this dialog"
				end if
				
				-- Click OK to proceed with import
				click button "OK"
			end tell
		end if
		
		-- Wait a moment for warning dialog to potentially appear
		delay 2
		
		-- CRITICAL: Dismiss "Session Start Time" warning if it appears
		-- This warning shows when template has different start time than current session
		-- Check for warning dialog and dismiss it
		repeat 5 times
			if exists (window 1 whose name contains "Session Start Time" or (exists (window 1 whose description contains "start time"))) then
				-- Click OK or Continue button to dismiss
				tell window 1
					try
						click button "OK"
						log "Dismissed Session Start Time warning (OK)"
						exit repeat
					on error
						try
							click button "Continue"
							log "Dismissed Session Start Time warning (Continue)"
							exit repeat
						on error
							-- Try any button that might dismiss it
							try
								click button 1
								log "Dismissed Session Start Time warning (button 1)"
								exit repeat
							end try
						end try
					end try
				end tell
			end if
			delay 0.5
		end repeat
		
		-- Poll for import completion (progress indicator disappears)
		set maxAttempts to {import_timeout}
		set attemptCount to 0
		
		repeat while attemptCount < maxAttempts
			delay 1
			
			-- Check if progress indicator still exists
			if not (exists (window 1 whose name contains "Importing")) then
				-- Import complete
				exit repeat
			end if
			
			set attemptCount to attemptCount + 1
		end repeat
		
		if attemptCount ≥ maxAttempts then
			error "Template import did not complete within " & maxAttempts & " seconds"
		end if
		
		-- Check for error dialogs after import
		delay 0.5
		if exists (window 1 whose name contains "Error" or (exists (window 1 whose name contains "Warning" or (exists (window 1 whose name contains "Alert"))))) then
			error "Import failed with error dialog"
		end if
	end tell
end tell

return "Template import completed successfully with SRC disabled and warnings dismissed"
