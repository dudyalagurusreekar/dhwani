# Dhwani (ध्वनि) — Enterprise Voice Deepfake Detection & Anti-Spoofing Platform

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch 2.14](https://img.shields.io/badge/PyTorch-2.14+-ee4c2c.svg?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests: 147 Passed](https://img.shields.io/badge/Tests-147%20Passed%20(100%25)-success.svg?logo=pytest&logoColor=white)](tests/)
[![Security: Audited](https://img.shields.io/badge/Security-BFF%20%7C%20SSRF%20%7C%20HMAC-blueviolet.svg)](#-enterprise-security-architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Dhwani** is an industrial-grade, multi-tier cyber-security platform engineered to detect synthetic voice clones, neural vocoder artifacts, and speech spoofing attacks in real-time streaming audio (VoIP calls, Twilio telephony, identity verification, and video meetings).

---

## 📑 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture](#-system-architecture)
- [AI Inference Engine & Detector Ensemble](#-ai-inference-engine--detector-ensemble)
- [Enterprise Security Architecture](#-enterprise-security-architecture)
- [Scientific Evaluation & Benchmarking (Phase 4)](#-scientific-evaluation--benchmarking-phase-4)
- [Directory Structure](#-directory-structure)
- [Quickstart & Setup](#-quickstart--setup)
- [Automated Test Suite (147 Tests)](#-automated-test-suite-147-tests)
- [Engineering Documentation & Phase History](#-engineering-documentation--phase-history)

---

## 🛡️ Executive Summary

Modern zero-shot voice cloning algorithms (e.g., ElevenLabs, XTTS, CosyVoice, VALL-E) allow threat actors to clone voices from seconds of reference audio for CEO fraud, banking social engineering, and synthetic identity fraud.

Traditional spectrogram-based CNN detectors fail in production because lossy audio compression (Opus, G.711 $\mu$-law) destroys 2D frequency representations. **Dhwani** solves this with a **multi-tiered, defense-in-depth architecture**:

1. **Raw-Waveform Graph Attention Networks:** Evaluates audio directly in the time domain via **AASIST** and **AASIST-L**, modeling spectral and temporal graph dependencies without spectrogram conversion loss.
2. **Sub-400ms Streaming Latency:** Inference latency runs at **$p_{50} = 360$ ms** and **$p_{95} = 376$ ms** on standard CPU devices, comfortably satisfying the $\le 500$ ms real-time streaming budget for live telephony.
3. **BFF Security Trust Boundary:** A Next.js Backend-for-Frontend proxy eliminates browser credential exposure, enforces token-bucket rate limiting, blocks SSRF DNS rebinding, and validates Twilio HMAC-SHA1 signatures.
4. **Tamper-Evident Incident Ledger:** Every flagged detection and policy enforcement event is chained using cryptographic **SHA-256 hash chains** to ensure non-repudiation.
5. **Leakage-Safe Scientific Protocol:** Implements a decoupled evaluation harness with continuous linear-interpolated **Equal Error Rate (EER)**, **ROC-AUC**, cross-split **speaker disjointness checking**, and **SHA-256 waveform duplicate detection**.

---

## 🏗️ System Architecture

Dhwani enforces strict boundary segregation between untrusted clients, trusted intermediaries, backend inference workers, and external telephony channels:

```mermaid
graph TD
    subgraph Untrusted External Zone
        User["End User Browser"]
        PSTN["Inbound Phone Call (Twilio PSTN)"]
        Attacker["Potential Adversary"]
    end

    subgraph Trust Boundary 1: Next.js BFF Gateway
        BFF["Next.js Route Handlers (/api/[...path])"]
        ClientAuth["Client Auth Validator & Session Gate"]
        BFFRouter["Route Whitelist & HTTP Method Filter"]
        RateLimiter["Token Bucket Rate Limiter"]
    end

    subgraph Trust Boundary 2: FastAPI Application Core
        FastAPI["FastAPI Backend (:8000)"]
        BackendAuth["Constant-Time API Key Guard (secrets.compare_digest)"]
        SSRFGuard["SSRF & IP Rebinding Defense"]
        TwilioGuard["Twilio HMAC-SHA1 Signature Validator"]
    end

    subgraph Real-Time Inference Pipeline
        VAD["WebRTC Voice Activity Detector"]
        AASIST["AASIST GAT (PyTorch Raw Waveform)"]
        AASIST_L["AASIST-L Lightweight GAT (PyTorch)"]
        Acoustic["Acoustic Heuristic (Spectral & Voicing)"]
        Fusion["Dynamic Bayesian Risk Fusion Engine"]
    end

    subgraph Compliance & State
        AuditChain["Tamper-Evident SHA-256 Audit Chain"]
        Notifier["Incident Alert Engine (SMS / Webhook)"]
    end

    User -->|Public Demo / Auth Headers| BFF
    BFF --> ClientAuth
    ClientAuth --> RateLimiter
    RateLimiter --> BFFRouter
    BFFRouter -->|Server-Injected API Key| BackendAuth

    PSTN -->|Live Media Stream (WebSockets)| FastAPI
    FastAPI --> TwilioGuard
    FastAPI --> BackendAuth

    BackendAuth --> VAD
    VAD -->|Active Voice Windows| AASIST & AASIST_L & Acoustic
    AASIST & AASIST_L & Acoustic --> Fusion
    Fusion -->|Risk Score & Threats| AuditChain
    Fusion -->|Threshold Alerts| Notifier
    AuditChain --> FastAPI
```

---

## 🧠 AI Inference Engine & Detector Ensemble

Dhwani fuses diverse, complementary detector paradigms to prevent any single blind spot from compromising the pipeline.

### Model Hierarchy & Operational Status

| Detector Model | Architecture Type | Input Domain | Status in Repo | Primary Detection Strength |
| :--- | :--- | :--- | :---: | :--- |
| **AASIST** | Raw-waveform Graph Attention Network | 16 kHz Linear PCM | **OPERATIONAL (PyTorch)** | Global spectro-temporal graph relationships across time frames. |
| **AASIST-L** | Lightweight Graph Attention Network | 16 kHz Linear PCM | **OPERATIONAL (PyTorch)** | High-frequency vocoder phase artifacts; low latency (~30 ms). |
| **ACOUSTIC** | Handcrafted Statistical Heuristics | Frequency & Time | **OPERATIONAL (NumPy/SciPy)** | Spectral centroid variance, voicing consistency, high-frequency energy ratio. |
| **W2V2-AASIST** | Self-Supervised wav2vec 2.0 Feature Extractor | 16 kHz Linear PCM | **DEFERRED (ONNX)** | Contextual acoustic representations; gracefully skipped when asset absent. |
| **ECAPA-TDNN** | Deep Speaker Embedding & Verification | 16 kHz Linear PCM | **DEFERRED (ONNX)** | Cross-utterance speaker timbre verification. |

### Dynamic Weight Normalization
If an optional model (such as `W2V2-AASIST`) is offline or missing from local storage, Dhwani's inference manager records the detector status as `SKIPPED` and `raw_score=None`.

The risk fusion engine automatically renormalizes weights across active detectors:
$$w_i' = \frac{w_i}{\sum_{j \in \mathcal{M}_{\text{active}}} w_j}$$
Missing detectors are **never imputed as zero** (which would falsely classify an utterance as authentic), preventing silent false-negative vulnerabilities.

### Telephony Chunking & Latency Profile
- **Streaming Chunks:** Incoming audio is buffered into overlapping 1.0s to 3.0s windows.
- **CPU Inference Budget:**
  - Median Latency ($p_{50}$): **360.41 ms**
  - 95th Percentile ($p_{95}$): **376.02 ms**
  - Production SLA Budget: $\le 500$ ms for real-time alerting during live calls.

---

## 🔒 Enterprise Security Architecture

Dhwani treats security as an integral part of model inference, protecting against attack vectors that target AI infrastructure:

| Security Domain | Threat Vector Mitigated | Defense Implementation | Implementation File |
| :--- | :--- | :--- | :--- |
| **Credential Shielding** | Browser token leakage & secret extraction | **Next.js BFF (Backend-for-Frontend):** Clients never receive the master backend API key. The BFF validates sessions and injects server-side secrets. | `frontend/src/app/api/[...path]/route.ts` |
| **Route Authorization** | Confused Deputy / Unauthorized Access | Segregated endpoints: **Public Demo** (`/api/system/status`, `/api/analyze/upload`) vs **Protected Operational** (`/api/incidents`, `/api/audit/*`). | `frontend/src/app/api/[...path]/route.ts` |
| **Side-Channel Timing** | Token enumeration via character timing | Constant-time token verification using Python's `secrets.compare_digest`. | `security/auth.py` |
| **SSRF Defense** | Cloud metadata theft & intranet scanning | Synchronous DNS resolution checking against RFC 1918 private ranges, loopback (`127.0.0.0/8`), link-local (`169.254.169.254`), and non-HTTP schemes. | `security/ssrf.py` |
| **Telephony Integrity** | Fake Twilio webhook injection & replay | Canonical URL signature reconstruction with **HMAC-SHA1** request signing verification. | `security/twilio_validator.py` |
| **Audit Ledger** | Cover-up of security breaches & log tampering | **Cryptographic Hash Chain:** Every audit event includes the SHA-256 hash of the preceding record: $H_k = \text{SHA256}(H_{k-1} \parallel \text{Payload}_k)$. | `security/audit_chain.py` |

---

## 📊 Scientific Evaluation & Benchmarking (Phase 4)

Dhwani includes a mathematically rigorous evaluation harness (`scripts/evaluation/`) designed to prevent misleading accuracy reporting.

### 1. Metric Formulations
- **Positive Class:** Strictly defined as `spoof` ($y = 1$).
- **Negative Class:** Strictly defined as `bonafide` ($y = 0$).
- **Score Semantics:** Continuous posterior $s \in [0.0, 1.0]$, representing $P(\text{spoof} \mid \mathbf{x})$. Higher is more spoof.
- **Biometric Error Rates:**
  $$\text{False Alarm Rate (FAR / } P_{fa}) = \frac{\text{FP}}{\text{TN} + \text{FP}} \quad (\text{genuine rejected})$$
  $$\text{Miss Rate (FRR / } P_{miss}) = \frac{\text{FN}}{\text{TP} + \text{FN}} \quad (\text{spoof accepted})$$
- **Equal Error Rate (EER):** Continuous linear interpolation over zero-crossings of $(P_{fa} - P_{miss})$.
- **ROC-AUC:** Continuous trapezoidal integration anchored at $(0, 0)$ and $(1, 1)$.

### 2. Leakage-Safe Partitioning Guarantees
- **Speaker Disjointness:** Built-in checks (`verify_split_leakage`) enforce that training, validation, and evaluation partitions share **zero speaker IDs** ($\mathcal{S}_{\text{train}} \cap \mathcal{S}_{\text{dev}} = \emptyset$).
- **SHA-256 Waveform Duplicate Detection:** Audio files are hashed at the binary sample level to catch duplicate recordings disguised under different filenames.

### 3. Threshold Calibration Discipline
- **Safety Fallback:** If validation samples $< 100$ or if real labeled data is unavailable, the production threshold remains unchanged at **`0.5000`** and is formally marked **`UNCALIBRATED`** (`config/evaluation/calibrated_thresholds.json`).
- Synthetic smoke test thresholds (e.g. 0.9266) are strictly quarantined from mutating production defaults.

### 4. Acoustic Robustness Perturbation Suite
Evaluates pipeline degradation across synthetic acoustic perturbations (`scripts/evaluation/robustness.py`):
- **Telephony Companding:** ITU-T G.711 $\mu$-law (8-bit quantization).
- **Narrowband Resampling:** 8 kHz downsampling simulating legacy PSTN networks.
- **Additive Gaussian Noise:** Signal-to-Noise Ratio (SNR) sweeps at 20 dB, 10 dB, and 0 dB.
- **Duration Truncation:** Clip slicing down to 1.0s and 0.5s.

---

## 📁 Directory Structure

```text
dhwani/
├── ai/                              # Core AI Inference & Adapter Implementations
│   ├── aasist/                      # AASIST Graph Attention Network (PyTorch)
│   ├── acoustic/                    # Handcrafted spectral & voicing heuristics
│   ├── ssl_detector/                # Self-supervised wav2vec 2.0 adapter (optional)
│   └── common/                      # Common detector interfaces & tiered inference
├── backend/                         # FastAPI Application & WebSocket Gateway
│   ├── routes/                      # REST routers (analyze, incidents, system, twilio)
│   ├── services/                    # Inference dispatch, risk engine, notifications
│   ├── streaming/                   # Audio stream buffer management
│   └── websocket/                   # Real-time dashboard & audio WebSockets
├── frontend/                        # Next.js 14 Unified Cyber Dashboard
│   ├── src/app/api/[...path]/       # Backend-for-Frontend (BFF) Security Proxy
│   ├── src/components/dashboard/    # Real-time threat visualizer & waveform telemetry
│   └── src/app/health/              # Public zero-secret deployment health check
├── security/                        # Security Controls & Cryptographic Ledger
│   ├── auth.py                      # Constant-time API key verification & rate limits
│   ├── ssrf.py                      # DNS resolution SSRF & IP rebinding defense
│   ├── twilio_validator.py          # Twilio HMAC-SHA1 signature verification
│   └── audit_chain.py               # Cryptographic SHA-256 tamper-evident log
├── scripts/                         # MLOps, Evaluation, and Verification Scripts
│   ├── evaluation/                  # Decoupled manifest loader, EER metrics, calibration
│   │   ├── dataset.py               # Manifest loader, audio validator & leakage auditor
│   │   ├── metrics.py               # EER, ROC-AUC, FAR/FRR, latency statistics
│   │   ├── evaluate.py              # Reproducible evaluation runner
│   │   ├── calibrate_thresholds.py  # Cost-sensitive validation threshold selector
│   │   └── robustness.py            # Acoustic perturbation test harness
│   └── verify_live_integration.py   # Live E2E verification of Next.js BFF + FastAPI
├── config/                          # Configuration & Versioned Threshold Artifacts
│   └── evaluation/                  # calibrated_thresholds.json (marked UNCALIBRATED)
├── docs/                            # Comprehensive Engineering Phase Documentation
│   ├── phase-0/                     # Feature verification matrix & initial findings
│   ├── phase-1/                     # Inference foundation & PyTorch AASIST integration
│   ├── phase-2/                     # Initial evaluation protocol & metric formulas
│   ├── phase-3/                     # Security controls, threat models & BFF architecture
│   └── phase-4/                     # Real-world benchmark protocol, readiness & limitations
├── models/                          # Neural network checkpoints (.pth)
├── tests/                           # 147 Unit & Integration Tests (100% Pass)
└── requirements.txt                 # Pinned backend dependencies
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- **Python:** 3.10, 3.11, or 3.12 (Recommended: 3.12)
- **Node.js:** 18.x or 20.x+
- **Host OS:** Windows 10/11, Ubuntu 22.04 LTS, or macOS

### 2. Environment Configuration
Clone the repository and create your local environment:
```bash
git clone https://github.com/dudyalagurusreekar/dhwani.git
cd dhwani

# Backend virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env` in the repository root:
```env
DHWANI_API_KEY=your-secure-internal-api-key-here
DHWANI_AUTH_REQUIRED=true
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
PORT=8000
```

Configure Frontend environment:
```bash
cd frontend
npm install
```
Create `frontend/.env.local`:
```env
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
DHWANI_API_KEY=your-secure-internal-api-key-here
```

### 3. Running Locally

#### Option A: One-Click Launch (Windows)
We provide automated launchers that verify dependencies, auto-generate local `.env` and `frontend/.env.local` configurations, check port availability, and launch both services together:

- **From PowerShell:**
  ```powershell
  .\run_all.ps1
  ```
- **From Command Prompt (CMD):**
  ```cmd
  run_all.bat
  ```

#### Option B: Manual Multi-Terminal Launch

**Terminal 1 — FastAPI Backend:**
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js Dashboard & BFF:**
```bash
cd frontend
npm run dev
```

Visit the dashboard at `http://localhost:3000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

---

## 🧪 Automated Test Suite (147 Tests)

Dhwani includes 147 automated unit and integration tests verifying numerical correctness, security boundaries, and inference stability.

### Run All Tests
```bash
pytest tests/ -v
```

### Test Suite Composition

```
Test File                           Tests  Area Verified
-----------------------------------------------------------------------------------------------------
tests/test_phase4_evaluation.py     14     Content hashing, split leakage, latency p95, perturbations
tests/test_phase3_security.py       37     BFF proxy, SSRF IP-rebinding, HMAC verification, audit chain
tests/test_phase2_evaluation.py     16     Manifest parsing, EER interpolation, ROC-AUC, calibration
tests/test_phase1_inference.py      20     PyTorch AASIST & AASIST-L inference, dynamic weight fusion
tests/test_api_endpoints.py         5      FastAPI REST endpoints & parameter validation
tests/test_backend_api.py           9      Audio analysis routes & payload size enforcement
tests/test_telephony_audio.py       5      Twilio WebSocket streams & G.711 mu-law decoding
tests/test_audit_chain.py           6      Cryptographic hash chaining & tamper detection
tests/test_hasher.py / test_hash*   12     SHA-256 integrity utilities
tests/test_notifications.py         3      Multi-channel alert dispatch
tests/test_privacy.py               4      Sensitive data redaction & log privacy
tests/test_risk_engine.py           4      Temporal risk scoring & Bayesian aggregation
tests/test_unified_media.py         4      Unified media ingest & channel downmixing
tests/test_pipeline.py              2      End-to-end synthetic audio pipeline smoke test
-----------------------------------------------------------------------------------------------------
TOTAL:                              147    100% Passed (0 Failures, 0 Regressions)
```

### Run Live End-to-End Trust-Boundary Verification
Tests the live interaction between Next.js BFF and FastAPI on isolated test ports:
```bash
python scripts/verify_live_integration.py
```
*(Runs 9 live E2E tests: BFF token injection, anonymous endpoint rejections, forged key handling, and secret redaction).*

### Frontend Type Safety
```bash
cd frontend
npx tsc --noEmit
```
*(Returns 0 TypeScript compilation errors).*

---

## 📚 Engineering Documentation & Phase History

Comprehensive design artifacts, verification registers, and threat models are preserved in the `docs/` directory:

- [docs/phase-1/inference-foundation.md](docs/phase-1/inference-foundation.md) — PyTorch AASIST/AASIST-L integration and missing-model normalization.
- [docs/phase-2/evaluation-protocol.md](docs/phase-2/evaluation-protocol.md) — Initial biometric error rate formulas and threshold calibration.
- [docs/phase-3/threat-model.md](docs/phase-3/threat-model.md) — Threat model covering SSRF, WebSocket abuse, and client credential leakage.
- [docs/phase-3/security-controls.md](docs/phase-3/security-controls.md) — Next.js BFF proxy pattern and cryptographic audit chain implementation.
- [docs/phase-4/dataset-readiness.md](docs/phase-4/dataset-readiness.md) — ASVspoof 2019 LA benchmark specifications and licensing.
- [docs/phase-4/evaluation-protocol.md](docs/phase-4/evaluation-protocol.md) — Leakage-safe evaluation protocol and mathematical definitions.
- [docs/phase-4/evaluation-results.md](docs/phase-4/evaluation-results.md) — Segregated results report: real benchmark status, smoke tests, and robustness.
- [docs/phase-4/limitations.md](docs/phase-4/limitations.md) — Unvarnished register of architectural limitations and operational risks.

---

## ⚖️ License & Ethical Use

- **Application Source Code:** All application architecture, FastAPI backend services, Next.js dashboard, BFF proxy, security controls, risk fusion engines, and evaluation pipelines are licensed under the [MIT License](LICENSE).
- **Pretrained Model Checkpoints:** Pretrained weights for AASIST and AASIST-L are redistributed in accordance with their original academic research licenses (BSD 3-Clause / Interspeech Consortium).
- **Benchmark Protocols:** Evaluation metadata and protocols referencing ASVspoof 2019/2021 are subject to the open research terms of the Interspeech ASVspoof Consortium (CC BY 4.0).

**Ethical Use Notice:** Dhwani is engineered to defend communication channels, customer support centers, and biometric identity authentication systems against unauthorized voice cloning and social engineering fraud. It must not be deployed for unauthorized surveillance, intrusive audio interception, or to circumvent individual privacy rights.
