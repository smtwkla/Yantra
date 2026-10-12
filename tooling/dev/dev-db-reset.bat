@echo off
:: Stop the dev MariaDB container and DELETE all data (fresh start)
echo This will destroy all dev database data.
set /p confirm="Continue? (y/N): "
if /i not "%confirm%"=="y" (
    echo Cancelled.
    exit /b 0
)
docker compose -f "%~dp0docker-compose.dev.yml" down -v
docker compose -f "%~dp0docker-compose.dev.yml" up -d
echo Dev database reset complete.
