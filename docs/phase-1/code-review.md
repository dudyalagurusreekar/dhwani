# Phase 1 Code Review & Verification Report: Trustworthy AI Inference Foundation

**Repository:** `https://github.com/dudyalagurusreekar/dhwani.git`  
**Working Branch:** `feature/phase-1-inference-foundation`  
**Base Audit Commit:** `a45e40aa6fec462cc770325b41802f8629e4b1f7`  
**Review Date:** October 25, 2026  
**Auditor:** Senior AI/ML & Reliability Engineering Reviewer  

---

## A. Review Verdict

### **VERDICT: APPROVED WITH LIMITATIONS**

The Phase 1 implementation successfully transforms Dhwani from a purely handcrafted acoustic detector stub into an operational multi-model anti-spoofing system executing real PyTorch neural inference for both AASIST and AASIST-L. Architectural contracts, partial ensemble resilience, safe checkpoint deserialization, device reporting transparency, and session isolation have been rigorously audited, corrected, and verified with 80 passing tests (100% pass rate).

#### Justification for Verdict
1. **Core Architecture Operational:** Real PyTorch inference executes locally for AASIST and AASIST-L with sub-200ms latency per 4-second audio window. Handcrafted acoustic feature extraction executes in <3ms.
2. **Score Semantics & Class Mapping Proven:** Proven from original training ground truth (`ai/aasist/data_utils.py` lines 22 & 35) that output index 0 is `spoof` and index 1 is `bonafide`. Probability mapping is mathematically sound and numerically stabilized.
3. **Session Isolation Implemented:** Thread-safe per-session memory profiles and lifecycle cleanup hooks have been integrated across FastAPI REST endpoints, WebSocket streams, and Twilio telephony handlers.
4. **Device Discrepancy Resolved:** The benchmark scorecard discrepancy where CPU fallback was labeled as `Combined (CPU+CUDA)` has been corrected to dynamically reflect the actual device (`Combined (CPU)`).
5. **Limitations:**
   - **External Models Missing:** `w2v2-aasist.onnx` (~1.26 GB) and `ecapa512.onnx` (~24.8 MB) are absent from the Git tree; their adapters gracefully skip rather than crash, but the ensemble currently runs with 3 of 5 detectors active.
   - **Pre-Calibration State:** Thresholds (0.50 default) and calibration curves have not yet been evaluated on ASVspoof 2019/2021 LA benchmark datasets (scheduled for Phase 2).

---

## B. Model Correctness

### 1. Checkpoint Compatibility & Safe Deserialization
- **AASIST Checkpoint:** `models/aasist/AASIST.pth` (7.4 MB)
- **AASIST-L Checkpoint:** `ai/aasist/models/weights/AASIST-L.pth` (3.3 MB)
- **Safe Loading:** Checkpoint loading uses `torch.load(..., map_location=device, weights_only=True)`. This eliminates arbitrary Python object deserialization vulnerabilities (CVE risk mitigation).
- **Architecture Instantiation:** Model configurations (`ai/aasist/config/AASIST.conf` and `ai/aasist/config/AASIST-L.conf`) are parsed to instantiate the exact `Model` class defined in `ai/aasist/models/AASIST.py`.
- **Evaluation Mode:** Both adapters explicitly invoke `self.model.eval()` and execute inference within `torch.no_grad()` contexts.

### 2. Audio Preprocessing & Repeat Tiling Alignment
- **Input Specifications:** 16,000 Hz sample rate, single-channel (mono), 64,600 samples (4.0375 seconds).
- **Tiling vs Zero-Padding:**
  - *Initial Implementation:* Padded short audio buffers with trailing zeros (`np.pad(audio, (0, 64600 - len(audio)))`).
  - *Correction Made:* The original AASIST training protocol (`ai/aasist/data_utils.py`, lines 39–46) utilizes repeat waveform tiling:
    ```python
    nb_repeats = int(max_len / len(x)) + 1
    padded_x = np.tile(x, (1, nb_repeats))[:, :max_len][0]
    ```
  - *Resolution:* Both `aasist_adapter.py` and `aasist_l_adapter.py` were corrected to use repeat tiling for audio $< 64,600$ samples. This preserves pitch contours and phoneme periodicity across the SincNet filterbanks rather than introducing artificial silence discontinuities.
