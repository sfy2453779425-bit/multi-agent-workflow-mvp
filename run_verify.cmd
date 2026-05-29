@echo off
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
  "%BUNDLED%" "%~dp0verify_project.py"
) else (
  python "%~dp0verify_project.py"
)
pause
