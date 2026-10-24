@echo off
:: Step snapshots (tooling\steps\step_snapshot.py, 24-10-2026): "snapshot S0NN <message>" at gate B writes the
:: working tree as a commit under refs/steps/S0NN (HEAD, the index and the files untouched); "list" shows them;
:: "adopt S0NN" moves the branch to a snapshot that builds on HEAD (the user, or Claude when asked to commit).
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_snapshot.py %*
exit /b %ERRORLEVEL%
