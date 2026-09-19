"""
EchoShield AASIST-L Detector Adapter
====================================
Adapts the official AASIST-L (Lightweight Graph Attention Network)
model into EchoShield's standardized BaseDetector / DetectorResult interface.

Model Reference:
SpeechAntiSpoofingBenchmarks/AASIST-L
Architecture: SincNet + Lightweight Spectral/Temporal Graph Attention Network
Input: 64,600 samples @ 16 kHz mono (~4.0375 seconds)
Output: 2-class logits [class 0 = spoof, class 1 = bona fide]

SCORE DIRECTION:
Official AASIST-L: class 1 = bona fide, class 0 = spoof.
EchoShield standardized convention: higher score = more spoof.
The adapter applies softmax and returns P(spoof) = 1 / (1 + exp(s1 - s0)).
"""

import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

import numpy as np
import librosa

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.detector_interface import BaseDetector, DetectorResult
from ai.common.gpu_utils import setup_nvidia_dll_paths

setup_nvidia_dll_paths()
import onnxruntime as ort


ONNX_MODEL_PATH = PROJECT_ROOT / "models" / "aasist" / "aasist-l.onnx"


class AASISTLAdapter(BaseDetector):
    """
    Standardized adapter for AASIST-L (Lightweight Graph Attention Network).
    Runs ONNX with CUDAExecutionProvider (fallback CPUExecutionProvider).
    """

    model_name = "AASIST-L"
    SAMPLE_RATE = 16000
    WINDOW_SAMPLES = 64600

    def __init__(self, model_path: Optional[str | Path] = None):
        self.model_path = Path(model_path) if model_path else ONNX_MODEL_PATH

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"AASIST-L model not found at {self.model_path}."
            )

        print(f"Loading AASIST-L from: {self.model_path}")
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.provider = self.session.get_providers()[0]
        print(f"AASIST-L loaded on: {self.provider}")

    def prepare_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> np.ndarray:
        """Standardize audio to 1D float32 of exactly 64,600 samples at 16 kHz."""
        audio = np.asarray(audio, dtype=np.float32)

        # Stereo -> Mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # Resample if needed
        if sample_rate != self.SAMPLE_RATE:
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=self.SAMPLE_RATE,
            )

        # Remove DC offset
        audio = audio - np.mean(audio)
        audio = np.nan_to_num(audio)

        # Pad or slice to WINDOW_SAMPLES
        if len(audio) < self.WINDOW_SAMPLES:
            audio = np.pad(
                audio,
                (0, self.WINDOW_SAMPLES - len(audio)),
                mode="constant",
            )
        else:
            audio = audio[: self.WINDOW_SAMPLES]

        return audio.astype(np.float32)

    def predict_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:
        """
        Execute AASIST-L inference on audio and return standardized DetectorResult.
        """
        processed_audio = self.prepare_audio(audio, sample_rate)
        model_input = processed_audio[np.newaxis, :]  # shape: (1, 64600)

        t_start = time.perf_counter()
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: model_input},
        )
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        logits = np.asarray(outputs[0])[0]
        spoof_logit = float(logits[0])
        bona_fide_logit = float(logits[1])

        # Softmax spoof probability
        diff = max(-60.0, min(60.0, bona_fide_logit - spoof_logit))
        spoof_score = float(1.0 / (1.0 + math.exp(diff)))

        standardized = DetectorResult(
            model=self.model_name,
            raw_score=spoof_score,
            latency_ms=round(latency_ms, 2),
            score_direction="higher_is_more_spoof",
            metadata={
                "provider": self.provider,
                "spoof_logit": round(spoof_logit, 4),
                "bona_fide_logit": round(bona_fide_logit, 4),
                "is_real": True,
            },
        )
        return standardized.to_dict()