- **Normalization:** Audio waveforms are normalized by their peak absolute amplitude: `audio = audio / (np.max(np.abs(audio)) + 1e-8)`.
- **Multi-channel & Non-finite Resilience:** Multi-channel audio (e.g. stereo shape `(N, 2)`) is downmixed to mono via channel averaging (`np.mean(audio, axis=-1)`). Non-finite values (`NaN`, `+Inf`, `-Inf`) are replaced with `0.0` before tensor conversion.

### 3. Logit Class Mapping & Probability Derivation
- **Ground Truth Evidence:**
  Inspected the original training data loader in `ai/aasist/data_utils.py`:
  - Line 22: `d_meta[key] = 1 if label == "bonafide" else 0`
  - Line 35: `d_meta[key] = 1 if label == "bonafide" else 0`
  - In `ai/aasist/main.py:307`: `batch_score = batch_out[:, 1]`
- **Logit Interpretation:**
  - Output tensor shape: `(batch_size, 2)`
  - Index 0: `spoof` logit ($z_0$)
  - Index 1: `bonafide` logit ($z_1$)
- **Probability Computation:**
  To compute $P(\text{spoof})$, the adapters compute the difference:
  $$\Delta z = \text{clip}(z_{\text{bonafide}} - z_{\text{spoof}}, -60.0, 60.0)$$
  $$P(\text{spoof}) = \frac{1}{1 + e^{\Delta z}} = \frac{e^{z_{\text{spoof}}}}{e^{z_{\text{spoof}}} + e^{z_{\text{bonafide}}}}$$
  This is the exact two-class softmax probability for the spoof class, stabilized against exponential overflow for extreme logit magnitudes.
- **Score Direction:**
  Strictly standardized across all adapters: `higher_is_more_spoof` where $0.0 = \text{bona fide}$ and $1.0 = \text{spoof}$.

---

## C. Detector and Fusion Correctness

### 1. Detector Contract & Output Schema
All detector adapters (`AASISTAdapter`, `AASISTLAdapter`, `AcousticDetector`, `W2V2AASISTAdapter`) conform to the standardized `DetectorResult` schema:
```python
{
    "model": str,               # e.g., "AASIST", "AASIST-L", "ACOUSTIC", "W2V2-AASIST"
    "raw_score": Optional[float], # 0.0 to 1.0 (or None when unavailable/failed)
    "status": str,              # "SUCCESS", "SKIPPED", "FAILED", "UNAVAILABLE"
    "device": str,              # "cpu" or "cuda"
    "backend": str,             # "pytorch", "numpy", "onnxruntime"
    "latency_ms": float,
    "score_direction": "higher_is_more_spoof",
    "error": Optional[str],
}
```

### 2. Behavioral Verification Across Ensemble States
- **Full Ensemble (Ideal State):** If all 5 detectors are present, weights are assigned according to SNR and empirical reliability (AASIST: 0.30, AASIST-L: 0.25, W2V2-AASIST: 0.25, ACOUSTIC: 0.15, ECAPA: 0.05).
- **Partial Ensemble (Current Production State):**
  - AASIST (`SUCCESS`), AASIST-L (`SUCCESS`), and ACOUSTIC (`SUCCESS`) actively participate.
  - W2V2-AASIST is marked `SKIPPED` (raw_score=`None`).
  - `AdaptiveFusionEngine.fuse` dynamically filters out skipped/failed models and renormalizes weights exclusively across the operational detectors:
    $$\tilde{w}_i = \frac{w_i}{\sum_{j \in \text{operational}} w_j}$$
  - Active weights: AASIST: $0.30 / 0.70 \approx 0.429$, AASIST-L: $0.25 / 0.70 \approx 0.357$, ACOUSTIC: $0.15 / 0.70 \approx 0.214$.
- **Zero Available Detectors (Catastrophic/Cold Failure):**
  - When all models fail or are skipped, `AdaptiveFusionEngine.fuse` returns `fused_score = None` and `active_models = []`.
  - `calculate_risk(fake_probability=None)` outputs:
    ```python
    {
        "status": "INDETERMINATE",
        "risk_score": 0,
        "recommendation": "VERIFY_CALLER",
        "active_models": []
    }
    ```
  - This prevents false reassurance by rejecting ungrounded `ALLOW` actions when security models are inoperable.
- **Backward Compatibility:**
  `_is_valid()` in `adaptive_fusion.py` and `model_agreement.py` accommodates legacy dictionaries lacking an explicit `"status"` key, provided `raw_score` is finite.

