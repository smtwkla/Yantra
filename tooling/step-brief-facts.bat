@echo off
:: Facts behind a brief's claims (tooling\steps\brief_facts.py): every `backticked` file, test,
:: route and code name in the brief, with where it exists and which tests use it. Run by the
:: planner before brief review round 1; output also in scratch\brief-facts-<step>.md.
:: Usage: tooling\step-brief-facts.bat S029
cd /d "%~dp0.." && uv run --no-project python tooling\steps\brief_facts.py %*
exit /b %ERRORLEVEL%
