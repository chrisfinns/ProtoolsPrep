-- Dialog supervisor: dismiss whitelisted Pro Tools dialogs, report anything else.
--
-- Returns exactly one of:
--   "dismissed:<label>"  - a whitelisted dialog was dismissed with its safe button
--   "none"               - no dialog is blocking Pro Tools
--   "unknown:<title>"    - a non-whitelisted dialog is up; NOT touched
--
-- Rules (docs/DEVELOPER_IMPROVEMENT_PLAN.md section 5):
--   * Never dismiss blind, never send a bare Return.
--   * "Save changes" dialogs are answered with Save - our sessions are always
--     worth keeping; "Don't Save" would discard imported data.
--   * Modal dialogs make ALL PTSL commands return PT_NoOpenedSession (106),
--     so Python calls this on every 106 and after import/close.

on collectText(w)
	tell application "System Events"
		set collected to ""
		try
			set wName to name of w
			if wName is not missing value then set collected to wName
		end try
		try
			repeat with textItem in (static texts of w)
				try
					set textValue to value of textItem
					if textValue is not missing value then set collected to collected & " | " & textValue
				end try
			end repeat
		end try
		return collected
	end tell
end collectText

on run
	tell application "System Events"
		if not (exists process "Pro Tools") then return "none"
		tell process "Pro Tools"
			if not (exists window 1) then return "none"

			----------------------------------------------------------
			-- Pass 1: dismiss the first whitelisted dialog found
			----------------------------------------------------------
			repeat with w in windows
				set allText to my collectText(w)

				-- Missing AAX Plugins (fires on every template import on
				-- machines missing the template's plugins - normal path)
				if allText contains "Missing AAX" then
					try
						click button "OK" of w
						return "dismissed:Missing AAX Plugins"
					end try
				end if

				-- Save-changes-before-closing prompt: always Save
				if (allText contains "before closing") or (allText contains "Save changes") then
					try
						click button "Save" of w
						return "dismissed:Save Changes"
					end try
				end if

				-- Session Notes (shown when opening sessions with issues)
				if allText contains "Session Notes" then
					try
						click button "OK" of w
						return "dismissed:Session Notes"
					end try
				end if

				-- Playback engine / hardware notices
				if (allText contains "Playback Engine") or (allText contains "playback engine") then
					try
						click button "OK" of w
						return "dismissed:Playback Engine Notice"
					end try
				end if
			end repeat

			----------------------------------------------------------
			-- Pass 2: report (do NOT touch) any other modal dialog
			----------------------------------------------------------
			repeat with w in windows
				set wRole to ""
				try
					set wRole to subrole of w
				end try
				if wRole is in {"AXDialog", "AXSystemDialog", "AXSheet"} then
					set wTitle to my collectText(w)
					if wTitle is "" then set wTitle to "(untitled dialog)"
					return "unknown:" & wTitle
				end if
			end repeat

			return "none"
		end tell
	end tell
end run
