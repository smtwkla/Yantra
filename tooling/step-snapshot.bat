@echo off
:: Step snapshots (tooling\steps\step_snapshot.py): "snapshot S0NN <message>" at gate B writes the
:: working tree as a commit under refs/steps/S0NN (HEAD, the index and the files untouched); "list" shows them;
:: "adopt S0NN" moves the branch to a snapshot that builds on HEAD (the user, or Claude when asked to commit).
:: Each snapshot keeps a round ref (refs/step-rounds/S0NN-n): "rounds S0NN" lists them; "diff S0NN
:: [--from-round n] [--stat] [-- <path>...]" shows the step's change, new files as added, from its base or from
:: round n; it leaves out the step folders, docs\steps\INDEX.md, docs\steps\feedback-log.md and docs\roadmap\
:: (--all shows them; paths after -- replace that default). "diff [S0NN] --base <commit>"
:: compares with any commit, for a step with no snapshot yet. "diff S0NN --worktree [--from-round n]"
:: compares the working tree, untracked files too, with the snapshot (or round n) itself: "working tree equals
:: <ref>" and exit 0, else the diff and exit 1; "--by-folder" gives one line per top-level folder.
cd /d "%~dp0.." && uv run --no-project python tooling\steps\step_snapshot.py %*
exit /b %ERRORLEVEL%
