# Dhwani Phase 0: Environment Audit & Setup Report
**Project:** Dhwani (ध्वनि) / EchoShield AI — Real-Time Voice Deepfake & Speech Spoofing Platform  
**Target Branch:** `master`  
**Audit Timestamp:** 2026-10-24T23:45:00+05:30  
**Audit Status:** Environment Configured & Verified (Readiness: Partially Ready — Models & Services Pending)

---

## 1. System Runtime & Hardware Inventory

| Component | Host System Detection | Project Requirement (README) | Status |
| :--- | :--- | :--- | :--- |
| **Operating System** | Microsoft Windows 11 Home (NT 10.0.26200, 64-bit) | Windows 10/11, Ubuntu 22.04+, macOS | **COMPLIANT** |
| **System Python** | Python 3.14.8 (Global Default) | Python 3.10 / 3.11 (Min), 3.12 (Rec) | **INCOMPATIBLE FOR ML** |
| **Project Python** | Python 3.12.10 (via Windows `py -3.12`) | Python 3.12 (Recommended) | **COMPLIANT (.venv configured)** |
| **Node.js** | v24.19.0 (npm v11.x) | Node.js 18+ (Min), 20+ (Rec) | **COMPLIANT** |
| **Git** | git version 2.56.0.windows.1 | Git 2.x | **COMPLIANT** |
| **Discrete GPU** | NVIDIA GeForce RTX 5060 Laptop GPU (8,151 MiB VRAM) | NVIDIA RTX 3060+ (CUDA 12.x) | **DETECTED & OPERATIONAL** |
| **GPU Driver & CUDA** | NVIDIA Driver 610.88 (CUDA Driver 13.3) | CUDA 12.x+ | **COMPLIANT** |
| **Audio Processing** | FFmpeg 0.0.0 (WinGet links on system PATH) | FFmpeg (Video/Audio extraction) | **AVAILABLE** |
| **Disk Storage** | Drive `C:` with ~299.25 GB free | >= 20 GB recommended | **AMPILY SUFFICIENT** |

> [!IMPORTANT]
> **Python 3.14 Incompatibility Warning:**  
> The system default Python is Python 3.14.8. Core scientific, audio, and machine learning packages (`torch`, `torchaudio`, `librosa`, `scipy`, `numba`, `onnxruntime-gpu`) currently lack precompiled binary wheels for Python 3.14 on Windows.  
> **Resolution:** An isolated virtual environment (`.venv`) was explicitly created using **Python 3.12.10** (`py -3.12 -m venv .venv`).

---

## 2. Environment Setup Strategy & Isolation

To prevent system-level package pollution and avoid breaking changes to user toolchains:

1. **Python Virtual Environment (`.venv`):**
   - Created at: `C:\Users\gurus\.gemini\antigravity-ide\scratch\dhwani\.venv`
   - Python executable: `C:\Users\gurus\.gemini\antigravity-ide\scratch\dhwani\.venv\Scripts\python.exe`
   - Package manager utilized: `uv` (located at `C:\Users\gurus\.local\bin\uv.exe`) for fast, deterministic, non-destructive package installation into the project-local `.venv`.
   - Core backend packages installed: 87 packages installed in 4.71s from `requirements.txt` plus test runners `pytest` and `httpx`.

2. **Frontend Environment (`frontend/node_modules`):**
   - Installed via `npm ci` inside `frontend/` to strictly preserve `frontend/package-lock.json` without updating dependencies or mutating locks.
   - Node packages installed: 416 packages installed cleanly.

---

## 3. Dependency Inventory & Manifest Analysis

### 3.1 Python Backend Dependencies

The project defines dependencies across multiple files:
- `requirements.txt` (Root manifest): Specifies scientific, ML, API, and utility libraries.
- `requirements-lock.txt` (Frozen environment lock): Encoded in UTF-16LE, contains 107 pinned packages from a previous Python environment.
- `backend/requirements.txt` (Minimal backend subset): Contains basic FastAPI, Uvicorn, Pydantic, and NumPy declarations.

#### Critical Dependency Gaps Identified:
1. **Missing `yt-dlp` in `requirements.txt`:**
   - Referenced in: `ai/common/media_sources.py` (Line 181: `import yt_dlp`).
   - Effect: Ingesting YouTube URLs via `POST /api/analyze/youtube` raises a `RuntimeError` ("yt-dlp is required for YouTube audio extraction").
2. **Missing `pytest` and `httpx` in `requirements.txt`:**
   - `README.md` explicitly documents running `pytest tests/ -v`.
   - FastAPI `TestClient` requires `httpx`. Neither was declared in `requirements.txt`.
3. **Missing `pydantic-settings` or modern schema requirements:**
   - FastAPI 0.162+ and Pydantic 2.14+ are installed in `.venv`. All existing routes import correctly.

### 3.2 Frontend Dependencies (`frontend/package.json`)

- Framework: Next.js `16.3.5` (App Router)
- UI & State: React `19.2.8`, React DOM `19.2.8`
- Visualization: Three.js `^0.186.0`, Recharts `^3.10.1`, Lucide React `^1.47.0`
- Styling: TailwindCSS `^4.0.0` with `@tailwindcss/postcss`
- HTTP Client: Axios `^1.20.0`

---

## 4. Configuration & Secrets Checklist

