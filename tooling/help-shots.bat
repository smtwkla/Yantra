@echo off
:: The Help screenshot tour (S103): the app's screens on lane 9 into scratch\help-shots\ (PNG and
:: lossless WebP), for help\guide\shots\ and help\documents\shots\ (help\README.md).
:: Needs the dev DB container (tooling\dev\dev-db-up.bat). Takes the machine's e2e lock, so it waits
:: for a browser run and never runs beside one. Exit 0 when every shot was taken.
setlocal
cd /d "%~dp0..\frontend"
call npx playwright install chromium
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
uv run --project backend python tooling\help\tour.py %*
exit /b %ERRORLEVEL%
