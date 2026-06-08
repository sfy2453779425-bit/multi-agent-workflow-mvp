@echo off
setlocal
cd /d "%~dp0\..\.."

if not exist "_local_artifacts\gpu_results\gpu_v2_lora_results" mkdir "_local_artifacts\gpu_results\gpu_v2_lora_results"

echo Downloading V2 LoRA comparison outputs...
echo You will be asked for the server password. Do not save it in this file.
set /p SERVER_HOST=Enter GPU server host or IP:
set /p SERVER_PORT=Enter SSH port:
set /p SERVER_USER=Enter GPU user:

scp -P %SERVER_PORT% -r %SERVER_USER%@%SERVER_HOST%:~/gpu_llm/results/v2_lora_comparison/* _local_artifacts\gpu_results\gpu_v2_lora_results\

echo.
echo Results saved to:
echo %CD%\_local_artifacts\gpu_results\gpu_v2_lora_results
pause
