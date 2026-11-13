@echo off
:: Housekeeping for finished steps (tooling\steps\step_clean.py): deletes the scratch entries that carry
:: a Committed, Done or Dropped step's id, and its snapshot and round refs; docs\steps is never touched.
:: No step named: every finished step. A dry run unless --apply is given.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_clean.py %*
exit /b %ERRORLEVEL%
