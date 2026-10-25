@echo off
setlocal
:: The release's tests (TEST_CMD of the Release run configs): the four unit suites
:: (tooling\run-tests.bat) and the browser tests at the Full level (S047) on a clean copy of
:: HEAD, so nobody's edits in the working folder during the run can change what is tested, and
:: on databases of its own (YANTRA_TEST_RUN=release: vel_yantra_test_release_<worker>),
:: so an agent's test run at the same time cannot spoil it, nor it the agent's.
::
::   1. A git worktree of HEAD (detached) in %TEMP%\yantra-release-tests; a stale one is removed first.
::   2. frontend\node_modules: a directory junction to the working folder's (no npm install).
::      backend: uv builds the worktree's own .venv from its uv cache (seconds, no download).
::   3. The worktree's tooling\run-tests.bat, logs in scratch\release-tests\ of the working folder.
::   4. The browser tests at the Full level (S047): the worktree's tooling\run-e2e-tests.bat
::      --level=full, every test on all three devices, the iPhone in its Docker container (needs
::      Docker Desktop). It runs also when step 3 was red, so one attempt shows every fault. It
::      takes the machine's e2e lock in the working folder's scratch\, so it waits for an agent's
::      e2e run, and an agent's run waits for it.
::   5. The e2e report (its HTML and results.json, which /pre-flight reads, S049), the lane logs and
::      the backend logs are copied to scratch\release-tests\e2e\ of the working folder, also when
::      the e2e run failed, before the worktree goes.
::   6. The worktree is removed, also when a suite failed. The junction goes first, on its own, so
::      removing the worktree can never reach into the working folder's node_modules.
:: The worktree is added LOCKED and unlocked only after the junction is gone: while the junction
:: is inside, `git worktree remove --force` (or an IDE's "remove worktree") would follow it and empty
:: the working folder's frontend\node_modules. A locked worktree refuses that and `git worktree prune`.
:: A run that was cut off leaves the locked worktree; running this script again cleans it up.
:: Exit code: 0 when run-tests.bat and the e2e run are both green, else 1 (also when the worktree
:: could not be made).
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
set UNIT_RESULT=%ERRORLEVEL%
call "%WT%\tooling\run-e2e-tests.bat" --level=full
set E2E_RESULT=%ERRORLEVEL%
call :copy_e2e_report
call :remove_worktree
:: Both lines print when both parts failed, so the end of the output shows every fault.
set RELEASE_RESULT=0
if not "%UNIT_RESULT%"=="0" (
  echo Release tests: the unit suites failed ^(see the summary above and scratch\release-tests\^).
  set RELEASE_RESULT=1
)
if not "%E2E_RESULT%"=="0" (
  echo Release tests: the browser tests failed. Report: scratch\release-tests\e2e\html\index.html
  set RELEASE_RESULT=1
)
if "%RELEASE_RESULT%"=="0" echo Release tests: all green.
exit /b %RELEASE_RESULT%


:copy_e2e_report
:: robocopy's exit code is a bit mask (1 = files copied); a missing source only means that part
:: of the run did not happen, so nothing here stops the script.
set "E2E_COPY=%YANTRA_TEST_LOG_DIR%\e2e"
if exist "%E2E_COPY%" rmdir /s /q "%E2E_COPY%"
mkdir "%E2E_COPY%"
robocopy "%WT%\scratch\e2e-report\html" "%E2E_COPY%\html" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%WT%\scratch\e2e-lanes" "%E2E_COPY%\e2e-lanes" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "%WT%\scratch" "%E2E_COPY%" "e2e-backend*.log" /NFL /NDL /NJH /NJS /NP >nul
robocopy "%WT%\scratch\e2e-report" "%E2E_COPY%" "results.json" /NFL /NDL /NJH /NJS /NP >nul
echo E2E report and logs copied to %E2E_COPY%
exit /b 0


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
