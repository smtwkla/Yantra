@echo off
:: Browser tests (S024): Playwright drives the real screens on phone and desktop against the
:: e2e backend (127.0.0.1:5002, database vel_yantra_e2e, rebuilt at every run) and its own
:: Vite (5177). Needs the dev DB container (tooling\dev\dev-db-up.bat). Not part of
:: run-tests.bat or the release. Extra arguments go to Playwright (e.g. a spec file, or
:: --project=phone-chromium). Exit 0 green, 1 a failure (as Playwright).
:: Report: scratch\e2e-report\html\index.html (npx playwright show-report ..\scratch\e2e-report\html).
setlocal
set COMPOSE=docker compose -f "%~dp0dev\docker-compose.dev.yml"

:: 1. The dev DB container is up
for /f %%i in ('%COMPOSE% ps --status running -q mariadb 2^>nul') do set DB_UP=%%i
if not defined DB_UP (
  echo The dev DB container is not running. Start it with tooling\dev\dev-db-up.bat.
  exit /b 1
)

:: 2. The e2e database and its grant, if missing (dev root password from the compose file; dev only)
%COMPOSE% exec -T mariadb mariadb -uroot -pdev-root-password -e "CREATE DATABASE IF NOT EXISTS vel_yantra_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON vel_yantra_e2e.* TO 'vel_yantra_master'@'%%'; FLUSH PRIVILEGES;"
if errorlevel 1 (
  echo Could not create the e2e database vel_yantra_e2e.
  exit /b 1
)

cd /d "%~dp0..\frontend"

:: 3. The browsers (a no-op when they are there; fetches the right ones after a Playwright update)
call npx playwright install chromium webkit
if errorlevel 1 exit /b 1

:: 4. The tests
echo Started %date% %time%
call npx playwright test %*
set RESULT=%ERRORLEVEL%
echo Finished %date% %time%
echo Report: %~dp0..\scratch\e2e-report\html\index.html  (backend log: scratch\e2e-backend.log)
exit /b %RESULT%
