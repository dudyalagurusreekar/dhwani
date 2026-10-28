"""
EchoShield Real Multi-Model Detector Service
============================================
Manages lifecycle, execution, and health monitoring of anti-spoofing detectors:
1. W2V2-AASIST (Self-Supervised Wav2Vec 2.0 + GAT)
2. AASIST (Raw Waveform SincNet + Spectral/Temporal GAT)
3. AASIST-L (Lightweight GAT)
4. ACOUSTIC (Spectral/Cepstral Handcrafted Anomaly Detector)
5. Audio Quality Analyzer (SNR, Flatness, Clipping, RMS)
6. Adaptive Reliability Fusion
7. Speaker Identity Consistency (ECAPA-TDNN)
"""

import io
import math
from pathlib import Path
import sys
import threading
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

from ai.common.detector_interface import BaseDetector, DetectorStatus, DetectorResult
from ai.ssl_detector.w2v2_aasist_adapter import W2V2AASISTAdapter
from ai.aasist.aasist_adapter import AASISTAdapter
from ai.aasist.aasist_l_adapter import AASISTLAdapter
from ai.acoustic.acoustic_detector import AcousticDetector
from ai.acoustic.audio_quality import AudioQualityAnalyzer
from risk_engine.adaptive_fusion import AdaptiveFusionEngine
from ai.speaker.speaker_consistency import SpeakerConsistencyEngine

# Thread-safe initialization lock & state
_INIT_LOCK = threading.Lock()
_INITIALIZATION_STATE = DetectorStatus.NOT_INITIALIZED
_INITIALIZATION_ERROR: Optional[str] = None

# Registry of active detector instances: name -> BaseDetector
_DETECTOR_REGISTRY: Dict[str, BaseDetector] = {}

# Individual singleton references maintained for backward compatibility
_W2V2_MODEL: Optional[W2V2AASISTAdapter] = None
_AASIST_MODEL: Optional[AASISTAdapter] = None
_AASIST_L_MODEL: Optional[AASISTLAdapter] = None
_ACOUSTIC_MODEL: Optional[AcousticDetector] = None
_SPEAKER_ENGINE: Optional[SpeakerConsistencyEngine] = None
_QUALITY_ANALYZER: Optional[AudioQualityAnalyzer] = None
_FUSION_ENGINE: Optional[AdaptiveFusionEngine] = None


