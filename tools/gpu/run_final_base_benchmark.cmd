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

set "MODEL=Qwen/Qwen2.5-1.5B-Instruct"

echo.
echo Running final base benchmark on GPU server.
echo Model: %MODEL%
echo Output: ~/gpu_llm/results/final_base_benchmark
echo You will be asked for the server password.
echo.

ssh -p "%GPU_PORT%" "%GPU_USER%@%GPU_HOST%" "cd ~/gpu_llm && if [ ! -f benchmark_llm.py ]; then echo 'ERROR: ~/gpu_llm/benchmark_llm.py not found. Upload the GPU experiment package first.'; exit 1; fi && source .venv/bin/activate && mkdir -p results/final_base_benchmark && python benchmark_llm.py --model Qwen/Qwen2.5-1.5B-Instruct --output-dir results/final_base_benchmark && echo && echo Latest final benchmark files: && ls -1t results/final_base_benchmark | head -n 6"
if errorlevel 1 (
  echo.
  echo Final base benchmark failed.
  pause
  exit /b 1
)

echo.
echo Final base benchmark finished on the GPU server.
echo Next: run tools\gpu\download_final_base_benchmark.cmd
pause
