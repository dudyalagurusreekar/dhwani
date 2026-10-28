# Dhwani Phase 0: Repository Baseline Report
**Target Repository:** `https://github.com/dudyalagurusreekar/dhwani.git`  
**Current Active Branch:** `master`  
**Commit SHA:** `a45e40aa6fec462cc770325b41802f8629e4b1f7`  
**Commit Date:** Sun Sep 20 16:01:42 2026 +0530  
**Commit Message:** `docs: create comprehensive README explaining recent architectural changes`  
**Working Tree Status:** Clean (`nothing to commit, working tree clean`)  

---

## 1. Source & Branch Verification

```text
Commit SHA:      a45e40aa6fec462cc770325b41802f8629e4b1f7
Remote URL:      https://github.com/dudyalagurusreekar/dhwani.git
Checked-out Ref: refs/heads/master
Tracking Remote: refs/remotes/origin/master
Working Tree:    Clean (0 uncommitted changes, 0 untracked files)
```

### Remote Branch Topology
```text
* master (HEAD -> refs/heads/master)
  remotes/origin/HEAD -> origin/feature/member2-speaker-consistency
  remotes/origin/backend
  remotes/origin/feature/member2-speaker-consistency
  remotes/origin/frontend
  remotes/origin/guru
  remotes/origin/main
  remotes/origin/master
  remotes/origin/pintu
```

> [!IMPORTANT]
> **Default Branch Observation:**  
> When initially cloned, the remote repository checked out `feature/member2-speaker-consistency` by default (commit `bd51723`). In strict compliance with audit instructions, branch `master` was explicitly selected, checked out, and verified.

---

## 2. Branch Comparison: `master` vs `guru`

A formal non-destructive commit and diff analysis was conducted between `origin/master` and `origin/guru`:

```powershell
git merge-base origin/master origin/guru
# Output: c2566d00cdd10f7cdf624fb1f4e022785312d6cc (origin/guru HEAD)

git log --left-right --oneline origin/master...origin/guru
# Output:
# < a45e40a docs: create comprehensive README explaining recent architectural changes
# < 4094860 feat: update telemetry streaming, incident management, schemas, and live risk dashboard
```

### Commit Lineage
`origin/guru` is an exact direct ancestor of `origin/master`.  
`origin/master` is **2 commits ahead** of `origin/guru` with **zero diverging commits**.

### File Diff Analysis (`origin/guru` -> `origin/master`)

| Changed File | Insertions / Deletions | Functional Impact & Assessment |
| :--- | :--- | :--- |
| `backend/routes/incidents.py` | +2 / -2 | **Bug Fix:** Fixed attribute mismatch on `ChainVerificationReport`: changed `report.tampered_index` to `report.tampered_event_seq` and `report.error_message` to `report.error_reason`. Matches actual schema definition. |
| `security/schemas.py` | +2 / 0 | **Schema Extension:** Added `EventType.RISK_ASSESSMENT = "RISK_ASSESSMENT"` and `EventType.VERIFICATION_STEP = "VERIFICATION_STEP"` to `EventType` Enum. |
| `streaming/telephony/twilio_websocket.py` | +7 / -2 | **Bug Fix & Enhancement:** Fixed invalid keyword argument in `VADGate` initialization (`active_frame_ratio_threshold=0.25`), added missing `await` to `detect_voice(window)`, and passed `audio_quality` to `assess_risk()`. |
| `frontend/.../UnifiedCyberDashboard.tsx` | +183 / -1 | **UI Enhancement:** Added live risk score bar, model consensus box, attack attribution display, WebSocket status indicator, and neural score breakdown cards to the live call dashboard view. |
| `README.md` | +58 / -105 | **Documentation:** Updated architecture, directory structure, system prerequisites, and setup instructions. |

**Verdict:** All changes in `master` represent strictly additive bug fixes, schema completions, and telemetry improvements over `guru`. `master` is the correct audit target.

---

## 3. High-Level Repository Architecture

