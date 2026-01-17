-- TEST: Launch Pro Tools and wait for Dashboard window
-- This is a simplified version for manual testing
-- No placeholders - runs as-is

tell application "Pro Tools"
	activate
end tell

-- Wait for Pro Tools to be frontmost and initialize
delay 5

-- Verify Pro Tools process is responsive
tell application "System Events"
	tell process "Pro Tools"
		-- Wait for menu bar to be accessible (indicates UI is ready)
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
	end tell
end tell

-- Poll for Dashboard window (up to 10 seconds)
set maxAttempts to 10
set attemptCount to 0
set dashboardFound to false

repeat while attemptCount < maxAttempts
	tell application "System Events"
		tell process "Pro Tools"
			if exists window "Dashboard" then
				set dashboardFound to true
				exit repeat
			end if
		end tell
	end tell

	-- If Dashboard not found and this is our first check, try opening it
	if attemptCount is 0 then
		tell application "System Events"
			tell process "Pro Tools"
				-- Open Dashboard via File → New Session (Cmd+N)
				keystroke "n" using command down
				delay 2
			end tell
		end tell
	end if

	delay 1
	set attemptCount to attemptCount + 1
end repeat

if not dashboardFound then
	error "Dashboard window did not appear within " & maxAttempts & " seconds"
end if

-- Success
return "Pro Tools launched successfully - Dashboard is open"
