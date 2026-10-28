# Dhwani Phase 0: Prioritized Findings Register
**Project:** Dhwani (ध्वनि) / EchoShield AI  
**Audit Target:** `master` Branch (`a45e40aa6fec462cc770325b41802f8629e4b1f7`)  
**Audit Scope:** Phase 0 Discovery, Architecture Verification, Security & Reliability Review  

---

## Findings Summary by Severity

| Severity | Count | Primary Focus Areas |
| :--- | :---: | :--- |
| **Critical** | 1 | Missing ONNX models causing benchmark crashes and single-model degradation |
| **High** | 4 | Audit chain fragmentation, unintegrated notifications, unauthenticated endpoints, permissive CORS |
| **Medium** | 6 | Webhook spoofing, shared mutable state, telemetry rebinding bug, missing dependencies, test runner pathing, DoS upload limits |
| **Low** | 3 | Frontend ESLint errors, synthetic UI telemetry, absent CI/CD pipelines |
| **TOTAL** | **14** | |

---

## Detailed Findings Register

### DHW-ENG-001: Missing ONNX Model Checkpoints Cause Benchmark Crashes and Single-Model Ensemble Degradation
- **Severity:** Critical
- **Confidence:** Confirmed
- **Affected Component:** Core AI Ensemble (`ai/aasist/`, `ai/ssl_detector/`, `ai/speaker/`, `scripts/system_benchmark_test.py`)
- **Evidence & File/Function:**
  - `scripts/system_benchmark_test.py` line 119: crashes with `FileNotFoundError: AASIST-L model not found at models/aasist/aasist-l.onnx`.
  - `backend/services/detector.py` lines 58-82: fails to load `W2V2-AASIST`, `AASIST`, `AASIST-L`, and `ECAPA-TDNN`, falling back to `ACOUSTIC` detector alone.
  - `ai/aasist/aasist_adapter.py` lines 57-63: expects `models/aasist/aasist.onnx`, completely ignoring `models/aasist/AASIST.pth` (1.28 MB) and `ai/aasist/models/weights/AASIST.pth` present in the repository.
  - `ai/aasist/aasist_l_adapter.py` lines 54-60: expects `models/aasist/aasist-l.onnx`, ignoring `ai/aasist/models/weights/AASIST-L.pth` (426 KB) present in the repository.
- **User / System Impact:**
  - Full system benchmark cannot complete.
  - The platform operates with only 1 handcrafted acoustic model instead of the advertised 5-model neural ensemble, severely impairing deepfake detection robustness.
- **Recommended Remediation:**
  - Implement a PyTorch inference fallback or export script (`scripts/export_aasist_to_onnx.py`) to convert existing `.pth` checkpoints to `.onnx`.
  - Execute `scripts/download_models.py` to acquire `w2v2-aasist.onnx`.
  - Provide download or export script for `ecapa512.onnx`.
- **Dependencies & Prerequisites:** PyTorch 2.x, ONNX Runtime.
- **Verification Test:** Run `python scripts/system_benchmark_test.py` and verify all 8 sections pass without `FileNotFoundError`.
- **Target Resolution Phase:** Phase 1 (Model Pipeline & Benchmark Remediation).

---

### DHW-ENG-002: Dual Disconnected Audit Hash Chains Cause Fragmented Provenance
- **Severity:** High
- **Confidence:** Confirmed
- **Affected Component:** Security Ledger & REST APIs (`security/pipeline.py`, `backend/routes/incidents.py`, `backend/routes/audit.py`)
- **Evidence & File/Function:**
  - `backend/routes/analyze.py` (Line 48) writes events to `_GLOBAL_PIPELINE.chain` (in-memory by default).
  - `backend/routes/audit.py` (Lines 16, 28, 36) inspects `_GLOBAL_PIPELINE.chain`.
  - `backend/routes/incidents.py` (Line 24) maintains its own independent `audit_chain = AuditHashChain(persistence_file="data/audit_ledger.jsonl")`.
  - `INCIDENT_RECORDS: Dict[str, Dict[str, Any]] = {}` in `incidents.py` is an in-memory dictionary never restored from `data/audit_ledger.jsonl`.
