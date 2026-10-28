# Phase 3.2: Deployment-Readiness Verification Report

**Document Version:** 1.0.0  
**Verification Date:** October 25, 2026  
**Auditor:** Principal AI/DevOps Security Engineer & System Architect  
**Target Repository:** Dhwani / EchoShield AI Voice Anti-Spoofing Platform  
**Target Branch:** `feature/phase-1-inference-foundation`  
**Base Commit SHA:** `a45e40aa6fec462cc770325b41802f8629e4b1f7`  
**Deployment Verdict:** **`READY WITH LIMITATIONS`**  

---

## 1. Repository Safety & Starting State

Before undertaking the Phase 3.2 deployment-readiness verification, the repository state was inspected:
- **Active Branch:** `feature/phase-1-inference-foundation`
- **HEAD Commit:** `a45e40aa6fec462cc770325b41802f8629e4b1f7`
- **Working Tree Integrity:** All uncommitted changes from Phase 1 (deep inference foundation), Phase 2 (evaluation framework & calibration), Phase 3 (API security & streaming hardening), and Phase 3.1 (independent security review) have been strictly preserved.
- **Change Discipline:** No commits, branch switches, resets, stash operations, or cleanups were performed.

---

## 2. Production Authentication Verification

### 2.1 Application Startup & Route Guard Tracing
The application startup in `backend/main.py` was traced across all REST and WebSocket routes:
- **Public Endpoints (Unauthenticated):**
  - `GET /health` — Liveness & readiness probe for container orchestrators. Returns `{ "status": "ok", "app": "Dhwani / EchoShield AI" }`. Exposes no secrets, tokens, or PII.
  - `GET /` — Root service metadata and public route catalog.
  - `POST /twilio/voice` — Inbound telephony webhook from Twilio Programmable Voice. Authenticated via HMAC-SHA1 signature verification using `TWILIO_AUTH_TOKEN`.
- **Protected REST API Endpoints:**
  - All routes mounted under `/api/*` (`/api/analyze/*`, `/api/system/*`, `/api/incidents/*`, `/api/audit/*`, `/api/session/*`, `/api/honeypot/*`) are declared with router-level dependency `dependencies=[Depends(require_api_key)]`.
  - Authentication checks `X-API-Key` or `Authorization: Bearer <token>` using constant-time comparison (`hmac.compare_digest`).

### 2.2 Fail-Closed Semantics Under Missing Configuration
- When `DHWANI_AUTH_REQUIRED=true` but `DHWANI_API_KEY` is empty or unset:
  - `validate_api_key(candidate_key)` returns `False` for any token because `configured_key` is empty.
  - All protected REST requests fail closed with HTTP `401 Unauthorized` (`Missing or unconfigured server API key`).
  - All WebSocket connections fail closed with WebSocket close code `1008 (Policy Violation)`.
  - Verified empirically in tests: `test_auth_required_with_missing_api_key_fails_closed` and `test_websocket_fails_closed_when_auth_required_but_key_missing`.

### 2.3 Default Configuration Safety Assessment
- **Default State:** `DHWANI_AUTH_REQUIRED=false`, `DHWANI_API_KEY=""`.
- **Safety Assessment:** The default configuration is designed for local developer ergonomics (zero-configuration local testing). It is **NOT safe for public or multi-tenant production deployment**.
- **Requirement for Staging/Production:** Production environments **MUST** set `DHWANI_AUTH_REQUIRED=true` and inject a cryptographically secure `DHWANI_API_KEY` via secret management (e.g., HashiCorp Vault, AWS Secrets Manager, Kubernetes Secrets).

### 2.4 Frontend Authentication Compatibility & Gateway Requirements
- **Frontend Current State:** `frontend/src/components/dashboard/UnifiedCyberDashboard.tsx` currently performs standard HTTP `fetch()` requests and creates native WebSocket instances (`new WebSocket(...)`) without authentication headers or subprotocols.
- **Compatibility Analysis:**
  - In default development mode (`DHWANI_AUTH_REQUIRED=false`), the frontend connects seamlessly.
  - In production with `DHWANI_AUTH_REQUIRED=true`, browser clients cannot send arbitrary headers in native WebSockets. They must supply `new WebSocket(url, ["dhwani-auth", apiKey])` or connect through an authenticating reverse proxy / API Gateway.
- **Deployment Recommendation:** For controlled staging, either configure `NEXT_PUBLIC_DHWANI_API_KEY` to attach `X-API-Key` headers and pass the subprotocol, or terminate authentication at an API Gateway / reverse proxy (e.g., Kong, Cloudflare Access, Envoy, Nginx) that injects the key into upstream backend requests.

