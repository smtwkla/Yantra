@echo off
:: Start the dev MariaDB container (creates DB, user and test DB on first run)
docker compose -f "%~dp0docker-compose.dev.yml" up -d
