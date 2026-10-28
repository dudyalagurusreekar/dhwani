# Security, Privacy & Compliance Architecture

Dhwani is engineered as a defense-in-depth zero-trust platform for detecting and preventing AI voice impersonation attacks.

---

## 1. Cryptographic Tamper-Evident Audit Ledger

- Every security assessment, policy mitigation action, and verification attempt is committed to an immutable append-only hash chain (`security/audit_chain.py`).
- **Genesis Block**: Preceded by 64 zeros (`0000000000000000000000000000000000000000000000000000000000000000`).
- **Chain Hash Calculation**:
  $$H_n = \text{SHA-256}(H_{n-1} \parallel \text{canonical\_json}(\text{event\_body}))$$
- Any modification, deletion, or insertion in the event ledger invalidates downstream hashes and is immediately flagged by `/api/incidents/verify/chain`.

---

## 2. Caller Privacy & Number Masking

- In adherence to cybersecurity privacy standards, raw telephone numbers are **never displayed in full** on dashboards or logged in plaintext.
- Phone numbers are masked at ingestion:
  - `+14155552671` $\rightarrow$ `+1 ***-***-2671`
  - `+919876543210` $\rightarrow$ `+91 ***-***-3210`

---

## 3. Zero-Knowledge Audio Retention Policy

- Dhwani does **not** persist raw telephone audio or file uploads on permanent storage by default.
- Audio waveforms are held exclusively in volatile RAM during the 4.0375-second analysis window and immediately overwritten or purged.
- Evidence preservation is achieved cryptographically: Dhwani computes and logs the SHA-256 digest of the audio waveform array (`compute_numpy_hash`), providing indisputable legal proof of tampering without storing sensitive conversation recordings.

---

## 4. Responsible AI & Defense-in-Depth Policy

- **No Automated Law Enforcement Reporting**: Dhwani does not automatically file police or authority reports based strictly on AI scores.
- **No Unilateral Blocking**: Calls are not automatically disconnected on an isolated model prediction.
- **Graduated Countermeasures**:
  - `LOW`: Continue call normally.
  - `SUSPICIOUS`: Flag session and elevate monitoring.
  - `HIGH`: Request secondary verification / issue dynamic voice challenge phrase / hold protected transactions.
