@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PID_FILE=.bot.pid
set LOCK_FILE=.bot.lock

:: Stop existing bot via PID file
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    if defined OLD_PID (
        tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
        if !errorlevel! == 0 (
            echo Stopping existing Telegram bot (PID !OLD_PID!)...
            taskkill /PID !OLD_PID! /T /F >nul 2>&1
            timeout /t 1 /nobreak >nul
        )
    )
    del "%PID_FILE%" 2>nul
)

:: Fallback: stop any python process running bot.py
for /f "tokens=1" %%i in ('wmic process where "name='python.exe' and commandline like '%%bot.py%%'" get processid 2^>nul ^| findstr /r "^[0-9]"') do (
    echo Stopping leftover bot process (PID %%i)...
    taskkill /PID %%i /T /F >nul 2>&1
)

del "%LOCK_FILE%" 2>nul

:: Stop leftover chromedriver
taskkill /F /IM chromedriver.exe /T >nul 2>&1

:: Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Virtual environment .venv not found.
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
