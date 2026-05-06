@echo off
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
  "%BUNDLED%" "%~dp0baseline_traditional.py"
) else (
  python "%~dp0baseline_traditional.py"
)
