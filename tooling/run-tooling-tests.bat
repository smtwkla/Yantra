@echo off
:: Tests of the tooling scripts (tooling\tests: deploy.py, S025). pytest and python-dotenv are
:: fetched by uv (not locked); the tests use no network, fetching them needs it once on a cold uv cache.
cd /d "%~dp0.." && uv run --no-project --with "pytest>=8,<10" --with python-dotenv pytest tooling\tests %*
exit /b %ERRORLEVEL%
