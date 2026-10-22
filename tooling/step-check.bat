@echo off
:: /step check (tooling\steps\step_check.py): the step files checked against each other and git, read-only;
:: one line per problem, the planner judges the rest and proposes fixes.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_check.py %*
exit /b %ERRORLEVEL%
