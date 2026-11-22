@echo off
:: Facts for /step feedback (tooling\steps\step_feedback.py): the agents' "## Feedback" items (waste,
:: hindrance, rule, idea) from every step's advice, reviews and impl report; step IDs narrow it.
:: --new lists only the items not yet in docs\steps\feedback-log.md; --rows prints them as log rows;
:: --themes counts the log's rows by theme and marks a theme noted twice;
:: --dropped prints one line with the themes last decided "dropped", for spawn prompts.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_feedback.py %*
exit /b %ERRORLEVEL%
