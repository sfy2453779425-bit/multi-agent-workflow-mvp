@echo off
setlocal
cd /d "%~dp0..\.."

if not exist "_local_artifacts\gpu_results\gpu_lora_outputs" mkdir "_local_artifacts\gpu_results\gpu_lora_outputs"

echo Downloading LoRA training outputs...
echo You will be asked for the server password. Do not save it in this file.
set /p SERVER_HOST=Enter GPU server host or IP:
set /p SERVER_PORT=Enter SSH port:
set /p SERVER_USER=Enter GPU user:
scp -r -P %SERVER_PORT% %SERVER_USER%@%SERVER_HOST%:~/gpu_llm/lora_outputs/* .\_local_artifacts\gpu_results\gpu_lora_outputs\

echo.
echo Results saved to:
echo %CD%\_local_artifacts\gpu_results\gpu_lora_outputs
pause