def _init_detectors(force: bool = False) -> None:
    """Thread-safe lazy initialization of all detector models."""
    global _INITIALIZATION_STATE, _INITIALIZATION_ERROR
    global _W2V2_MODEL, _AASIST_MODEL, _AASIST_L_MODEL, _ACOUSTIC_MODEL
    global _SPEAKER_ENGINE, _QUALITY_ANALYZER, _FUSION_ENGINE, _DETECTOR_REGISTRY

    if _INITIALIZATION_STATE == DetectorStatus.READY and not force:
        return

    with _INIT_LOCK:
        if _INITIALIZATION_STATE == DetectorStatus.READY and not force:
            return

        _INITIALIZATION_STATE = DetectorStatus.INITIALIZING
        _DETECTOR_REGISTRY.clear()

        # 1. W2V2-AASIST Adapter (Optional SSL model)
        try:
            _W2V2_MODEL = W2V2AASISTAdapter(strict=False)
        except Exception as e:
            _W2V2_MODEL = None
            print(f"[WARN] W2V2-AASIST unexpected initialization failure: {e}")
        if _W2V2_MODEL is not None:
            _DETECTOR_REGISTRY["W2V2-AASIST"] = _W2V2_MODEL

        # 2. AASIST Adapter (PyTorch / ONNX)
        try:
            _AASIST_MODEL = AASISTAdapter(strict=False)
        except Exception as e:
            _AASIST_MODEL = None
            print(f"[WARN] AASIST unexpected initialization failure: {e}")
        if _AASIST_MODEL is not None:
            _DETECTOR_REGISTRY["AASIST"] = _AASIST_MODEL

        # 3. AASIST-L Adapter (PyTorch / ONNX)
        try:
            _AASIST_L_MODEL = AASISTLAdapter(strict=False)
        except Exception as e:
            _AASIST_L_MODEL = None
            print(f"[WARN] AASIST-L unexpected initialization failure: {e}")
        if _AASIST_L_MODEL is not None:
            _DETECTOR_REGISTRY["AASIST-L"] = _AASIST_L_MODEL

        # 4. Handcrafted Acoustic Detector
        try:
            _ACOUSTIC_MODEL = AcousticDetector()
        except Exception as e:
            _ACOUSTIC_MODEL = None
            print(f"[WARN] AcousticDetector unexpected initialization failure: {e}")
        if _ACOUSTIC_MODEL is not None:
            _DETECTOR_REGISTRY["ACOUSTIC"] = _ACOUSTIC_MODEL

        # 5. Speaker Consistency Engine (ECAPA-TDNN)
        try:
            _SPEAKER_ENGINE = SpeakerConsistencyEngine(strict=False)
        except Exception as e:
            _SPEAKER_ENGINE = None
            print(f"[WARN] SpeakerConsistencyEngine unexpected initialization failure: {e}")

        # 6. Audio Quality Analyzer & Fusion Engine
        _QUALITY_ANALYZER = AudioQualityAnalyzer(sample_rate=16000)
        _FUSION_ENGINE = AdaptiveFusionEngine()

        _INITIALIZATION_STATE = DetectorStatus.READY
        _INITIALIZATION_ERROR = None


def get_detector_registry() -> Dict[str, BaseDetector]:
    """Retrieve live mapping of all registered detector instances."""
    _init_detectors()
    return _DETECTOR_REGISTRY


def get_active_detectors() -> List[Dict[str, Any]]:
    """
    Query the real-time operational status of all registered detectors and engines.
    Returns truthful status without masking unavailable models.
    """
    _init_detectors()
    detectors: List[Dict[str, Any]] = []

    for name, det in _DETECTOR_REGISTRY.items():
        status_str = det.status.value if hasattr(det.status, "value") else str(det.status)
        detectors.append({
            "model": name,
            "status": status_str,
            "is_available": det.is_available,
            "device": det.device,
            "backend": det.backend,
            "error": det.error,
        })

    if _SPEAKER_ENGINE is not None:
        speaker_status = (
            _SPEAKER_ENGINE.status.value
            if hasattr(_SPEAKER_ENGINE.status, "value")
            else str(_SPEAKER_ENGINE.status)
        )
        detectors.append({
            "model": "ECAPA-TDNN",
            "type": "Deep Speaker Identity Verification",
            "status": speaker_status,
            "is_available": _SPEAKER_ENGINE.is_available,
            "device": _SPEAKER_ENGINE.provider,
            "backend": "onnx" if _SPEAKER_ENGINE.is_available else "unavailable",
            "error": _SPEAKER_ENGINE.error,
        })

    return detectors


