@echo off
:: Load sample data into an EMPTY dev database through the running dev backend (see seed_dev.py)
python "%~dp0seed_dev.py" %*
