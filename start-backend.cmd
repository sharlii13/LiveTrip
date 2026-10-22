@echo off
rem Starts the LiveTrip backend on http://localhost:8000 (double-click, or run from any folder)
cd /d "%~dp0Backend\Backend\app"
set PYTHONUTF8=1
python -m uvicorn main:app --port 8000
pause
