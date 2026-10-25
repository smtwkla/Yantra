@echo off
setlocal
:: Backend tests (pytest), in parallel (pytest-xdist). Needs the dev DB container (tooling\dev\dev-db-up.bat).
:: Extra arguments go to pytest: test files (tooling\run-backend-tests.bat tests\test_x.py), -k ..., -x,
:: or -n 0 for one process.
::
:: Databases: one per run and worker, so parallel workers and two runs at once never share data
:: (backend\tests\db_names.py): vel_yantra_test_<run>_<worker> and vel_yantra_upgrade_<run>_<worker>.
:: The tests create them; this script grants the DB user the right to (as root, dev password from the
:: compose file; also in tooling\dev\init-test-db.sql for a new container).
::
::   YANTRA_TEST_RUN       the run's name in the database names (default dev; the release uses release).
::                         Two runs at the same time need two names.
::   YANTRA_TEST_WORKERS   pytest-xdist workers (default 8: measured 22-10-2026 on the full suite,
::                         4 = 61 s, 6 = 44 s, 8 = 38-42 s, 12 = 35 s, 16 = 35 s). Starting the workers
::                         costs about 4 s: add -n 0 to run one small test file in one process.
::   YANTRA_TEST_LOG_DIR   where the log goes (default scratch\)
::
:: Output: quiet (-q); failures in full (--tb=short). The whole output is also in
:: scratch\backend-tests.log (backend-tests-<run>.log for another run), and the last line is a
:: summary: PASSED/FAILED, counts, duration and the log path.
if not defined YANTRA_TEST_RUN set "YANTRA_TEST_RUN=dev"
if not defined YANTRA_TEST_WORKERS set "YANTRA_TEST_WORKERS=8"
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
set "LOG=%YANTRA_TEST_LOG_DIR%\backend-tests.log"
if /i not "%YANTRA_TEST_RUN%"=="dev" set "LOG=%YANTRA_TEST_LOG_DIR%\backend-tests-%YANTRA_TEST_RUN%.log"

set COMPOSE=docker compose -f "%~dp0dev\docker-compose.dev.yml"
%COMPOSE% exec -T mariadb mariadb -uroot -pdev-root-password -e "GRANT ALL PRIVILEGES ON `vel\_yantra\_test\_%%`.* TO 'vel_yantra_master'@'%%'; GRANT ALL PRIVILEGES ON `vel\_yantra\_upgrade\_%%`.* TO 'vel_yantra_master'@'%%'; FLUSH PRIVILEGES;"
if errorlevel 1 (
  echo Could not grant the test databases. Is the dev DB up? tooling\dev\dev-db-up.bat
  exit /b 1
)

:: -n first: a -n among the arguments wins. loadscope: a module's test functions, or one class's
:: tests, run together on one worker, in order. (loadfile kept test_alerts.py, 90 s, on one worker;
:: its classes now spread over the workers.)
cd /d "%~dp0..\backend" && uv run --no-project python "%~dp0common\run_test_suite.py" backend "%LOG%" -- uv run pytest -q --tb=short -n %YANTRA_TEST_WORKERS% --dist loadscope %*
exit /b %ERRORLEVEL%
