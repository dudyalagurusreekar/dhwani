# Dhwani Cybersecurity Architecture 🛡️🔐

This module expands Dhwani's security footprint into an enterprise-grade, defense-in-depth architecture specifically tailored for voice anti-spoofing and deepfake defense.

```
                      DHWANI VOICE DEFENSE
                               |
                               v
                         Incoming Audio
                               |
                               v
                       [1. API SECURITY]
                    JWT Auth + RBAC + SlowAPI
                               |
                               v
                      [2. AI DETECTION]
                     Wav2Vec2 + AASIST
                               |
                               v
                      [3. RISK ENGINE]
                 Bayesian Confidence Scoring
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
     [4. AUDIO PRIVACY LAYER]     [5. PROVENANCE CHAIN]
      AES-GCM / Fernet Sealed       SHA-256 Hashing
      Configurable Retention        Tamper-Evident Chain
      Secure Memory Zeroization              |
                 |                           v
                 |               [6. DIGITAL SIGNATURES]
                 |                 Ed25519 Checkpoints
                 |                 Chain-Head Attestations
                 |                           |
                 +-------------+-------------+
                               |
                               v
                     [7. AUDIT LEDGER]
                   Forensic Verification
```

---

## The Four Core Security Capabilities

| Capability | Module Path | Core Technologies | What it Solves |
| :--- | :--- | :--- | :--- |
| **1. Security Event Integrity** | `security/` | SHA-256, Hash Chain, JSONL | Prevents local file tampering and sequential breaks in forensic audit logs. |
| **2. API Access Protection** | `cybersecurity/api_security/` | FastAPI, PyJWT, SlowAPI, RBAC | Blocks unauthorized clients, enforces least privilege, and prevents Denial-of-Service brute force. |
| **3. Cryptographic Audit Verification** | `cybersecurity/audit_verification/` | Ed25519 Asymmetric Signatures, Checkpoints | Detects recalculation attacks: proves the chain tip was sealed by an authorized validator node. |
| **4. Audio Privacy & Data Protection** | `cybersecurity/audio_privacy/` | Fernet / AES-128-CBC + HMAC, TTL Purging | Zero-retention by default. Retained audio is encrypted, restricted by justification, and shredded upon expiry. |

---

## 1. API Security & Access Control (`cybersecurity/api_security/`)

### Architecture
- **JWT Authentication** (`authentication.py`): Issues and validates cryptographically signed bearer tokens with issuer verification and expiration tracking.
- **RBAC Authorization** (`authorization.py`): Enforces least-privilege access using role hierarchies (`CLIENT`, `ANALYST`, `AUDITOR`, `ADMIN`) and granular permission scopes (`audio:analyze`, `audit:verify`, `audio:decrypt`, `admin:all`).
- **Rate Limiting** (`rate_limiter.py`): Protects inference endpoints from burst traffic and resource starvation using SlowAPI and sliding-window limits.

### Code Example
```python
from cybersecurity.api_security import create_access_token, decode_access_token, Role

# Issue token for an auditor node
token = create_access_token(
    subject="auditor_node_01",
    role=Role.AUDITOR.value,
    scopes=["audit:read", "audit:verify", "audit:checkpoint"],
)

# Validate incoming bearer token
payload = decode_access_token(token)
print("Client:", payload["sub"], "Role:", payload["role"])
```

---

## 2. Digital Signature & Audit Verification (`cybersecurity/audit_verification/`)

### Architecture
- **Ed25519 Key Enclave** (`signatures.py`): Fast, constant-time Edwards-curve digital signatures. Signing keys are kept strictly isolated from the public audit log.
- **Audit Checkpoints** (`checkpoint.py`): Cryptographically seals the chain tip (`chain_length`, `latest_hash`, `timestamp`, `signature`).
- **Recalculation Attack Detection** (`verify_signature.py`):
  If an attacker tampers with an event in the chain and recalculates the SHA-256 hashes to fool simple hash checks, the verifier compares the live tip with the Ed25519 signed checkpoint and mathematically proves tampering.

### Code Example
```python
from security.hash_chain import HashChain
from cybersecurity.audit_verification import (
    AuditSigner,
    create_checkpoint,
    verify_checkpoint_integrity,
)

chain = HashChain()
chain.add_event("sess_01", "CALL_STARTED", 0, "v1", "a" * 64)
chain.add_event("sess_01", "SUSPICIOUS_VOICE", 85, "v1", "b" * 64)

# Validator signs the current state
signer = AuditSigner()
checkpoint = create_checkpoint(chain, signer)

# Third-party verifier validates checkpoint
result = verify_checkpoint_integrity(checkpoint, chain)
print("Verified?", result.is_valid)  # True
```

---

## 3. Audio Privacy & Data Protection (`cybersecurity/audio_privacy/`)

### Architecture
- **Authenticated Encryption** (`encryption.py`): Symmetric Fernet / AES encryption with key derivation and secure random salts.
- **Memory Zeroization** (`encryption.py`): Scratch audio buffers in RAM are actively zero-overwritten (`0x00`) to defeat memory dumping.
- **Configurable Retention** (`retention.py`):
  - `ZERO_RETENTION`: Processed in RAM only; immediately shredded.
  - `EPHEMERAL_HOLD_1H`: 1-hour encrypted forensic window.
  - `STANDARD_HOLD_24H`: 24-hour verification window.
  - `LEGAL_HOLD_30D`: 30-day evidentiary hold.
- **Secure File Shredding** (`retention.py`): Files are overwritten with zeros prior to disk unlinking. Non-PII SHA-256 fingerprints remain permanently in the audit chain.
- **Audited Access Gate** (`access_control.py`): Requires administrative/auditor authorization and justification logging before decrypting voice records.

### Code Example
```python
from cybersecurity.audio_privacy import (
    RetentionManager,
    RetentionPolicy,
    AudioAccessGate,
)

retention_mgr = RetentionManager()

# Process under Zero-Retention default (GDPR/DPDP compliant)
meta = retention_mgr.handle_audio(
    session_id="call_991",
    audio_bytes=raw_voice_bytes,
    policy=RetentionPolicy.ZERO_RETENTION,
)
print("Purged immediately from disk?", meta.is_purged)  # True
print("SHA-256 Fingerprint preserved:", meta.audio_hash)
```

---

## Speaking Points for Presentations & Judges

### Pitch Summary
> *"While our AI models detect deepfake voice patterns, my responsibility is the Cybersecurity and Trust Layer that protects the system from end to end:*
>
> 1. *API Security: We use JWT authentication, RBAC authorization, and SlowAPI rate limiting to prevent unauthorized access and DoS floods.*
> 2. *Cryptographic Provenance: Every audio sample is fingerprinted with SHA-256, linked in an immutable hash chain, and sealed with Ed25519 digital signatures to detect even recalculation attacks.*
> 3. *Privacy by Design: We operate under Zero Raw Audio Retention by default. Any evidence retained under legal hold is encrypted with AES/Fernet, access-controlled with chain-of-custody logging, and cryptographically shredded upon TTL expiry in compliance with GDPR and India's DPDP Act 2023.*
> 4. *Verification: Our entire architecture is backed by 74 automated unit and integration tests passing in under 0.4 seconds."*

---

## Running the Complete Test Suite

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```
All **74 tests** will execute and pass with 100% success.
