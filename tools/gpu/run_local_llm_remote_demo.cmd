@echo off
setlocal
cd /d "%~dp0..\.."
echo Running workflow with remote Local LLM Node config.
echo If the GPU API is not reachable, the config falls back to mock output.
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.remote.example.json --user user_a "Seoul tomorrow casual outfit recommendation"
pause