```text
dhwani/
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git exclusion rules (ignores .venv, .env, large onnx)
├── README.md                          # Project documentation and getting-started guide
├── acoustic_test.wav                  # Verification audio clip (128 KB)
├── microphone_test.wav                # Verification audio clip (160 KB)
├── real_speech.wav                    # Reference human speech audio clip (434 KB)
├── requirements.txt                   # Core Python dependencies
├── requirements-lock.txt              # Frozen Python dependencies (UTF-16LE, 107 pkgs)
├── run_all.bat                        # Windows one-click dual launcher (backend + frontend)
├── start_dhwani.bat                   # Wrapper for run_all.bat
├── ai/                                # AI Model Implementations & Adapters
│   ├── aasist/                        # Official AASIST & AASIST-L graph attention models
│   │   ├── aasist_adapter.py          # Standardized BaseDetector adapter (looks for ONNX)
│   │   ├── aasist_l_adapter.py        # Standardized BaseDetector adapter (looks for ONNX)
│   │   └── models/weights/            # Tracked PyTorch weights: AASIST.pth, AASIST-L.pth
│   ├── acoustic/                      # Handcrafted Spectral & Acoustic Detectors
│   │   ├── acoustic_detector.py       # LFCC, high-frequency energy ratio, kurtosis (NumPy/SciPy)
│   │   └── audio_quality.py           # Spectral SNR, flatness, clipping analyzer
│   ├── common/                        # Common pipeline, media sources, and GPU utilities
│   │   ├── common_pipeline.py         # UnifiedMediaPipeline orchestrator
│   │   ├── media_sources.py           # FileAudioSource, VideoAudioSource, YouTubeAudioSource
│   │   ├── attack_attribution.py      # Attribution engine (TTS vs VC vs Replay)
│   │   └── tiered_inference.py        # GPU/CPU tiered execution manager
│   ├── prevention/                    # Active disruption & honeypot modules
│   │   ├── call_interceptor.py        # Policy evaluator (Allow, Honeypot, Disruption, Terminate)
│   │   └── honeypot.py                # Acoustic delay and challenge-response engine
│   ├── speaker/                       # Speaker consistency & identity verification
│   │   └── speaker_consistency.py     # ECAPA-TDNN 192-dim embedding similarity engine
│   ├── ssl_detector/                  # Self-supervised deep learning detectors
│   │   ├── w2v2_aasist_adapter.py     # W2V2-AASIST adapter for Wav2Vec2 + GAT
│   │   └── w2v2_aasist_detector.py    # Raw ONNX inference wrapper
│   └── watermark/                     # Acoustic watermarking engine
├── backend/                           # FastAPI REST & WebSocket Backend
│   ├── main.py                        # FastAPI application entry point, CORS, and route registration
│   ├── notifications/                 # Multi-channel incident notifications
│   │   ├── service.py                 # Central dispatch coordinator with cooldown deduplication
│   │   └── providers/                 # Twilio SMS, WhatsApp, Email (SMTP), and Console providers
│   ├── routes/                        # REST API Routers
│   │   ├── health.py                  # GET /health
│   │   ├── analyze.py                 # POST /api/analyze (raw audio file analysis)
│   │   ├── media_analysis.py          # POST /api/analyze/upload & /api/analyze/youtube
│   │   ├── incidents.py               # GET /api/incidents, /verify/chain, /verification
│   │   ├── audit.py                   # GET /api/audit/verify, /trail, /latest, /certificate
│   │   ├── system.py                  # GET /api/system/status (GPU/CPU/models telemetry)
│   │   ├── sessions.py                # Session management routes
│   │   └── twilio_routes.py           # POST /twilio/voice (inbound TwiML webhook)
│   ├── services/                      # Business logic services
│   │   ├── detector.py                # Multi-model inference coordinator
│   │   └── risk_engine.py             # Risk calculation, consensus, and policy mapping
│   └── websocket/                     # WebSocket endpoints
│       ├── audio.py                   # Chunked real-time audio WebSocket
│       └── dashboard.py               # Live dashboard telemetry broadcaster
├── docs/                              # System documentation & setup guides
├── frontend/                          # Next.js 16 Unified Cyber Dashboard
│   ├── package.json                   # Next.js, React 19, TailwindCSS v4, Three.js
│   ├── package-lock.json              # Frozen npm dependencies
│   ├── next.config.ts                 # Next.js configuration
│   └── src/                           # Frontend source code
│       ├── app/                       # Next.js App Router (page.tsx, layout.tsx, globals.css)
│       ├── components/                # React UI components (UnifiedCyberDashboard, etc.)
│       └── data/                      # Dashboard mockup & initial telemetry data
├── models/                            # Model weight storage directories
│   ├── aasist/                        # Contains AASIST.pth (1.28 MB); missing aasist.onnx
│   ├── speaker/                       # Missing ecapa512.onnx
│   ├── ssl/                           # .gitkeep
│   └── w2v2_aasist/                   # Missing w2v2-aasist.onnx (~1.26 GB)
├── risk_engine/                       # Core Risk & Scoring Algorithms
│   ├── adaptive_fusion.py             # Reliability-weighted multi-model fusion
│   ├── model_agreement.py             # Consensus evaluation (Unanimous, Majority, Conflicted)
│   ├── normalizer.py                  # Score normalization utilities
│   ├── risk_engine.py                 # Temporal smoothing (EMA) and state escalation
│   └── temporal.py                    # Temporal tracking utilities
├── scripts/                           # Benchmarking & Asset Management Scripts
│   ├── download_models.py             # Hugging Face downloader for W2V2-AASIST ONNX
│   └── system_benchmark_test.py       # Exhaustive 8-section system benchmark suite
├── security/                          # Security, Provenance & Audit Ledger
│   ├── audit_chain.py                 # Cryptographic SHA-256 AuditHashChain
│   ├── event_schema.py                # SecurityEvent schema creation and validation
│   ├── hash_chain.py                  # Alternative HashChain implementation
│   ├── hasher.py                      # AudioHasher (audio, metadata, and provenance tokens)
│   ├── hashing.py                     # Standalone hashing utilities
│   ├── integrity.py                   # Tamper detection and chain validation
│   ├── middleware.py                  # FastAPI dependency and singleton pipeline accessor
│   ├── pipeline.py                    # DhwaniProvenancePipeline (7-stage security orchestrator)
│   ├── privacy.py                     # EphemeralAudioBuffer (memory-zeroing context manager)
│   ├── risk_engine.py                 # Security-domain RiskEngine
│   └── schemas.py                     # Core Pydantic dataclasses & Enums
├── streaming/                         # Telephony & Live Streaming Engine
│   ├── capture.py                     # Microphone capture
│   ├── live_risk_pipeline.py          # Real-time streaming pipeline
│   ├── telephony/                     # Twilio G.711 u-law telephony engine
│   │   ├── audio_decoder.py           # G.711 u-law to 16 kHz float32 resampler
│   │   ├── call_session.py            # CallSession rolling buffer & privacy masking
│   │   ├── twilio_websocket.py        # WebSocket consumer for Twilio media stream
│   │   └── twiml.py                   # TwiML generation helper
│   └── vad_gate.py                    # EnergyVADGate & VADGate
└── tests/                             # Automated Test Suite (13 test modules)
```

