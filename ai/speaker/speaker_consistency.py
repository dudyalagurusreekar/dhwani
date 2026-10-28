"""
EchoShield Speaker Consistency Engine (Member 2 Deliverable)
============================================================
Extracts deep speaker embeddings and computes temporal voice consistency
across streaming audio windows to detect:
1. Mid-call speaker switches (impersonation / handoff).
2. Voice conversion drift (target speaker mismatch).
3. Replay of foreign audio.

Architecture:
- Front-end: 80-dimensional Log Mel-Filterbanks (Kaldi standard @ 16 kHz).
- Embedding Network: ECAPA-TDNN (models/speaker/ecapa512.onnx) on CUDA (~7 ms).
- Embedding Dimension: 192 float32.
- Metric: Cosine Similarity against initial enrollment anchor or rolling profile.
"""

from collections import deque
import math
from pathlib import Path
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.gpu_utils import setup_nvidia_dll_paths
setup_nvidia_dll_paths()

import numpy as np
import torch
import torchaudio.compliance.kaldi as kaldi
import onnxruntime as ort


from ai.common.detector_interface import DetectorStatus

MODEL_PATH = PROJECT_ROOT / "models" / "speaker" / "ecapa512.onnx"


class SpeakerConsistencyEngine:
    """
    Computes 192-dimensional ECAPA-TDNN speaker embeddings and evaluates
    cross-window speaker identity consistency.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        consistency_threshold: float = 0.65,
        suspicious_threshold: float = 0.45,
        rolling_history_size: int = 5,
        preferred_provider: str = "CUDAExecutionProvider",
        strict: bool = False,
    ):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.consistency_threshold = consistency_threshold
        self.suspicious_threshold = suspicious_threshold
        self.rolling_history_size = rolling_history_size
        self.preferred_provider = preferred_provider
        self.strict = strict

        # Lifecycle status
        self.status = DetectorStatus.NOT_INITIALIZED
        self.error: Optional[str] = None
        self.session: Optional[ort.InferenceSession] = None
        self.provider: str = "unknown"

        # Session state: anchor embedding and rolling history (default session)
        self.anchor_embedding: Optional[np.ndarray] = None
        self.recent_embeddings: deque = deque(maxlen=rolling_history_size)
        # Multi-session store: session_id -> {"anchor": np.ndarray, "recent": deque}
        self.session_profiles: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        self._load_model()

    @property
    def is_available(self) -> bool:
        return self.status == DetectorStatus.READY and self.session is not None

    def _load_model(self) -> None:
        self.status = DetectorStatus.INITIALIZING
        if not self.model_path.exists():
            msg = (
                f"ECAPA-TDNN model not found at {self.model_path}. "
                "Required artifact: ecapa512.onnx. Speaker consistency checks will be unavailable."
            )
            if self.strict:
                self.status = DetectorStatus.FAILED
                self.error = msg
                raise FileNotFoundError(msg)
            self.status = DetectorStatus.UNAVAILABLE
            self.error = msg
            self.session = None
            self.provider = "unavailable"
            return

        try:
            providers = []
            if self.preferred_provider in ort.get_available_providers():
                providers.append(self.preferred_provider)
            providers.append("CPUExecutionProvider")

            so = ort.SessionOptions()
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so.log_severity_level = 3

            self.session = ort.InferenceSession(
                str(self.model_path),
                sess_options=so,
                providers=providers,
            )
            self.provider = self.session.get_providers()[0]
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.status = DetectorStatus.READY
            self.error = None
        except Exception as exc:
            msg = f"Failed to initialize ECAPA-TDNN session: {exc}"
            if self.strict:
                self.status = DetectorStatus.FAILED
                self.error = msg
                raise RuntimeError(msg) from exc
            self.status = DetectorStatus.FAILED
            self.error = msg
            self.session = None
            self.provider = "failed"

    def reset_session(self, session_id: Optional[str] = None) -> None:
        """Reset anchor and rolling history for a session (or all if None)."""
        with self._lock:
            if session_id is not None:
                self.session_profiles.pop(session_id, None)
            else:
                self.anchor_embedding = None
                self.recent_embeddings.clear()
                self.session_profiles.clear()

    def extract_embedding(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Extract 192-dimensional normalized speaker embedding from audio.
        """
        if not self.is_available:
            raise RuntimeError(f"SpeakerConsistencyEngine is unavailable: {self.error}")

        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)

        # Minimum required duration for speaker embedding is ~0.5s (8000 samples)
        if len(audio) < 8000:
            audio = np.pad(audio, (0, 8000 - len(audio)))

        # 80-dim log Mel filterbank
        waveform_t = torch.from_numpy(audio).unsqueeze(0)
        fbank = kaldi.fbank(
            waveform_t,
            num_mel_bins=80,
            sample_frequency=sample_rate,
        )  # shape: (T, 80)

        # Mean subtraction over time
        fbank = fbank - torch.mean(fbank, dim=0, keepdim=True)
        feats = fbank.unsqueeze(0).numpy().astype(np.float32)  # shape: (1, T, 80)

        outputs = self.session.run([self.output_name], {self.input_name: feats})
        emb = outputs[0][0]  # shape: (192,)

        # L2 normalize embedding
        norm = np.linalg.norm(emb) + 1e-12
        return (emb / norm).astype(np.float32)

    def evaluate_consistency(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        is_speech: bool = True,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract embedding, update profile, and compute consistency against anchor.

        Returns:
            {
                "cosine_similarity": float (-1.0 to 1.0) | None,
                "inconsistency_score": float (0.0 to 1.0, higher = more suspicious) | None,
                "speaker_consistent": bool,
                "status": "ENROLLED" | "CONSISTENT" | "SUSPICIOUS_SHIFT" | "SPEAKER_SWITCH" | "UNAVAILABLE",
                "latency_ms": float,
            }
        """
        if not self.is_available:
            return {
                "cosine_similarity": None,
                "inconsistency_score": None,
                "speaker_consistent": True,
                "status": "UNAVAILABLE",
                "explanation": self.error or "ECAPA-TDNN model is unavailable.",
                "latency_ms": 0.0,
                "provider": None,
            }

        if not is_speech:
            return {
                "cosine_similarity": 1.0,
                "inconsistency_score": 0.0,
                "speaker_consistent": True,
                "status": "NO_SPEECH",
                "latency_ms": 0.0,
            }

        t_start = time.perf_counter()
        current_emb = self.extract_embedding(audio, sample_rate)
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        if not np.all(np.isfinite(current_emb)):
            return {
                "cosine_similarity": None,
                "inconsistency_score": None,
                "speaker_consistent": False,
                "status": "FAILED",
                "explanation": "Non-finite embedding generated during speaker inference.",
                "latency_ms": round(latency_ms, 2),
                "provider": self.provider,
            }

        with self._lock:
            if session_id is not None:
                if session_id not in self.session_profiles:
                    self.session_profiles[session_id] = {
                        "anchor": None,
                        "recent": deque(maxlen=self.rolling_history_size),
                    }
                anchor_emb = self.session_profiles[session_id]["anchor"]
                recent_list = self.session_profiles[session_id]["recent"]
            else:
                anchor_emb = self.anchor_embedding
                recent_list = self.recent_embeddings

            # If no anchor exists, enroll this first speech window as anchor
            if anchor_emb is None:
                if session_id is not None:
                    self.session_profiles[session_id]["anchor"] = current_emb
                    self.session_profiles[session_id]["recent"].append(current_emb)
                else:
                    self.anchor_embedding = current_emb
                    self.recent_embeddings.append(current_emb)
                return {
                    "cosine_similarity": 1.0,
                    "inconsistency_score": 0.0,
                    "speaker_consistent": True,
                    "status": "ENROLLED",
                    "explanation": "Initial speaker identity enrolled as session baseline.",
                    "latency_ms": round(latency_ms, 2),
                    "provider": self.provider,
                }

            # Compute cosine similarity against anchor
            sim_anchor = float(np.dot(current_emb, anchor_emb))

            # Compute cosine similarity against rolling average of recent windows
            if recent_list:
                avg_recent = np.mean(recent_list, axis=0)
                avg_recent = avg_recent / (np.linalg.norm(avg_recent) + 1e-12)
                sim_recent = float(np.dot(current_emb, avg_recent))
            else:
                sim_recent = sim_anchor

            # Combined similarity
            similarity = 0.6 * sim_anchor + 0.4 * sim_recent

            # Map similarity to standardized inconsistency score in [0.0, 1.0]
            inconsistency = max(0.0, min(1.0, (1.0 - similarity) / 0.8))

            if similarity >= self.consistency_threshold:
                status = "CONSISTENT"
                speaker_consistent = True
                explanation = f"Speaker voice matches enrolled anchor (similarity: {similarity:.2f})."
                recent_list.append(current_emb)
            elif similarity >= self.suspicious_threshold:
                status = "SUSPICIOUS_SHIFT"
                speaker_consistent = False
                explanation = f"Acoustic identity drift detected (similarity: {similarity:.2f}). Possible voice conversion."
            else:
                status = "SPEAKER_SWITCH"
                speaker_consistent = False
                explanation = f"Severe voice identity mismatch (similarity: {similarity:.2f}). Speaker switch detected!"

            return {
                "cosine_similarity": round(similarity, 4),
                "inconsistency_score": round(inconsistency, 4),
                "speaker_consistent": speaker_consistent,
                "status": status,
                "explanation": explanation,
                "latency_ms": round(latency_ms, 2),
                "provider": self.provider,
            }
