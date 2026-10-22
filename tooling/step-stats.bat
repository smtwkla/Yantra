@echo off
:: /step stats (tooling\steps\step_stats.py): review rounds, findings by severity, time, tokens and e2e cost per
:: step and per role, from the step files and Claude Code's stored transcripts. Writes scratch\step-stats.md.
:: An argument S0NN adds that step's runs one by one.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_stats.py %*
exit /b %ERRORLEVEL%
