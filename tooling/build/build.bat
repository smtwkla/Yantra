@echo off
setlocal enabledelayedexpansion

:: ---------------------------------------------------------------------------
:: Build and push Docker images for Yantra
:: Called by tooling/common/release.py (BUILD_SCRIPT) or run manually.
::
:: Usage:  build.bat [-u] [--dry-run]
::   -u          Use current VERSION as-is (default when called by release.py)
::   --dry-run   The git refusals (dirty tree, no tag, HEAD not at the tag) and the checkout only:
::               makes the clean checkout, checks it, prints the docker build commands and removes
::               it. It does NOT check the registry (that needs the login): no login, build or push.
::
:: Refuses (S025 § 1.2), so a version tag always means one commit:
::   - a working tree with changes;
::   - HEAD that is not the commit tagged v%VERSION%;
::   - a version already in the registry (release.py reuses the version when
::     there is no new commit: the Deploy run config redeploys it instead).
:: Every build and push is checked; the first failure stops the script.
::
:: The images are built from a clean checkout of tag v%VERSION% (a git worktree in
:: %TEMP%\yantra-build-v%VERSION%), never from the working folder: an edit made there while the
:: build runs (an agent at work) cannot enter an image. The checkout is removed after the builds,
:: also when one failed; a stale one from an interrupted run is removed first.
:: ---------------------------------------------------------------------------

set "PROJECT_ROOT=%~dp0..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
set "VERSION_FILE=%PROJECT_ROOT%\VERSION"
set "BUILD_DIR=%~dp0"
set "DRY_RUN="
for %%A in (%*) do if /i "%%~A"=="--dry-run" set "DRY_RUN=1"

:: Read version
if not exist "%VERSION_FILE%" (
    echo ERROR: VERSION file not found at %VERSION_FILE%
    exit /b 1
)
set /p VERSION=<"%VERSION_FILE%"
echo Building version: %VERSION%

:: --- The commit: clean tree, HEAD at the version's tag ---
set "DIRTY="
for /f "delims=" %%i in ('git -C "%PROJECT_ROOT%" status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo ERROR: the working tree has changes. Commit or stash them first: an image is built from a tagged commit only.
    exit /b 1
)
set "HEAD_COMMIT="
set "TAG_COMMIT="
for /f "delims=" %%i in ('git -C "%PROJECT_ROOT%" rev-parse HEAD') do set "HEAD_COMMIT=%%i"
for /f "delims=" %%i in ('git -C "%PROJECT_ROOT%" rev-list -n 1 "v%VERSION%" 2^>nul') do set "TAG_COMMIT=%%i"
if not defined TAG_COMMIT (
    echo ERROR: there is no tag v%VERSION%. Run a release, which tags the commit, or check VERSION.
    exit /b 1
)
if not "%HEAD_COMMIT%"=="%TAG_COMMIT%" (
    echo ERROR: HEAD is not the commit tagged v%VERSION%. Check out v%VERSION%, or run a release.
    exit /b 1
)
set "SRC=%TEMP%\yantra-build-v%VERSION%"
if defined DRY_RUN (
    set "IMAGE_BACKEND=REGISTRY/yantra-backend"
    set "IMAGE_FRONTEND=REGISTRY/yantra-frontend"
    goto :checkout
)

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

:: --- Log in first: the registry check below needs the credentials ---
echo === Logging into registry ===
echo %REGISTRY_PASSWORD%| docker login %REGISTRY% -u %REGISTRY_USER% --password-stdin
if errorlevel 1 (
    echo ERROR: Registry login failed
    exit /b 1
)

:: --- Never overwrite a version in the registry. A failed inspect counts as "absent";
:: --- the push's own check below catches anything else.
for %%I in ("%IMAGE_BACKEND%" "%IMAGE_FRONTEND%") do (
    docker manifest inspect "%%~I:%VERSION%" >nul 2>&1
    if not errorlevel 1 (
        echo ERROR: v%VERSION% is already in the registry ^(%%~I:%VERSION%^) - nothing new to release; use the Deploy run config to redeploy
        exit /b 1
    )
)

:: --- The clean checkout of the tag: the build context and its Dockerfiles ---
:checkout
call :remove_src || exit /b 1
echo === Checking out v%VERSION% into %SRC% ===
git -C "%PROJECT_ROOT%" worktree add --detach "%SRC%" "v%VERSION%"
if errorlevel 1 (
    echo ERROR: could not check out v%VERSION% into %SRC%
    exit /b 1
)
set "SRC_VERSION="
set /p SRC_VERSION=<"%SRC%\VERSION"
if not "%SRC_VERSION%"=="%VERSION%" (
    echo ERROR: the checkout of v%VERSION% holds VERSION %SRC_VERSION%. Check the tag.
    call :remove_src
    exit /b 1
)
set "BUILD_BACKEND=docker build -f "%SRC%\tooling\build\Dockerfile.backend" -t "%IMAGE_BACKEND%:%VERSION%" -t "%IMAGE_BACKEND%:latest" "%SRC%""
set "BUILD_FRONTEND=docker build -f "%SRC%\tooling\build\Dockerfile.frontend" -t "%IMAGE_FRONTEND%:%VERSION%" -t "%IMAGE_FRONTEND%:latest" "%SRC%""

if defined DRY_RUN (
    for %%F in (Dockerfile.backend Dockerfile.frontend) do if not exist "%SRC%\tooling\build\%%F" (
        echo ERROR: %%F is missing from the checkout
        call :remove_src
        exit /b 1
    )
    echo Would run: !BUILD_BACKEND!
    echo Would run: !BUILD_FRONTEND!
    call :remove_src || exit /b 1
    echo === Dry run complete: v%VERSION% checks out cleanly; nothing was built or pushed ===
    exit /b 0
)

:: --- Build backend ---
echo === Building backend image ===
!BUILD_BACKEND!
if errorlevel 1 (
    echo ERROR: Backend build failed
    call :remove_src
    exit /b 1
)

:: --- Build frontend ---
echo === Building frontend image ===
!BUILD_FRONTEND!
if errorlevel 1 (
    echo ERROR: Frontend build failed
    call :remove_src
    exit /b 1
)
call :remove_src || exit /b 1

:: --- Push to registry: the version tags first, then latest ---
echo === Pushing backend ===
docker push "%IMAGE_BACKEND%:%VERSION%"
if errorlevel 1 (
    echo ERROR: Push of %IMAGE_BACKEND%:%VERSION% failed
    exit /b 1
)
docker push "%IMAGE_BACKEND%:latest"
if errorlevel 1 (
    echo ERROR: Push of %IMAGE_BACKEND%:latest failed
    exit /b 1
)

echo === Pushing frontend ===
docker push "%IMAGE_FRONTEND%:%VERSION%"
if errorlevel 1 (
    echo ERROR: Push of %IMAGE_FRONTEND%:%VERSION% failed
    exit /b 1
)
docker push "%IMAGE_FRONTEND%:latest"
if errorlevel 1 (
    echo ERROR: Push of %IMAGE_FRONTEND%:latest failed
    exit /b 1
)

echo.
echo === Build complete: v%VERSION% pushed to %REGISTRY% ===
exit /b 0


:: Remove the checkout %SRC% (worktree and folder) if it is there.
:remove_src
if exist "%SRC%" git -C "%PROJECT_ROOT%" worktree remove --force "%SRC%" >nul 2>&1
if exist "%SRC%" rmdir /s /q "%SRC%"
git -C "%PROJECT_ROOT%" worktree prune
if exist "%SRC%" (
    echo ERROR: could not remove the build checkout %SRC%
    exit /b 1
)
exit /b 0
