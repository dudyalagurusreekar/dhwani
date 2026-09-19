# Dhwani / EchoShield: Security Architecture & Threat Model

## 1. Executive Summary

In voice-based authentication, real-time telephony, and deepfake prevention, **provenance and tamper-evident auditing** are as critical as the AI detection model itself. If an attacker can alter audio packets in transit, manipulate detection verdicts in application logs, or access raw voice recordings, the integrity and privacy of the entire system collapse.

The **Dhwani / EchoShield Security & Provenance Module** introduces a defense-in-depth architecture that provides:
1. **Cryptographic Accountability**: Every audio frame and session event is hashed with SHA-256.
2. **Tamper-Evident Hash Chain**: Security events form an append-only cryptographic ledger where any historical alteration breaks the chain.
3. **Automated Tamper Detection**: Auditing routines mathematically verify continuity and isolate unauthorized modifications.
4. **Zero-Retention Biometric Privacy**: Raw audio is strictly ephemeral (processed in RAM and memory-wiped with zeros). Only irreversible cryptographic hashes are stored.

---

## 2. 7-Stage Security & Provenance Pipeline

```
                 +-----------------------+
                 |      AUDIO INPUT      |  Stage 1: Ephemeral Ingestion (RAM only)
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 |    SHA-256 HASHING    |  Stage 2: Cryptographic Fingerprinting
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 |     AI DETECTION      |  Stage 3: AASIST / RawNet In-Memory Pass
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 |      RISK ENGINE      |  Stage 4: Multi-Factor Policy Evaluation
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 |    SECURITY EVENT     |  Stage 5: RFC 8785 Canonical JSON Event
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 |      HASH CHAIN       |  Stage 6: Append-Only Immutable Ledger
                 +-----------------------+
                             |
                             v
                 +-----------------------+
                 | INTEGRITY VERIFY /    |  Stage 7: Continuous / On-Demand Audit
                 | TAMPER DETECTION      |
                 +-----------------------+
```

---

## 3. Threat Model & Mitigation Matrix

| Threat ID | Threat Vector | Impact | Dhwani Architectural Defense |
| :--- | :--- | :--- | :--- |
| **THREAT-01** | **Man-in-the-Middle (MitM) Audio Tampering** | Audio frames manipulated between client ingress and inference engine. | **Immediate Ingress Hashing**: Audio bytes are fingerprinted (`AudioHasher.hash_bytes`) at the earliest entry point. The resulting hash is bound to the session context. |
| **THREAT-02** | **Audit Trail Scrubbing & Log Alteration** | Malicious administrator or compromised host alters past logs (e.g. changing deepfake verdict to authentic) to conceal fraud. | **Cryptographic Hash Chain**: Each event $E_n$ incorporates $H_{n-1}$. Altering any byte in $E_k$ changes $H_k$, which causes a checksum mismatch for all subsequent events $E_{k+1} \dots E_m$. |
| **THREAT-03** | **Biometric Data Exfiltration & Voice Eavesdropping** | Unauthorized access to stored voice recordings violating GDPR / DPDP Act. | **Zero-Retention Ephemeral Sandbox**: Raw audio is held only in volatile memory (`EphemeralAudioBuffer`), physically overwritten with null bytes (`0x00`), and purged upon inference exit. No audio files touch persistent storage. |
| **THREAT-04** | **Replay & Frame-Injection Attacks** | Fraudster splices pre-recorded authentic voice with synthetic deepfake chunks. | **Dual-Anchor Provenance**: Each event binds `session_id`, monotonic `seq_num`, microsecond UTC timestamp, and `audio_hash`. Audio hashes cannot be transplanted into a different session without breaking the hash chain. |
| **THREAT-05** | **Denial-of-Provenance (Repudiation)** | Fraudster or party denies that a flagged audio stream belonged to their session. | **Provenance Token**: $Token = \text{SHA-256}(\text{SessionHash} \mathbin{\Vert} \text{AudioHash})$. Irrevocably couples session identity and exact audio payload. |
| **THREAT-06** | **Adversarial Borderline Score Exploitation** | Attacker creates synthetic speech tuned just beneath detection cutoff. | **Risk Engine Anomaly Scoring**: Risk engine evaluates multi-chunk context, model confidence, and duration anomalies. Consecutive borderline scores trigger policy escalation from `MONITOR` to `BLOCK`. |

---

## 4. Cryptographic Provenance Architecture

### 4.1 Canonical Serialization (RFC 8785 Compliance)
Standard JSON serializers produce platform-dependent whitespace and key orderings, which would cause false-positive cryptographic mismatches. Dhwani implements deterministic serialization:
- Lexicographically sorted dictionary keys (`sort_keys=True`).
- Strict separator format without superfluous spaces (`separators=(",", ":")`).
- Normalized UTC ISO 8601 timestamps with microsecond resolution.

