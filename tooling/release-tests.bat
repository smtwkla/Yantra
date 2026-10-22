@echo off
setlocal
:: The release's tests (TEST_CMD of the Release run configs): the full suite (tooling\run-tests.bat)
:: on a clean copy of HEAD, so nobody's edits in the working folder during the run can change what
:: is tested, and on databases of its own (YANTRA_TEST_RUN=release: vel_yantra_test_release_<worker>),
:: so an agent's test run at the same time cannot spoil it, nor it the agent's.
::
::   1. A git worktree of HEAD (detached) in %TEMP%\yantra-release-tests; a stale one is removed first.
::   2. frontend\node_modules: a directory junction to the working folder's (no npm install).
::      backend: uv builds the worktree's own .venv from its uv cache (seconds, no download).
::   3. The worktree's tooling\run-tests.bat, logs in scratch\release-tests\ of the working folder.
::   4. The worktree is removed, also when a suite failed. The junction goes first, on its own, so
::      removing the worktree can never reach into the working folder's node_modules.
:: The worktree is added LOCKED and unlocked only after the junction is gone: while the junction
:: is inside, `git worktree remove --force` (or an IDE's "remove worktree") would follow it and empty
:: the working folder's frontend\node_modules. A locked worktree refuses that and `git worktree prune`.
:: A run that was cut off leaves the locked worktree; running this script again cleans it up.
:: Exit code: run-tests.bat's (0 all green), or 1 when the worktree could not be made.
:: Usage: release-tests.bat [<commit>]   (default HEAD; another commit only to try this script out)
set "REPO=%~dp0.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
set "WT=%TEMP%\yantra-release-tests"
set "YANTRA_TEST_RUN=release"
set "YANTRA_TEST_LOG_DIR=%REPO%\scratch\release-tests"
set "REF=%~1"
if not defined REF set "REF=HEAD"

call :remove_worktree || exit /b 1
git -C "%REPO%" worktree add --detach --lock --reason "holds a junction to frontend\node_modules; remove it with tooling\release-tests.bat" "%WT%" "%REF%"
if errorlevel 1 (
  echo Could not create the test worktree %WT%.
  exit /b 1
)
mklink /J "%WT%\frontend\node_modules" "%REPO%\frontend\node_modules" >nul
if errorlevel 1 (
  echo Could not link frontend\node_modules into the test worktree.
  call :remove_worktree
  exit /b 1
)
for /f "delims=" %%i in ('git -C "%WT%" rev-parse --short HEAD') do echo Release tests on %%i in %WT%

call "%WT%\tooling\run-tests.bat"
set RESULT=%ERRORLEVEL%
call :remove_worktree
exit /b %RESULT%


:remove_worktree
:: The junction first: rmdir without /s removes the link, never the folder it points to.
if exist "%WT%\frontend\node_modules" rmdir "%WT%\frontend\node_modules"
if exist "%WT%\frontend\node_modules" (
  echo Could not remove the node_modules junction in %WT%. Remove it with: rmdir "%WT%\frontend\node_modules"
  exit /b 1
)
:: Only now unlock: nothing inside can be followed any more. (Fails harmlessly when not locked.)
git -C "%REPO%" worktree unlock "%WT%" >nul 2>&1
if exist "%WT%" git -C "%REPO%" worktree remove --force "%WT%" >nul 2>&1
if exist "%WT%" rmdir /s /q "%WT%"
git -C "%REPO%" worktree prune
if exist "%WT%" (
  echo Could not remove the test worktree %WT%.
  exit /b 1
)
exit /b 0
