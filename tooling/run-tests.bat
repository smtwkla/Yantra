@echo off
:: Full test suite: backend (pytest, needs the dev DB up) then frontend (vitest), then the dependency-audit
:: and tooling (deploy.py) tests. release.py runs this as TEST_CMD.
call "%~dp0run-backend-tests.bat" || exit /b 1
call "%~dp0run-frontend-tests.bat" || exit /b 1
call "%~dp0run-deps-tests.bat" || exit /b 1
call "%~dp0run-tooling-tests.bat" || exit /b 1
