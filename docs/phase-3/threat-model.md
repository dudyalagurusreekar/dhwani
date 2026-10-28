# Phase 3: Comprehensive API, Streaming & Telephony Threat Model

**Document Version:** 1.0.0  
**Target:** Dhwani / EchoShield AI Enterprise Speech Security Platform  
**Date:** October 25, 2026  
**Auditor:** Senior Security Architect & DevOps Engineer  

---

## 1. Executive Summary

This threat model identifies and classifies vulnerabilities in Dhwani's application boundaries, API endpoints, WebSocket streams, and external webhook integrations. Each threat is classified by **Severity**, **Exploit Preconditions**, **Technical Impact**, and **Architectural Mitigation**.

---

## 2. Threat Classification Matrix

| Threat ID | Threat Category | Severity | Preconditions | Technical Impact | Target Mitigation |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **THREAT-01** | **Unauthenticated REST Endpoints** | **High** | Network access to Dhwani backend. | Unauthorized access to incident ledgers, forensic audit certificates, hardware telemetry, and triggering expensive neural inference. | Header-based API key & Bearer token authentication (`X-API-Key`, `Authorization`). |
| **THREAT-02** | **WebSocket Abuse & Flooding** | **High** | WebSocket connection to `/ws/audio` or `/ws/dashboard`. | Resource exhaustion, unauthenticated streaming, unbounded GPU/CPU cycles consumed by rogue clients. | Token-based handshake authentication, per-frame size caps (1 MB), and frame rate limits. |
| **THREAT-03** | **Permissive / Invalid CORS** | **Medium** | Victim visits malicious site in browser. | Insecure origin wildcards (`*`) combined with credentialed requests violate CORS spec and allow cross-origin data exposure. | Strict environment-configurable `ALLOWED_ORIGINS` allowlist; disallow `*` with credentials. |
| **THREAT-04** | **Twilio Webhook Spoofing & Replay** | **High** | Publicly accessible `/twilio/voice` endpoint. | Attacker forges fake caller IDs, injects fraudulent calls, manipulates incident records, and triggers outbound calls. | HMAC-SHA1 signature verification using `X-Twilio-Signature` and `TWILIO_AUTH_TOKEN`. |
| **THREAT-05** | **Oversized / Malformed Audio DoS** | **High** | Access to `/api/analyze/*`. | Worker process crashes via Out-of-Memory (OOM); CPU pegging on giant audio buffers (>100 MB). | Early `Content-Length` enforcement (25 MB max), audio header format validation, and max duration limit (300s). |
| **THREAT-06** | **Cross-Session State Leakage** | **High** | Concurrent WebSocket or REST sessions. | Vocal anchor embeddings or rolling buffers leak between callers, corrupting anti-spoofing verdicts. | Per-session isolated profiles, thread-safe locks, and deterministic cleanup hooks on disconnect. |
| **THREAT-07** | **Server-Side Request Forgery (SSRF)** | **High** | Access to `/api/analyze/youtube` or URL ingest. | Attacker probes cloud metadata (`169.254.169.254`), internal microservices, or loopback interfaces. | DNS resolution checks, strict blocking of private/loopback/link-local CIDRs, and YouTube domain whitelist. |
| **THREAT-08** | **Sensitive Data Exposure in Logs/Errors** | **Medium** | Attacker triggers 500 errors or reads logs. | Leaking API keys, internal file system paths, Twilio tokens, or raw voice recordings. | Structured error handling without internal trace leaks; ephemeral buffer zeroing; token redaction. |
| **THREAT-09** | **Algorithmic Inference DoS** | **Medium** | Repeated submission of high-frequency audio. | SincNet and Graph Attention layers monopolize host CPU threads, starving other callers. | Fast Energy VAD gating to bypass silent frames, upload duration limits, and concurrency bounds. |

---

## 3. Deep-Dive Threat Analysis

### 3.1 THREAT-01: Unauthenticated REST Endpoints
- **Affected Endpoints:**
  - `POST /api/analyze`, `POST /api/analyze/upload`, `POST /api/analyze/youtube`
  - `GET /api/incidents`, `GET /api/incidents/{incident_id}`
  - `GET /api/audit/trail`, `GET /api/audit/verify`, `GET /api/audit/certificate`
  - `GET /api/system/status`
