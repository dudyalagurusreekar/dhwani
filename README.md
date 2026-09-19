# Dhwani (ध्वनि) / EchoShield 🛡️🎙️
> **Real-Time AI Voice Deepfake & Speech Spoofing Detection Platform**

Dhwani is a multi-tier defense architecture designed to detect synthetic voices, voice clones, and acoustic spoofing attacks in real-time streaming audio (e.g., live VoIP calls, voice meetings, identity authentication).

---

## 🏗️ Architecture & Project Structure

```
Dhwani/
├── ai/                      # AI Detection Models & Feature Extractors
│   ├── aasist/             # AASIST (Spectrogram-graph anti-spoofing)
│   ├── acoustic/           # Signal processing & MFCC feature extractor
│   ├── common/             # Standardized detector interface & risk config
│   ├── speaker/            # Speaker consistency & verification (Member 2)
│   ├── ssl_detector/       # Self-supervised learning (W2V2-AASIST) detector
│   └── watermark/          # Synthetic audio watermark detection
├── backend/                 # FastAPI REST & WebSocket streaming server
├── frontend/                # Real-time monitoring dashboard & visualizer
├── risk_engine/             # Multi-model risk fusion & anomaly scoring
├── streaming/               # Real-time microphone capture & rolling buffer
├── models/                  # Model weights & ONNX inference models
│   ├── aasist/             # AASIST.pth (~1.2MB, tracked in Git)
│   └── w2v2_aasist/        # w2v2-aasist.onnx (~1.26GB, download via script)
├── datasets/                # Benchmarks (ASVspoof 2019/2021)
├── scripts/                 # Automation scripts (download models, benchmarks)
├── docs/                    # Architecture diagrams and specifications
├── requirements.txt         # Core project dependencies
├── requirements-lock.txt    # Exact environment lockfile
└── .gitignore               # Ignores large models, .venv, datasets & caches
```

---

## 💻 System Prerequisites

Before starting, ensure your machine meets these requirements:

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **OS** | Windows 10/11, Ubuntu 22.04+, macOS | Windows 11 / Ubuntu 22.04 LTS |
| **Python** | Python 3.10 or 3.11 | Python 3.12 |
| **RAM** | 8 GB RAM | 16 GB+ RAM |
| **GPU (Optional)** | CPU supported (latency ~150-300ms) | NVIDIA GPU (RTX 3060+ with CUDA 12.x, latency < 40ms) |
| **Hardware** | Working microphone / audio input | Low-noise USB / headset mic |

---

## 🚀 Setup Instructions (Step-by-Step for Teammates)

Follow these steps to set up your local environment and run the project in parallel:

### 1. Clone the Repository & Checkout Branch
```bash
git clone https://github.com/dudyalagurusreekar/dhwani.git
cd dhwani
git checkout guru
```

### 2. Create and Activate Virtual Environment
```bash
# Windows PowerShell / CMD:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# (Or in CMD: .\.venv\Scripts\activate.bat)

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install PyTorch
Choose the version matching your hardware:

- **GPU (NVIDIA CUDA 12.8 / 12.x recommended)**:
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
  ```

- **CPU Only**:
  ```bash
  pip install torch torchvision torchaudio
  ```

### 4. Install Project Dependencies
```bash
pip install -r requirements.txt
```

> **Note for CPU-only machines**: If you do not have an NVIDIA GPU, uninstall `onnxruntime-gpu` and install standard `onnxruntime`:
> ```bash
> pip uninstall -y onnxruntime-gpu
> pip install onnxruntime
> ```

### 5. Download Pre-trained Models
The heavy W2V2-AASIST model (~1.26 GB) is hosted on Hugging Face and is excluded from Git to keep the repository lightweight. Run the automated download script:

```bash
python scripts/download_models.py
```
*This downloads `w2v2-aasist.onnx` directly into `models/w2v2_aasist/`.*

---

## 🧪 Testing & Verification

Run these quick checks to verify your setup:

### Test 1: Verify Core Stack & CUDA / ONNX Acceleration
```bash
python -c "import torch, torchaudio, onnxruntime as ort, librosa, sounddevice; print('CUDA Available:', torch.cuda.is_available()); print('ONNX Providers:', ort.get_available_providers())"
```

### Test 2: Test Audio Feature Extraction
```bash
python ai/acoustic/acoustic_detector.py real_speech.wav
```
*Expected: Prints `ACOUSTIC FEATURE EXTRACTION: PASS` with 50-dimensional feature vector.*

### Test 3: Test Model Prediction on Audio File
```bash
python ai/ssl_detector/w2v2_aasist_detector.py
```
*Expected: Prints Bona-fide / Spoof logits and inference latency in milliseconds.*

### Test 4: Run Real-Time Live Microphone Deepfake Detector
```bash
python streaming/live_w2v2_stream.py
```
*Speak into your microphone. After ~4 seconds of audio buffering, it prints live spoof/bona-fide logits every second.*

---

## 👥 Parallel Team Workstreams

To avoid git merge conflicts, teammates should work on dedicated branches and modules:

| Workstream | Directory | Description | Branch Name Convention |
| :--- | :--- | :--- | :--- |
| **Core AI & SSL** | `ai/ssl_detector/`, `ai/common/` | W2V2-AASIST optimizations, fusion contract | `guru` |
| **Speaker Consistency** | `ai/speaker/`, `models/speaker/` | Speaker verification embeddings & tracking | `feature/member2-speaker-consistency` |
| **Acoustic & Watermarking** | `ai/acoustic/`, `ai/watermark/` | Spectral features, synthetic watermark detector | `feature/acoustic-watermark` |
| **Risk Engine** | `risk_engine/` | Aggregation weights, thresholds, alert logic | `feature/risk-engine` |
| **Streaming & VAD** | `streaming/` | Silero-VAD integration, WebSocket client | `feature/streaming-vad` |
| **Backend API** | `backend/` | FastAPI routes, WebSocket ingestion endpoint | `feature/backend-api` |
| **Frontend UI** | `frontend/` | Live risk visualizer, waveform display | `feature/frontend-ui` |

---

## 🤝 Git Workflow

1. **Always pull latest updates before working**:
   ```bash
   git fetch origin
   git merge origin/guru
   ```
2. **Commit clean code (avoid committing `.venv`, large datasets, or temp `.wav` files)**.
3. **Push to your feature branch**:
   ```bash
   git push origin <your-branch-name>
   ```
4. **Create a Pull Request** on GitHub into `main` or `guru` for review.
