@echo off
setlocal
:: Full test suite: backend (pytest, needs the dev DB up), frontend (vitest), then the dependency-audit
:: and tooling (deploy.py, steps, run_lanes, run_logged) tests. tooling\release-tests.bat runs this in a
:: clean worktree for the release.
:: Every suite runs, even after one failed; each writes its log to scratch\ (YANTRA_TEST_LOG_DIR) and a
:: summary line, and the lines of all four are printed again at the end. Exit 1 when any suite failed.
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
if not exist "%YANTRA_TEST_LOG_DIR%" mkdir "%YANTRA_TEST_LOG_DIR%"
set "YANTRA_TEST_SUMMARY=%YANTRA_TEST_LOG_DIR%\test-summary.txt"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "YANTRA_TEST_SUMMARY=%YANTRA_TEST_LOG_DIR%\test-summary-%YANTRA_TEST_RUN%.txt"
if exist "%YANTRA_TEST_SUMMARY%" del "%YANTRA_TEST_SUMMARY%"
set "FAILED="

call "%~dp0run-backend-tests.bat" || set "FAILED=1"
call "%~dp0run-frontend-tests.bat" || set "FAILED=1"
call "%~dp0run-deps-tests.bat" || set "FAILED=1"
call "%~dp0run-tooling-tests.bat" || set "FAILED=1"

echo.
echo ===== Test summary =====
if exist "%YANTRA_TEST_SUMMARY%" type "%YANTRA_TEST_SUMMARY%"
if defined FAILED (
  echo == ALL SUITES: FAILED. A suite with no line above failed before it started; see its output.
  exit /b 1
)
echo == ALL SUITES: PASSED
exit /b 0