def get_detector_health() -> Dict[str, Any]:
    """Aggregate health summary of all detector subsystems."""
    _init_detectors()
    detectors = get_active_detectors()
    ready_count = sum(1 for d in detectors if d.get("is_available"))
    unavailable_count = sum(1 for d in detectors if d.get("status") == "UNAVAILABLE")
    failed_count = sum(1 for d in detectors if d.get("status") == "FAILED")

    return {
        "lifecycle": _INITIALIZATION_STATE.value,
        "total_registered": len(detectors),
        "ready_count": ready_count,
        "unavailable_count": unavailable_count,
        "failed_count": failed_count,
    }


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
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronous multi-model inference on audio input (bytes or float32 np.ndarray).
    Executes all ready detectors, skips unavailable ones, and fuses valid outputs.
    """
    _init_detectors()

    if isinstance(audio_input, np.ndarray):
        audio_array = audio_input.astype(np.float32)
        if audio_array.ndim > 1:
            audio_array = np.mean(audio_array, axis=1)
    else:
        audio_array = parse_audio_bytes_to_array(audio_input, sample_rate)

    # Ensure finite values
    audio_array = np.nan_to_num(audio_array, nan=0.0, posinf=0.0, neginf=0.0)

    # Pad or slice to 64,600 samples (~4.0375s @ 16 kHz)
    if len(audio_array) < 64600:
        audio_array = np.pad(audio_array, (0, 64600 - len(audio_array)))
    elif len(audio_array) > 64600:
        audio_array = audio_array[-64600:]

    # 1. Audio Quality Analysis
    quality_res = {}
    if _QUALITY_ANALYZER is not None:
        try:
            quality_res = _QUALITY_ANALYZER.analyze(audio_array, sample_rate)
        except Exception as e:
            quality_res = {"error": str(e), "quality_level": "POOR"}

    # 2. Run all registered detectors
    detector_results: List[Dict[str, Any]] = []

    for name, detector in _DETECTOR_REGISTRY.items():
        if detector.is_available:
            try:
                res = detector.predict_audio(audio_array, sample_rate)
                detector_results.append(res)
            except Exception as exc:
                detector_results.append({
                    "model": name,
                    "raw_score": None,
                    "latency_ms": 0.0,
                    "score_direction": "higher_is_more_spoof",
                    "status": "FAILED",
                    "device": detector.device,
                    "backend": detector.backend,
                    "error": str(exc),
                    "metadata": {},
                })
        else:
            # Explicitly report unavailable detector
            detector_results.append({
                "model": name,
                "raw_score": None,
                "latency_ms": 0.0,
                "score_direction": "higher_is_more_spoof",
                "status": "SKIPPED",
                "device": detector.device,
                "backend": detector.backend,
                "error": detector.error or f"{name} is unavailable.",
                "metadata": {"reason": "model_artifact_unavailable"},
            })

    # 3. Speaker Consistency Evaluation (ECAPA-TDNN)
    speaker_res = {}
    if _SPEAKER_ENGINE is not None:
        try:
            speaker_res = _SPEAKER_ENGINE.evaluate_consistency(
                audio_array, sample_rate, session_id=session_id
            )
        except Exception as e:
            speaker_res = {"status": "FAILED", "error": str(e)}

    # 4. Adaptive Fusion over successfully executed detectors
    contributing_models = [
        d["model"] for d in detector_results if d.get("status") == "SUCCESS"
    ]

    fused_metadata = {}
    if _FUSION_ENGINE is not None and contributing_models:
        fused = _FUSION_ENGINE.fuse(detector_results, quality_res)
        fused_metadata = fused
        fused_score = fused.get("fused_score")
        if fused_score is not None:
            fake_prob = float(fused_score)
            fake_prob = max(0.0, min(1.0, fake_prob))
            real_prob = round(1.0 - fake_prob, 4)
        else:
            fake_prob = None
            real_prob = None
    else:
        fake_prob = None
        real_prob = None

    return {
        "fake_probability": round(fake_prob, 4) if fake_prob is not None else None,
        "real_probability": real_prob,
        "detectors": detector_results,
        "quality": quality_res,
        "speaker_consistency": speaker_res,
        "active_models": contributing_models,
        "fused_metadata": fused_metadata,
    }


async def detect_voice(
    audio_bytes: bytes | np.ndarray,
    sample_rate: int = 16000,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Async wrapper for detect_voice_sync."""
    return detect_voice_sync(audio_bytes, sample_rate, session_id=session_id)


def reset_session(session_id: Optional[str] = None) -> None:
    """Reset session-specific state across stateful engines."""
    if _SPEAKER_ENGINE is not None:
        _SPEAKER_ENGINE.reset_session(session_id)