# Local Development & Operational Guide for Dhwani

This document describes how to configure, run, and test the complete Dhwani / EchoShield AI voice anti-spoofing platform on Windows 11 with NVIDIA RTX 5060 GPU acceleration.

---

## 1. System Requirements & Hardware

- **OS**: Windows 11 (x64)
- **GPU**: NVIDIA RTX 5060 Laptop GPU (8 GB VRAM)
- **CUDA Stack**: CUDA 12.8 + cuDNN 9.x
- **Python**: Python 3.12 (Virtual Environment located at `.venv`)
- **Node.js**: Node.js v24.x + npm 11.x
- **External Tools**: FFmpeg (installed and available on system PATH)

---

## 2. Environment Activation

Open PowerShell in the project root (`C:\Users\gurus\Dhwani`):

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Starting the Backend Server (FastAPI)

Run Uvicorn to host the REST API, Telephony receiver, and WebSockets on port 8000:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Core endpoints available:
- REST API Root: `http://localhost:8000/`
- Health Check: `http://localhost:8000/health`
- Hardware & Model Status: `http://localhost:8000/api/system/status`
- File/Video Upload: `http://localhost:8000/api/analyze/upload`
- YouTube URL Analysis: `http://localhost:8000/api/analyze/youtube`
- Security Incidents Ledger: `http://localhost:8000/api/incidents`
- Dashboard Telemetry WebSocket: `ws://localhost:8000/ws/dashboard`
- Twilio Media Stream WebSocket: `ws://localhost:8000/twilio/media`
- Twilio Voice Webhook: `http://localhost:8000/twilio/voice`

---

## 4. Starting the Frontend (Next.js 16)

In a separate terminal window, start the Next.js development server:

```powershell
cd frontend
npm run dev
```

Open your browser at `http://localhost:3000` to interact with the Unified Cyber Dashboard.

---

## 5. Exposing Public WebSocket for Telephony (ngrok Tunnel)

Twilio requires a public `wss://` endpoint to forward live phone calls to your local workstation. Run ngrok to tunnel port 8000:

```powershell
ngrok http 8000
```

Copy the generated HTTPS URL (e.g. `https://abc123xyz.ngrok-free.app`) and configure it in `.env`:

```env
TWILIO_STREAM_PUBLIC_URL=wss://abc123xyz.ngrok-free.app/twilio/media
```

---

## 6. Running Automated Tests

Run the complete test suite across all subsystems:

```powershell
python -m unittest discover tests
```

Run specific test modules:

```powershell
# Telephony G.711 mu-law decoding & 16 kHz resampling
python -m unittest tests/test_telephony_audio.py

# Unified media pipeline & file audio analysis
python -m unittest tests/test_unified_media.py

# Multi-channel notification routing & cooldowns
python -m unittest tests/test_notifications.py

# Cryptographic SHA-256 audit hash chain integrity
python -m unittest tests/test_audit_chain.py

# FastAPI REST endpoints & TwiML webhooks
python -m unittest tests/test_api_endpoints.py
```

---

## 7. Running System Performance & Hardware Benchmark

Execute the full 8-stage benchmark suite evaluating model speeds, VRAM, and consensus:

```powershell
python scripts/system_benchmark_test.py
```

---

## 8. Running Local Microphone Analysis (Live Audio)

Analyze live microphone speech continuously on hardware:

```powershell
python streaming/live_w2v2_test.py
```

---

## 9. Running Standalone File & Video Analysis

Analyze an audio or video file from the command line:

```powershell
python -c "from ai.common.media_sources import FileAudioSource; from ai.common.common_pipeline import UnifiedMediaPipeline; res = UnifiedMediaPipeline().analyze_source(FileAudioSource('real_speech.wav')); print(res)"
```
