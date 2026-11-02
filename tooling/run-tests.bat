@echo off
setlocal
:: Full test suite: backend (pytest, needs the dev DB up), frontend (vitest), then the tooling
:: (deploy.py, preflight, run_lanes) tests. tooling\release-tests.bat runs this in a
:: clean worktree for the release.
:: Every suite runs, even after one failed; each writes its log to scratch\ (YANTRA_TEST_LOG_DIR) and a
:: summary line, and the lines of all three are printed again at the end. Exit 1 when any suite failed.
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
if not exist "%YANTRA_TEST_LOG_DIR%" mkdir "%YANTRA_TEST_LOG_DIR%"
set "TEST_SUMMARY_FILE=%YANTRA_TEST_LOG_DIR%\test-summary.txt"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "TEST_SUMMARY_FILE=%YANTRA_TEST_LOG_DIR%\test-summary-%YANTRA_TEST_RUN%.txt"
if exist "%TEST_SUMMARY_FILE%" del "%TEST_SUMMARY_FILE%"
set "FAILED="

:: The line-width check first (S094; feedback triage 02-11-2026): a long line found after the 3-minute
:: backend suite cost a second full run. It takes seconds; when it fails, no suite runs.
set "WIDTH_LOG=%YANTRA_TEST_LOG_DIR%\line-width.log"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "WIDTH_LOG=%YANTRA_TEST_LOG_DIR%\line-width-%YANTRA_TEST_RUN%.log"
pushd "%~dp0.."
uv run --no-project --with "pytest>=8,<10" --with python-dotenv pytest -q tooling\tests\test_line_width.py > "%WIDTH_LOG%" 2>&1
set "WIDTH_EXIT=%ERRORLEVEL%"
popd
if not "%WIDTH_EXIT%"=="0" (
  type "%WIDTH_LOG%"
  echo == LINE WIDTH: FAILED. Wrap the lines listed above to 120 characters, then run again. No suite ran.
  exit /b 1
)

call "%~dp0run-backend-tests.bat" || set "FAILED=1"
call "%~dp0run-frontend-tests.bat" || set "FAILED=1"
call "%~dp0run-tooling-tests.bat" || set "FAILED=1"

echo.
echo ===== Test summary =====
if exist "%TEST_SUMMARY_FILE%" type "%TEST_SUMMARY_FILE%"
if defined FAILED (
  echo == ALL SUITES: FAILED. A suite with no line above failed before it started; see its output.
  exit /b 1
)
echo == ALL SUITES: PASSED
exit /b 0