| Variable Name | Required / Optional | Default in `.env.example` | Purpose | Configured in Local Audit |
| :--- | :--- | :--- | :--- | :--- |
| `TWILIO_ACCOUNT_SID` | Optional (Telephony) | `AC_YOUR_TWILIO_ACCOUNT_SID_HERE` | Inbound voice webhook auth & SMS | Dry-run / Unset |
| `TWILIO_AUTH_TOKEN` | Optional (Telephony) | `YOUR_TWILIO_AUTH_TOKEN_HERE` | Inbound voice webhook auth & SMS | Dry-run / Unset |
| `TWILIO_PHONE_NUMBER` | Optional (Telephony) | `+1234567890` | Inbound caller ID | Unset |
| `TWILIO_STREAM_PUBLIC_URL` | Optional (Telephony) | `wss://YOUR_NGROK_SUBDOMAIN...` | Public WSS URL for Twilio Media Stream | Localhost fallback |
| `DHWANI_ALERT_PHONE_NUMBER` | Optional (Alerts) | `+1987654321` | SMS alert dispatch target | Dry-run / Unset |
| `DHWANI_ALERT_DRY_RUN` | **Required** | `true` | Prevents live SMS/calls during dev | **Set to `true`** |
| `DHWANI_WHATSAPP_ENABLED` | Optional (Alerts) | `false` | Enables WhatsApp alert provider | `false` |
| `TWILIO_WHATSAPP_FROM` | Optional (Alerts) | `whatsapp:+14155238886` | Twilio sandbox WhatsApp sender | Default |
| `DHWANI_WHATSAPP_ALERT_NUMBER`| Optional (Alerts) | `whatsapp:+1987654321` | WhatsApp target number | Default |
| `SMTP_HOST` / `SMTP_PORT` | Optional (Alerts) | Unset / 587 | Fallback email dispatch | Unset |
| `SMTP_USER` / `SMTP_PASSWORD`| Optional (Alerts) | Unset | SMTP authentication | Unset |
| `DHWANI_RETAIN_AUDIO` | **Required (Privacy)**| `false` | Enforces zero-retention raw audio purge | **Set to `false`** |

> [!CAUTION]
> **Secrets Handling Policy:**  
> No secret credentials, API keys, or live Twilio tokens have been injected, forged, or committed. Testing was conducted strictly with `DHWANI_ALERT_DRY_RUN=true`. Git status was verified to ensure `.env` and sensitive files are ignored by `.gitignore`.

---

## 5. Model Weights & Data Asset Verification

| Model Name | Target Path | File Size / Format | Found in Repo? | Status |
| :--- | :--- | :--- | :--- | :--- |
| **W2V2-AASIST** | `models/w2v2_aasist/w2v2-aasist.onnx` | ~1.26 GB (ONNX) | No (`.gitkeep` only) | **BLOCKED (Requires download)** |
| **AASIST (Official)** | `models/aasist/AASIST.pth` | 1,281,532 bytes (PyTorch) | **YES** | **PRESENT ON DISK** |
| **AASIST (ONNX)** | `models/aasist/aasist.onnx` | ~1.54 MB (ONNX) | No | **BLOCKED (Adapter expects ONNX)** |
| **AASIST-L (PyTorch)**| `ai/aasist/models/weights/AASIST-L.pth` | 426,428 bytes (PyTorch) | **YES** | **PRESENT ON DISK** |
| **AASIST-L (ONNX)** | `models/aasist/aasist-l.onnx` | ~766 KB (ONNX) | No | **BLOCKED (Adapter expects ONNX)** |
| **ECAPA-TDNN** | `models/speaker/ecapa512.onnx` | ~24.8 MB (ONNX) | No (`.gitkeep` only) | **BLOCKED (Missing weights)** |
| **Acoustic Detector**| Pure Python (`ai/acoustic/acoustic_detector.py`) | Handcrafted spectral/LFCC | **YES** | **VERIFIED & OPERATIONAL** |
| **Audio Quality** | Pure Python (`ai/acoustic/audio_quality.py`) | Spectral SNR / Clipping | **YES** | **VERIFIED & OPERATIONAL** |
| **VAD Gate** | Pure Python (`streaming/vad_gate.py`) | Energy & ZCR threshold | **YES** | **VERIFIED & OPERATIONAL** |

---

## 6. Reproducible Setup Commands

### Step 1: Clone and Checkout Master
```powershell
git clone https://github.com/dudyalagurusreekar/dhwani.git dhwani
cd dhwani
git checkout master
```

### Step 2: Configure Python Virtual Environment (Python 3.12)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt pytest httpx --python .venv\Scripts\python.exe
```

### Step 3: Configure Frontend Dependencies
```powershell
cd frontend
npm ci
cd ..
```

### Step 4: Run Verified Automated Tests
```powershell
# Set project root on PYTHONPATH and execute pytest
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe tests/ -v
```

---

## 7. Current Environment Blockers & Next Actions

1. **Missing Neural Model ONNX Checkpoints:**
   - `scripts/system_benchmark_test.py` and full multi-model detection fail because `w2v2-aasist.onnx`, `aasist-l.onnx`, `aasist.onnx`, and `ecapa512.onnx` are absent.
   - *Key finding:* PyTorch checkpoints `AASIST.pth` and `AASIST-L.pth` are already checked into the repository under `ai/aasist/models/weights/`, but adapters look only for `.onnx` files.
2. **Missing `yt-dlp` in `requirements.txt`:**
   - Must be declared to allow YouTube audio extraction.
3. **Frontend ESLint Errors:**
   - 10 errors prevent clean `npm run lint` execution.
