# Phase 2: Dataset Acquisition, Manifest Specification & Setup Guide

**Document Version:** 1.0.0  
**Target:** Benchmark Dataset Integration for Dhwani Anti-Spoofing Pipeline  

---

## 1. Missing Benchmark Prerequisite Notice

As established during repository inspection, **no official ASVspoof 2019, ASVspoof 2021, or In-the-Wild labeled audio datasets are currently present in the repository**.

The only audio files present in the local workspace are:
- `real_speech.wav` (Single 27.1s real human speech sample)
- `acoustic_test.wav` (8.0s acoustic test recording)
- `microphone_test.wav` (10.0s microphone test recording)

To perform real-world benchmark evaluations and calculate empirical EER on genuine and synthetic speech, external benchmark data must be downloaded and prepared using the instructions below.

---

## 2. Standard Manifest Specification

The Dhwani evaluation runner (`scripts/evaluation/evaluate.py`) is decoupled from specific folder hierarchies and dataset naming conventions. It operates on a **CSV or TSV manifest file**.

### 2.1 Required Columns
- `audio_path`: Relative or absolute path to the audio file (WAV or FLAC format). If relative, it is resolved against the `--dataset-root` argument provided to the runner.
- `label`: Ground-truth label. Must be explicitly one of:
  - Genuine speech: `"bonafide"`, `"bona-fide"`, `"bona_fide"`, `"genuine"`, `"real"`, `"0"`
  - Deepfake / spoofed speech: `"spoof"`, `"fake"`, `"synthetic"`, `"clone"`, `"attack"`, `"1"`

### 2.2 Optional Metadata Columns
- `speaker_id`: Speaker identifier (e.g. `LA_0023`), used to verify speaker-independent splits.
- `attack_type`: Specific spoof attack algorithm (e.g. `A01` through `A19` in ASVspoof, or `TTS_VITS`, `VC_STARGAN`, `REPLAY`).
- `subset`: Dataset split designation (`train`, `dev`, `val`, `eval`, `test`).
- `duration_sec`: Duration of the recording in seconds.

### 2.3 Sample Manifest Example (`manifest.csv`)
```csv
audio_path,label,speaker_id,attack_type,subset
flac/LA_D_1000001.flac,spoof,LA_0023,A07,dev
flac/LA_D_1000002.flac,bonafide,LA_0023,-,dev
flac/LA_D_1000003.flac,spoof,LA_0038,A11,dev
flac/LA_D_1000004.flac,bonafide,LA_0038,-,dev
flac/LA_E_1000001.flac,bonafide,LA_0079,-,eval
flac/LA_E_1000002.flac,spoof,LA_0079,A19,eval
```

---

## 3. Official ASVspoof 2019 Logical Access (LA) Setup

### 3.1 Overview & Provenance
The **ASVspoof 2019 Logical Access (LA)** dataset contains speech generated using 17 different state-of-the-art text-to-speech (TTS) and voice conversion (VC) algorithms.
- **Development set (`dev`):** Contains 2,548 bona fide and 22,296 spoof utterances from 20 speakers (algorithms A01–A06).
- **Evaluation set (`eval`):** Contains 7,355 bona fide and 63,882 spoof utterances from 48 speakers (algorithms A07–A19, including unseen neural synthesis algorithms).
- **Licensing:** Open Data Commons Attribution License (ODC-By v1.0).

### 3.2 Acquisition Steps
1. Download the ASVspoof 2019 LA package from Edinburgh DataShare or Zenodo:
   - Link: `https://datashare.ed.ac.uk/handle/10283/3336`
   - Archive: `LA.zip` (~7.1 GB compressed, ~18 GB uncompressed)
2. Extract the archive into a dedicated directory outside the Git repository:
   ```bash
   # Recommended path (outside git tracking):
   C:\Users\gurus\.datasets\asvspoof2019_la\
   ```
3. Locate the official protocol files inside the archive:
   - Development protocol: `LA/ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.dev.trl.txt`
   - Evaluation protocol: `LA/ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.eval.trl.txt`
4. Convert the official protocol file into a standard Dhwani manifest using the helper script:
   ```bash
   python scripts/evaluation/asvspoof_to_manifest.py \
       --protocol-file "C:\Users\gurus\.datasets\asvspoof2019_la\LA\ASVspoof2019_LA_cm_protocols\ASVspoof2019.LA.cm.dev.trl.txt" \
       --audio-dir "C:\Users\gurus\.datasets\asvspoof2019_la\LA\ASVspoof2019_LA_dev\flac" \
       --output-manifest "data/manifests/asvspoof2019_dev_manifest.csv"
   ```

---

## 4. In-The-Wild Voice Clone Dataset Setup

### 4.1 Overview & Provenance
The **In-the-Wild Audio Deepfake Dataset** (Müller et al., 2022) consists of real speech excerpts from public figures alongside corresponding synthetic deepfakes generated using modern commercial voice cloners (ElevenLabs, Tortoise, Resemble.ai).
- **Licensing:** Creative Commons Attribution (CC-BY 4.0).
- **Audio Format:** 16 kHz or 44.1 kHz MP3 / WAV.

### 4.2 Preparation Protocol
1. Download from the official release repository (`https://deepfake-total.com/in_the_wild`).
2. Resample all audio files to 16,000 Hz 16-bit linear PCM WAV using `soxr` or `ffmpeg`:
   ```bash
   ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output_16k.wav
   ```
3. Construct the manifest matching Section 2.

---

## 5. Storage & Git Hygiene Guidelines

- **NEVER commit audio datasets (`.wav`, `.flac`, `.mp3`) or large manifests to the Git repository.**
- All dataset files must reside outside the repository root or inside `.gitignore` paths (`datasets/`, `data/audio/`, `data/external/`).
- The repository `.gitignore` has been updated to explicitly ignore all binary audio files and local benchmark archives.
