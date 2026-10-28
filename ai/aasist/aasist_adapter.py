"""
EchoShield AASIST Detector Adapter
==================================
Adapts the official AASIST (Graph Attention Network for Voice Anti-Spoofing)
model into Dhwani's standardized BaseDetector / DetectorResult interface.

Supports dual inference backends:
1. PyTorch (.pth checkpoint via official Model architecture) with weights_only=True
2. ONNX Runtime (.onnx graph via CUDAExecutionProvider / CPUExecutionProvider)

Model Reference:
SpeechAntiSpoofingBenchmarks/AASIST
Architecture: SincNet + Spectral/Temporal Graph Attention Network
Input: 64,600 samples @ 16 kHz mono (~4.0375 seconds)
Output: 2-class logits [class 0 = spoof, class 1 = bona fide]

SCORE DIRECTION CONVENTION:
Official AASIST score direction: higher logit[1] = more bona fide.
Dhwani standardized convention: higher score = more spoof in [0.0, 1.0].
Score conversion: P(spoof) = 1.0 / (1.0 + exp(bona_fide_logit - spoof_logit))
"""

import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
import librosa
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.detector_interface import BaseDetector, DetectorResult, DetectorStatus
from ai.common.gpu_utils import setup_nvidia_dll_paths

setup_nvidia_dll_paths()

# Candidate paths
ONNX_MODEL_PATHS: List[Path] = [
    PROJECT_ROOT / "models" / "aasist" / "aasist.onnx",
]
PTH_MODEL_PATHS: List[Path] = [
    PROJECT_ROOT / "models" / "aasist" / "AASIST.pth",
    PROJECT_ROOT / "ai" / "aasist" / "models" / "weights" / "AASIST.pth",
    PROJECT_ROOT / "ai" / "aasist" / "official" / "models" / "weights" / "AASIST.pth",
]
CONFIG_PATH = PROJECT_ROOT / "ai" / "aasist" / "config" / "AASIST.conf"


