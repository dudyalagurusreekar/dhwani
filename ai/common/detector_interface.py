from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class DetectorStatus(str, Enum):
    """Lifecycle and operational state of a detector."""
    NOT_INITIALIZED = "NOT_INITIALIZED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


@dataclass
class DetectorResult:
    """Standardized output format for every Dhwani detector execution."""

    model: str
    raw_score: Optional[float]
    latency_ms: float
    score_direction: str = "higher_is_more_spoof"
    status: str = "SUCCESS"  # "SUCCESS" | "FAILED" | "SKIPPED"
    device: str = "cpu"
    backend: str = "unknown"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "raw_score": float(self.raw_score) if self.raw_score is not None else None,
            "latency_ms": float(self.latency_ms),
            "score_direction": self.score_direction,
            "status": self.status,
            "device": self.device,
            "backend": self.backend,
            "error": self.error,
            "metadata": self.metadata or {},
        }


class BaseDetector:
    """Common interface that all Dhwani detectors must conform to."""

    model_name: str = "unknown"
    status: DetectorStatus = DetectorStatus.NOT_INITIALIZED
    device: str = "cpu"
    backend: str = "unknown"
    error: Optional[str] = None

    @property
    def is_available(self) -> bool:
        """Return True if detector is initialized and ready for inference."""
        return self.status == DetectorStatus.READY

    def predict_audio(self, audio, sample_rate: int = 16000) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement predict_audio()."
        )

