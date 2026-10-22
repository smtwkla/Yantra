@echo off
setlocal
:: Tests of the dependency audit (tooling\deps). pytest is fetched by uv (not locked);
:: the tests use no network, fetching pytest needs it once on a cold uv cache.
:: Log: scratch\deps-tests.log (YANTRA_TEST_LOG_DIR; deps-tests-<run>.log when YANTRA_TEST_RUN is not dev); the last line is a summary.
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
set "LOG=%YANTRA_TEST_LOG_DIR%\deps-tests.log"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "LOG=%YANTRA_TEST_LOG_DIR%\deps-tests-%YANTRA_TEST_RUN%.log"
cd /d "%~dp0.." && uv run --no-project python "%~dp0run_logged.py" deps "%LOG%" -- uv run --no-project --with "pytest>=8,<10" pytest -q tooling\deps\tests %*
exit /b %ERRORLEVEL%