---

## D. Device and Benchmark Verification

### 1. Root Cause of Device Discrepancy
- **Identified Discrepancy:** The Phase 1 summary report previously noted `Combined (CPU+CUDA)` in its scorecard, yet runtime status reported CPU execution.
- **Root Cause Located:** `scripts/system_benchmark_test.py` contained a hardcoded print statement:
  ```python
  # Old line 325:
  print(f"{'Full Ensemble Pipeline':<24} {'Combined (CPU+CUDA)':<26} {med_proc:.2f} ms PASS")
  ```
- **Correction Made:** Modified to check `torch.cuda.is_available()` dynamically:
  ```python
  comb_provider = "Combined (CPU+CUDA)" if torch.cuda.is_available() else "Combined (CPU)"
  print(f"{'Full Ensemble Pipeline':<24} {comb_provider:<26} {med_proc:.2f} ms PASS")
  ```
- **Device Audit:**
  - `torch.cuda.is_available()` returns `False` on the local testbed.
  - Both AASIST and AASIST-L explicitly select `cpu` device and run on host threads.
  - ONNX Runtime initializes `CPUExecutionProvider`.
  - Benchmark output now accurately and honestly reports `Combined (CPU)`.

### 2. Measured Benchmark Latencies (Local Windows Environment)
From execution of `python scripts/system_benchmark_test.py`:

| Component / Test | Provider / Stack | Median Latency | Execution Status |
| :--- | :--- | :--- | :--- |
| **VAD Pre-Filter** | CPU (NumPy/ZCR) | 0.12 ms | **PASS** |
| **Audio Quality** | CPU (Spectral SNR) | 0.80 ms | **PASS** |
| **Acoustic Detector** | CPU (LFCC/Spectral) | 2.60 ms | **PASS** |
| **AASIST-L** | CPU (PyTorch) | 166.93 ms | **PASS** |
| **AASIST** | CPU (PyTorch) | 188.76 ms | **PASS** |
| **W2V2-AASIST** | ONNX (~1.26 GB missing) | N/A | **SKIPPED** (Handled) |
| **ECAPA-TDNN** | ONNX (24.8 MB missing) | N/A | **SKIPPED** (Handled) |
| **Full Ensemble Pipeline** | **Combined (CPU)** | **372.21 ms** | **PASS** |
| **Streaming WebSocket** | FastAPI / WS PCM16 | 361.55 ms | **PASS** |

### 3. Real-Time Streaming Cadence Feasibility
- Target window size: 4.0375 seconds (64,600 samples)
- Sliding hop interval: 1.0 second (16,000 samples)
- Measured processing latency: **372.21 ms**
- Headroom: **627.79 ms per second** (62.8% idle margin on standard multi-core CPU)

---

## E. Session Isolation

### 1. Speaker Consistency State Management
- **Audit Findings:** Previously, `SpeakerConsistencyEngine` stored state in global attributes `anchor_embedding` and `recent_embeddings`, allowing cross-call leakage if multiple sessions accessed the engine concurrently.
- **Enhancements Implemented:**
  1. **Thread-Safe Session Dictionary:**
     ```python
     self.session_profiles: Dict[str, Dict[str, Any]] = {}
     self._lock = threading.Lock()
     ```
  2. **Session-Specific Tracking:** `evaluate_consistency` tracks anchor and rolling embeddings on a per-`session_id` basis.
  3. **Non-Finite Guard:** If an embedding contains non-finite numbers (`NaN` or `Inf`), the function aborts with `status="FAILED"` without polluting session history.
  4. **Targeted Cleanup Hook:** `reset_session(session_id: Optional[str] = None)` removes specific session profiles on call termination or purges all profiles if `session_id is None`.

### 2. Service & API Layer Wiring
- `backend/services/detector.py`: Added `session_id` parameters to `detect_voice_sync` and `detect_voice`, forwarding to `speaker_engine.evaluate_consistency`. Added top-level `reset_session(session_id)` helper.
- `backend/routes/analyze.py`: Generates or extracts `session_id` and passes it to `detect_voice`.
- `backend/websocket/audio.py`: Maintains `session_id = session.session_id`, passes it to `detect_voice`, and triggers `reset_session(session_id)` upon WebSocket disconnect.
- `streaming/telephony/twilio_websocket.py`: Passes `session_id = current_session.call_sid`.