- **Exploit Scenario:** An unauthenticated network attacker sends automated scripts to `/api/incidents`, downloading historical deepfake attack logs and victim phone numbers without credentials.
- **Mitigation Architecture:**
  - Define explicit public endpoints: `/health` (probes), `/` (metadata), `/twilio/voice` (secured via Twilio HMAC).
  - Protect all `/api/*` routes with `require_api_key` dependency.
  - Reject unauthorized requests with `401 Unauthorized` and `WWW-Authenticate: ApiKey`.

### 3.2 THREAT-02: WebSocket Connection Abuse
- **Affected Endpoints:** `/ws/audio`, `/ws/dashboard`
- **Exploit Scenario:** An attacker opens dozens of simultaneous persistent WebSocket connections, sending continuous 16 kHz random audio to force heavy PyTorch inference on CPU threads.
- **Mitigation Architecture:**
  - Enforce authentication during connection handshake (rejecting unauthorized sockets with close code `4001`).
  - Cap individual binary frames at `1 MB` (`MAX_WS_FRAME_SIZE`).
  - Limit total session duration and frames per session.

### 3.3 THREAT-03: CORS Misconfiguration
- **Vulnerability:** `backend/main.py` configured `allow_origins=["*"]` alongside `allow_credentials=True`.
- **W3C Standard Violation:** Browsers reject responses or allow malicious origins to query credentialed endpoints if headers are improperly configured.
- **Mitigation Architecture:**
  - Read `ALLOWED_ORIGINS` from environment (defaulting to safe local development origins: `http://localhost:3000`, `http://127.0.0.1:3000`).
  - If wildcard `*` is explicitly configured, force `allow_credentials=False`.

### 3.4 THREAT-04: Twilio Webhook Spoofing
- **Affected Endpoints:** `POST /twilio/voice`
- **Exploit Scenario:** Without validating `X-Twilio-Signature`, anyone on the Internet can send an HTTP POST pretending to be Twilio with `CallSid="FAKE_CALL_123"` and `From="+19999999999"`, causing Dhwani to log fraudulent incidents.
- **Mitigation Architecture:**
  - Extract `X-Twilio-Signature` and reconstruct the external request URL (accounting for reverse proxy headers `X-Forwarded-Proto` and `X-Forwarded-Host`).
  - Compute HMAC-SHA1 signature using `TWILIO_AUTH_TOKEN`. Reject mismatching requests with `403 Forbidden`.

### 3.5 THREAT-05: Oversized / Malformed Audio DoS
- **Vulnerability:** Endpoints called `await file.read()` into memory without pre-checking size or duration.
- **Mitigation Architecture:**
  - Pre-check `Content-Length` header against `MAX_UPLOAD_SIZE_BYTES` (25 MB).
  - Stream chunks with running byte counter to prevent spoofed `Content-Length` headers from bypassing checks.
  - Verify audio headers and enforce duration caps ($< 300$ seconds).

### 3.6 THREAT-06: Cross-Session State Leakage
- **Vulnerability:** Global speaker engine or shared rolling buffers retaining embeddings from previous calls.
- **Mitigation Architecture:**
  - Enforce thread-safe `session_profiles` keyed by `session_id`.
  - Wrap streaming handlers in `try ... finally` blocks to ensure `reset_session(session_id)` runs reliably on disconnect.

### 3.7 THREAT-07: Server-Side Request Forgery (SSRF)
- **Affected Endpoints:** `POST /api/analyze/youtube`
- **Exploit Scenario:** An attacker submits `http://169.254.169.254/latest/meta-data/` or `http://127.0.0.1:8000/internal` hoping the server will fetch internal resources.
- **Mitigation Architecture:**
  - Enforce URL protocol to strictly `https` or `http`.
  - Resolve DNS host and inspect all IP addresses against private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and cloud metadata IP ranges.
  - Enforce domain whitelist for YouTube sources.

### 3.8 THREAT-08 & 09: Information Leakage & DoS
- Standardize JSON error responses to avoid leaking local filesystem paths or framework tracebacks.
- Mask API tokens and secrets in all logs.
- Protect CPU cycles using the Energy VAD gate to bypass silence before invoking PyTorch neural models.
