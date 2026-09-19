# Dhwani / EchoShield - Threat Model (Member 3)

## 1. Overview
A threat model identifies what could go wrong and how the system should respond. In **Dhwani**, deepfake detection evidence must be legally defensible, tamper-evident, and compliant with biometric privacy laws.

---

## 2. Core Threat Matrix

| Threat | What could happen? | Security measure |
| :--- | :--- | :--- |
| **Evidence modification** | Someone changes recorded audio evidence. | **Hash the evidence and verify its integrity**: Compute SHA-256 fingerprint upon ingest. Any change to the audio waveform produces a completely different hash. |
| **Event modification** | Someone edits a suspicious-event record (e.g. changing deepfake score from 95% to 5%). | **Verify the hash chain**: Each event embeds the previous event's hash. Editing any past event breaks the cryptographic link and fails verification. |
| **Fake security events** | An attacker submits fabricated detection events. | **Validate requests and authenticate trusted event producers**: Require API session validation, enforce mandatory schema validation, and authenticate endpoints. |
| **Unauthorized access** | Someone accesses protected evidence. | **Apply authentication and access controls**: Restrict access using role-based access control (RBAC), TLS in transit, and authenticated audit query endpoints. |
| **Sensitive data exposure** | Private audio is unnecessarily stored or shared. | **Minimize audio retention and restrict access (Zero Retention)**: Audio is processed ephemerally in RAM and immediately purged. Only hashes and metadata are retained. |

---

## 3. Detailed Threat Analysis & Mitigations

### 3.1 Threat 1: Evidence Modification
- **Scenario**: An attacker intercepts an audio sample and splices in authentic audio, or alters a recorded file after detection to invalidate evidence.
- **Dhwani Defense**: 
  - The `hashing.py` module computes a 256-bit cryptographic digest (`hash_data` or `hash_audio_file`).
  - Due to the avalanche effect of SHA-256, altering even 1 bit in the audio stream changes the entire hash digest.
  - The audio hash is embedded permanently in the security event.

### 3.2 Threat 2: Event Modification (Log Scrubbing)
- **Scenario**: A malicious insider or compromised administrator alters the database to change an alert status from `SUSPICIOUS_VOICE` to `NORMAL` to hide a spoofing incident.
- **Dhwani Defense**:
  - The `hash_chain.py` module links events sequentially:
    $$\text{Event } 1 \rightarrow \text{Hash } 1$$
    $$\text{Event } 2 + \text{Hash } 1 \rightarrow \text{Hash } 2$$
    $$\text{Event } 3 + \text{Hash } 2 \rightarrow \text{Hash } 3$$
  - The `integrity.py` module runs `verify_hash_chain()`. When an event is modified, both its internal `event_hash` and the subsequent event's `previous_event_hash` fail comparison, pinpointing the exact modified event index.

### 3.3 Threat 3: Fake Security Events
- **Scenario**: An attacker injects fake events to flood the dashboard or trigger false alarms.
- **Dhwani Defense**:
  - Events must strictly adhere to the `event_schema.py` specification with valid monotonic sequence numbers, timestamps, and valid cryptographic hashes.
  - Integration with the backend ensures that only authenticated pipeline steps can trigger event creation.

### 3.4 Threat 4: Unauthorized Access
- **Scenario**: Attackers attempt to read or extract the audit logs.
- **Dhwani Defense**:
  - Audit logs are exposed via protected endpoints (`/api/audit/trail`, `/api/audit/verify`) with CORS controls and API authentication.
  - Events are stored in append-only JSON Lines format.

### 3.5 Threat 5: Sensitive Data Exposure (Biometric Privacy)
- **Scenario**: Voice recordings are saved on disk, violating GDPR Article 9 or India's DPDP Act 2023, and creating a data-leak risk.
- **Dhwani Defense**:
  - Dhwani enforces **Zero Raw Audio Retention**: the raw audio bytes are processed in memory and memory-wiped with zeros (`0x00`) immediately after inference.
  - Only the non-reversible SHA-256 digital fingerprint is saved in the audit log.
