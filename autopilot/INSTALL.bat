@echo off
title Deleqate AutoPilot - Setup

cd /d "%~dp0.."

echo.
echo ============================================
echo  Deleqate AutoPilot Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install from https://python.org ^(3.11+^)
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found
python --version
echo.

:: Create virtual environment if needed
if not exist "venv" (
    echo [SETUP] Creating virtual environment ^(venv^)...
    python -m venv venv
)
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment ready
echo.

:: Install/upgrade pip
echo [SETUP] Upgrading pip...
python -m pip install --upgrade pip -q

:: Install core dependencies
echo [SETUP] Installing core dependencies...
pip install flask>=3.0 flask-login>=0.6 werkzeug>=3.0 python-dotenv>=1.0 requests>=2.31 itsdangerous>=2.1 gunicorn>=21.2 -q
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install core dependencies.
    pause
    exit /b 1
)
echo [OK] Core dependencies installed

:: Install AutoPilot dependencies
echo [SETUP] Installing AutoPilot dependencies...
pip install playwright>=1.40 rembg pillow reportlab python-docx schedule -q
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install AutoPilot dependencies.
    pause
    exit /b 1
)
echo [OK] AutoPilot dependencies installed

:: Install Playwright browsers (Chromium)
echo [SETUP] Installing Chromium for browser automation...
playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Chromium.
    pause
    exit /b 1
)
echo [OK] Chromium installed

:: Create .env from template if not exists
if not exist "autopilot\.env" (
    echo.
    echo [SETUP] Creating autopilot\.env from template...
    copy "autopilot\.env.template" "autopilot\.env"
    echo.
    echo ============================================
    echo  *** ACTION REQUIRED ***
    echo ============================================
    echo  Open autopilot\.env and fill in:
    echo    1. AUTOPILOT_EMAIL
    echo    2. AUTOPILOT_APP_PASSWORD
    echo    3. AUTOPILOT_PILOT_PASSWORD
    echo    4. AUTOPILOT_API_TOKEN
    echo ============================================
) else (
    echo [OK] autopilot\.env already exists
)

:: Create directories
if not exist "autopilot\logs" mkdir "autopilot\logs"
if not exist "autopilot\downloads" mkdir "autopilot\downloads"
if not exist "autopilot\outputs" mkdir "autopilot\outputs"
echo [OK] Directories created

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo  Next steps:
echo    1. Edit autopilot\.env with your credentials
echo    2. Create pilot account in Deleqate admin (if not done)
echo    3. Run autopilot\START_AUTOPILOT.bat to launch the agent
echo.
pause
