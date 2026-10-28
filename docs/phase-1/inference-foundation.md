# Dhwani — Phase 1: Trustworthy AI Inference Foundation Report

## 1. Executive Summary
Phase 1 establishes a verified, robust, and observable AI inference foundation for Dhwani. It repairs detector model loading, introduces PyTorch inference paths for locally present checkpoints (`AASIST.pth`, `AASIST-L.pth`), gracefully handles missing neural artifacts (`w2v2-aasist.onnx`, `ecapa512.onnx`), ensures dynamic telemetry reporting, eliminates benchmark crashes, and protects against silent failures through 74 automated regression tests.

---

## 2. Detector Status Matrix

| Detector | Supported Architectures / Frameworks | Local Artifact Status | Loading Status | Inference Status | Device / Backend | Verified Latency (Median) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AASIST** | PyTorch (`AASIST.pth`), ONNX (`aasist.onnx`) | `models/aasist/AASIST.pth` (1.28 MB) present | `READY` | Real PyTorch Inference | CPU / PyTorch | ~214 ms |
| **AASIST-L** | PyTorch (`AASIST-L.pth`), ONNX (`aasist-l.onnx`) | `ai/aasist/models/weights/AASIST-L.pth` (426 KB) present | `READY` | Real PyTorch Inference | CPU / PyTorch | ~188 ms |
| **ACOUSTIC** | NumPy / SciPy (Spectral Anomaly) | Handcrafted (no weights needed) | `READY` | Real Algorithmic Inference | CPU / NumPy | ~2.6 ms |
| **W2V2-AASIST** | ONNX (`w2v2-aasist.onnx`) | Missing (`models/w2v2_aasist/w2v2-aasist.onnx`) | `UNAVAILABLE` | Explicitly Skipped | N/A | N/A |
| **ECAPA-TDNN** | ONNX (`ecapa512.onnx`) | Missing (`models/speaker/ecapa512.onnx`) | `UNAVAILABLE` | Explicitly Skipped | N/A | N/A |

---

## 3. Preprocessing and Score Semantics

### Preprocessing Specifications
- **Sample Rate:** Strictly 16 kHz (auto-resampled via Librosa if non-16 kHz).
- **Channels:** Single mono channel (auto-downmixed via channel averaging).
- **Format:** 32-bit floating point (`float32`), clamped and cleaned of NaNs / infinities.
- **Window Length:** 64,600 samples (~4.0375 seconds).
  - Audio $< 64,600$ samples is symmetrically/tail padded with zeros.
  - Audio $> 64,600$ samples is sliced to the most recent window.

### Output and Score Semantics
- **Contract Standard:** All active detectors return standardized `DetectorResult` dictionaries.
- **Score Scale:** Bounded float in $[0.0, 1.0]$.
- **Score Direction:** `higher_is_more_spoof`
  - $0.0$: Maximum bona fide / genuine speech confidence.
  - $1.0$: Maximum synthetic / spoof speech confidence.
- **AASIST Logit Conversion:**
  Official AASIST outputs two logits: `[spoof_logit, bona_fide_logit]`.
  The probability of spoof is computed via stabilized logistic calibration:
  $$\Delta = \text{clamp}(\text{logit}[1] - \text{logit}[0], -60.0, 60.0)$$
  $$\text{spoof\_score} = \frac{1}{1 + e^\Delta}$$
- **Acoustic Anomaly Sigmoid:** Anomaly score computed across high-frequency energy ratio, 85% rolloff, spectral flux, and cepstral kurtosis, calibrated via sigmoid transfer function.

---

## 4. Partial-Ensemble & Fusion Behavior

When optional detectors are missing or fail:
1. **Exclusion from Fusion:** Only detectors with `status == "SUCCESS"` and valid numeric `raw_score` values are passed to `AdaptiveFusionEngine` and `ModelAgreementEngine`.
2. **Dynamic Weight Renormalization:** The baseline weights of active detectors are normalized to sum to $1.0$.
3. **Decisiveness & Quality Scaling:** Active weights are scaled based on prediction decisiveness ($|score - 0.5|$) and input audio quality (SNR, clipping).
4. **Degraded Mode / Zero Detectors:** If zero detectors are available, `fake_probability` returns `None`, and the risk engine reports an explicit `INDETERMINATE` status without fabrication.

---

## 5. Runtime Telemetry Repair

### Bug Verified and Fixed
In `backend/routes/system.py`, detector singletons (`_ACOUSTIC_MODEL`, etc.) were imported statically at module load time when they were `None`. Reassignments in `detector.py` did not propagate to the route.

### Solution Implemented
`backend/routes/system.py` now accesses `backend.services.detector` dynamically via `detector.get_active_detectors()` and `detector.get_detector_health()`.
The `/system/status` endpoint truthfully reports live statuses (`ONLINE`, `UNAVAILABLE`, `FAILED`), execution device, and exact diagnostic reasons for missing assets.

---

## 6. Benchmark Verification & Latencies

Executed via:
```powershell
python scripts/system_benchmark_test.py
```
Outcome: All 8 benchmark sections completed with exit code `0`.

### Scorecard Summary
- **VAD Pre-Filter:** 0.12 ms (PASS)
- **Audio Quality Analysis:** 0.92 ms (PASS)
- **Acoustic Detector:** 2.66 ms (PASS)
- **AASIST-L (GAT):** 188.36 ms (PASS)
- **AASIST (Raw GAT):** 214.40 ms (PASS)
- **W2V2-AASIST:** Skipped — missing artifact `w2v2-aasist.onnx`
- **ECAPA-TDNN:** Skipped — missing artifact `ecapa512.onnx`
- **Full Ensemble Pipeline:** 425.61 ms (PASS)
- **Streaming WebSocket (/ws/audio):** 426.13 ms (PASS)

---

## 7. Automated Regression Suite

Executed via:
```powershell
$env:PYTHONPATH="." ; .\.venv\Scripts\pytest.exe tests/ -v
```
Results:
- **Total Tests:** 74 passed, 0 failed, 0 warnings in 17.13s
- **Baseline Preserved:** All 60 original tests continue to pass.
- **Phase 1 Additions:** 14 new tests in `tests/test_phase1_inference.py` covering PyTorch model inference, missing-weight resilience, non-crashing partial fusion, and dynamic status inspection.

---

## 8. Missing Assets and Reproduction Instructions

To activate the currently unavailable models:
1. **W2V2-AASIST ONNX Model (~1.26 GB):**
   - Source: Hugging Face repository `SpeechAntiSpoofingBenchmarks/W2V2-AASIST`
   - Target Path: `models/w2v2_aasist/w2v2-aasist.onnx`
   - Acquisition command: `python scripts/download_models.py`
2. **ECAPA-TDNN ONNX Model (~24.8 MB):**
   - Source: SpeechBrain ECAPA512 ONNX export
   - Target Path: `models/speaker/ecapa512.onnx`
