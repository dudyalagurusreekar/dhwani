"""
EchoShield AASIST Detector Adapter
==================================
Adapts the official AASIST (Graph Attention Network for Voice Anti-Spoofing)
model into EchoShield's standardized BaseDetector / DetectorResult interface.

Model Reference:
SpeechAntiSpoofingBenchmarks/AASIST
Architecture: SincNet + Spectral/Temporal Graph Attention Network
Input: 64,600 samples @ 16 kHz mono (~4.0375 seconds)
Output: 2-class logits [class 0 = spoof, class 1 = bona fide]

IMPORTANT SCORE DIRECTION CONVENTION:
Official AASIST score direction: higher logit[1] = more bona fide.
EchoShield standardized convention: higher score = more spoof.
The adapter converts raw AASIST evidence into a normalized spoof-oriented
score in [0.0, 1.0].
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

# Preload NVIDIA CUDA / cuDNN DLLs on Windows
setup_nvidia_dll_paths()
import onnxruntime as ort


ONNX_MODEL_PATH = PROJECT_ROOT / "models" / "aasist" / "aasist.onnx"
PTH_MODEL_PATH = PROJECT_ROOT / "models" / "aasist" / "AASIST.pth"


class AASISTAdapter(BaseDetector):
    """
    Standardized adapter for AASIST anti-spoofing model.
    Runs ONNX with CUDAExecutionProvider (fallback CPUExecutionProvider).
    """

    model_name = "AASIST"
    SAMPLE_RATE = 16000
    WINDOW_SAMPLES = 64600

    def __init__(self, model_path: Optional[str | Path] = None):
        self.model_path = Path(model_path) if model_path else ONNX_MODEL_PATH

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"AASIST model not found at {self.model_path}. "
                f"Ensure models/aasist/aasist.onnx exists."
            )

        print(f"Loading AASIST from: {self.model_path}")
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.provider = self.session.get_providers()[0]
        print(f"AASIST loaded on: {self.provider}")

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
        Execute AASIST inference on audio and return standardized DetectorResult.
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

        # AASIST: higher bona_fide_logit = more genuine.
        # Compute normalized spoof-oriented score using binary logistic softmax:
        # P(spoof) = 1 / (1 + exp(bona_fide_logit - spoof_logit))
        diff = max(-60.0, min(60.0, bona_fide_logit - spoof_logit))
        spoof_score = float(1.0 / (1.0 + math.exp(diff)))

        standardized = DetectorResult(
            model=self.model_name,
            raw_score=spoof_score,
            latency_ms=round(latency_ms, 2),
            score_direction="higher_is_more_spoof",
            metadata={
                "original_score": round(bona_fide_logit, 4),
                "bona_fide_logit": round(bona_fide_logit, 4),
                "spoof_logit": round(spoof_logit, 4),
                "converted_spoof_score": round(spoof_score, 4),
                "sample_rate": self.SAMPLE_RATE,
                "window_samples": self.WINDOW_SAMPLES,
                "provider": self.provider,
            },
        )

        return standardized.to_dict()


if __name__ == "__main__":
    print("AASIST ADAPTER: SELF TEST")
    print("=" * 50)

    adapter = AASISTAdapter()
    dummy_audio = np.zeros(64600, dtype=np.float32)
    res = adapter.predict_audio(dummy_audio)

    print("Inference Result on Dummy Audio:")
    for k, v in res.items():
        print(f"  {k}: {v}")
