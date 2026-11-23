@echo off
:: Read-only SQL against PRODUCTION (tooling\dev\prod_query.py): the PROD_RO_DB_* user of backend\secrets_app.py,
:: refused unless it holds only SELECT. No argument: the probe, then a prompt. --file <path>: SQL from a file,
:: relative to the caller's folder (the repo root from Claude Code).
uv run --project "%~dp0..\backend" python "%~dp0dev\prod_query.py" %*
