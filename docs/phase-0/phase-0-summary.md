# Dhwani Phase 0: Executive Engineering Summary & Next Actions
**Project:** Dhwani (ध्वनि) / EchoShield AI — Real-Time Voice Deepfake & Speech Spoofing Detection Platform  
**Target Branch:** `master` (`a45e40aa6fec462cc770325b41802f8629e4b1f7`)  
**Audit Completion Date:** 2026-10-24T23:55:00+05:30  
**Audit Stage:** Phase 0 Completed (Setup, Discovery, Architecture Mapping, Baseline Verification, Prioritization)  

---

## 1. Executive Summary

Phase 0 established a reproducible local development environment on Windows 11 with an isolated Python 3.12 virtual environment and audited the entire Dhwani repository on the `master` branch.

All claims in documentation, scripts, and commit histories were evaluated against real implementation files, hardware execution, and reproducible test runs.

### Headline Discoveries:
1. **The Software Foundations are Functional:**  
   The core audio pre-filtering (Energy VAD, spectral audio quality analyzer, handcrafted acoustic feature detector), the cryptographic SHA-256 hash chain, the ephemeral memory-zeroing privacy sandbox, and the FastAPI routing framework are solidly engineered and pass **60 out of 60 unit/integration tests** in 6.64 seconds.
2. **The 5-Model Neural Ensemble is Degraded to 1 Detector:**  
   The platform advertises a 5-model neural ensemble. However, in the current repository state, 4 out of 5 models fail to initialize due to missing `.onnx` files, causing `scripts/system_benchmark_test.py` to crash on step 1. Only the CPU-based `ACOUSTIC` detector actually runs during inference.
   *Crucial finding:* The official PyTorch weights for `AASIST.pth` (1.28 MB) and `AASIST-L.pth` (426 KB) **already exist in the repository** under `ai/aasist/models/weights/`, but the adapters hardcode a check for `.onnx` files that were never generated or committed.
3. **Architectural Disconnects Exist Across Subsystems:**  
   The audit identified two disjoint cryptographic audit hash chains (one in-memory in `security/middleware.py`, one on-disk in `backend/routes/incidents.py`), an unintegrated notification service whose dispatch function is never called in production, and an import rebinding bug causing `GET /api/system/status` to report `active_models: []`.
4. **Zero Phase 1 Fixes Applied:**  
   In strict adherence to Phase 0 constraints, no application logic was modified, no models were trained or retuned, and no production code was refactored.

---

## 2. What Actually Works vs What Remains Unverified or Blocked

### ✅ What Actually Works (Verified)
- **Fast VAD Pre-Filtering (`streaming/vad_gate.py`):** Bypasses digital silence and low-level noise floor (-85 dBFS) in ~0.25 ms.
- **Audio Quality Analyzer (`ai/acoustic/audio_quality.py`):** Computes SNR, clipping ratio, and spectral flatness in ~1.17 ms.
- **Handcrafted Acoustic Detector (`ai/acoustic/acoustic_detector.py`):** Pure NumPy/SciPy LFCC/spectral analysis in ~3.04 ms.
- **Cryptographic Provenance Token Binding (`security/hasher.py`):** Canonicalizes session and audio SHA-256 hashes.
- **Ephemeral Audio Privacy Sandbox (`security/privacy.py`):** Zeroes in-memory audio buffers immediately upon context manager exit.
- **TwiML Generation & Audio Decoding (`streaming/telephony/`):** Decodes G.711 u-law, masks caller phone numbers, and resamples to 16 kHz.
- **Automated Test Suite (`tests/`):** 60 out of 60 automated tests pass cleanly.
- **Frontend Type Safety (`frontend/`):** Full TypeScript compilation with `npx tsc --noEmit` exits with 0 errors.

### ⚠️ What is Partially Verified / Disconnected
- **Adaptive Reliability Fusion & Attribution:** Math and decision tables work when fed synthetic detector vectors, but have not run on real neural model outputs.
- **Telephony Inbound Streaming:** WebSocket handlers and rolling buffers pass simulated test chunks, but live calls require external ngrok tunnels and Twilio accounts.
- **Audit Persistence:** The chain math works, but two disconnected chain instances prevent a single source of forensic truth.
- **Unified Cyber Dashboard:** Next.js UI connects to backend WebSockets and polls APIs, but displays simulated initial call state when idle.

### ⛔ What is Blocked / Inoperative
- **System Benchmark Suite (`scripts/system_benchmark_test.py`):** Crashes at Step 1/8 due to `FileNotFoundError: AASIST-L model not found at models/aasist/aasist-l.onnx`.
- **W2V2-AASIST Neural Model:** Checkpoint `w2v2-aasist.onnx` (~1.26 GB) is not downloaded.
- **ECAPA-TDNN Speaker Consistency:** Checkpoint `models/speaker/ecapa512.onnx` is missing, and the engine lacks session-isolated state.
- **Multi-Channel Alert Dispatch:** `NotificationService.dispatch_security_alert()` is never called outside tests.
- **YouTube Media Ingestion:** Crashes due to missing `yt-dlp` package in `requirements.txt`.
- **System Telemetry:** `active_models` reports `[]` due to module import rebinding bug.

