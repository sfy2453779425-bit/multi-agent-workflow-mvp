@echo off
setlocal
cd /d "%~dp0..\.."

set /p GPU_HOST=Enter GPU server host or IP:
set /p GPU_PORT=Enter SSH port:
set /p GPU_USER=Enter GPU user:

echo.
echo Opening SSH tunnel:
echo   local http://127.0.0.1:9100 -> GPU http://127.0.0.1:9100
echo Keep this window open while testing the remote node.
echo You will be asked for the server password.
ssh -p %GPU_PORT% -L 9100:127.0.0.1:9100 %GPU_USER%@%GPU_HOST%

echo.
echo SSH tunnel closed.
pause
