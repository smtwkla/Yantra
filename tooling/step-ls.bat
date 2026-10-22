@echo off
:: Facts for /step ls (tooling\steps\step_ls.py): each open step's Status, latest review verdict, commits and
:: working-tree changes, in one run; the planner builds the table from them. "all" includes Done and Dropped steps.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_ls.py %*
exit /b %ERRORLEVEL%
