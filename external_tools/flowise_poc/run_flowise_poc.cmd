@echo off
cd /d "%~dp0"
echo Starting Flowise at http://127.0.0.1:3100
echo Login: admin / admin
echo This uses pinned npx package: flowise@3.1.2
echo.
call npm run start
