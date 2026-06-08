@echo off
setlocal
cd /d "%~dp0..\.."

set /p GPU_HOST=Enter GPU server host or IP:
set /p GPU_PORT=Enter SSH port:
set /p GPU_USER=Enter GPU user:
set /p MODEL=Model [Qwen/Qwen2.5-1.5B-Instruct]:
if "%MODEL%"=="" set MODEL=Qwen/Qwen2.5-1.5B-Instruct

echo.
echo Starting Local LLM API server on GPU.
echo Keep this window open while testing the remote node.
echo You will be asked for the server password.
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% "cd ~/gpu_llm && source .venv/bin/activate && MODEL='%MODEL%' bash run_local_llm_api_server.sh"

echo.
echo GPU API server stopped.
pause
