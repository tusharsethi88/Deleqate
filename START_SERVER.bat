@echo off
title Deleqate SUGGESTION Test Server (port 8061)
cd /d "%~dp0"

REM --- auto-detect Python (py launcher, then python on PATH, then common paths) ---
set "PYTHON="
where py >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON ( where python >nul 2>&1 && set "PYTHON=python" )
if not defined PYTHON ( if exist "C:\Python314\python.exe" set "PYTHON=C:\Python314\python.exe" )
if not defined PYTHON (
    echo [ERROR] Python was not found. Install it from https://www.python.org/downloads/
    echo During install, tick "Add python.exe to PATH", then re-run this script.
    pause
    exit /b 1
)
echo [OK] Using Python: %PYTHON%

echo.
echo ============================================
echo  Deleqate - Starting Local Server
echo ============================================
echo.

:: Check if Django is installed; if not, install from backend/requirements.txt
"%PYTHON%" -c "import django" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Django not found. Installing backend requirements...
    echo This only happens once.
    echo.
    "%PYTHON%" -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] pip install failed. Check internet connection.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Requirements installed.
)

echo [OK] Running database migrations...
cd backend
"%PYTHON%" manage.py migrate --run-syncdb >nul 2>&1
echo [OK] Migrations done.
echo.
echo [OK] Starting Django on http://127.0.0.1:8061
echo  Open Chrome: http://127.0.0.1:8061
echo  Press Ctrl+C to stop.
echo.

"%PYTHON%" manage.py runserver 127.0.0.1:8061

pause
