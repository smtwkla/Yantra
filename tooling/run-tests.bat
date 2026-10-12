@echo off
:: Full test suite: backend (pytest, needs the dev DB up) then frontend (vitest).
:: release.py runs this as TEST_CMD.
call "%~dp0run-backend-tests.bat" || exit /b 1
call "%~dp0run-frontend-tests.bat" || exit /b 1
