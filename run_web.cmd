@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

echo Starting visual Builder frontend...
echo URL: http://127.0.0.1:8000
echo Keep this window open. Close this window to stop the server.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
"%PYTHON_EXE%" "%~dp0web_app.py" 8000

echo.
echo Server stopped.
pause
