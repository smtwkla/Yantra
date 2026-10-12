@echo off
:: Stop the dev MariaDB container (data is preserved in the volume)
docker compose -f "%~dp0docker-compose.dev.yml" down