---

## 4. Automated Test Suite Baseline Execution

The automated test suite was executed in the clean isolated Python 3.12 environment using pytest:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe tests/ -v
```

### Test Outcome Summary

| Metric | Result |
| :--- | :--- |
| **Total Test Files** | 13 test files |
| **Total Test Items** | 60 test cases |
| **Passed** | **60 (100.0%)** |
| **Failed** | **0** |
| **Skipped** | **0** |
| **Errors** | **0** |
| **Warnings** | 3 RuntimeWarnings (`scipy.stats.kurtosis` moment calculation in `acoustic_detector.py:99`) |
| **Execution Duration** | 6.64 seconds |

### Module-by-Module Test Breakdown

| Test File | Test Case Count | Status | Scope Tested |
| :--- | :---: | :---: | :--- |
| `tests/test_api_endpoints.py` | 5 | **PASS** | REST endpoints (`/health`, `/api/system/status`, `/api/incidents`, `/twilio/voice`, `/api/analyze/upload`) |
| `tests/test_audit_chain.py` | 6 | **PASS** | `AuditHashChain` append, persistence, reload, and tamper detection |
| `tests/test_backend_api.py` | 9 | **PASS** | Backend REST endpoints with cryptographic provenance headers |
| `tests/test_hash_chain.py` | 2 | **PASS** | Sequential linking and disk save/load in `HashChain` |
| `tests/test_hasher.py` | 6 | **PASS** | `AudioHasher` equivalence, provenance token binding, and metadata hashing |
| `tests/test_hashing.py` | 4 | **PASS** | SHA-256 determinism, audio file hashing, and mismatch detection |
| `tests/test_integrity.py` | 6 | **PASS** | Tampering detection on broken pointers, deleted events, modified payload |
| `tests/test_notifications.py` | 3 | **PASS** | Console provider, cooldown deduplication, and Twilio SMS dry-run |
| `tests/test_pipeline.py` | 2 | **PASS** | Full 7-stage provenance pipeline execution and sequential chunks |
| `tests/test_privacy.py` | 4 | **PASS** | Zero raw audio retention in audit events and automatic buffer purge |
| `tests/test_risk_engine.py` | 4 | **PASS** | Threshold classification, duration penalty, and stateful session escalation |
| `tests/test_telephony_audio.py` | 5 | **PASS** | G.711 u-law decoding, 8k to 16k resampling, phone masking, TwiML generation |
| `tests/test_unified_media.py` | 4 | **PASS** | File source loading, pipeline on `real_speech.wav`, video extension check |

> [!WARNING]
> **Test Suite Scope Limitation:**  
> While all 60 tests pass, **zero tests evaluate real deep neural network inference on ONNX models** (`W2V2-AASIST`, `AASIST`, `AASIST-L`, or `ECAPA-TDNN`). The existing test suite verifies cryptographic hash chains, schema validation, audio decoders, and mock pipelines, but does not validate real-world deepfake classification accuracy.

---

## 5. System Benchmark Execution Baseline

The repository provides an end-to-end benchmarking script (`scripts/system_benchmark_test.py`).  
Execution command:
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts/system_benchmark_test.py
```

