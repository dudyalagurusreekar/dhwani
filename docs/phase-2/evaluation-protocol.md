# Phase 2: Scientific Evaluation Protocol for Voice Anti-Spoofing & Deepfake Detection

**Document Version:** 1.0.0  
**Date:** October 25, 2026  
**Status:** Canonical Evaluation Standard  
**Target Architecture:** Dhwani / EchoShield AI Inference & Risk Pipeline  

---

## 1. Intended Task Definition

The objective of Dhwani is **binary anti-spoofing classification**: determining whether an input audio recording represents authentic human vocalization (**bona fide**) or artificially generated / manipulated speech (**spoof**).

In this protocol:
- **Positive Class:** `spoof` (label = `1`). Represents synthetic text-to-speech (TTS), voice conversion (VC), or physical loudspeaker replay attacks.
- **Negative Class:** `bonafide` (label = `0`). Represents genuine, un-manipulated human speech.

---

## 2. Label Convention & Score Semantics

### 2.1 Label Canonicalization
Manifests and metadata files may use varying label conventions depending on the source dataset. The loader canonicalizes all labels into standard binary representations:

| Source Label String | Canonical Token | Numerical Class | Meaning |
| :--- | :--- | :---: | :--- |
| `"bonafide"`, `"bona-fide"`, `"bona_fide"`, `"genuine"`, `"real"`, `"0"` | `bonafide` | `0` | Authentic human speech |
| `"spoof"`, `"fake"`, `"synthetic"`, `"clone"`, `"attack"`, `"1"` | `spoof` | `1` | Deepfake / manipulated speech |

Any label outside this set (such as `"unknown"`, `""`, or multi-class annotations) is rejected with an actionable parsing error. Ambiguous labels are never silently coerced.

### 2.2 Score Semantics
Every operational detector and the fused ensemble produce a continuous probability score:
$$s \in [0.0, 1.0]$$
- **Direction:** `higher_is_more_spoof`
- $s = 0.0$: Maximum confidence of bona fide speech.
- $s = 1.0$: Maximum confidence of spoof speech.
- **Decision Rule:**
  Given an operational decision threshold $\tau \in (0.0, 1.0)$:
  $$\hat{y} = \begin{cases} 1 \ (\text{spoof}) & \text{if } s \ge \tau \\ 0 \ (\text{bonafide}) & \text{if } s < \tau \end{cases}$$

---

## 3. Detector Inventory & Operational Availability

As verified in Phase 1, the pipeline consists of 5 detectors with the following runtime availability:

| Detector Identifier | Architecture / Engine | Operational Status | Default Weight | Behavior in Evaluation |
| :--- | :--- | :---: | :---: | :--- |
| **AASIST** | Raw waveform Graph Attention (PyTorch) | **OPERATIONAL** | 0.30 | Executes real PyTorch inference on CPU |
| **AASIST-L** | Lightweight Graph Attention (PyTorch) | **OPERATIONAL** | 0.25 | Executes real PyTorch inference on CPU |
| **ACOUSTIC** | Handcrafted LFCC & Spectral moments (NumPy) | **OPERATIONAL** | 0.15 | Executes feature extraction on CPU |
| **W2V2-AASIST** | Wav2Vec 2.0 Self-Supervised + GAT (ONNX) | **UNAVAILABLE** | 0.25 | Checkpoint missing; returns `status="SKIPPED"` |
| **ECAPA-TDNN** | Deep Speaker Embeddings (ONNX) | **UNAVAILABLE** | 0.05 | Checkpoint missing; returns `status="UNAVAILABLE"` |

### Partial Ensemble Rule
In the current environment, the ensemble runs with 3 operational detectors (AASIST, AASIST-L, ACOUSTIC).
Weights are dynamically normalized over the active set:
$$\tilde{w}_i = \frac{w_i}{\sum_{j \in \text{operational}} w_j}$$
For the active subset, effective weights are:
- $\tilde{w}_{\text{AASIST}} = 0.30 / 0.70 \approx 0.4286$
- $\tilde{w}_{\text{AASIST-L}} = 0.25 / 0.70 \approx 0.3571$
- $\tilde{w}_{\text{ACOUSTIC}} = 0.15 / 0.70 \approx 0.2143$

