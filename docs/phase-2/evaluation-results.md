# Phase 2: Evaluation Results & Verification Summary

**Date:** October 25, 2026  
**Repository Branch:** `feature/phase-1-inference-foundation`  
**Evaluation Harness:** `scripts/evaluation/evaluate.py`  
**Calibration Engine:** `scripts/evaluation/calibrate_thresholds.py`  

---

## 1. Categorization of Results

In strict adherence to the Phase 2 Evaluation Protocol, this report explicitly distinguishes between the evaluation categories:

1. **Official Benchmark Split Results:** **NONE / NOT EVALUATED**  
   *Official ASVspoof 2019 LA, ASVspoof 2021 LA, or In-the-Wild benchmark splits are not present in the local repository.* Benchmark accuracy, true EER, and min t-DCF on out-of-distribution speech can only be computed once the external datasets are downloaded using `docs/phase-2/dataset-setup.md`.
2. **Results from Locally Available Labeled Data:** **EVALUATED FOR VERIFICATION ONLY**  
   *The repository contains `real_speech.wav` (27.1s), `acoustic_test.wav` (8.0s), and `microphone_test.wav` (10.0s).* These recordings verify basic audio ingestion and single-sample inference, but cannot establish statistical generalization.
3. **Synthetic Smoke-Test Results:** **EVALUATED (5 Utterances)**  
   *Conducted using `tests/fixtures/sample_manifest.csv` and `tests/fixtures/audio_smoke/`.* The results below represent a mechanical smoke verification of the evaluator, metrics calculations, and calibration engine. **They do not represent real-world model accuracy.**

---

## 2. Synthetic Smoke-Test Execution Metrics

### 2.1 Execution Configuration
- **Manifest:** `tests/fixtures/sample_manifest.csv` (5 audio records: 3 bona fide, 2 spoof)
- **Audio Root:** `tests/fixtures/audio_smoke/`
- **Active Operational Ensemble:** AASIST (PyTorch), AASIST-L (PyTorch), ACOUSTIC (NumPy)
- **Skipped / Unavailable Detectors:** W2V2-AASIST (ONNX ~1.26 GB missing), ECAPA-TDNN (ONNX 24.8 MB missing)
- **Decision Threshold Tested:** $0.5000$ (default production baseline)
- **Execution Environment:** Windows 11, Intel/AMD multi-core host CPU, PyTorch 2.14.1+cpu (CUDA disabled)
- **Timing:** 1.82 seconds total elapsed time (avg 364.28 ms per 4-second audio window)

### 2.2 Fused Pipeline Confusion Matrix & Hard Metrics
$$\text{Positive Class} = \text{spoof} \ (1), \quad \text{Negative Class} = \text{bonafide} \ (0)$$

| Metric | Measured Value | Theoretical Meaning |
| :--- | :---: | :--- |
| **True Positives ($\text{TP}$)** | 2 | Spoofs correctly classified as spoof |
| **False Positives ($\text{FP}$)** | 2 | Bona fide audio falsely flagged as spoof |
| **True Negatives ($\text{TN}$)** | 1 | Bona fide audio correctly classified as genuine |
| **False Negatives ($\text{FN}$)** | 0 | Spoofs missed (classified as bona fide) |
| **Total Utterances** | 5 | 3 bona fide, 2 spoof |
| **Accuracy** | **0.6000** | $(2 + 1) / 5 = 60.0\%$ |
| **Precision** | **0.5000** | $2 / (2 + 2) = 50.0\%$ |
| **Recall / Sensitivity ($\text{TPR}$)** | **1.0000** | $2 / (2 + 0) = 100.0\%$ (All synthetic chirps flagged) |
| **Specificity ($\text{TNR}$)** | **0.3333** | $1 / 3 = 33.3\%$ |
| **F1-Score** | **0.6667** | Harmonic mean of precision and recall |
| **False Alarm Rate ($\text{FAR}$)** | **0.6667** | $2 / (1 + 2) = 66.7\%$ false rejection of bona fide |
| **Miss Rate ($\text{FRR}$)** | **0.0000** | $0 / (2 + 0) = 0.0\%$ missed spoofs |

### 2.3 Continuous Score Metrics
- **ROC-AUC:** $0.3333$ (Reflects synthetic tone vs sine wave heuristic on tiny sample size)
- **Calculated EER:** $0.6667$ (at threshold $\tau = 0.9259$)
- **Per-Utterance Log:** Recorded in `evaluation_results/smoke_test/predictions.jsonl`
- **Structured Metrics:** Recorded in `evaluation_results/smoke_test/metrics.json`

---

## 3. Threshold Calibration Verification

Using `scripts/evaluation/calibrate_thresholds.py` on the smoke predictions:
- **Optimization Objective:** `eer` (Equal Error Rate operating point)
- **Uncertainty Warning Triggered:**
  > `WARNING: Small sample size (5 samples < 100). Threshold estimates have high variance.`
- **Selected Threshold:** $\tau = 0.9266$
- **Artifact Output:** Written to `config/evaluation/calibrated_thresholds.json`
- **Production Isolation:** Production defaults (`0.50`) remain completely unchanged; calibration output is cleanly stored in a versioned JSON artifact.

---

## 4. Pipeline Behavioral Verifications Confirmed

1. **Non-destructive Evaluation:** Running `scripts/evaluation/evaluate.py` does not alter running backend state or overwrite production configuration files.
2. **Missing Model Handling:** `W2V2-AASIST` was recorded as `status="SKIPPED"` and `raw_score=None` across all utterances in `predictions.jsonl`. It was never converted to zero or counted as bona fide.
3. **Weight Normalization:** The partial ensemble dynamically normalized weights across the 3 operational detectors (AASIST: 0.429, AASIST-L: 0.357, ACOUSTIC: 0.214).
4. **Reproducibility:** Evaluation metadata captured Git commit SHA (`a45e40aa6fec462cc770325b41802f8629e4b1f7`), host CPU device, manifest path, and UTC timestamps.