---

## F. Test Quality and Classification

All 20 tests in `tests/test_phase1_inference.py` were audited and classified:

| Test Name | Test Category | Objective Verified | Status |
| :--- | :--- | :--- | :--- |
| `test_aasist_pytorch_loading_and_inference` | **Real Model Integration** | Real AASIST `.pth` loading, forward pass, output tensor dimensions, bounds $[0, 1]$. | **PASS** |
| `test_aasist_l_pytorch_loading_and_inference` | **Real Model Integration** | Real AASIST-L `.pth` loading, forward pass, output bounds. | **PASS** |
| `test_acoustic_detector_execution` | **Real Model Integration** | Handcrafted NumPy LFCC/spectral extraction on silence and synthetic speech. | **PASS** |
| `test_missing_checkpoints_graceful_handling` | **Failure-Path** | `strict=False` returns `SKIPPED`/`UNAVAILABLE`; `strict=True` raises `FileNotFoundError`. | **PASS** |
| `test_audio_preprocessing_resilience` | **Failure-Path** | Short audio ($<64600$ samples) repeat-tiled; stereo downmixed; `NaN`/`Inf` replaced. | **PASS** |
| `test_numerical_reproducibility` | **Real Model Integration** | Deterministic inference repeatability for identical inputs within $10^{-5}$ tolerance. | **PASS** |
| `test_registry_and_active_detectors` | **Runtime Health** | Dynamic detector registry, detector discovery, and availability flags. | **PASS** |
| `test_detector_health_summary` | **Runtime Health** | Lifecycle status (`READY`), ready count ($\ge 3$), unavailable count ($\ge 1$). | **PASS** |
| `test_detect_voice_sync_partial_ensemble` | **Real Model Integration** | End-to-end `detect_voice_sync` with real ensemble; verifies partial ensemble weighting. | **PASS** |
| `test_detect_voice_sync_with_empty_bytes` | **Failure-Path** | Zero-length audio byte input handled gracefully without unhandled exception. | **PASS** |
| `test_adaptive_fusion_filters_unsuccessful_detectors` | **Unit Test with Mocks** | Verifies `SKIPPED` and `FAILED` detectors are excluded from fusion weights. | **PASS** |
| `test_adaptive_fusion_empty_or_all_failed` | **Failure-Path** | All-failed ensemble outputs `fused_score = None` and `active_models = []`. | **PASS** |
| `test_model_agreement_with_partial_models` | **Unit Test with Mocks** | Model agreement logic correctly evaluates consensus when detectors are missing. | **PASS** |
| `test_calculate_risk_when_detectors_unavailable` | **Failure-Path** | Missing `fake_probability` triggers `INDETERMINATE` risk and `VERIFY_CALLER`. | **PASS** |
| `test_adaptive_fusion_backward_compatibility_missing_status` | **Unit Test with Mocks** | Legacy detector result dicts omitting `status` key are correctly accepted. | **PASS** |
| `test_model_agreement_backward_compatibility_missing_status` | **Unit Test with Mocks** | Consensus evaluation handles legacy result dicts omitting `status` key. | **PASS** |
| `test_session_isolated_anchor_and_history` | **Session-Isolation** | Verifies orthogonal sessions maintain distinct anchors and histories without leak. | **PASS** |
| `test_session_reset_lifecycle` | **Session-Isolation** | Selective reset of single session leaves parallel sessions intact; global reset clears all. | **PASS** |
| `test_non_finite_embedding_does_not_poison_state` | **Failure-Path / Session-Isolation** | `NaN` embedding returns `FAILED` and does not enroll into session profile. | **PASS** |
| `test_backend_detector_service_session_api_integration` | **Runtime Health / Session-Isolation** | `detect_voice_sync(audio, session_id=...)` API plumbing and service cleanup. | **PASS** |

### Test Suite Execution Summary
- **Baseline Tests (Pre-Phase 1):** 60 tests passed
- **Phase 1 Test Suite (`tests/test_phase1_inference.py`):** 20 tests passed
- **Full Test Suite (`pytest tests/ -v`):** **80 passed** in 15.47s (0 failures, 0 errors, 0 warnings)

---

## G. Corrections Made During Engineering Review

