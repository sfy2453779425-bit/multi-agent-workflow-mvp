@echo off
setlocal
cd /d "%~dp0..\.."

set "PACKAGE_PATH=_local_artifacts\gpu_packages\gpu_llm_api_update.zip"

if not exist "%PACKAGE_PATH%" (
  echo Missing gpu_llm_api_update.zip.
  echo Expected: %CD%\%PACKAGE_PATH%
  echo Ask Codex to regenerate the GPU API update package.
  pause
  exit /b 1
)

set /p GPU_HOST=Enter GPU server host or IP:
set /p GPU_PORT=Enter SSH port:
set /p GPU_USER=Enter GPU user:

echo.
echo Uploading gpu_llm_api_update.zip...
echo You will be asked for the server password.
scp -P %GPU_PORT% "%PACKAGE_PATH%" %GPU_USER%@%GPU_HOST%:~/gpu_llm_api_update.zip
if errorlevel 1 (
  echo Upload failed.
  pause
  exit /b 1
)

echo.
echo Installing update into ~/gpu_llm on the GPU server...
echo You may be asked for the server password again.
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% "cd ~ && rm -rf gpu_llm_api_update && mkdir -p gpu_llm_api_update && python3 -m zipfile -e gpu_llm_api_update.zip gpu_llm_api_update && mkdir -p gpu_llm && cp -f gpu_llm_api_update/* gpu_llm/ && ls -1 gpu_llm/local_llm_api_server.py gpu_llm/run_local_llm_api_server.sh gpu_llm/smoke_local_llm_api.py"
if errorlevel 1 (
  echo Remote install failed.
  pause
  exit /b 1
)

echo.
echo GPU API update uploaded and installed.
pause
