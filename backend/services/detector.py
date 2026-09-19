"""
EchoShield Real Multi-Model Detector Service
============================================
Replaces mock with real deep neural and acoustic detectors:
1. W2V2-AASIST (Self-Supervised Wav2Vec 2.0 + GAT on CUDA)
2. AASIST (Raw Waveform SincNet + Spectral/Temporal GAT on CUDA)
3. AASIST-L (Lightweight GAT on CUDA)
4. ACOUSTIC (Spectral/Cepstral Handcrafted Anomaly Detector on CPU)
5. Audio Quality Analyzer (SNR, Flatness, Clipping, RMS)
6. Adaptive Reliability Fusion
"""

import io
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.gpu_utils import setup_nvidia_dll_paths
setup_nvidia_dll_paths()

import numpy as np
import soundfile as sf
import librosa

from ai.ssl_detector.w2v2_aasist_adapter import W2V2AASISTAdapter
from ai.aasist.aasist_adapter import AASISTAdapter
from ai.aasist.aasist_l_adapter import AASISTLAdapter
from ai.acoustic.acoustic_detector import AcousticDetector
from ai.acoustic.audio_quality import AudioQualityAnalyzer
from risk_engine.adaptive_fusion import AdaptiveFusionEngine
from ai.speaker.speaker_consistency import SpeakerConsistencyEngine

# Singleton detector container to prevent re-instantiation across requests
_DETECTORS_INITIALIZED = False
_W2V2_MODEL: Optional[W2V2AASISTAdapter] = None
_AASIST_MODEL: Optional[AASISTAdapter] = None
_AASIST_L_MODEL: Optional[AASISTLAdapter] = None
_ACOUSTIC_MODEL: Optional[AcousticDetector] = None
_SPEAKER_ENGINE: Optional[SpeakerConsistencyEngine] = None
_QUALITY_ANALYZER: Optional[AudioQualityAnalyzer] = None
_FUSION_ENGINE: Optional[AdaptiveFusionEngine] = None


def _init_detectors():
    global _DETECTORS_INITIALIZED, _W2V2_MODEL, _AASIST_MODEL, _AASIST_L_MODEL
    global _ACOUSTIC_MODEL, _SPEAKER_ENGINE, _QUALITY_ANALYZER, _FUSION_ENGINE

    if _DETECTORS_INITIALIZED:
        return

    print("[DETECTOR SERVICE] Loading production models onto CUDA/CPU...")
    try:
        _W2V2_MODEL = W2V2AASISTAdapter()
    except Exception as e:
        print(f"[WARN] W2V2-AASIST init failed: {e}")

    try:
        _AASIST_MODEL = AASISTAdapter()
    except Exception as e:
        print(f"[WARN] AASIST init failed: {e}")

    try:
        _AASIST_L_MODEL = AASISTLAdapter()
    except Exception as e:
        print(f"[WARN] AASIST-L init failed: {e}")

    try:
        _ACOUSTIC_MODEL = AcousticDetector()
    except Exception as e:
        print(f"[WARN] AcousticDetector init failed: {e}")

    try:
        _SPEAKER_ENGINE = SpeakerConsistencyEngine()
    except Exception as e:
        print(f"[WARN] SpeakerConsistencyEngine init failed: {e}")

    _QUALITY_ANALYZER = AudioQualityAnalyzer(sample_rate=16000)
    _FUSION_ENGINE = AdaptiveFusionEngine()
    _DETECTORS_INITIALIZED = True
    print("[DETECTOR SERVICE] All active models initialized.")


def parse_audio_bytes_to_array(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Parse incoming bytes into a 1D float32 numpy array @ 16 kHz.
    Handles WAV/FLAC/OGG containers or raw 16-bit PCM.
    """
    if not audio_bytes:
        return np.zeros(64600, dtype=np.float32)

    # 1. Try reading as containerized audio file (WAV / OGG / FLAC)
    try:
        with io.BytesIO(audio_bytes) as bio:
            data, sr = sf.read(bio, dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != sample_rate:
                data = librosa.resample(data, orig_sr=sr, target_sr=sample_rate)
            return data.astype(np.float32)
    except Exception:
        pass

    # 2. Try parsing as raw 16-bit PCM
    try:
        pcm = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        pcm = pcm / 32768.0
        return pcm
    except Exception:
        pass

    # Fallback zeros
    return np.zeros(64600, dtype=np.float32)


def detect_voice_sync(
    audio_input: bytes | np.ndarray,
    sample_rate: int = 16000,
) -> Dict[str, Any]:
    """
    Synchronous multi-model inference on audio input (bytes or float32 np.ndarray).
    """
    _init_detectors()

    if isinstance(audio_input, np.ndarray):
        audio_array = audio_input.astype(np.float32)
        if audio_array.ndim > 1:
            audio_array = np.mean(audio_array, axis=1)
    else:
        audio_array = parse_audio_bytes_to_array(audio_input, sample_rate)

    # Pad/slice to 64,600 samples
    if len(audio_array) < 64600:
        audio_array = np.pad(audio_array, (0, 64600 - len(audio_array)))
    elif len(audio_array) > 64600:
        audio_array = audio_array[-64600:]

    # 1. Audio Quality Analysis
    quality_res = {}
    if _QUALITY_ANALYZER:
        quality_res = _QUALITY_ANALYZER.analyze(audio_array, sample_rate)

    # 2. Run active detectors
    detector_results = []

    if _AASIST_MODEL:
        try:
            r = _AASIST_MODEL.predict_audio(audio_array, sample_rate)
            detector_results.append(r)
        except Exception as e:
            print(f"[AASIST error] {e}")

    if _AASIST_L_MODEL:
        try:
            r = _AASIST_L_MODEL.predict_audio(audio_array, sample_rate)
            detector_results.append(r)
        except Exception as e:
            print(f"[AASIST-L error] {e}")

    if _ACOUSTIC_MODEL:
        try:
            r = _ACOUSTIC_MODEL.predict_audio(audio_array, sample_rate)
            detector_results.append(r)
        except Exception as e:
            print(f"[Acoustic error] {e}")

    if _W2V2_MODEL:
        try:
            r = _W2V2_MODEL.predict_audio(audio_array, sample_rate)
            detector_results.append(r)
        except Exception as e:
            print(f"[W2V2 error] {e}")

    # 3. Speaker Consistency Evaluation (ECAPA-TDNN)
    speaker_res = {}
    if _SPEAKER_ENGINE:
        try:
            speaker_res = _SPEAKER_ENGINE.evaluate_consistency(audio_array, sample_rate)
        except Exception as e:
            print(f"[SpeakerConsistency error] {e}")

    # 4. Dynamic Adaptive Fusion
    if _FUSION_ENGINE and detector_results:
        fused = _FUSION_ENGINE.fuse(detector_results, quality_res)
        fake_prob = float(fused["fused_score"])
    else:
        scores = [float(d["raw_score"]) for d in detector_results]
        fake_prob = float(np.mean(scores)) if scores else 0.5

    fake_prob = max(0.0, min(1.0, fake_prob))
    real_prob = round(1.0 - fake_prob, 4)

    return {
        "fake_probability": round(fake_prob, 4),
        "real_probability": real_prob,
        "detectors": detector_results,
        "quality": quality_res,
        "speaker_consistency": speaker_res,
        "active_models": [d["model"] for d in detector_results],
    }


async def detect_voice(
    audio_bytes: bytes | np.ndarray,
    sample_rate: int = 16000,
) -> Dict[str, Any]:
    """Async wrapper for detect_voice_sync."""
    return detect_voice_sync(audio_bytes, sample_rate)