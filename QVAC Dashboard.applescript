-- Portable launcher source (optional). Prefer scripts/build_dashboard_app.sh which
-- creates QVAC Dashboard.app/Contents/MacOS/launcher with a relative project path.
on run
	set appPath to POSIX path of (path to me)
	set projectDir to do shell script "cd " & quoted form of appPath & "/../../.. && pwd"
	do shell script "bash " & quoted form of (projectDir & "/launch_dashboard.sh")
end run
