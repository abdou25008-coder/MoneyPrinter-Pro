@echo off
setlocal
title MoneyPrinter PRO - Local Server

set "PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"
set "PYTHONPATH=%APP_DIR%"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%LOCALAPPDATA%\Programs\Python\Python311;%PATH%"

cls
echo ======================================================================
echo           MoneyPrinter PRO - Local Superfast Server
echo ======================================================================
echo.

if not exist "%PYTHON_PATH%" (
    echo [ERROR] Python 3.11 not found at: %PYTHON_PATH%
    echo.
    pause
    exit /b 1
)

if not exist "%APP_DIR%\webui\Main.py" (
    echo [ERROR] Project files not found at: %APP_DIR%
    echo.
    pause
    exit /b 1
)

echo [1/2] Checking local environment and FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [NOTE] FFmpeg fallback active.
) else (
    echo [OK] FFmpeg engine is ready and accelerated!
)

echo [2/2] Starting Streamlit Local WebUI...
echo.
echo ======================================================================
echo   Local WebUI is starting!
echo   Opening in your default browser: http://127.0.0.1:8501
echo   (Keep this window open while using the application)
echo ======================================================================
echo.

"%PYTHON_PATH%" -m streamlit run webui\Main.py --server.port 8501 --server.address 127.0.0.1 --server.headless false

echo.
echo Application stopped.
pause