class AASISTAdapter(BaseDetector):
    """
    Standardized adapter for AASIST anti-spoofing model.
    Selects ONNX or PyTorch based on available artifacts and preferences.
    """

    model_name = "AASIST"
    SAMPLE_RATE = 16000
    WINDOW_SAMPLES = 64600

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        config_path: Optional[Union[str, Path]] = None,
        preferred_backend: Optional[str] = None,  # "onnx" | "pytorch" | None (auto)
        strict: bool = False,
    ):
        super().__init__()
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.pytorch_model: Optional[torch.nn.Module] = None
        self.session = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.backend = "unknown"
        self.status = DetectorStatus.INITIALIZING
        self.error = None

        try:
            self._initialize(model_path, preferred_backend)
            self.status = DetectorStatus.READY
        except Exception as e:
            self.status = DetectorStatus.UNAVAILABLE if isinstance(e, FileNotFoundError) else DetectorStatus.FAILED
            self.error = str(e)
            if strict:
                raise

    def _initialize(self, model_path: Optional[Union[str, Path]], preferred_backend: Optional[str]) -> None:
        target_path = Path(model_path) if model_path else None

        # 1. Check if user specified a specific file
        if target_path:
            if not target_path.exists():
                raise FileNotFoundError(f"AASIST model file not found at: {target_path}")
            if target_path.suffix.lower() == ".onnx":
                self._load_onnx(target_path)
                return
            elif target_path.suffix.lower() in (".pth", ".pt", ".bin"):
                self._load_pytorch(target_path)
                return
            else:
                raise ValueError(f"Unsupported model extension: {target_path.suffix}")

        # 2. Automatic selection: Check ONNX first if requested
        if preferred_backend == "onnx":
            for p in ONNX_MODEL_PATHS:
                if p.exists():
                    self._load_onnx(p)
                    return
            raise FileNotFoundError(f"AASIST ONNX model requested but not found at any of: {ONNX_MODEL_PATHS}")

        # 3. Check for ONNX
        for p in ONNX_MODEL_PATHS:
            if p.exists():
                try:
                    self._load_onnx(p)
                    return
                except Exception as e:
                    print(f"[WARN] Failed loading AASIST ONNX ({p}): {e}, falling back to PyTorch")

        # 4. Check for PyTorch .pth checkpoints
        for p in PTH_MODEL_PATHS:
            if p.exists():
                self._load_pytorch(p)
                return

        raise FileNotFoundError(
            f"AASIST weights not found. Looked for ONNX at {ONNX_MODEL_PATHS} "
            f"and PyTorch checkpoints at {PTH_MODEL_PATHS}."
        )

    def _load_onnx(self, onnx_path: Path) -> None:
        import onnxruntime as ort

        providers = []
        if torch.cuda.is_available() and "CUDAExecutionProvider" in ort.get_available_providers():
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(onnx_path), sess_options=so, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.backend = "onnx"
        self.device = self.session.get_providers()[0]
        self.model_path = onnx_path
        print(f"[AASIST] Loaded ONNX model from {onnx_path} on {self.device}")

    def _load_pytorch(self, pth_path: Path) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"AASIST config not found at: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        model_config = config_data.get("model_config", {})

        from ai.aasist.models.AASIST import Model as AASISTModel

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AASISTModel(model_config).to(self.device)

        # Safe checkpoint deserialization with PyTorch weights_only=True
        state_dict = torch.load(str(pth_path), map_location=self.device, weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()

        self.pytorch_model = model
        self.backend = "pytorch"
        self.model_path = pth_path
        print(f"[AASIST] Loaded PyTorch checkpoint from {pth_path} on {self.device}")

    def prepare_audio(self, audio: Optional[np.ndarray], sample_rate: int = 16000) -> np.ndarray:
        """Standardize audio to 1D float32 of exactly 64,600 samples at 16 kHz."""
        if audio is None or len(audio) == 0:
            return np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)

        audio = np.asarray(audio, dtype=np.float32)

        # Stereo -> Mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)

        # Resample if needed
        if sample_rate != self.SAMPLE_RATE and len(audio) > 0:
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=self.SAMPLE_RATE,
            )

        # Remove DC offset and cleanse NaNs
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        mean_val = np.mean(audio) if len(audio) > 0 else 0.0
        audio = audio - mean_val

        # Pad or slice to WINDOW_SAMPLES matching official ASVspoof/AASIST data_utils pad()
        if len(audio) == 0:
            audio = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
        elif len(audio) < self.WINDOW_SAMPLES:
            num_repeats = int(self.WINDOW_SAMPLES / len(audio)) + 1
            audio = np.tile(audio, num_repeats)[: self.WINDOW_SAMPLES]
        else:
            audio = audio[: self.WINDOW_SAMPLES]

        return audio.astype(np.float32)

    def predict_audio(self, audio: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Execute AASIST inference on audio and return standardized DetectorResult dict.
        """
        if self.status != DetectorStatus.READY:
            res = DetectorResult(
                model=self.model_name,
                raw_score=None,
                latency_ms=0.0,
                score_direction="higher_is_more_spoof",
                status="FAILED",
                device=self.device,
                backend=self.backend,
                error=self.error or "Detector not ready",
                metadata={"status": self.status.value},
            )
            return res.to_dict()

        processed_audio = self.prepare_audio(audio, sample_rate)
        t_start = time.perf_counter()

        try:
            if self.backend == "pytorch" and self.pytorch_model is not None:
                tensor_in = torch.from_numpy(processed_audio).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    _, batch_out = self.pytorch_model(tensor_in)
                    logits = batch_out[0].detach().cpu().numpy()
            elif self.backend == "onnx" and self.session is not None:
                model_input = processed_audio[np.newaxis, :]
                outputs = self.session.run([self.output_name], {self.input_name: model_input})
                logits = np.asarray(outputs[0])[0]
            else:
                raise RuntimeError(f"No active backend loaded ({self.backend})")

            latency_ms = (time.perf_counter() - t_start) * 1000.0

            spoof_logit = float(logits[0])
            bona_fide_logit = float(logits[1])

            # AASIST: class 1 = bona fide, class 0 = spoof.
            # Stable binary logistic softmax: P(spoof) = 1 / (1 + exp(bona_fide - spoof))
            diff = max(-60.0, min(60.0, bona_fide_logit - spoof_logit))
            spoof_score = float(1.0 / (1.0 + math.exp(diff)))

            if math.isnan(spoof_score) or math.isinf(spoof_score):
                spoof_score = 0.5

            res = DetectorResult(
                model=self.model_name,
                raw_score=round(spoof_score, 4),
                latency_ms=round(latency_ms, 2),
                score_direction="higher_is_more_spoof",
                status="SUCCESS",
                device=self.device,
                backend=self.backend,
                error=None,
                metadata={
                    "bona_fide_logit": round(bona_fide_logit, 4),
                    "spoof_logit": round(spoof_logit, 4),
                    "window_samples": self.WINDOW_SAMPLES,
                    "sample_rate": self.SAMPLE_RATE,
                    "is_real": True,
                },
            )
            return res.to_dict()

        except Exception as e:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            res = DetectorResult(
                model=self.model_name,
                raw_score=None,
                latency_ms=round(latency_ms, 2),
                score_direction="higher_is_more_spoof",
                status="FAILED",
                device=self.device,
                backend=self.backend,
                error=str(e),
                metadata={},
            )
            return res.to_dict()


if __name__ == "__main__":
    adapter = AASISTAdapter()
    print(f"AASIST Status: {adapter.status.value}, Backend: {adapter.backend}, Device: {adapter.device}")
    if adapter.is_available:
        dummy = np.zeros(64600, dtype=np.float32)
        out = adapter.predict_audio(dummy)
        print("Inference output on dummy:", out)
