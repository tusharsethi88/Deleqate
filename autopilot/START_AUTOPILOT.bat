@echo off
title Deleqate AutoPilot

:: Change to the project directory
cd /d "%~dp0.."

echo.
echo ============================================
echo  Deleqate AutoPilot - Starting...
echo ============================================
echo.

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] No virtual environment ^(venv^) found.
    echo Please run autopilot\INSTALL.bat first.
    echo.
    pause
    exit /b 1
)

:: Check .env exists
if not exist "autopilot\.env" (
    echo [ERROR] autopilot\.env not found!
    echo Please copy autopilot\.env.template to autopilot\.env and fill in credentials.
    echo.
    pause
    exit /b 1
)

echo [OK] Environment ready
echo ============================================
echo  Agent email:  ^(See autopilot\.env^)
echo  Platform:     http://localhost:5051
echo  Logs:         autopilot\logs\agent.log
echo ============================================
echo.
echo  Press Ctrl+C to stop the agent gracefully.
echo.

:: Run the agent
set PYTHONIOENCODING=utf-8
python -m autopilot.agent

echo.
echo  AutoPilot stopped.
pause
