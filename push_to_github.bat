@echo off
set "GIT_EXE=C:\Users\LENOVO\AppData\Local\Programs\PortableGit\cmd\git.exe"
set "PATH=C:\Users\LENOVO\AppData\Local\Programs\PortableGit\cmd;C:\Users\LENOVO\AppData\Local\Programs\PortableGit\usr\bin;%PATH%"
cd /d "D:\Upload_To_GitHub"

echo ===================================================
echo   Uploading MoneyPrinter Pro Updates to GitHub
echo ===================================================
echo.

"%GIT_EXE%" config user.name "abdou25008-coder"
"%GIT_EXE%" config user.email "abdou25008@users.noreply.github.com"
"%GIT_EXE%" config credential.helper manager
"%GIT_EXE%" remote remove origin 2>nul
"%GIT_EXE%" remote add origin https://github.com/abdou25008-coder/MoneyPrinter-Pro.git
"%GIT_EXE%" branch -M main

echo Staging files...
"%GIT_EXE%" add -A
"%GIT_EXE%" commit -m "feat: MoneyPrinter Pro v2.0 update" 2>nul

echo.
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