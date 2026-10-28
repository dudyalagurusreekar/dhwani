# Phase 3: Remaining Risks & Architectural Limitations

**Document Version:** 1.0.0  
**Target:** Dhwani / EchoShield AI Voice Deepfake Detection Platform  
**Date:** October 25, 2026  
**Status:** Documented for Phase 4 / Production Readiness  

---

## 1. Executive Summary

While Phase 3 resolved critical vulnerabilities across REST authentication, WebSocket abuse, CORS configuration, Twilio spoofing, and SSRF attacks, several architectural constraints and operational trade-offs remain. This document details each remaining risk, its preconditions, potential business/system impact, and the recommended roadmap for production readiness.

---

## 2. Detailed Risk Register

### 2.1 RISK-01: Static API Key Scheme vs. Dynamic Identity Provider (OIDC / JWT)
- **Current Architecture:** Authentication is managed via a shared environment key (`DHWANI_API_KEY`).
- **Preconditions:** Multiple API clients, frontends, or automated agents sharing the same key.
- **Limitation:**
  - Lack of fine-grained role-based access control (RBAC). A client authorized to send audio for inference also has permission to list incident ledgers and trigger step-up verifications.
  - Revocation requires re-deploying the server with a new environment key, disrupting all clients simultaneously.
- **Mitigation Roadmap (Phase 4):**
  - Implement asymmetric JWT authentication (e.g., Auth0, Keycloak, or AWS Cognito).
  - Scope tokens with distinct permissions (e.g. `voice:infer`, `incidents:read`, `admin:verify`).

### 2.2 RISK-02: Single-Node In-Memory Rate Limiting vs. Distributed Token Bucket
- **Current Architecture:** WebSocket frame limits (`MAX_WS_FRAME_SIZE = 1MB`, `MAX_WS_FRAMES_PER_SESSION = 3600`) and stream buffers are tracked in-process inside the running Python process.
- **Preconditions:** Distributed multi-worker or multi-container deployment behind a load balancer.
- **Limitation:**
  - Each container maintains its own memory state. A distributed attacker could open connections across multiple worker instances, evading cumulative rate limits.
- **Mitigation Roadmap:**
  - Integrate a Redis-backed distributed rate limiter using a sliding-window counter or leaky bucket algorithm.

### 2.3 RISK-03: Twilio Webhook Replay Window Mitigation
- **Current Architecture:** Twilio webhook signatures are validated via HMAC-SHA1 over the complete request URL and parameters.
- **Preconditions:** An attacker intercepts a valid signed Twilio request on an unencrypted or compromised network hop.
- **Limitation:**
  - While Twilio signs every request uniquely, Twilio signatures do not intrinsically include an explicit client-side timestamp header. If an attacker captures a valid payload and signature, they could replay the request within a network session unless deduplication is enforced.
- **Mitigation Roadmap:**
  - Enforce monotonic `CallSid` state tracking and reject repeated `CallSid` events that attempt to reopen completed calls.

### 2.4 RISK-04: Local Append-Only JSONL Audit Ledger vs. Immutable Cloud WORM
- **Current Architecture:** Security incidents and audit events are appended to `data/audit_ledger.jsonl` with SHA-256 cryptographic chaining. Chain tampering is cryptographically detectable via `/api/audit/verify`.
- **Preconditions:** Host operating system compromise with root or administrator access.
- **Limitation:**
  - While an attacker cannot modify or insert ledger entries without breaking the hash chain, a malicious root process could truncate the file or overwrite the entire ledger with an alternate valid chain from genesis.
- **Mitigation Roadmap:**
  - Ship daily ledger root hashes to a cloud Write-Once-Read-Many (WORM) storage bucket (e.g., AWS S3 Object Lock in Compliance Mode) or an external timestamping authority (RFC 3161).

### 2.5 RISK-05: Deep Neural Inference Concurrency Ceiling (CPU/GPU Contention)
- **Current Architecture:** AASIST, AASIST-L, and Acoustic detectors run synchronously or semi-asynchronously per inference call.
- **Preconditions:** High concurrent call volume (> 20 concurrent audio streams on a single GPU or CPU).
- **Limitation:**
  - Although fast energy VAD gates silent audio frames, sustained concurrent speech streams will increase model inference latency beyond the real-time threshold (~500 ms).
- **Mitigation Roadmap:**
  - Offload batch inference to dedicated Triton Inference Server or Ray Serve workers with dynamic batching.

---

## 3. Production Readiness Verdict

In accordance with Phase 3 guidelines:
- Security posture is **substantially hardened** and verified with 19 new automated tests.
- Zero regressions across existing Phase 1 (deep inference) and Phase 2 (calibration harness) capabilities.
- **Final Phase 3 Verdict:** **`APPROVED WITH LIMITATIONS`** (approved for secure staging and demonstration; limitations noted above to be addressed prior to global multi-tenant production deployment).
