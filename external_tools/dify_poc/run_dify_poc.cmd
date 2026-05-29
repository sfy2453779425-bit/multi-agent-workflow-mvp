@echo off
echo Dify PoC requires Docker Desktop / Docker Compose.
echo.
docker --version
if errorlevel 1 (
  echo Docker is not available on this machine.
  echo See README.md for the official setup steps.
  pause
  exit /b 1
)
docker compose version
if errorlevel 1 (
  echo Docker Compose is not available on this machine.
  echo See README.md for the official setup steps.
  pause
  exit /b 1
)
echo Docker is available. Follow README.md to clone and run Dify.
pause
