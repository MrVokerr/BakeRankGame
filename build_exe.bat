@echo off
title BakeRank - Build EXE
cd /d "%~dp0"
color 0E

echo ========================================
echo   BakeRank Bot - EXE Builder
echo ========================================
echo.
echo Cleaning up previous builds...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "BakeRankBot.spec" del "BakeRankBot.spec"
if exist "BakeRankBot.exe" (
    del "BakeRankBot.exe"
    if exist "BakeRankBot.exe" (
        echo.
        echo ERROR: Cannot delete BakeRankBot.exe. Is it still running?
        echo Please close the bot and try again.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Building executable...
echo.

REM Check for icon
set "ICON_PARAM=--icon=NONE"
if exist "exe_icon.ico" (
    echo Found custom icon: exe_icon.ico
    set "ICON_PARAM=--icon=exe_icon.ico"
) else (
    echo No exe_icon.ico found in root folder. Using default icon.
)

REM Try py launcher first
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using py launcher...
    py -m PyInstaller --clean --noconfirm --onefile --windowed --name "BakeRankBot" %ICON_PARAM% ^
        --hidden-import "twitchio" ^
        --hidden-import "twitchio.ext.commands" ^
        --hidden-import "websockets" ^
        --hidden-import "PyQt5" ^
        --hidden-import "aiohttp" ^
        bakerank_gui.py
    goto :move_exe
)

REM Try python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using python...
    python -m PyInstaller --clean --noconfirm --onefile --windowed --name "BakeRankBot" %ICON_PARAM% ^
        --hidden-import "twitchio" ^
        --hidden-import "twitchio.ext.commands" ^
        --hidden-import "websockets" ^
        --hidden-import "PyQt5" ^
        --hidden-import "aiohttp" ^
        bakerank_gui.py
    goto :move_exe
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

:move_exe
echo.
echo Moving executable to root folder...
if exist "dist\BakeRankBot.exe" (
    move /Y "dist\BakeRankBot.exe" "%~dp0BakeRankBot.exe"
    echo.
    echo Cleaning up build folders...
    if exist "build" rd /s /q "build"
    if exist "dist" rd /s /q "dist"
    if exist "BakeRankBot.spec" del "BakeRankBot.spec"
    
    echo.
    echo ========================================
    echo   Build Complete!
    echo ========================================
    echo.
    echo BakeRankBot.exe is ready in this folder:
    echo %~dp0
    echo.
    echo Press any key to close...
) else (
    echo.
    echo ERROR: Build failed! No EXE found in dist folder.
    echo.
)
pause >nul