---

## 3. Environment Setup & Test Baseline Results

- **OS:** Windows 11 Home (64-bit)
- **Python:** Python 3.12.10 (isolated in `.venv` via `uv`)
- **Node.js:** v24.19.0 (installed via `npm ci` in `frontend/`)
- **GPU:** NVIDIA GeForce RTX 5060 Laptop GPU (Driver 610.88, CUDA 13.3)
- **Test Baseline:**  
  `$env:PYTHONPATH="." ; .\.venv\Scripts\pytest.exe tests/ -v`  
  **60 passed, 0 failed, 3 warnings in 6.64s**
- **Benchmark Baseline:**  
  `$env:PYTHONPATH="." ; .\.venv\Scripts\python.exe scripts/system_benchmark_test.py`  
  **Failed at Step 1/8 (FileNotFoundError on AASIST-L)**
- **Frontend Lint Baseline:**  
  `npm run lint` inside `frontend/`  
  **10 errors, 45 warnings (Exit code 1)**

---

## 4. Highest-Priority Risks (Top 5)

1. **DHW-ENG-001 (Critical): Missing Neural Model Weights Crash Benchmarks.**  
   Missing `.onnx` files reduce the advertised 5-model deepfake defense ensemble to a single handcrafted acoustic heuristic.
2. **DHW-ENG-002 (High): Fragmented Audit Chains.**  
   Two independent chain instances (one in-memory, one in `data/audit_ledger.jsonl`) prevent coherent forensic verification.
3. **DHW-ENG-003 (High): Disconnected Notification Dispatch.**  
   No SMS, WhatsApp, or Email alerts are sent when critical deepfakes are detected.
4. **DHW-SEC-004 & 005 (High): Zero Endpoint Authentication & Permissive CORS.**  
   All APIs, audit ledgers, and WebSockets are unauthenticated, and CORS uses `allow_origins=["*"]` with `allow_credentials=True`.
5. **DHW-ENG-007 (Medium): Shared Mutable State in Speaker Consistency.**  
   Singleton `SpeakerConsistencyEngine` shares vocal anchors across concurrent callers, creating cross-call contamination.

---

## 5. Recommended Phase 1 Scope (Actionable & Evidence-Based)

Phase 1 should focus on the **minimum viable set of changes required to make Dhwani functionally complete, benchmark-verified, and architecturally coherent**:

1. **Task 1.1: Restore AASIST & AASIST-L Detection Without Heavy Downloads**  
   - Add PyTorch inference fallbacks in `AASISTAdapter` and `AASISTLAdapter` using the existing `.pth` weights already committed in the repository (`ai/aasist/models/weights/`).  
   - Alternatively, add an automated ONNX export script (`scripts/export_weights.py`).
2. **Task 1.2: Resolve System Benchmark Crashes**  
   - Download `w2v2-aasist.onnx` via `scripts/download_models.py` or enable graceful skips with clear diagnostic reporting in `scripts/system_benchmark_test.py`.
3. **Task 1.3: Unify the Audit Ledger & Hydrate Incidents on Startup**  
   - Unify `_GLOBAL_PIPELINE.chain` and `incidents.py` onto a single singleton chain bound to `data/audit_ledger.jsonl`.  
   - Ensure `INCIDENT_RECORDS` hydratively restores from the ledger on startup.
4. **Task 1.4: Hook Up Multi-Channel Notification Alerts**  
   - Invoke `NotificationService.dispatch_security_alert()` when `risk_level == "HIGH"` in `streaming/telephony/twilio_websocket.py` and `backend/routes/media_analysis.py`.
5. **Task 1.5: Fix Developer Experience & Telemetry Bugs**  
   - Add `pytest.ini` with `pythonpath = .` so bare `pytest tests/` runs out of the box.  
   - Fix the module import rebinding bug in `backend/routes/system.py` so `active_models` reflects active detectors.  
   - Add `yt-dlp` to `requirements.txt`.  
   - Fix the 10 ESLint errors in `UnifiedCyberDashboard.tsx`.

---

## 6. Phase 0 Compliance & Scope Confirmation

- [x] Environment safely inspected before running commands.
- [x] No existing user files or branches overwritten or deleted.
- [x] Master branch confirmed (`a45e40aa6fec462cc770325b41802f8629e4b1f7`).
- [x] Isolated Python 3.12 `.venv` created; system Python untouched.
- [x] No secrets committed or printed.
- [x] All 60 automated tests executed and verified with exact outcomes.
- [x] Real-world benchmark crash documented empirically.
- [x] All 6 Phase 0 documentation deliverables created under `docs/phase-0/`.
- [x] **Explicit Confirmation:** Phase 0 was the sole phase executed. Zero Phase 1 feature fixes or application modifications were implemented.