- **User / System Impact:**
  - Audio uploads analyzed via `/api/analyze` do not appear in `/api/incidents`.
  - Server restarts wipe the incident registry completely, leaving the dashboard blank while `data/audit_ledger.jsonl` contains orphaned events.
  - Cryptographic verification certificates exported via `/api/audit/certificate` fail to reflect incidents recorded in the ledger.
- **Recommended Remediation:**
  - Unify the application on a single singleton `AuditHashChain` bound to a persistent ledger (`data/audit_ledger.jsonl`).
  - Hydrate `INCIDENT_RECORDS` from the persistent ledger on backend startup.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Upload an audio file via `/api/analyze`, trigger an incident, restart the backend, and verify `/api/incidents` and `/api/audit/trail` return matching, intact event histories.
- **Target Resolution Phase:** Phase 1 (Core Persistence & Architecture Unification).

---

### DHW-ENG-003: Multi-Channel Notification Service is Disconnected from Production Detection Routes
- **Severity:** High
- **Confidence:** Confirmed
- **Affected Component:** Alerting Subsystem (`backend/notifications/service.py`)
- **Evidence & File/Function:**
  - Global search confirms `dispatch_security_alert` is only called in `tests/test_notifications.py` (Lines 53, 67).
  - Neither `backend/routes/analyze.py`, `backend/routes/media_analysis.py`, `backend/routes/incidents.py`, nor `streaming/telephony/twilio_websocket.py` calls `NotificationService`.
- **User / System Impact:**
  - Critical voice cloning attacks and telephony breaches trigger zero SMS, WhatsApp, or Email alerts in production.
  - Advertised multi-channel alerting capability is completely inoperative in live deployment.
- **Recommended Remediation:**
  - Wire `NotificationService.dispatch_security_alert()` into `streaming/telephony/twilio_websocket.py` and `backend/routes/media_analysis.py` when `risk_level == "HIGH"` or policy requires mitigation.
- **Dependencies & Prerequisites:** DHW-ENG-002 (Unified session and incident IDs).
- **Verification Test:** Simulate a high-risk voice stream via WebSocket and verify SMS/Email dry-run logs are generated with the incident payload.
- **Target Resolution Phase:** Phase 1 (Alerting & Telephony Integration).

---

### DHW-SEC-004: Lack of Authentication and Authorization on Sensitive REST and WebSocket Endpoints
- **Severity:** High
- **Confidence:** Confirmed
- **Affected Component:** API Security (`backend/main.py`, `backend/routes/`)
- **Evidence & File/Function:**
  - All routes in `backend/main.py` (`/api/incidents`, `/api/audit/*`, `/api/system/status`, `/api/analyze/*`, `/ws/dashboard`, `/twilio/media`) have zero authentication dependencies, API keys, or JWT checks.
- **User / System Impact:**
  - Any unauthorized party on the network can query the entire audit trail, download cryptographic certificates, view hardware telemetry, list security incidents, trigger file uploads, or connect to the real-time telemetry WebSocket.
- **Recommended Remediation:**
  - Implement API key or Bearer token middleware (`security/middleware.py`) for management, incident, and audit endpoints.
- **Dependencies & Prerequisites:** Frontend authentication integration.
- **Verification Test:** Verify unauthenticated requests to `/api/incidents` return `401 Unauthorized`.
- **Target Resolution Phase:** Phase 2 (Enterprise Security Hardening).

---

### DHW-SEC-005: Permissive and Invalid CORS Configuration
- **Severity:** High
- **Confidence:** Confirmed
- **Affected Component:** Web Security (`backend/main.py`)
- **Evidence & File/Function:**
  - `backend/main.py` lines 44-50:
    ```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ```
- **User / System Impact:**
  - Combining `allow_origins=["*"]` with `allow_credentials=True` violates the W3C CORS specification and creates cross-origin leakage vulnerabilities if cookies or credentials are used.
- **Recommended Remediation:**
  - Specify explicit allowed origins (e.g. `http://localhost:3000`, `http://127.0.0.1:3000`, or environment-configured frontend domains).
- **Dependencies & Prerequisites:** `.env` CORS origin configuration.
- **Verification Test:** Test CORS preflight response headers from an unauthorized external origin.
- **Target Resolution Phase:** Phase 1 (API Configuration Hardening).

---

