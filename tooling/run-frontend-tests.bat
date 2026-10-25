@echo off
setlocal
:: Frontend unit tests (vitest). Extra arguments go to vitest (a test file, -t ...).
:: The whole output is also in scratch\frontend-tests.log (YANTRA_TEST_LOG_DIR; frontend-tests-<run>.log when YANTRA_TEST_RUN is not dev); the last line is a
:: summary: PASSED/FAILED, counts, duration and the log path.
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
set "LOG=%YANTRA_TEST_LOG_DIR%\frontend-tests.log"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "LOG=%YANTRA_TEST_LOG_DIR%\frontend-tests-%YANTRA_TEST_RUN%.log"
cd /d "%~dp0..\frontend" && uv run --no-project python "%~dp0common\run_test_suite.py" frontend "%LOG%" -- npx vitest run %*
exit /b %ERRORLEVEL%
