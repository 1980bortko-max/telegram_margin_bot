@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PID_FILE=.bot.pid

:: Stop bot via PID file
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    if defined OLD_PID (
        tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
        if !errorlevel! == 0 (
            echo Stopping Telegram bot (PID !OLD_PID!)...
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

del ".bot.lock" 2>nul

:: Stop chromedriver
taskkill /F /IM chromedriver.exe /T >nul 2>&1

echo.
echo Bot stopped.
pause
