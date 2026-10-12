@echo off
cd /d "%~dp0..\backend" && uv run pytest -v %*
