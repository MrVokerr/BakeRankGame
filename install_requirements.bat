@echo off
title BakeRank - Install Requirements
cd /d "%~dp0"
color 0B

echo ========================================
echo   BakeRank Bot - Dependency Installer
echo ========================================
echo.

REM Try using 'py' launcher first (most reliable on Windows)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python detected via py launcher:
    py --version
    echo.
    echo Installing packages...
    echo.
    py -m pip install --upgrade pip
    py -m pip install twitchio==2.9.1
    py -m pip install websockets
    py -m pip install PyQt5
    py -m pip install pyinstaller
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    py -m pip show twitchio websockets PyQt5 pyinstaller
    echo.
    echo You can now run bakerank_bot.py
    echo.
    pause
    exit /b 0
)

REM If py launcher doesn't work, try python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python detected:
    python --version
    echo.
    echo Installing packages...
    echo.
    python -m pip install --upgrade pip
    python -m pip install twitchio==2.9.1
    python -m pip install websockets
    python -m pip install PyQt5
    python -m pip install pyinstaller
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    python -m pip show twitchio websockets PyQt5 pyinstaller
    echo.
    echo You can now run bakerank_bot.py
    echo.
    pause
    exit /b 0
)

REM If nothing works, show error
echo ========================================
echo ERROR: Python not found!
echo ========================================
echo.
echo Python is not recognized. Please either:
echo.
echo 1. Reinstall Python and check "Add to PATH"
echo    Download: https://www.python.org/downloads/
echo.
echo 2. Or manually run in PowerShell:
echo    where.exe python
echo.
echo Then copy the path and run:
echo    "C:\path\to\python.exe" -m pip install twitchio==2.9.1 websockets
echo.
pause
