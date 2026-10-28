# Phase 3: Security Controls & Architecture Specification

**Document Version:** 1.0.0  
**Target:** Dhwani / EchoShield AI Voice Deepfake Detection Platform  
**Date:** October 25, 2026  
**Status:** Implemented & Verified  

---

## 1. Overview & Architecture Summary

Phase 3 introduces enterprise-grade security controls to harden Dhwani's REST APIs, WebSocket streaming endpoints, and telephony webhooks against abuse, unauthorized access, and cross-session data leakage. All controls maintain strict backward compatibility with the existing inference pipeline (Phase 1) and evaluation harness (Phase 2).

```
                      +---------------------------------------+
                      |       Client / Telephony Caller       |
                      +-------------------+-------------------+
                                          |
                +-------------------------+-------------------------+
                |                         |                         |
         [ REST API ]            [ Audio WebSocket ]       [ Twilio Webhook ]
        /api/analyze/*              /ws/audio                /twilio/voice
                |                         |                         |
       +--------v--------+       +--------v--------+       +--------v--------+
       |   API Key /     |       | Handshake Auth  |       | Twilio HMAC-    |
       |  Bearer Auth    |       |  Verification   |       | SHA1 Signature  |
       |  (Constant-     |       | (Policy Code    |       | Verification    |
       |   Time Match)   |       |     WS_1008)    |       |  (RFC 2104)     |
       +--------+--------+       +--------+--------+       +--------+--------+
                |                         |                         |
       +--------v--------+       +--------v--------+                |
       | Payload Limits  |       | Frame & Session |                |
       | (25MB/50MB cap, |       | Caps (1MB frame,|                |
       | audio validation|       | 3600 frames max)|                |
       |  + SSRF Check)  |       +--------+--------+                |
       +--------+--------+                |                         |
                |                +--------v--------+                |
                |                | Session Buffer  |                |
                |                | Cleanup Finally |                |
                +----------------+--------+--------+----------------+
                                          |
                                 +--------v--------+
                                 | Multi-Model AI  |
                                 | Inference &     |
                                 | Cryptographic   |
                                 | Audit Ledger    |
                                 +-----------------+
```

---

## 2. Implemented Security Controls

### 2.1 REST Authentication & Authorization (`security/auth.py`)

- **Credential Scheme:** Dual-support for `X-API-Key: <token>` and `Authorization: Bearer <token>`.
- **Constant-Time Verification:** Uses `hmac.compare_digest` to prevent timing side-channel attacks against credential strings.
- **Environment Driven:**
  - `DHWANI_API_KEY`: Master secret key.
  - `DHWANI_AUTH_REQUIRED`: Set to `true` to mandate authentication across all protected endpoints.
  - Defaults to non-breaking mode when unconfigured, allowing existing test suites and development scripts to execute without obstruction.
- **Public vs. Protected Route Boundaries:**
  - **Public:**
    - `GET /health`: Health probes and container liveness monitors.
    - `GET /`: Metadata and supported model architecture summary.
    - `POST /twilio/voice`: Protected via dedicated HMAC-SHA1 webhook signature verification.
  - **Protected (Mandatory Auth):**
    - `POST /api/analyze`, `POST /api/analyze/upload`, `POST /api/analyze/youtube`
    - `GET /api/system/status`
    - `GET /api/incidents`, `GET /api/incidents/*`, `POST /api/incidents/verification/*`
    - `GET /api/audit/*`
    - `POST /api/session`, `GET /api/session/*`, `DELETE /api/session/*`
    - `POST /api/honeypot/*`

### 2.2 CORS & Request Limit Hardening (`backend/main.py`, `backend/routes/analyze.py`)

- **CORS Specification Compliance:**
  - Replaced wildcard origin `["*"]` with environment-configurable allowlist `ALLOWED_ORIGINS` / `CORS_ALLOW_ORIGINS`.
  - Default allowlist: `http://localhost:3000,http://127.0.0.1:3000`.
  - Enforced W3C standard rule: If wildcard `*` is explicitly configured, `allow_credentials` is strictly disabled (`False`) to prevent credential leakage.
- **Payload Size Ceilings:**
  - `POST /api/analyze`: 25 MB max upload size. Checked via `Content-Length` header pre-parsing and bounded chunk streaming (`CHUNK_SIZE = 1MB`).
  - `POST /api/analyze/upload`: 50 MB max media file limit. Bounded chunk streaming prevents memory exhaustion from compressed archive bombs.
  - Status code: `413 Payload Too Large` with descriptive error details.
- **Audio Pre-Validation:**
  - Ingestion checks magic headers (`RIFF`, `OggS`, `fLaC`, `ID3`) and container readability via `soundfile.SoundFile` before invoking expensive neural network detectors, preventing CPU/GPU starvation attacks on malformed inputs.

### 2.3 WebSocket Security & Session Isolation (`backend/websocket/audio.py`, `backend/streaming/stream_manager.py`)

- **Handshake Authentication:**
  - Incoming WebSocket connections to `/ws/audio` and `/ws/dashboard` validate credentials via query parameters (`?api_key=...` or `?token=...`) or headers.
  - Unauthorized handshakes are terminated immediately with standard WebSocket close code `1008 (Policy Violation)`.
