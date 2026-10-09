-- New Markdown File
--
-- Creates a .md file in the front Finder window and reveals it in Finder.
-- Name collisions get an incrementing counter (Untitled.md, Untitled 1.md, ...).
-- If the front window shows a folder, use it; otherwise fall back to Desktop.
--
-- Adapted for FinderPilot.

on run
	with timeout of 5 seconds
		tell application "Finder"
			try
				set theTarget to target of front Finder window
				set theFolder to POSIX path of (theTarget as alias)
			on error
				set theFolder to POSIX path of (desktop as alias)
			end try
		end tell
	end timeout

	set baseName to "Untitled"
	set ext to ".md"
	set fileName to baseName & ext
	set filePath to theFolder & fileName

	-- Avoid collisions by appending an incrementing counter.
	set i to 1
	repeat
		try
			do shell script "test -e " & quoted form of filePath
			set fileName to baseName & " " & i & ext
			set filePath to theFolder & fileName
			set i to i + 1
		on error
			exit repeat
		end try
	end repeat

	do shell script "touch " & quoted form of filePath

	with timeout of 5 seconds
		tell application "Finder"
			try
				reveal POSIX file filePath
				activate
			end try
		end tell
	end timeout
end run