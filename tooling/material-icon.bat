@echo off
:: Download Material Symbols icons into the frontend: material-icon.bat table_edit [more names] [options]
:: Options (--style, --weight, --fill/--no-fill, --grade, --size, --force): see tooling\common\material_icon.py
cd /d "%~dp0.."
uv run tooling\common\material_icon.py --out frontend\src\assets\icons %*
exit /b %ERRORLEVEL%
