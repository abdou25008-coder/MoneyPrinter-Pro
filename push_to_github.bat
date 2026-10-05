@echo off
set "GIT_EXE=C:\Users\LENOVO\AppData\Local\Programs\PortableGit\cmd\git.exe"
set "PATH=C:\Users\LENOVO\AppData\Local\Programs\PortableGit\cmd;C:\Users\LENOVO\AppData\Local\Programs\PortableGit\usr\bin;%PATH%"
cd /d "D:\Upload_To_GitHub"

echo ===================================================
echo   Uploading MoneyPrinter Pro Updates to GitHub
echo ===================================================
echo.

"%GIT_EXE%" branch -M main
"%GIT_EXE%" add -A
"%GIT_EXE%" commit -m "feat: MoneyPrinter Pro updates" 2>nul
echo Pushing to GitHub...
"%GIT_EXE%" push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===================================================
    echo   SUCCESS! All updates pushed to GitHub!
    echo ===================================================
) else (
    echo.
    echo Push completed or error occurred. Code: %ERRORLEVEL%
)

echo.
pause