Unavailable detectors are never assigned a synthetic zero score; they are omitted from fusion without distorting the operational scores.

---

## 4. Audio Ingestion & Preprocessing Specification

All audio samples evaluated under this protocol must satisfy:
1. **Sampling Rate:** 16,000 Hz. Audio at other rates must be resampled using high-quality anti-aliasing interpolation (`soxr` or `scipy.signal.resample_poly`).
2. **Channel Format:** Single-channel mono. Stereo recordings are downmixed by channel averaging: $x = \frac{x_L + x_R}{2}$.
3. **Encoding:** 16-bit linear PCM (WAV) or lossless FLAC.
4. **Window Length:** Exactly 64,600 samples (4.0375 seconds) for neural model input.
   - **Short Audio ($< 64,600$ samples):** Padded via **repeat waveform tiling** (`np.tile`) matching original AASIST training data loader (`ai/aasist/data_utils.py:39-46`). Zero-padding is explicitly prohibited because it introduces artificial silence discontinuities.
   - **Long Audio ($> 64,600$ samples):** Evaluated in sliding windows or truncated to the initial 64,600 samples for standardized static evaluation.
5. **Amplitude Normalization:** Waveforms are peak-normalized: $x_{\text{norm}} = \frac{x}{\max(|x|) + 10^{-8}}$.
6. **Integrity Validation:** Audio buffers containing non-finite samples (`NaN`, `+Inf`, `-Inf`) or zero-byte payloads are rejected or sanitized prior to inference.

---

## 5. Dataset Provenance, Partitions & Leakage Prevention

### 5.1 Canonical Benchmark Target: ASVspoof 2019 / 2021 Logical Access (LA)
- **Provenance:** The ASVspoof consortium (Automatic Speaker Verification Spoofing and Countermeasures Challenge).
- **Licensing:** Open Data Commons Attribution License (ODC-By) or Creative Commons Attribution (CC-BY).
- **Split Definitions:**
  - `train`: Used exclusively for model parameter training. (No training occurs in Phase 2).
  - `dev` (Validation): Used **exclusively** for operating threshold calibration, EER estimation, and hyperparameter tuning.
  - `eval` (Test): Held-out test set evaluated **exactly once** using the threshold selected on `dev`.
- **Speaker Independence:** Speaker IDs in `eval` must not overlap with speaker IDs in `dev` or `train`.
- **Attack Disjointness:** `eval` contains unseen attack algorithms (e.g., neural vocoders, diffusion synthesis) not present in `dev`, testing out-of-distribution generalization.

### 5.2 Prohibition of Synthetic Smoke Data as Benchmark Evidence
Synthetic sine waves, chirp signals, or pure Gaussian noise are strictly reserved for unit-test sanity checks and smoke verification. Under no circumstances may metrics derived from synthetic fixtures be reported as detection accuracy or benchmark performance.

---

## 6. Evaluation Metrics

### 6.1 Confusion Matrix & Basic Rates
With positive class = `spoof`:
- **True Positive ($\text{TP}$):** Spoof audio correctly classified as spoof ($\hat{y}=1, y=1$).
- **False Negative ($\text{FN}$):** Spoof audio incorrectly classified as bona fide ($\hat{y}=0, y=1$) — **Missed attack**.
- **True Negative ($\text{TN}$):** Bona fide audio correctly classified as bona fide ($\hat{y}=0, y=0$).
- **False Positive ($\text{FP}$):** Bona fide audio incorrectly classified as spoof ($\hat{y}=1, y=0$) — **False alarm**.

Key derived metrics:
- $\text{Accuracy} = \frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}}$
- $\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$
- $\text{Recall / TPR} = \frac{\text{TP}}{\text{TP} + \text{FN}}$
- $\text{Specificity / TNR} = \frac{\text{TN}}{\text{TN} + \text{FP}}$
- $\text{F1-Score} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$

