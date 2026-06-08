@echo off
setlocal
cd /d "%~dp0..\.."

echo Testing Local LLM API through http://127.0.0.1:9100/generate ...
python experiments\gpu_llm\smoke_local_llm_api.py --endpoint http://127.0.0.1:9100/generate
if errorlevel 1 (
  echo.
  echo Smoke test failed. Check that:
  echo 1. start_gpu_local_llm_api.cmd is still running.
  echo 2. open_gpu_local_llm_tunnel.cmd is still running.
  echo 3. The GPU server allowed the SSH tunnel.
  pause
  exit /b 1
)

echo.
echo Running Builder Workflow with remote Local LLM Node...
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.remote.example.json --user user_a "Seoul tomorrow casual outfit recommendation"
pause
