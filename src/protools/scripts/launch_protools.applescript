-- Launch Pro Tools and wait for Dashboard window
-- This script activates Pro Tools and polls for the Dashboard window to appear

tell application "Pro Tools"
	activate
end tell

-- Wait for Pro Tools to be frontmost and initialize
-- Longer delay for cold starts (splash screen, plugin loading)
delay 5

-- Verify Pro Tools process is responsive
tell application "System Events"
	tell process "Pro Tools"
		-- Ensure Pro Tools stays in focus
		set frontmost to true

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

-- Poll for Dashboard window (up to {window_timeout} seconds)
-- If not found, open it via File → New Session
set maxAttempts to {window_timeout}
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

-- Dashboard is ready
return "Pro Tools launched successfully"
