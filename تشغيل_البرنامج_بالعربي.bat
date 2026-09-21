@echo off
chcp 65001 >nul
title تشغيل MoneyPrinterTurbo - النسخة المعربة بنمط inVideo
echo =====================================================================
echo       مرحباً بك في MoneyPrinterTurbo (النسخة المعربة بنمط inVideo)
echo =====================================================================
echo.

set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"
set "PYTHONPATH=%CURRENT_DIR%"

echo [1/4] جاري فحص بيئة بايثون (Python)...

set "PY_EXE="

:: 1. Check local virtual environment
if exist "%CURRENT_DIR%\.venv\Scripts\python.exe" (
    set "PY_EXE=%CURRENT_DIR%\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

:: 2. Check system python
for %%P in (python3.exe python.exe py.exe) do (
    where %%P >nul 2>nul
    if not errorlevel 1 (
        %%P -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
        if not errorlevel 1 (
            set "PY_EXE=%%P"
            goto :SETUP_VENV
        )
    )
)

:: 3. Check common Python installation paths
for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%D (
        set "PY_EXE=%%~D"
        goto :SETUP_VENV
    )
)

:: 4. If Python is not found, install via winget
echo.
echo [!] لم يتم العثور على بايثون في جهازك.
echo [*] جاري محاولة تثبيت بايثون 3.11 تلقائياً عبر Windows Package Manager (winget)...
where winget >nul 2>nul
if not errorlevel 1 (
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    echo.
    echo [*] اكتمل تثبيت بايثون! يرجى إعادة تشغيل هذا الملف لتحديث متغيرات البيئة.
    pause
    exit /b 0
) else (
    echo [X] لم يتم العثور على winget. يرجى تثبيت Python 3.11 يدوياً من:
    echo     https://www.python.org/downloads/
    pause
    exit /b 1
)

:SETUP_VENV
echo [*] تم العثور على بايثون: %PY_EXE%
if not exist "%CURRENT_DIR%\.venv\Scripts\python.exe" (
    echo [2/4] جاري إنشاء البيئة الافتراضية (.venv)...
    "%PY_EXE%" -m venv "%CURRENT_DIR%\.venv"
)
set "PY_EXE=%CURRENT_DIR%\.venv\Scripts\python.exe"

:PYTHON_FOUND
echo [*] بايثون جاهز في البيئة: %PY_EXE%

echo [3/4] جاري التحقق من تثبيت مكتبات المشروع ومتطلبات اللغة العربية...
"%PY_EXE%" -m pip install --upgrade pip -q
"%PY_EXE%" -m pip install -r "%CURRENT_DIR%\requirements.txt" -q

:: Set default language in config.toml to Arabic if not configured
if not exist "%CURRENT_DIR%\config.toml" (
    if exist "%CURRENT_DIR%\config.example.toml" (
        copy /y "%CURRENT_DIR%\config.example.toml" "%CURRENT_DIR%\config.toml" >nul
    )
)

echo [4/4] جاري بدء تشغيل الخادم وفتح الواجهة العربية...
echo.
echo =====================================================================
echo  رابط الواجهة المحلي:  http://localhost:8501
echo =====================================================================
echo.

:: Open browser automatically after 2 seconds
start "" powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8501'"

"%PY_EXE%" -m streamlit run "%CURRENT_DIR%\webui\Main.py" --server.port 8501 --server.address 127.0.0.1

pause
