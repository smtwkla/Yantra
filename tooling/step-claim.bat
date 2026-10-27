@echo off
:: Step claims (tooling\steps\step_claim.py): one orchestrator session at a time per step, and the
:: watchdog that wakes the orchestrator when an agent passes its budget. take, agent, agent-done, touch,
:: release, watch, show; see the script's help (run it with no argument).
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_claim.py %*
exit /b %ERRORLEVEL%
