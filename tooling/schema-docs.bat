@echo off
setlocal
:: The schema docs (S078): docs\schema\schema.json and docs\schema\schema-data.js, made from the
:: migrations (backend\local_db.py _MIGRATIONS) and docs\schema\notes.json.
::   tooling\schema-docs.bat write   build, write both files, then check them
::   tooling\schema-docs.bat check   build and check; writes nothing
:: Needs the dev DB container (tooling\dev\dev-db-up.bat). Each run builds the database
:: vel_yantra_test_<run>_schemadocs from the migrations and drops it again (backend\tests\db_names.py).
::
::   YANTRA_TEST_RUN       the run's name in the database name (default dev; the release uses release).
::   YANTRA_TEST_LOG_DIR   where the log goes (default scratch\)
::
:: Exit code: 0 every check passed, 1 a check failed (a stale file or a notes problem), 2 not
:: completed (the database could not be reached or built, the lock timed out, a wrong mode).
:: The whole output is in scratch\schema-docs.log (schema-docs-<run>.log for another run), and the
:: last line is a summary: PASSED/FAILED, counts, duration and the log path.
if not "%~1"=="write" if not "%~1"=="check" (
  echo Usage: tooling\schema-docs.bat write^|check
  exit /b 2
)
if not "%~2"=="" (
  echo Usage: tooling\schema-docs.bat write^|check
  exit /b 2
)
if not defined YANTRA_TEST_RUN set "YANTRA_TEST_RUN=dev"
if not defined YANTRA_TEST_LOG_DIR set "YANTRA_TEST_LOG_DIR=%~dp0..\scratch"
set "LOG=%YANTRA_TEST_LOG_DIR%\schema-docs.log"
if /i not "%YANTRA_TEST_RUN%"=="dev" set "LOG=%YANTRA_TEST_LOG_DIR%\schema-docs-%YANTRA_TEST_RUN%.log"

cd /d "%~dp0..\backend" && uv run --no-project python "%~dp0common\run_test_suite.py" schema-docs "%LOG%" -- uv run python "%~dp0schema\schema_docs.py" %1
exit /b %ERRORLEVEL%
