@echo off
setlocal
:: Tests of the tooling scripts (tooling\tests: deploy.py, S025; preflight; run_lanes).
:: The tests of the step tools, run_test_suite.py and the deps audit live in smtw-common (S057, S058). pytest and python-dotenv are fetched by uv (not locked); the tests use no network,
:: fetching them needs it once on a cold uv cache.
:: Log: scratch\tooling-tests.log (YANTRA_TEST_LOG_DIR; tooling-tests-<run>.log when YANTRA_TEST_RUN is not dev); the last line is a summary.
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
set "LOG=%YANTRA_TEST_LOG_DIR%\tooling-tests.log"
if defined YANTRA_TEST_RUN if /i not "%YANTRA_TEST_RUN%"=="dev" set "LOG=%YANTRA_TEST_LOG_DIR%\tooling-tests-%YANTRA_TEST_RUN%.log"
cd /d "%~dp0.." && uv run --no-project python "%~dp0common\run_test_suite.py" tooling "%LOG%" -- uv run --no-project --with "pytest>=8,<10" --with python-dotenv pytest -q tooling\tests %*
exit /b %ERRORLEVEL%