### DHW-SEC-006: Missing Twilio Webhook Signature Verification (`X-Twilio-Signature`)
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** Telephony Security (`backend/routes/twilio_routes.py`)
- **Evidence & File/Function:**
  - `backend/routes/twilio_routes.py` lines 14-51: `POST /twilio/voice` parses `Form` parameters directly without validating `X-Twilio-Signature` using `twilio.request_validator.RequestValidator`.
- **User / System Impact:**
  - An attacker can forge HTTP POST requests to `/twilio/voice`, inject fraudulent `CallSid` and `From` metadata, and manipulate system telephony logs.
- **Recommended Remediation:**
  - Add Twilio webhook verification decorator or middleware validating the signature against `TWILIO_AUTH_TOKEN` when not in dry-run mode.
- **Dependencies & Prerequisites:** Twilio SDK dependency.
- **Verification Test:** Send unauthenticated POST request to `/twilio/voice` and verify rejection with `403 Forbidden`.
- **Target Resolution Phase:** Phase 2 (Telephony Hardening).

---

### DHW-ENG-007: Shared Mutable State in Global Detector Singletons
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** Concurrency & Session Isolation (`ai/speaker/speaker_consistency.py`, `backend/services/detector.py`)
- **Evidence & File/Function:**
  - `ai/speaker/speaker_consistency.py` lines 60-62: `self.anchor_embedding` and `self.recent_embeddings` are stored as instance variables.
  - `backend/services/detector.py` line 45: instantiates `_SPEAKER_ENGINE` as a module-level global singleton.
- **User / System Impact:**
  - Concurrent calls or audio analyses will overwrite each other's vocal anchor embeddings, corrupting speaker verification for all active sessions.
- **Recommended Remediation:**
  - Refactor `SpeakerConsistencyEngine` to store session-keyed profiles (`Dict[session_id, SessionProfile]`) with TTL-based expiration and thread-safe locking.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Run concurrent simulated calls in two separate threads and verify session anchor isolation.
- **Target Resolution Phase:** Phase 1 (Concurrency & Session Safety).

---

### DHW-ENG-008: Module Import Rebinder Bug in System Telemetry Endpoint
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** Hardware Telemetry (`backend/routes/system.py`)
- **Evidence & File/Function:**
  - `backend/routes/system.py` line 12: `from backend.services.detector import _AASIST_MODEL, ...` imports local copies of `None`.
  - When `_init_detectors()` rebinds the global variables in `detector.py`, `system.py` still holds `None`.
  - Verification test confirmed: `GET /api/system/status` returns `"active_models": []` even when `_ACOUSTIC_MODEL` is operational.
- **User / System Impact:**
  - The frontend dashboard displays no active models online, misrepresenting system health.
- **Recommended Remediation:**
  - Access detectors dynamically via helper function `detector.get_active_detectors()` or import the module `detector` directly.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Call `GET /api/system/status` after initialization and verify `active_models` lists all initialized detectors.
- **Target Resolution Phase:** Phase 1 (Bug Fix & Telemetry Integrity).

---

### DHW-ENG-009: Missing `yt-dlp` Dependency Breaks YouTube Ingestion Endpoint
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** Media Ingestion (`ai/common/media_sources.py`, `backend/routes/media_analysis.py`)
- **Evidence & File/Function:**
  - `ai/common/media_sources.py` line 181: `import yt_dlp` inside `YouTubeAudioSource.load_audio()`.
  - `requirements.txt` does not declare `yt-dlp`.
- **User / System Impact:**
  - Submitting any YouTube URL to `POST /api/analyze/youtube` fails with a 501/500 error.
- **Recommended Remediation:**
  - Add `yt-dlp>=2024.0.0` to `requirements.txt`.
- **Dependencies & Prerequisites:** Python environment.
- **Verification Test:** Submit a sample URL and verify audio track extraction.
- **Target Resolution Phase:** Phase 1 (Dependency & Ingestion Completion).

---

### DHW-ENG-010: Pytest Test Collection Fails Without Explicit `PYTHONPATH`
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** Developer Workflow & Test Reproducibility (`tests/`)
- **Evidence & File/Function:**
  - Running `pytest tests/ -v` directly fails with:
    `ModuleNotFoundError: No module named 'backend'`
    `ModuleNotFoundError: No module named 'security'`
  - Only succeeds when `$env:PYTHONPATH="."` is manually exported.
- **User / System Impact:**
  - New developers or CI runners following standard `pytest tests/` instructions will encounter immediate test collection failure.
