@echo off
set "APP=%~dp0desktop_app.py"
set "BUNDLEDW=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLEDW%" (
  start "" "%BUNDLEDW%" "%APP%"
) else if exist "%BUNDLED%" (
  start "" "%BUNDLED%" "%APP%"
) else (
  start "" pythonw "%APP%"
)
