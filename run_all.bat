@echo off
setlocal enabledelayedexpansion

title Dhwani / EchoShield AI - Launcher

echo =====================================================================
echo           DHWANI / ECHOSHIELD AI - ENTERPRISE CONTROL PLATFORM
echo       AI-Powered Real-Time Voice Cloning Detection ^& Prevention
echo =====================================================================
echo.

:: 1. Check Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv\
    echo Please ensure the virtual environment is set up at C:\Users\gurus\Dhwani\.venv
    pause
    exit /b 1
)

:: 2. Check or Create .env
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Creating .env from .env.example...
        copy .env.example .env >nul
        echo [*] Created .env successfully.
    )
)

:: 3. Check Frontend Dependencies
if not exist "frontend\node_modules" (
    echo [*] Frontend dependencies not found. Running npm install...
    pushd frontend
    call npm install
    popd
)

echo [*] Starting Dhwani AI FastAPI Backend on http://localhost:8000 ...
start "Dhwani AI Backend [Port 8000]" cmd /k "title Dhwani AI Backend && color 0A && cd /d "%~dp0" && call .\.venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] Starting Dhwani Cyber Frontend on http://localhost:3000 ...
start "Dhwani Cyber Dashboard [Port 3000]" cmd /k "title Dhwani Cyber Dashboard && color 0B && cd /d "%~dp0frontend" && npm run dev"

echo.
echo =====================================================================
echo                   SERVICES ARE STARTING UP
echo =====================================================================
echo  - Backend API:       http://localhost:8000
echo  - API Docs (Swagger): http://localhost:8000/docs
echo  - Cyber Dashboard:   http://localhost:3000
echo  - Dashboard WS:      ws://localhost:8000/ws/dashboard
echo.
echo [*] Waiting 5 seconds for services to initialize...
timeout /t 5 /nobreak >nul

echo [*] Launching browser to http://localhost:3000 ...
start http://localhost:3000

echo.
echo [OK] Dhwani AI is running! Keep the opened terminal windows active.
echo Press any key to exit this launcher window...
pause >nul
