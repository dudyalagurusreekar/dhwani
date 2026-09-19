from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DetectorResult:
    """Standard output format for every EchoShield detector."""

    model: str
    raw_score: float
    latency_ms: float
    score_direction: str = "unknown"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "raw_score": float(self.raw_score),
            "latency_ms": float(self.latency_ms),
            "score_direction": self.score_direction,
            "metadata": self.metadata or {},
        }


class BaseDetector:
    """Common interface that all EchoShield detectors should follow."""

    model_name = "unknown"

    def predict_audio(self, audio, sample_rate: int = 16000) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement predict_audio()."
        )
