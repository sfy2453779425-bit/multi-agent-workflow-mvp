@echo off
setlocal
cd /d "%~dp0..\.."

set /p GPU_HOST=Enter GPU server host or IP:
if "%GPU_HOST%"=="" (
  echo GPU server host is required.
  pause
  exit /b 1
)

set /p GPU_PORT=Enter SSH port:
if "%GPU_PORT%"=="" (
  echo SSH port is required.
  pause
  exit /b 1
)

set /p GPU_USER=Enter GPU user:
if "%GPU_USER%"=="" (
  echo GPU user is required.
  pause
  exit /b 1
)

set "OUT_DIR=_local_artifacts\gpu_results\final_base_benchmark"
if not exist "_local_artifacts" mkdir "_local_artifacts"
if not exist "_local_artifacts\gpu_results" mkdir "_local_artifacts\gpu_results"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo.
echo Downloading final base benchmark results...
echo Remote: ~/gpu_llm/results/final_base_benchmark/*
echo Local:  %CD%\%OUT_DIR%
echo You will be asked for the server password.
echo.

scp -P "%GPU_PORT%" -r "%GPU_USER%@%GPU_HOST%:~/gpu_llm/results/final_base_benchmark/*" "%OUT_DIR%\"
if errorlevel 1 (
  echo.
  echo Download failed. Check whether run_final_base_benchmark.cmd finished successfully.
  pause
  exit /b 1
)

echo.
echo Results saved to:
echo %CD%\%OUT_DIR%
pause
