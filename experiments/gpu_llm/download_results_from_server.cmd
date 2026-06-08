@echo off
setlocal
cd /d "%~dp0..\.."

if not exist "_local_artifacts\gpu_results\gpu_llm_results" mkdir "_local_artifacts\gpu_results\gpu_llm_results"

echo Downloading GPU experiment results...
echo You will be asked for the server password. Do not save it in this file.
set /p SERVER_HOST=Enter GPU server host or IP:
set /p SERVER_PORT=Enter SSH port:
set /p SERVER_USER=Enter GPU user:
scp -P %SERVER_PORT% %SERVER_USER%@%SERVER_HOST%:~/gpu_llm/results/* .\_local_artifacts\gpu_results\gpu_llm_results\

echo.
echo Results saved to:
echo %CD%\_local_artifacts\gpu_results\gpu_llm_results
pause
