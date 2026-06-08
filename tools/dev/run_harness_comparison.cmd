@echo off
setlocal
cd /d "%~dp0..\.."

set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" "experiments\harness_comparison.py"

echo.
echo Report:
echo outputs\harness_comparison\harness_comparison_report_zh.md
echo outputs\harness_comparison\harness_comparison_report_kr.md
pause
