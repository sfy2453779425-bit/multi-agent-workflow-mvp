@echo off
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
  "%BUNDLED%" "%~dp0builder_demo.py" --all
) else (
  python "%~dp0builder_demo.py" --all
)