- **Recommended Remediation:**
  - Add a root `pyproject.toml` or `pytest.ini` with `pythonpath = "."`.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Run `pytest tests/ -v` in a bare terminal without setting `PYTHONPATH`.
- **Target Resolution Phase:** Phase 1 (Tooling & Developer Experience).

---

### DHW-ENG-011: Unbounded File Uploads Cause Memory Exhaustion (DoS) Risk
- **Severity:** Medium
- **Confidence:** Confirmed
- **Affected Component:** File Upload Ingestion (`backend/routes/analyze.py`, `backend/routes/media_analysis.py`)
- **Evidence & File/Function:**
  - `backend/routes/analyze.py` line 30: `audio_bytes = await file.read()` reads entire file into memory with no size boundary.
  - `backend/routes/media_analysis.py` line 59: `content = await file.read()` has no size limit.
- **User / System Impact:**
  - A client uploading a multi-gigabyte payload can crash the Uvicorn worker process via Out-Of-Memory (OOM).
- **Recommended Remediation:**
  - Enforce a maximum file size limit (e.g. 50 MB) via chunked streaming validation.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Upload a 100 MB file and verify `413 Payload Too Large` is returned before buffering.
- **Target Resolution Phase:** Phase 1 (Ingestion Hardening).

---

### DHW-ENG-012: Frontend ESLint Violations (10 Errors, 45 Warnings)
- **Severity:** Low
- **Confidence:** Confirmed
- **Affected Component:** Frontend Quality (`frontend/src/components/dashboard/UnifiedCyberDashboard.tsx`)
- **Evidence & File/Function:**
  - `npm run lint` fails with exit code 1 (55 problems).
  - Line 191: `fetchStatusAndIncidents();` called synchronously within `useEffect` triggering cascading renders (`react-hooks/set-state-in-effect`).
  - Multiple `@typescript-eslint/no-explicit-any` and unused variable warnings.
- **User / System Impact:**
  - Prevents clean production bundle building (`next build`).
- **Recommended Remediation:**
  - Refactor `useEffect` in `UnifiedCyberDashboard.tsx` to handle async fetching properly; replace `any` with strict TypeScript interfaces.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Run `npm run lint` and verify zero errors.
- **Target Resolution Phase:** Phase 1 (Frontend Polish & Build Integrity).

---

### DHW-ENG-013: Hardcoded Simulated Live Call Telemetry Masks Real System State
- **Severity:** Low
- **Confidence:** Confirmed
- **Affected Component:** Dashboard UI (`frontend/src/components/dashboard/UnifiedCyberDashboard.tsx`, `frontend/src/data/dashboardData.ts`)
- **Evidence & File/Function:**
  - `UnifiedCyberDashboard.tsx` lines 68-98: initial `liveCall` state hardcodes `CA-981240-LIVE`, 78% risk, and fake model scores.
  - `dashboardData.ts`: hardcodes marketing metrics ("12,584 voice interactions", "98.4% accuracy").
- **User / System Impact:**
  - Users viewing the dashboard without an active call see simulated high-risk attack telemetry, creating confusion regarding actual system state.
- **Recommended Remediation:**
  - Set default state to an idle placeholder ("NO ACTIVE CALL") until live WebSocket events arrive.
- **Dependencies & Prerequisites:** None.
- **Verification Test:** Open dashboard with backend idle; verify UI displays idle state.
- **Target Resolution Phase:** Phase 1 (UI Telemetry Polish).

---

### DHW-ENG-014: Absent CI/CD Pipelines and Automated Build Verification
- **Severity:** Low
- **Confidence:** Confirmed
- **Affected Component:** DevOps & Repository Health (`.github/workflows/`)
- **Evidence & File/Function:**
  - No `.github/` directory or CI workflows exist in the repository.
- **User / System Impact:**
  - Pull requests and commits can introduce silent regressions without automated lint, test, or build validation.
- **Recommended Remediation:**
  - Add GitHub Actions workflow (`.github/workflows/ci.yml`) running pytest and frontend type-checking on PRs to `master`.
- **Dependencies & Prerequisites:** DHW-ENG-010 (pytest.ini).
- **Verification Test:** Push a commit or trigger workflow dispatch.
- **Target Resolution Phase:** Phase 2 (DevOps & CI/CD Setup).
