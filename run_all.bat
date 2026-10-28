@echo off
setlocal enabledelayedexpansion

title Dhwani / EchoShield AI - Enterprise Launcher

:: Guarantee execution from the script's directory
cd /d "%~dp0"

echo =====================================================================
echo           DHWANI / ECHOSHIELD AI - ENTERPRISE CONTROL PLATFORM
echo       AI-Powered Real-Time Voice Cloning Detection ^& Prevention
echo =====================================================================
echo.

:: 1. Check Virtual Environment
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv\
    echo.
    echo To initialize the environment, run:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: 2. Check Node.js and npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm not found in system PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

:: 3. Configure Root Backend .env if missing
if not exist "%~dp0.env" (
    echo [*] Creating synchronized root .env configuration...
    (
        echo # ==============================================================================
        echo # Dhwani / EchoShield AI - Local Development Configuration
        echo # ==============================================================================
        echo DHWANI_API_KEY=dhwani-local-dev-key-2026
        echo DHWANI_AUTH_REQUIRED=false
        echo DHWANI_BACKEND_URL=http://127.0.0.1:8000
        echo PORT=8000
        echo DHWANI_DEMO_MODE=true
        echo DHWANI_RETAIN_AUDIO=false
        echo.
        echo # Twilio Telephony Stream Configuration (Optional - configure if using live PSTN)
        echo TWILIO_ACCOUNT_SID=
        echo TWILIO_AUTH_TOKEN=
        echo TWILIO_PHONE_NUMBER=
        echo TWILIO_STREAM_PUBLIC_URL=
    ) > "%~dp0.env"
    echo [OK] Created root .env successfully.
)

:: 4. Configure Frontend .env.local if missing
if not exist "%~dp0frontend\.env.local" (
    echo [*] Creating synchronized frontend\.env.local configuration...
    (
        echo # ==============================================================================
        echo # Dhwani Next.js Frontend - Local Interconnect Configuration
        echo # ==============================================================================
        echo DHWANI_BACKEND_URL=http://127.0.0.1:8000
        echo DHWANI_API_KEY=dhwani-local-dev-key-2026
        echo NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/ws/dashboard
        echo DHWANI_DEMO_MODE=true
    ) > "%~dp0frontend\.env.local"
    echo [OK] Created frontend\.env.local successfully.
)

:: 5. Check Frontend Dependencies
if not exist "%~dp0frontend\node_modules" (
    echo [*] Frontend dependencies not found. Installing npm packages (this may take a minute)...
    pushd "%~dp0frontend"
    call npm install
    popd
    echo [OK] Frontend packages installed.
)

:: 6. Check Port Availability
netstat -ano | findstr /R ":8000[ ]" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Port 8000 is already in use by another process.
    echo If Dhwani backend is already running, you can access it directly.
)

netstat -ano | findstr /R ":3000[ ]" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Port 3000 is in use; Next.js will automatically select the next free port (e.g. 3001).
)

echo.
echo [*] Starting Dhwani AI FastAPI Backend on http://127.0.0.1:8000 ...
start "Dhwani AI Backend [Port 8000]" cmd /k "title Dhwani AI Backend && color 0A && cd /d "%~dp0" && call "%~dp0.venv\Scripts\activate.bat" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo [*] Starting Dhwani Cyber Dashboard on http://localhost:3000 ...
start "Dhwani Cyber Dashboard [Port 3000]" cmd /k "title Dhwani Cyber Dashboard && color 0B && cd /d "%~dp0frontend" && npm run dev"

echo.
echo =====================================================================
echo                   SERVICES ARE STARTING UP
echo =====================================================================
echo  - Backend Core API:     http://127.0.0.1:8000
echo  - Interactive Docs:     http://127.0.0.1:8000/docs
echo  - Cyber Dashboard:      http://localhost:3000
echo  - Real-Time WS Feed:    ws://127.0.0.1:8000/ws/dashboard
echo =====================================================================
echo.
echo [*] Waiting 6 seconds for services to initialize...
timeout /t 6 /nobreak >nul

echo [*] Launching dashboard in default browser...
start http://localhost:3000

echo.
echo [OK] Dhwani AI is running! Keep both background terminal windows open.
echo To stop services, close the Backend and Dashboard terminal windows.
echo.
pause
