@echo off
:: Software inventory and vulnerability check: regenerates sbom\, looks up CVEs, writes
:: scratch\dependency-report.md. Exit 0 clean, 1 high/critical/unknown vulnerability,
:: 2 check incomplete. Not part of run-tests.bat.
cd /d "%~dp0.."
uv run tooling\deps\audit.py
exit /b %ERRORLEVEL%
