@echo off
cd /d "%~dp0"

if exist ".bot.pid" (
    for /f %%i in (.bot.pid) do taskkill /PID %%i /T /F >nul 2>&1
    del ".bot.pid" 2>nul
)

del ".bot.lock" 2>nul
taskkill /F /IM chromedriver.exe /T >nul 2>&1

echo.
echo Bot stopped.
pause
