@echo off
setlocal
cd /d "%~dp0..\.."

echo Running workflow with replayed GPU result.
echo This does not require SSH, API server, or a live GPU connection.
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.replay.json --user user_a "Seoul tomorrow casual outfit recommendation"
pause
