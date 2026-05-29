@echo off
cd /d "%~dp0"
echo Langflow PoC
echo.
echo This will install and run langflow==1.9.4.
echo If installation is slow, use this only for external-tool screenshots.
echo.
python -m pip install "langflow==1.9.4"
python -m langflow run --host 127.0.0.1 --port 7860