### 2.5 Secret Handling Verification
- No API keys, passwords, or Twilio tokens are hardcoded in the codebase.
- Error payloads return standardized error details without echoing back user tokens or server secrets.
- Logging statements sanitize parameters and log only session identifiers and masked phone numbers (e.g., `+1***4321`).

---

## 3. WebSocket Authentication & Connection Safety

### 3.1 Browser Client Compatibility & Subprotocol Negotiation
- **Mechanism:** Browser WebSockets do not support custom request headers during handshake. To avoid leaking tokens in URL query strings (CWE-598), Dhwani implements `Sec-WebSocket-Protocol` subprotocol authentication:
  ```javascript
  const socket = new WebSocket("wss://api.dhwani.ai/ws/dashboard", ["dhwani-auth", apiToken]);
  ```
- **Response Cleanliness:** The server parses the subprotocol list, authenticates against `DHWANI_API_KEY`, and accepts with `subprotocol="dhwani-auth"`. The credential itself is **never returned or echoed** in the `Sec-WebSocket-Protocol` response header, preventing credential leakage in proxy and client logs.
- Verified in `test_websocket_subprotocol_returned_cleanly`.

### 3.2 Concurrency & Session Collision Prevention
- **Risk:** In `/ws/audio`, if two clients connect with the identical `session_id`, they could corrupt audio buffers or inspect another caller's risk state.
- **Remediation & Verification:**
  - Added atomic tracking via `ACTIVE_WS_SESSIONS` and threading lock `ACTIVE_SESSIONS_LOCK`.
  - When a second connection attempts to attach to an already-active `session_id`, the server immediately rejects the handshake with close code `1008 (Policy Violation)` and log message `Session collision rejected`.
  - Disconnected sessions cleanly discard their ID in a `finally` block, freeing the session ID for reuse.
  - Verified in `test_websocket_concurrent_session_collision_rejection`.

### 3.3 Inactivity & Resource Bounds
- A 60-second inactivity timeout (`asyncio.wait_for(timeout=60.0)`) terminates stale connections.
- A per-connection rate ceiling of 50 chunks/sec prevents audio flooding.
- Per-frame ceiling (`MAX_WS_FRAME_SIZE = 1MB`) and session quota (`MAX_WS_FRAMES_PER_SESSION = 3600`) prevent buffer memory exhaustion.

---

## 4. External URL & Twilio Telephony Configuration

### 4.1 SSRF & YouTube Media Ingestion
- **Fetch Path:** In `ai/common/media_sources.py`, `YouTubeAudioSource.load_audio()` enforces a strictly canonical URL:
  ```python
  canonical_url = f"https://www.youtube.com/watch?v={self.video_id}"
  ```
  Where `video_id` is validated against regex `^[a-zA-Z0-9_-]{11}$`.
- **Attack Defenses:**
  - User-supplied domains, protocols, port specifications, query strings, and IP addresses are completely discarded.
  - DNS rebinding, internal loopback access (`127.0.0.1`), and cloud metadata endpoints (`169.254.169.254`) are physically unreachable through the media fetcher.
  - `ydl_opts` bounds downloads with `socket_timeout: 15`, `max_filesize: 52428800` (50MB), `playlistend: 1`, and `noplaylist: True`.
  - Verified in `test_youtube_canonical_url_safeguard` and `test_youtube_endpoint_rejects_ssrf`.

### 4.2 Twilio Webhook Validation & Proxy Canonical URL
- **HMAC-SHA1 Signature:** `security/twilio_validator.py` calculates HMAC-SHA1 signatures across the full request URL and alphabetically sorted form parameters.
- **Fail-Closed Verification:**
  - If `TWILIO_VERIFY_SIGNATURE=true` and `TWILIO_AUTH_TOKEN` is unset or empty, `/twilio/voice` immediately aborts with HTTP `500 Server configuration error`, refusing to process unauthenticated calls.
  - Missing signatures return HTTP `403 Forbidden` (`Missing X-Twilio-Signature`).
  - Forged signatures return HTTP `403 Forbidden` (`Invalid Twilio signature.`).
- **Proxy Header Trust & Canonical Public URL:**
  - `get_external_request_url` checks `TWILIO_PUBLIC_URL` first.
  - If untrusted clients can directly connect to the server without a proxy, they could spoof `X-Forwarded-Host`.
  - **Deployment Rule:** Staging and production deployments **MUST** set `TWILIO_PUBLIC_URL=https://<public-domain>/twilio/voice` or configure the reverse proxy to overwrite `X-Forwarded-*` headers.

