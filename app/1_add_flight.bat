@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
echo ADD FLIGHT (flights.py add)
echo.
%PY% flights.py add
echo.
pause
