@echo off
setlocal
:: Backend tests (pytest). Needs the dev DB container (tooling\dev\dev-db-up.bat).
:: The migration upgrade tests (S025) use vel_yantra_upgrade: created here as root, with its
:: grant, on a container that predates it (the dev root password is from the compose file).
:: The tests drop and recreate it themselves.
set COMPOSE=docker compose -f "%~dp0dev\docker-compose.dev.yml"
%COMPOSE% exec -T mariadb mariadb -uroot -pdev-root-password -e "CREATE DATABASE IF NOT EXISTS vel_yantra_upgrade CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON vel_yantra_upgrade.* TO 'vel_yantra_master'@'%%'; FLUSH PRIVILEGES;"
if errorlevel 1 (
  echo Could not create the upgrade test database vel_yantra_upgrade. Is the dev DB up? tooling\dev\dev-db-up.bat
  exit /b 1
)
cd /d "%~dp0..\backend" && uv run pytest -v %*
