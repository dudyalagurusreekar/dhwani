# Phase 2: Scientific Limitations, Generalization Boundaries & Operational Risks

**Date:** October 25, 2026  
**Document Target:** Risk & Validity Analysis for Dhwani Evaluation Framework  

---

## 1. Dataset Scope & Generalization Boundaries

### 1.1 Unseen Synthesis & Generator Mismatch
- Modern deepfake speech synthesis algorithms evolve rapidly (e.g. diffusion-based speech synthesis like NaturalSpeech 3, zero-shot neural codec models like VALL-E, Voicebox, and commercial black-box models from ElevenLabs and PlayHT).
- Models trained or calibrated on older datasets (such as ASVspoof 2019, which primarily features classical neural vocoders like WaveNet and Griffin-Lim) frequently suffer severe performance degradation when exposed to modern flow-matching and diffusion architectures.
- **Evaluation Rule:** Achieving a low Equal Error Rate (EER) on an academic development split (e.g., ASVspoof 2019 dev) **does not establish or guarantee real-world generalization** against contemporary zero-shot voice cloners.

### 1.2 Telephony & Codec Acoustic Domain Shift
- The operational Dhwani pipeline integrates Twilio telephony media streams, where audio is compressed using standard 8 kHz G.711 $\mu$-law or AMR-WB before being upsampled to 16 kHz.
- Telephony codecs apply steep bandpass filtering (attenuating frequencies below 300 Hz and above 3,400 Hz) and non-linear companding.
- Handcrafted acoustic detectors relying on high-frequency spectral roll-off ($>4$ kHz) or SincNet filterbanks tuned to wideband speech will experience significant domain shift when processing telephone audio.
- True operational calibration requires evaluating a telephony-degraded partition (such as ASVspoof 2021 DF or audio processed through G.711 transcoders).

### 1.3 Multi-Lingual, Demographic & Accent Variance
- Pretrained anti-spoofing models (AASIST / AASIST-L) were trained predominantly on English-language corpora (VCTK baseline in ASVspoof).
- Phonetic structures, tone variations (e.g., tonal languages like Mandarin), glottal stops, and regional accents (e.g., Indian English, Hindi) can introduce distribution shifts in spectral temporal graphs, potentially increasing the False Alarm Rate (FAR) for genuine non-native speakers.

---

## 2. Infrastructure & Ensemble Limitations

### 2.1 Degraded 3-Model Ensemble (Missing Checkpoints)
- The target production architecture specifies a 5-model ensemble:
  1. AASIST (PyTorch) — **Active**
  2. AASIST-L (PyTorch) — **Active**
  3. ACOUSTIC (NumPy) — **Active**
  4. W2V2-AASIST (ONNX) — **UNAVAILABLE** (Checkpoint `w2v2-aasist.onnx` ~1.26 GB missing)
  5. ECAPA-TDNN (ONNX) — **UNAVAILABLE** (Checkpoint `ecapa512.onnx` ~24.8 MB missing)
- In the current environment, the ensemble runs in partial fallback mode with 3 active detectors.
- The absence of Wav2Vec 2.0 self-supervised representations means the system currently lacks contextual semantic embeddings that are particularly effective at spotting modern neural vocoder artifacts.
- The absence of ECAPA-TDNN speaker embeddings means mid-call speaker consistency verification cannot detect voice-switching attacks during live calls.

### 2.2 Calibration Uncertainty on Small Sample Sizes
- The threshold calibration engine (`scripts/evaluation/calibrate_thresholds.py`) calculates empirical EER and operating thresholds.
- When validation sample sizes are small ($N < 100$) or heavily imbalanced, the threshold estimates exhibit high variance and wide confidence intervals.
- Calibrated thresholds must be re-derived on a full dataset ($N > 2,000$ utterances per split) before being adopted into production configurations.

---

## 3. Operational Deployment Guidance

1. **Threshold Versioning:** Calibrated operating thresholds must always be maintained in versioned JSON artifacts (`config/evaluation/`) rather than hardcoded in source code.
2. **Periodic Benchmark Audits:** Re-run the evaluation runner whenever new detector weights are added or underlying PyTorch / ONNX Runtime dependencies are updated.
3. **Defense-in-Depth:** Anti-spoofing scores must never act as a single-point-of-failure. They should always be fused with cryptographic provenance tokens (`security/hasher.py`), behavioral telephony risk signals, and human-in-the-loop escalation policies.