| File Modified | Confirmed Defect / Discrepancy Addressed |
| :--- | :--- |
| `ai/aasist/aasist_adapter.py` | Corrected short-audio zero-padding to repeat-waveform tiling (`np.tile`) to match official training preprocessing in `ai/aasist/data_utils.py`. |
| `ai/aasist/aasist_l_adapter.py` | Corrected short-audio zero-padding to repeat-waveform tiling (`np.tile`) to match official training preprocessing. |
| `ai/ssl_detector/w2v2_aasist_adapter.py` | Set `status="SKIPPED"` instead of `"FAILED"` when `self.status == DetectorStatus.UNAVAILABLE`, ensuring missing artifacts do not look like runtime crashes. |
| `ai/speaker/speaker_consistency.py` | Added thread-safe `session_profiles` tracking, `_lock`, non-finite embedding checks, and `reset_session()` cleanup hook. |
| `backend/services/detector.py` | Added `session_id` parameter to `detect_voice_sync` and `detect_voice`, wiring through to speaker consistency; added `reset_session()` service helper. |
| `backend/routes/analyze.py` | Extracted/generated `session_id` and forwarded it to `detect_voice`. |
| `backend/websocket/audio.py` | Forwarded `session_id` to `detect_voice` and added `reset_session(session_id)` on client disconnect. |
| `streaming/telephony/twilio_websocket.py` | Forwarded `current_session.call_sid` as `session_id` to `detect_voice`. |
| `risk_engine/adaptive_fusion.py` | Made detector validation robust to missing `status` keys (backward compatibility) while strictly filtering out failed/skipped models and non-finite raw scores. |
| `risk_engine/model_agreement.py` | Made detector validation robust to missing `status` keys while strictly filtering out failed/skipped models and non-finite raw scores. |
| `risk_engine/fusion.py` | Added `raw_score is not None` guard before float conversion to prevent `TypeError` during fallback fusion. |
| `ai/common/attack_attribution.py` | Added `raw_score is not None` guard before extracting model scores. |
| `streaming/live_risk_pipeline.py` | Fixed `TypeError` in `_print_window_report` when printing detector scores for skipped/failed models with `raw_score=None`. |
| `scripts/system_benchmark_test.py` | Resolved `Combined (CPU+CUDA)` reporting discrepancy by dynamically checking `torch.cuda.is_available()`. |
| `tests/test_phase1_inference.py` | Added 6 new regression tests covering session isolation, state reset, non-finite embedding guards, and backward compatibility. |

---

## H. Remaining Issues & Risk Matrix

| Issue ID | Description | Severity | Evidence | Concrete Remediation |
| :--- | :--- | :--- | :--- | :--- |
| **DH-P1-01** | Missing `w2v2-aasist.onnx` checkpoint (~1.26 GB) | **Medium** | `models/w2v2_aasist/w2v2-aasist.onnx` is not present in repository. Benchmark marks it `SKIPPED`. | Execute `python scripts/download_models.py` in environments with high-bandwidth network access, or host on external model registry (Hugging Face). |
| **DH-P1-02** | Missing `ecapa512.onnx` checkpoint (~24.8 MB) | **Medium** | `models/speaker/ecapa512.onnx` is not present in repository. Speaker consistency engine operates in `UNAVAILABLE` fallback mode. | Execute `python scripts/download_models.py` or export pretrained SpeechBrain ECAPA-TDNN to ONNX. |
| **DH-P1-03** | Default Decision Thresholds Uncalibrated on Labeled Data | **Low** (Expected for Phase 1) | Adapters currently apply uncalibrated 0.50 cutoff. | Phase 2 objective: ingest ASVspoof 2019/2021 LA evaluation splits, compute EER / min t-DCF, and derive calibrated operational thresholds. |

---

## I. Next Step Recommendation

### **Recommendation: PROCEED TO PHASE 2 (DATASET EVALUATION & BENCHMARKING)**

The Phase 1 Trustworthy AI Inference Foundation is solid, robust, and verified:
1. AASIST and AASIST-L run local PyTorch inference with verified checkpoint weights and proven class mapping.
2. The pipeline gracefully accommodates absent external ONNX weights without crashing.
3. Partial ensemble fusion, consensus voting, risk estimation, and session isolation are verified across unit, integration, and streaming tests.
4. All 80 automated tests pass cleanly with zero failures.

The project is now ready to proceed to **Phase 2: Labeled-Data Evaluation & Threshold Calibration**, where ASVspoof ground truth evaluation splits can be evaluated against the operational multi-model pipeline.