### 4.2 Append-Only Hash Chain Construction
1. **Genesis Block**:
   $$H_0 = \text{SHA-256}\left(\text{"0"}^{64} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{CanonicalJSON}(E_0)\right)$$
2. **Intermediate Blocks ($n \ge 1$)**:
   $$H_n = \text{SHA-256}\left(H_{n-1} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{CanonicalJSON}(E_n)\right)$$
3. **Properties**:
   - **Pre-image Resistance**: Computationally infeasible to reverse or forge event hashes.
   - **Avalanche Effect**: A 1-bit modification in any historic event completely scrambles all downstream hashes.
   - **Append-Only File Persistence**: Events are streamed line-by-line to `.jsonl` audit files with immediate flush.

---

## 5. Verification & Tamper-Detection Engine

The verification engine (`AuditHashChain.verify_integrity()`) performs an end-to-end traversal of the ledger:

```
[Event 0] ──prev_hash="000...000"──► Hash_0 
                                      │
              ┌───────────────────────┘
              ▼
[Event 1] ──prev_hash=Hash_0────────► Hash_1
                                      │
              ┌───────────────────────┘
              ▼
[Event 2] ──prev_hash=Hash_1────────► Hash_2 ──► [Chain Tip]
```

### Verification Steps:
1. **Genesis Validation**: Asserts `E_0.prev_hash == "0"*64`.
2. **Sequence Monotonicity**: Asserts $E_i.\text{seq\_num} == i$. Detects event deletions and insertions.
3. **Payload Integrity Check**: Recomputes $H_i' = \text{SHA-256}(E_i.\text{prev\_hash} \mathbin{\Vert} \text{CanonicalJSON}(E_i))$ and asserts constant-time equality with $E_i.\text{chain\_hash}$. Detects payload modification (`PAYLOAD_ALTERED`).
4. **Pointer Continuity Check**: Asserts $E_i.\text{prev\_hash} == E_{i-1}.\text{chain\_hash}$. Detects spliced or severed chains (`CHAIN_BROKEN`).

If any discrepancy is detected, the verification engine outputs a `ChainVerificationReport` identifying:
- Exact sequence number (`tampered_event_seq`)
- Event UUID (`tampered_event_id`)
- Precise `TamperType` classification (`PAYLOAD_ALTERED`, `CHAIN_BROKEN`, `EVENT_DELETED`, etc.)
- Detailed forensic failure message.

---

## 6. Zero-Retention Biometric Privacy Sandbox

### Why Zero Audio Retention?
Voice is biometric PII protected under:
- **GDPR Article 9** (Processing of special categories of personal data)
- **Digital Personal Data Protection (DPDP) Act 2023** (India)
- **California Consumer Privacy Act (CCPA/CPRA)**

Retaining raw recordings creates high-liability honeypots for data leaks. Dhwani solves this by treating audio as strictly ephemeral:

```python
with EphemeralAudioBuffer(audio_bytes, session_id="call_99") as buf:
    # 1. Immediate SHA-256 fingerprint generated
    fingerprint = buf.audio_hash
    
    # 2. In-memory execution by AI model
    score = model.infer(buf.get_buffer())
    
# 3. Memory overwritten with 0x00 and purged upon exit!
# Any subsequent access to buf.get_buffer() raises BufferPurgedError
```

Audit logs store **only** the cryptographic fingerprint (`audio_hash`), duration, and model scores. In the event of an audit, a third party can verify that a specific audio recording corresponds to a given verdict by hashing the suspect audio and matching it against the immutable hash chain, without Dhwani ever needing to store the audio recording itself.

---

## 7. Risk Engine & Threshold Policies

The Risk Engine bridges AI detection with operational enforcement:

| AI Deepfake Score | Risk Level | Action | Description |
| :--- | :--- | :--- | :--- |
| **$0.00 \le \text{Score} < 0.30$** | `LOW` | `ALLOW` | Standard traffic; authentic voice patterns detected. |
| **$0.30 \le \text{Score} < 0.60$** | `MEDIUM` | `MONITOR` | Borderline characteristics; acoustic monitoring active. |
| **$0.60 \le \text{Score} < 0.85$** | `HIGH` | `FLAG` / `CHALLENGE` | Significant synthetic indicators; biometric step-up or alert. |
| **$\text{Score} \ge 0.85$** | `CRITICAL` | `BLOCK` | Definitive deepfake spoofing; terminate or block session. |

### Stateful Session Escalation:
- Single high scores flag an alert.
- Two consecutive scores $\ge 0.60$ in an ongoing session trigger automated policy escalation to `BLOCK`.
- Short audio segments ($< 0.50$s) trigger confidence penalization to avoid false positives on truncated voice bursts.