### Benchmark Results & Premature Termination

```text
======================================================================
 ECHOSHIELD AI -- FULL SYSTEM BENCHMARK & ARCHITECTURE VERIFICATION
======================================================================
Compute Device: CPU
Initial VRAM:   Allocated: 0.0 MB | Reserved: 0.0 MB

[1/8] Profiling Individual Model Latencies & Throughput...
  [PASS] VAD Pre-Filter:        Median: 0.25 ms | Range: [0.18-0.43] ms
  [PASS] Audio Quality:         Median: 1.17 ms | Range: [1.11-1.51] ms
  [PASS] Acoustic Detector:     Median: 3.04 ms | Range: [2.54-6.18] ms
Traceback (most recent call last):
  File "scripts/system_benchmark_test.py", line 310, in <module>
    main()
  File "scripts/system_benchmark_test.py", line 119, in main
    aasist_l = AASISTLAdapter()
  File "ai/aasist/aasist_l_adapter.py", line 57, in __init__
    raise FileNotFoundError(
FileNotFoundError: AASIST-L model not found at models/aasist/aasist-l.onnx.
```

**Benchmark Assessment:**  
- Handcrafted CPU pre-filters (Energy VAD, Audio Quality Analyzer, and Acoustic Detector) run with ultra-low latency (< 3.1 ms).
- Execution crashes on the very first neural model adapter (`AASISTLAdapter`) due to missing `.onnx` model files. Sections 2 through 8 never execute.

---

## 6. Frontend Compilation & Lint Baseline

### TypeScript Type-Checking
```powershell
cd frontend
npx tsc --noEmit
```
**Outcome:** Exited with code `0`. All TypeScript types, JSX elements, and imports compile cleanly with zero errors.

### ESLint Check
```powershell
npm run lint
```
**Outcome:** Exited with code `1` (55 problems: 10 errors, 45 warnings).  
Key errors:
- `UnifiedCyberDashboard.tsx:191`: Calling `fetchStatusAndIncidents()` synchronously in an effect causes cascading state updates (`react-hooks/set-state-in-effect`).
- `UnifiedCyberDashboard.tsx`: Multiple explicit `any` types violating `@typescript-eslint/no-explicit-any`.
- Multiple components have unused imports and variables (`@typescript-eslint/no-unused-vars`).

---

## 7. Continuous Integration & Docker Audit

- **CI Workflows:** Neither `.github/workflows/` nor any CI configuration files exist in the repository. Pull requests and commits currently have no automated CI validation.
- **Containerization:** No `Dockerfile` or `docker-compose.yml` exists. All services currently run directly on the host OS via shell/batch scripts.