- **Session Identifier Validation:**
  - `session_id` must match `^[a-zA-Z0-9_\-\.:]{1,128}$`.
  - Malformed or directory traversal strings (`../../`) are rejected during handshake.
- **Resource Exhaustion Defenses:**
  - `MAX_WS_FRAME_SIZE`: 1 MB per audio chunk. Chunks exceeding 1 MB terminate the connection with code `1009 (Message Too Big)`.
  - `MAX_WS_FRAMES_PER_SESSION`: 3,600 chunks per connection (1 hour of continuous speech at 1 frame/sec).
- **Guaranteed Session Cleanup:**
  - Audio buffers and speaker consistency profiles are purged in a `finally` block:
    ```python
    finally:
        reset_session(session_id)
        stream_manager.remove_session(session_id)
    ```
  - Prevents memory leaks and guarantees that speaker embeddings from one caller cannot bleed into subsequent callers.

### 2.4 Twilio Webhook Verification (`security/twilio_validator.py`, `backend/routes/twilio_routes.py`)

- **HMAC-SHA1 Signature Validation:**
  - Implements official Twilio signature specification (RFC 2104).
  - Alphabetically sorts all form parameters, appends them to the full request URL, computes HMAC-SHA1 using `TWILIO_AUTH_TOKEN`, and compares using `hmac.compare_digest`.
- **Reverse Proxy / Ingress Awareness:**
  - `get_external_request_url` inspects `X-Forwarded-Proto`, `X-Forwarded-Host`, and `TWILIO_PUBLIC_URL` to reconstruct the exact external URL visible to Twilio behind TLS terminators and API gateways.
- **Enforcement:**
  - Active when `TWILIO_AUTH_TOKEN` is configured or `TWILIO_VERIFY_SIGNATURE=true`.
  - Rejects missing signatures with `403 Forbidden` (`Missing X-Twilio-Signature`).
  - Rejects forged signatures with `403 Forbidden` (`Invalid Twilio signature.`).

### 2.5 Server-Side Request Forgery (SSRF) Defenses (`security/ssrf.py`)

- **Multi-Layer IP Address Validation:**
  - Validates URL syntax and scheme (only `http` and `https` permitted).
  - Rejects URLs containing embedded user credentials (`http://user:pass@host`).
  - Resolves domain names to IP addresses via `socket.getaddrinfo` and inspects every returned address against restricted networks:
    - `127.0.0.0/8` (IPv4 Loopback)
    - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (Private RFC 1918)
    - `169.254.0.0/16` (Link-Local & Cloud Metadata: AWS/GCP/Azure)
    - `100.64.0.0/10` (Carrier-Grade NAT / RFC 6598)
    - `0.0.0.0/8` (Current Network)
    - `::1/128`, `fc00::/7`, `fe80::/10` (IPv6 Loopback, ULA, Link-Local)
- **Domain Allowlisting:**
  - `/api/analyze/youtube` enforces strict YouTube domain allowlist: `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`.
  - Non-YouTube domains or internal targets return `400 Bad Request` with `SSRF Protection: ...`.

### 2.6 Audit Logging & Cryptographic Integrity (`security/audit_chain.py`, `backend/routes/incidents.py`)

- **Cryptographic Hash Chain:**
  - Every security event, incident, and inference result is recorded with canonical JSON serialization and SHA-256 hash chaining:
    $$H_n = \text{SHA-256}(H_{n-1} \mathbin{\Vert} \text{canonical\_json}(E_n))$$
- **Unified Pipeline:**
  - `backend/routes/incidents.py` is unified with `get_global_pipeline()`, ensuring incident records and forensic audit trails share a single authoritative ledger.
- **Thread Safety:**
  - Ledger appends and incident dictionary access are protected by `threading.RLock()` to ensure consistency under concurrent HTTP requests.
- **Privacy & Redaction:**
  - Audio payloads are represented by their SHA-256 digest (`audio_hash`). Raw audio bytes, auth tokens, and session credentials are never written to the audit ledger or log messages.

---

## 3. Configuration & Environment Variables

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `DHWANI_API_KEY` | `string` | `""` | Master API key for REST endpoints and WebSocket handshakes. |
| `DHWANI_AUTH_REQUIRED` | `boolean` | `false` | When `true`, enforces authentication on all `/api/*` endpoints. |
| `ALLOWED_ORIGINS` | `string` | `http://localhost:3000,...` | Comma-separated list of allowed CORS origins. |
| `MAX_UPLOAD_SIZE_BYTES` | `integer` | `26214400` (25 MB) | Maximum upload file size for REST audio endpoints. |
| `MAX_MEDIA_UPLOAD_SIZE` | `integer` | `52428800` (50 MB) | Maximum upload file size for `/api/analyze/upload`. |
| `TWILIO_AUTH_TOKEN` | `string` | `""` | Twilio Account Auth Token used for HMAC-SHA1 webhook signature verification. |
| `TWILIO_VERIFY_SIGNATURE` | `boolean` | `false` | When `true`, mandates valid `X-Twilio-Signature` on telephony webhooks. |
| `TWILIO_PUBLIC_URL` | `string` | `""` | Canonical external URL prefix for Twilio callbacks (e.g. `https://api.dhwani.ai`). |