### 6.2 Biometric Error Rates
In speaker verification and anti-spoofing biometrics:
- **False Alarm Rate ($\text{FAR}$):** Proportion of genuine speech falsely rejected/flagged:
  $$\text{FAR}(\tau) = \frac{\text{FP}}{N_{\text{bonafide}}}$$
- **False Acceptance Rate ($\text{FRR}$ or $\text{Miss Rate}$):** Proportion of spoof attacks falsely accepted as authentic:
  $$\text{FRR}(\tau) = \frac{\text{FN}}{N_{\text{spoof}}}$$

### 6.3 Equal Error Rate (EER)
The Equal Error Rate is the empirical operating point where the false alarm rate equals the false acceptance rate:
$$\text{EER} = \text{FAR}(\tau^*) = \text{FRR}(\tau^*)$$
- **Calculation Protocol:**
  1. Evaluate $\text{FAR}(\tau)$ and $\text{FRR}(\tau)$ across all unique candidate score thresholds.
  2. Locate the threshold pair $(\tau_k, \tau_{k+1})$ where $(\text{FAR} - \text{FRR})$ changes sign.
  3. Interpolate linearly to determine the exact threshold $\tau^*$ and corresponding $\text{EER}$:
     $$\tau^* = \tau_k + (\tau_{k+1} - \tau_k) \cdot \frac{\text{FRR}(\tau_k) - \text{FAR}(\tau_k)}{(\text{FAR}(\tau_{k+1}) - \text{FAR}(\tau_k)) - (\text{FRR}(\tau_{k+1}) - \text{FRR}(\tau_k))}$$
- **Edge Cases:** If all scores are identical, or if a class is entirely absent, EER is mathematically undefined. The evaluator must report `EER: None` with an explicit diagnostic reason rather than inventing $0\%$ or $50\%$.

### 6.4 Receiver Operating Characteristic (ROC) & AUC
- The ROC curve plots $\text{TPR}(\tau)$ against $\text{FPR}(\tau) = \text{FAR}(\tau)$ across all thresholds $\tau \in [0, 1]$.
- **ROC-AUC:** Computed via trapezoidal integration. An uninformative classifier yields $\text{AUC} = 0.50$; a perfect classifier yields $\text{AUC} = 1.00$.

---

## 7. Threshold Calibration Protocol

1. **Validation Split Only:** Threshold calibration is executed strictly on predictions from the validation partition (`dev`). The test partition (`eval`) is never inspected during calibration.
2. **Supported Objectives:**
   - **`eer`:** Minimize $|\text{FAR}(\tau) - \text{FRR}(\tau)|$. Standard academic operating point.
   - **`target_far`:** Find threshold $\tau$ such that $\text{FAR}(\tau) \le \alpha$ (e.g. $\alpha = 1.0\%$) to minimize nuisance false alarms in high-volume customer service centers.
   - **`cost_sensitive`:** Minimize weighted decision cost:
     $$C_{\text{decision}} = C_{\text{miss}} \cdot P_{\text{spoof}} \cdot \text{FRR}(\tau) + C_{\text{fa}} \cdot (1 - P_{\text{spoof}}) \cdot \text{FAR}(\tau)$$
3. **Artifact Output:** Selected thresholds are stored in `config/evaluation/calibrated_thresholds.json` alongside dataset provenance, sample counts, optimization objective, and creation timestamp. Production defaults are never overwritten automatically.

---

## 8. Reproducibility & Environment Reporting

Every evaluation report generated must include:
1. Git commit SHA and working branch name.
2. System hardware specification (CPU architecture, RAM, GPU availability).
3. PyTorch, ONNX Runtime, and NumPy library versions.
4. Active vs skipped detector list.
5. Deterministic random seed where applicable.
6. Checksum (SHA-256) of the evaluation manifest file.
