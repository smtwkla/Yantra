@echo off
:: Screenshots of a roadmap's mock-ups for its slide deck (tooling\roadmap\render_mockups.mjs):
:: every <folder>\*.html becomes a PNG beside it, with the Chromium of the browser tests.
:: Usage: render-mockups.bat docs\roadmap\R01-mockups
cd /d "%~dp0.." && node tooling\roadmap\render_mockups.mjs %*
exit /b %ERRORLEVEL%
