@echo off
cd /d "%~dp0..\.."
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
  "%BUNDLED%" -m unittest discover -s "tests"
) else (
  python -m unittest discover -s "tests"
)
