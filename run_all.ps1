# Dhwani / EchoShield AI - PowerShell Enterprise Launcher
# Usage: .\run_all.ps1 (from PowerShell)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          DHWANI / ECHOSHIELD AI - ENTERPRISE CONTROL PLATFORM" -ForegroundColor Cyan
Write-Host "      AI-Powered Real-Time Voice Cloning Detection & Prevention" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Virtual Environment
$PythonPath = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-Host "[ERROR] Python virtual environment not found in .venv\" -ForegroundColor Red
    Write-Host "To initialize the environment, run:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# 2. Check Node.js and npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js / npm was not found in system PATH." -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# 3. Synchronize Root .env
$RootEnvPath = Join-Path $ScriptDir ".env"
if (-not (Test-Path $RootEnvPath)) {
    Write-Host "[*] Creating synchronized root .env configuration..." -ForegroundColor Yellow
    @"
# ==============================================================================
# Dhwani / EchoShield AI - Local Development Configuration
# ==============================================================================
DHWANI_API_KEY=dhwani-local-dev-key-2026
DHWANI_AUTH_REQUIRED=false
DHWANI_BACKEND_URL=http://127.0.0.1:8000
PORT=8000
DHWANI_DEMO_MODE=true
DHWANI_RETAIN_AUDIO=false

# Twilio Telephony Stream Configuration (Optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
TWILIO_STREAM_PUBLIC_URL=
"@ | Out-File -FilePath $RootEnvPath -Encoding utf8
    Write-Host "[OK] Created root .env successfully." -ForegroundColor Green
}

# 4. Synchronize Frontend .env.local
$FrontendEnvPath = Join-Path $ScriptDir "frontend\.env.local"
if (-not (Test-Path $FrontendEnvPath)) {
    Write-Host "[*] Creating synchronized frontend\.env.local configuration..." -ForegroundColor Yellow
    @"
# ==============================================================================
# Dhwani Next.js Frontend - Local Interconnect Configuration
# ==============================================================================
DHWANI_BACKEND_URL=http://127.0.0.1:8000
DHWANI_API_KEY=dhwani-local-dev-key-2026
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/ws/dashboard
DHWANI_DEMO_MODE=true
"@ | Out-File -FilePath $FrontendEnvPath -Encoding utf8
    Write-Host "[OK] Created frontend\.env.local successfully." -ForegroundColor Green
}

# 5. Check Frontend node_modules
$NodeModulesPath = Join-Path $ScriptDir "frontend\node_modules"
if (-not (Test-Path $NodeModulesPath)) {
    Write-Host "[*] Frontend dependencies not found. Installing npm packages..." -ForegroundColor Yellow
    Push-Location (Join-Path $ScriptDir "frontend")
    & npm install
    Pop-Location
    Write-Host "[OK] Frontend packages installed." -ForegroundColor Green
}

# 6. Check Port 8000 & 3000
$Port8000Active = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($Port8000Active) {
    Write-Host "[WARNING] Port 8000 is already in use by another process." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] Starting Dhwani AI FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process cmd.exe -ArgumentList "/k title Dhwani AI Backend && color 0A && cd /d `"$ScriptDir`" && call `"$ScriptDir\.venv\Scripts\activate.bat`" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "[*] Starting Dhwani Cyber Dashboard on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process cmd.exe -ArgumentList "/k title Dhwani Cyber Dashboard && color 0B && cd /d `"$ScriptDir\frontend`" && npm run dev"

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "                   SERVICES ARE STARTING UP" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "  - Backend Core API:     http://127.0.0.1:8000"
Write-Host "  - Interactive Docs:     http://127.0.0.1:8000/docs"
Write-Host "  - Cyber Dashboard:      http://localhost:3000"
Write-Host "  - Real-Time WS Feed:    ws://127.0.0.1:8000/ws/dashboard"
Write-Host "====================================================================="
Write-Host ""

Write-Host "[*] Waiting 6 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

Write-Host "[*] Launching dashboard in default browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "[OK] Dhwani AI is running! Keep both background terminal windows open." -ForegroundColor Green
Write-Host "To stop services, close the Backend and Dashboard terminal windows."
Write-Host ""
