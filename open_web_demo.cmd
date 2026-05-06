@echo off
setlocal
set "ROOT=%~dp0"
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED%" (
  set "PYTHON=%BUNDLED%"
) else (
  set "PYTHON=python"
)

start "Template Agent Web Server" /min "%PYTHON%" "%ROOT%web_app.py" 8000
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
endlocal
