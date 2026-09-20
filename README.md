# Dhwani (ध्वनि) / EchoShield 🛡️🎙️
> **Real-Time AI Voice Deepfake & Speech Spoofing Detection Platform**

Dhwani is a multi-tier enterprise defense architecture designed to detect synthetic voices, voice clones, and acoustic spoofing attacks in real-time streaming audio (e.g., live VoIP calls, voice meetings, identity authentication).

---

## 🌟 What's New: Enterprise Security & Telephony Update
Recent updates have transformed Dhwani from a core AI detector into a full enterprise cyber-security suite:

1. **Enterprise Telephony Integration:** Full support for Twilio WebSocket streaming. Real-time media ingestion, decoding, and VAD (Voice Activity Detection) gating during live phone calls.
2. **Unified Cyber Dashboard:** A stunning Next.js frontend providing live risk telemetry, incident management, visual waveforms, and multi-model threat detection scores.
3. **Cryptographic Audit Chain:** All security events (risk assessments, policy enforcement) are now immutably logged using cryptographic hash chains (`security/audit_chain.py`) to prevent tampering.
4. **Multi-Channel Incident Notifications:** Automated alert routing via Twilio SMS, WhatsApp, and Email when critical spoofing thresholds are breached.
5. **System Benchmarking:** New automated benchmarking suites covering all 5 neural models, REST APIs, and WebSocket latency (`scripts/system_benchmark_test.py`).
6. **One-Click Launch:** Easily start the entire stack (FastAPI backend + Next.js frontend) using the `run_all.bat` script.

---

## 🏗️ Architecture & Project Structure

```text
Dhwani/
├── ai/                      # AI Detection Models (AASIST, W2V2, Acoustic, Speaker, Watermark)
├── backend/                 # FastAPI REST, WebSocket servers, & Notification providers
├── frontend/                # Next.js Unified Cyber Dashboard & live visualizer
├── security/                # Cryptographic audit chains, hashing, and event schemas
├── streaming/               # Real-time microphone capture & Twilio telephony websocket
├── risk_engine/             # Multi-model risk fusion & anomaly scoring
├── models/                  # Model weights & ONNX inference models
├── datasets/                # Benchmarks (ASVspoof 2019/2021)
├── scripts/                 # System benchmarks, downloading models, test scripts
├── docs/                    # Architecture diagrams and API specifications
├── tests/                   # Comprehensive unit & integration tests
├── requirements.txt         # Core backend project dependencies
└── run_all.bat              # One-click startup script for frontend and backend
```

---

## 💻 System Prerequisites

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **OS** | Windows 10/11, Ubuntu 22.04+, macOS | Windows 11 / Ubuntu 22.04 LTS |
| **Python** | Python 3.10 or 3.11 | Python 3.12 |
| **Node.js**| Node.js 18+ (for Frontend) | Node.js 20+ |
| **RAM** | 8 GB RAM | 16 GB+ RAM |
| **GPU (Optional)** | CPU supported (latency ~150-300ms) | NVIDIA GPU (RTX 3060+ with CUDA 12.x) |

---

## 🚀 Setup Instructions (Step-by-Step)

### 1. Clone the Repository
```bash
git clone https://github.com/dudyalagurusreekar/dhwani.git
cd dhwani
```

### 2. Backend Setup (Python)
Create and activate your virtual environment, then install dependencies:
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```
*(Optional) Install PyTorch with CUDA support if you have an NVIDIA GPU.*

Download the heavy pre-trained models:
```bash
python scripts/download_models.py
```

### 3. Frontend Setup (Node.js)
Open a new terminal, navigate to the frontend directory, and install npm packages:
```bash
cd frontend
npm install
```

### 4. Launch the System 🚀
You can now start both the backend API and the frontend Next.js dashboard with a single click:

**On Windows:**
```cmd
.\run_all.bat
```
This will open the FastAPI server on `http://localhost:8000` and the Dashboard on `http://localhost:3000`.

---

## 🧪 Testing & Verification

Run the full system benchmark to ensure all models, VAD logic, and API routes are functioning optimally:

```bash
# Run full backend & model benchmark tests
python scripts/system_benchmark_test.py

# Run standard pytest suite
pytest tests/ -v
```

---

## 🤝 Git Workflow

1. **Pull the latest updates**: `git pull origin master`
2. **Commit clean code**. Avoid pushing `.venv`, `node_modules`, or heavy `.wav`/`.onnx` files.
3. **Push to `master`** or create a feature branch and open a Pull Request.

*Protected by Dhwani AI Core.*
