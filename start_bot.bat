@echo off
cd /d "%~dp0"

if exist ".bot.pid" (
    for /f %%i in (.bot.pid) do taskkill /PID %%i /T /F >/dev/null 2>&1
    del ".bot.pid" 2>nul
)

del ".bot.lock" 2>nul
taskkill /F /IM chromedriver.exe /T >/dev/null 2>&1

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment .venv not found.
    echo.
    echo Run first:
    echo   python -m venv .venv
    echo   .venv\Scripts\python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Starting Telegram bot...
echo.
.venv\Scripts\python bot.py

echo.
echo Bot stopped.
pause
