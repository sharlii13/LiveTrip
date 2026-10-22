@echo off
rem Starts the LiveTrip website on http://localhost:5173 (run start-backend.cmd too)
cd /d "%~dp0frontend"
if not exist node_modules call npm.cmd install
call npm.cmd run dev
pause
