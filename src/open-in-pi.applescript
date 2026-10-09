-- Open in Pi
--
-- Opens the pi coding agent in a terminal, rooted at whatever is selected in
-- Finder. Selecting a folder uses that folder; selecting a file uses its parent.
--
-- Adapted for FinderPilot.

on run
	set theFolder to ""
	with timeout of 8 seconds
		tell application "Finder"
			set sel to {}
			try
				set sel to selection
			on error
				set sel to {}
			end try

			if (count of sel) is greater than 0 then
				set chosen to item 1 of sel
				try
					set itemPath to POSIX path of (chosen as alias)
					if (do shell script "test -d " & quoted form of itemPath & " && echo d || echo f") is "d" then
						set theFolder to itemPath
					else
						set theFolder to do shell script "dirname " & quoted form of itemPath
					end if
				on error
					-- Fall through to the front-window fallback below.
				end try
			end if

			-- Nothing selected, or the lookup failed: use the front window's folder.
			if theFolder is "" then
				try
					set theFolder to POSIX path of (target of front Finder window as alias)
				on error
					set theFolder to POSIX path of (desktop as alias)
				end try
			end if
		end tell
	end timeout

	-- Locate pi: user-local install first, then common system paths, then PATH.
	set piBin to do shell script "
		if [ -x \"$HOME/.local/bin/pi\" ]; then printf '%s' \"$HOME/.local/bin/pi\"; exit 0; fi
		for p in /opt/homebrew/bin/pi /usr/local/bin/pi \"$HOME/.pi/bin/pi\"; do
			if [ -x \"$p\" ]; then printf '%s' \"$p\"; exit 0; fi
		done
		command -v pi 2>/dev/null || true
	"

	if piBin is "" then
		display dialog "Could not find the pi command." & return & return & "Install it with:" & return & return & "    npm install -g @earendil-works/pi-coding-agent" & return & return & "Then run this tool again." with title "pi not installed" buttons {"OK"} default button 1 with icon caution
		return
	end if

	-- Prefer iTerm when it's already running, otherwise fall back to Terminal.
	set useITerm to false
	try
		tell application "System Events" to set useITerm to (exists process "iTerm2") or (exists process "iTerm")
	end try

	if useITerm then
		tell application "iTerm"
			activate
			set newWin to (create window with default profile)
			tell current session of newWin
				write text "cd " & quoted form of theFolder & " && " & quoted form of piBin
			end tell
		end tell
	else
		tell application "Terminal"
			activate
			do script "cd " & quoted form of theFolder & " && " & quoted form of piBin
		end tell
	end if
end run