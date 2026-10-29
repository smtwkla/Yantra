@echo off
:: Step snapshots (tooling\steps\step_snapshot.py, 24-10-2026): "snapshot S0NN <message>" at gate B writes the
:: working tree as a commit under refs/steps/S0NN (HEAD, the index and the files untouched); "list" shows them;
:: "adopt S0NN" moves the branch to a snapshot that builds on HEAD (the user, or Claude when asked to commit).
:: Each snapshot keeps a round ref (refs/step-rounds/S0NN-n, 27-10-2026): "rounds S0NN" lists them; "diff S0NN
:: [--from-round n] [--stat] [-- <path>...]" shows the step's change, new files as added, from its base or from
:: round n; it leaves out docs\steps\S0NN-*\ unless paths are named (29-10-2026).
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_snapshot.py %*
exit /b %ERRORLEVEL%
