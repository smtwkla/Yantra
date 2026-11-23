@echo off
:: SQL against the dev DB (vel_yantra_master on 3307, config.DB_CONFIG), the same tool as run-prod-query.bat.
:: FLASK_DEBUG=1 lets config fall back to example_secrets_app.py when secrets_app.py is missing.
:: Runs in the caller's folder, so a --file path is relative to it (the repo root from Claude Code).
setlocal
set "FLASK_DEBUG=1"
uv run --project "%~dp0..\backend" python "%~dp0dev\prod_query.py" --dev %*
