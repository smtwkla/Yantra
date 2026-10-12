@echo off
setlocal enabledelayedexpansion

:: ---------------------------------------------------------------------------
:: Build and push Docker images for Yantra
:: Called by tooling/common/release.py (BUILD_SCRIPT) or run manually.
::
:: Usage:  build.bat [-u]
::   -u   Use current VERSION as-is (default when called by release.py)
:: ---------------------------------------------------------------------------

set "PROJECT_ROOT=%~dp0..\.."
set "VERSION_FILE=%PROJECT_ROOT%\VERSION"
set "BUILD_DIR=%~dp0"

:: Read version
if not exist "%VERSION_FILE%" (
    echo ERROR: VERSION file not found at %VERSION_FILE%
    exit /b 1
)
set /p VERSION=<"%VERSION_FILE%"
echo Building version: %VERSION%

:: Load registry credentials
if not exist "%BUILD_DIR%secrets_registry.bat" (
    echo ERROR: secrets_registry.bat not found in %BUILD_DIR%
    echo Copy example_secrets_registry.bat and fill in your credentials.
    exit /b 1
)
call "%BUILD_DIR%secrets_registry.bat"

:: Verify required vars
if "%REGISTRY%"=="" (
    echo ERROR: REGISTRY not set in secrets_registry.bat
    exit /b 1
)

set "IMAGE_BACKEND=%REGISTRY%/yantra-backend"
set "IMAGE_FRONTEND=%REGISTRY%/yantra-frontend"

echo.
echo Registry:  %REGISTRY%
echo Backend:   %IMAGE_BACKEND%:%VERSION%
echo Frontend:  %IMAGE_FRONTEND%:%VERSION%
echo.

:: --- Build backend ---
echo === Building backend image ===
docker build -f "%BUILD_DIR%Dockerfile.backend" -t "%IMAGE_BACKEND%:%VERSION%" -t "%IMAGE_BACKEND%:latest" "%PROJECT_ROOT%"
if errorlevel 1 (
    echo ERROR: Backend build failed
    exit /b 1
)

:: --- Build frontend ---
echo === Building frontend image ===
docker build -f "%BUILD_DIR%Dockerfile.frontend" -t "%IMAGE_FRONTEND%:%VERSION%" -t "%IMAGE_FRONTEND%:latest" "%PROJECT_ROOT%"
if errorlevel 1 (
    echo ERROR: Frontend build failed
    exit /b 1
)

:: --- Push to registry ---
echo === Logging into registry ===
echo %REGISTRY_PASSWORD%| docker login %REGISTRY% -u %REGISTRY_USER% --password-stdin
if errorlevel 1 (
    echo ERROR: Registry login failed
    exit /b 1
)

echo === Pushing backend ===
docker push "%IMAGE_BACKEND%:%VERSION%"
docker push "%IMAGE_BACKEND%:latest"

echo === Pushing frontend ===
docker push "%IMAGE_FRONTEND%:%VERSION%"
docker push "%IMAGE_FRONTEND%:latest"

:: --- Cleanup ---
if exist "%PROJECT_ROOT%\scratch" (
    del /q "%PROJECT_ROOT%\scratch\*" 2>nul
)

echo.
echo === Build complete: v%VERSION% pushed to %REGISTRY% ===
