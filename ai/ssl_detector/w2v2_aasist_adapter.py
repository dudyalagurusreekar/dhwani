from pathlib import Path
from typing import Any, Dict, Optional, Union
import math

from ai.common.detector_interface import BaseDetector, DetectorResult, DetectorStatus
from ai.ssl_detector.w2v2_aasist_detector import W2V2AASISTDetector

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "w2v2_aasist"
    / "w2v2-aasist.onnx"
)


class W2V2AASISTAdapter(BaseDetector):
    """
    Adapter that converts the W2V2-AASIST self-supervised detector
    output into Dhwani's standardized BaseDetector format.
    """

    model_name = "W2V2-AASIST"
    MODEL_NAME = "W2V2-AASIST"  # Backward compatibility

    def __init__(self, model_path: Optional[Union[str, Path]] = None, strict: bool = False):
        super().__init__()
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.detector: Optional[W2V2AASISTDetector] = None
        self.device = "unknown"
        self.backend = "onnx"
        self.status = DetectorStatus.INITIALIZING
        self.error = None

        if not self.model_path.exists():
            self.status = DetectorStatus.UNAVAILABLE
            self.error = (
                f"W2V2-AASIST model not found at {self.model_path}. "
                "Expected: w2v2-aasist.onnx (~1.26 GB) from Hugging Face "
                "'SpeechAntiSpoofingBenchmarks/W2V2-AASIST'. "
                "Download via: python scripts/download_models.py"
            )
            if strict:
                raise FileNotFoundError(self.error)
            return

        try:
            self.detector = W2V2AASISTDetector(str(self.model_path))
            self.device = self.detector.session.get_providers()[0]
            self.status = DetectorStatus.READY
        except Exception as e:
            self.status = DetectorStatus.FAILED
            self.error = str(e)
            if strict:
                raise

    @staticmethod
    def _sigmoid(x: float) -> float:
        x = max(min(float(x), 60.0), -60.0)
        return 1.0 / (1.0 + math.exp(-x))

    def predict_audio(
        self,
        audio,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:
        if self.status != DetectorStatus.READY or self.detector is None:
            exec_status = "SKIPPED" if self.status == DetectorStatus.UNAVAILABLE else "FAILED"
            res = DetectorResult(
                model=self.model_name,
                raw_score=None,
                latency_ms=0.0,
                score_direction="higher_is_more_spoof",
                status=exec_status,
                device=self.device,
                backend=self.backend,
                error=self.error or "W2V2-AASIST detector is not operational",
                metadata={"status": self.status.value},
            )
            return res.to_dict()

        try:
            result = self.detector.predict_audio(
                audio,
                sample_rate=sample_rate,
            )

            bona_fide_logit = float(result["bona_fide_logit"])
            spoof_logit = float(result["spoof_logit"])

            bona_fide_probability = self._sigmoid(bona_fide_logit)
            spoof_score = 1.0 - bona_fide_probability

            if math.isnan(spoof_score) or math.isinf(spoof_score):
                spoof_score = 0.5

            standardized = DetectorResult(
                model=self.model_name,
                raw_score=round(spoof_score, 4),
                latency_ms=round(float(result["latency_ms"]), 2),
                score_direction="higher_is_more_spoof",
                status="SUCCESS",
                device=self.device,
                backend=self.backend,
                metadata={
                    "bona_fide_logit": round(bona_fide_logit, 4),
                    "spoof_logit": round(spoof_logit, 4),
                    "bona_fide_probability": round(bona_fide_probability, 4),
                    "sample_rate": result["sample_rate"],
                    "window_samples": result["window_samples"],
                    "window_seconds": result["window_seconds"],
                    "is_real": True,
                },
            )

            return standardized.to_dict()

        except Exception as e:
            res = DetectorResult(
                model=self.model_name,
                raw_score=None,
                latency_ms=0.0,
                score_direction="higher_is_more_spoof",
                status="FAILED",
                device=self.device,
                backend=self.backend,
                error=str(e),
                metadata={},
            )
            return res.to_dict()


if __name__ == "__main__":
    adapter = W2V2AASISTAdapter()
    print("Model:", adapter.model_name)
    print("Status:", adapter.status.value)
    if adapter.error:
        print("Note:", adapter.error)