---

## 5. Resource Limits & Deployment Topology

### 5.1 Request Body & Upload Ceilings
- `MAX_UPLOAD_SIZE_BYTES` defaults to 25 MB for single audio files.
- `MAX_MEDIA_UPLOAD_SIZE` defaults to 100 MB for rich media.
- If `Content-Length` is omitted or forged by an attacker, the streaming chunk reader in `backend/routes/analyze.py` monitors total bytes read and raises HTTP `413 Payload Too Large` immediately upon exceeding the limit.

### 5.2 Decoded Audio Memory & CPU Bounds
- Soundfile metadata is inspected before full decompression and resampling:
  - **Duration Limit:** Audio exceeding 300.0 seconds (5 minutes) is rejected with HTTP `400 Bad Request`.
  - **Sample Rate Limit:** Sample rates exceeding 192,000 Hz are rejected with HTTP `400 Bad Request` to prevent quadratic CPU starvation in `librosa.resample`.
  - **Channel Limit:** Multi-channel files exceeding 8 channels are rejected with HTTP `400 Bad Request`.

### 5.3 Process-Local Limits vs. Multi-Worker Shared State
- Stream buffers (`StreamManager`), active WebSocket sessions (`ACTIVE_WS_SESSIONS`), and telephony calls (`ACTIVE_TELEPHONY_SESSIONS`) reside in local Python process memory.
- **Single-Worker / Container Deployment:** Fully isolated, thread-safe, and self-contained.
- **Multi-Worker / Multi-Pod Deployment:**
  - If deployed with Uvicorn `--workers > 1` or across multiple Kubernetes pods without sticky sessions, incoming WebSocket packets or reconnects may hit a different worker where the session buffer does not exist.
  - Memory rate limits are enforced per-worker rather than globally.
  - **Deployment Requirement:** Multi-worker deployments require **session affinity (sticky sessions)** at the load balancer (ALB / Ingress / Cloudflare). Shared state via Redis is planned for Phase 4.

---

## 6. Required Environment Variables

| Variable | Type | Default | Production Requirement | Purpose |
| :--- | :---: | :---: | :---: | :--- |
| `DHWANI_AUTH_REQUIRED` | bool | `false` | **Required (`true`)** | Enforces API key verification on all `/api/*` and `/ws/*` routes. |
| `DHWANI_API_KEY` | str | `""` | **Required (Secret)** | Strong shared secret or token for REST and WebSocket authentication. |
| `ALLOWED_ORIGINS` | list[str] | `http://localhost:3000,...` | **Required (FQDNs)** | Explicit CORS allowlist for trusted web frontends. Wildcard disallowed with credentials. |
| `TWILIO_AUTH_TOKEN` | str | `""` | **Required if Twilio used** | Twilio account auth token for HMAC-SHA1 webhook signature verification. |
| `TWILIO_VERIFY_SIGNATURE` | bool | `false` | **Required if Twilio used (`true`)** | Strictly fails closed if Twilio webhook signatures are absent or forged. |
| `TWILIO_PUBLIC_URL` | str | `""` | **Recommended (FQDN)** | Canonical public URL (e.g. `https://api.dhwani.ai/twilio/voice`) to prevent proxy header spoofing. |
| `TWILIO_STREAM_PUBLIC_URL` | str | `""` | **Recommended (WSS)** | Public WSS endpoint for Twilio Media Streams (e.g. `wss://api.dhwani.ai/twilio/media`). |
| `MAX_UPLOAD_SIZE_BYTES` | int | `26214400` (25MB) | Optional (Tuning) | Maximum allowed file upload size for direct audio analysis. |
| `MAX_MEDIA_UPLOAD_SIZE` | int | `104857600` (100MB)| Optional (Tuning) | Maximum allowed media upload size for multi-modal ingestion. |

---

## 7. Security & Regression Test Results

### 7.1 Security Test Suite (`tests/test_phase3_security.py`)
Executed: `pytest tests/test_phase3_security.py -v`  
**Result:** **29 passed in 4.48s** (100% pass rate)

