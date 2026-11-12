@echo off
:: The Mermaid diagrams of a Markdown file render (tooling\architecture\check_diagrams.mjs), with
:: the Chromium of the browser tests. Exit 0 all rendered, 1 a diagram failed, 2 not completed.
:: Usage: tooling\check-diagrams.bat docs\Architecture.md
cd /d "%~dp0.." && node tooling\architecture\check_diagrams.mjs %*
exit /b %ERRORLEVEL%
