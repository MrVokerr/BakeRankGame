@echo off
title BakeRank - Build EXE
cd /d "%~dp0"
color 0E

echo ========================================
echo   BakeRank Bot - EXE Builder
echo ========================================
echo.
echo This will create a standalone .exe file
echo that works without Python installed!
echo.
echo Building executable...
echo.

REM Try py launcher first
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using py launcher...
    py -m PyInstaller --clean --noconfirm --onefile --windowed --name "BakeRankBot" --icon=NONE ^
        --add-data "overlay;overlay" ^
        --hidden-import "twitchio" ^
        --hidden-import "twitchio.ext.commands" ^
        --hidden-import "websockets" ^
        --hidden-import "PyQt5" ^
        bakerank_gui.py
    goto :build_complete
)

REM Try python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using python...
    python -m PyInstaller --clean --noconfirm --onefile --windowed --name "BakeRankBot" --icon=NONE ^
        --add-data "overlay;overlay" ^
        --hidden-import "twitchio" ^
        --hidden-import "twitchio.ext.commands" ^
        --hidden-import "websockets" ^
        --hidden-import "PyQt5" ^
        bakerank_gui.py
    goto :build_complete
)

echo ========================================
echo ERROR: Python not found!
echo ========================================
echo.
echo Please install Python or run:
echo   py -m pip install pyinstaller
echo.
pause
exit /b 1

:build_complete
echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Copying overlay folder to dist...
xcopy /E /I /Y "overlay" "dist\overlay"
if errorlevel 1 (
    echo ERROR: Failed to copy overlay folder to dist!
    echo Please make sure the 'overlay' folder exists and try again.
    pause
    exit /b 1
)
echo.
echo Your executable is in the 'dist' folder:
echo   dist\BakeRankBot.exe
echo.
echo The 'overlay' folder has been copied there too!
echo.
echo You can distribute the entire 'dist' folder content.
echo.
echo No Python required for users!
echo.
pause
