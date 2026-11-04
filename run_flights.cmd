@echo off
cd /d "%~dp0"
python scripts\run_flights.py %*
exit /b %ERRORLEVEL%
