@echo off
:: Tests of the dependency audit (tooling\deps). pytest is fetched by uv (not locked);
:: the tests use no network, fetching pytest needs it once on a cold uv cache.
cd /d "%~dp0.." && uv run --no-project --with "pytest>=8,<10" pytest tooling\deps\tests %*
exit /b %ERRORLEVEL%