| Test Name | Area | Verification Result |
| :--- | :--- | :---: |
| `test_auth_not_required_by_default` | REST Auth | **PASSED** |
| `test_auth_enforced_when_configured` | REST Auth | **PASSED** |
| `test_public_endpoints_remain_accessible_without_auth` | REST Auth | **PASSED** |
| `test_constant_time_api_key_validation` | REST Auth | **PASSED** |
| `test_cors_allowlist_headers` | CORS | **PASSED** |
| `test_analyze_content_length_limit` | Resource Limits | **PASSED** |
| `test_analyze_streaming_chunk_limit` | Resource Limits | **PASSED** |
| `test_media_upload_size_limit` | Resource Limits | **PASSED** |
| `test_malformed_audio_handling_rest` | Payload Safety | **PASSED** |
| `test_ssrf_ip_blocking_matrix` | SSRF Defenses | **PASSED** |
| `test_ssrf_url_validation_blocks_unsafe` | SSRF Defenses | **PASSED** |
| `test_youtube_endpoint_rejects_ssrf` | SSRF Defenses | **PASSED** |
| `test_twilio_signature_computation` | Telephony Auth | **PASSED** |
| `test_twilio_proxy_url_reconstruction` | Telephony Auth | **PASSED** |
| `test_twilio_voice_endpoint_enforces_signature` | Telephony Auth | **PASSED** |
| `test_websocket_auth_rejection` | WS Auth | **PASSED** |
| `test_websocket_audio_frame_size_limit` | WS Limits | **PASSED** |
| `test_websocket_session_isolation_and_buffer_cleanup`| Isolation | **PASSED** |
| `test_audit_chain_tamper_detection` | Audit Chain | **PASSED** |
| `test_websocket_subprotocol_auth` | WS Auth | **PASSED** |
| `test_websocket_concurrent_session_collision_rejection`| WS Concurrency | **PASSED** |
| `test_analyze_audio_duration_limit_rejection` | Resource Limits | **PASSED** |
| `test_youtube_canonical_url_safeguard` | SSRF / URL | **PASSED** |
| `test_auth_required_with_missing_api_key_fails_closed`| Fail-Closed | **PASSED** |
| `test_twilio_verification_required_with_missing_token_fails_closed`| Fail-Closed | **PASSED** |
| `test_cors_disallowed_origin_preflight` | CORS | **PASSED** |
| `test_websocket_subprotocol_returned_cleanly` | WS Protocol | **PASSED** |
| `test_websocket_fails_closed_when_auth_required_but_key_missing`| Fail-Closed | **PASSED** |
| `test_analyze_audio_extreme_sample_rate_rejected` | Resource Limits | **PASSED** |

### 7.2 Full Repository Regression Suite
Executed: `pytest tests/ -q`  
**Result:** **125 passed in 18.30s** (0 errors, 0 failures, 0 regressions)

### 7.3 Frontend Compilation
Executed: `cd frontend && npx tsc --noEmit`  
**Result:** **Exit code 0** (0 TypeScript errors)

---

## 8. Deployment Blockers & Operational Limitations

| Item | Severity | Category | Preconditions & Impact | Required Action / Limitation |
| :--- | :---: | :---: | :--- | :--- |
| **BLOCKER-01** | **Medium** | Auth Topology | Frontend does not pass `X-API-Key` or subprotocols when `DHWANI_AUTH_REQUIRED=true`. | Terminate auth at reverse proxy/API gateway OR configure `NEXT_PUBLIC_DHWANI_API_KEY`. |
| **BLOCKER-02** | **Medium** | Telephony | Reverse proxy without `TWILIO_PUBLIC_URL` allows header tampering. | Set `TWILIO_PUBLIC_URL` explicitly in environment. |
| **LIMITATION-01** | **Low** | Scalability | In-memory stream buffers and rate limits are process-local. | Requires single worker or load balancer session affinity (sticky sessions). |
| **LIMITATION-02** | **Low** | Audit Storage | Audit ledger is stored on local filesystem (`data/audit_ledger.jsonl`). | Host file tampering detectable but local truncation possible; backup to WORM storage in Phase 4. |

---

## 9. Final Deployment Verdict

### **Verdict: `READY WITH LIMITATIONS`**

**Rationale:**
1. **Security Posture Verified:** All authentication and telephony paths fail closed under missing or invalid configurations. SSRF protections enforce canonical YouTube URLs and reject all non-public IP ranges. Audio upload duration and sample rates are strictly bounded against DoS attacks.
2. **WebSocket Robustness:** Subprotocol authentication negotiates cleanly without credential leakage, duplicate active sessions are rejected atomically, and inactive sessions time out.
3. **Zero Regressions:** All 125 backend tests and frontend TypeScript compilation pass cleanly.
4. **Controlled Staging Ready:** The system is fully ready for controlled staging and pilot deployment behind an authenticating reverse proxy / API gateway with documented environment variables. Full multi-tenant enterprise production deployment requires the distributed features scheduled for Phase 4 (Redis rate limiting, OIDC/JWT, WORM audit sync).
