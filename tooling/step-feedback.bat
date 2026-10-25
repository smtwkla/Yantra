@echo off
:: Facts for /step feedback (tooling\steps\step_feedback.py): the agents' "## Feedback" items (waste,
:: hindrance, rule, idea) from every step's advice, reviews and impl report; step IDs narrow it.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_feedback.py %*
exit /b %ERRORLEVEL%
