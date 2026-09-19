from pathlib import Path
from typing import Any, Dict
import math

from ai.common.detector_interface import DetectorResult
from ai.ssl_detector.w2v2_aasist_detector import W2V2AASISTDetector


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "w2v2_aasist"
    / "w2v2-aasist.onnx"
)


class W2V2AASISTAdapter:
    """
    Adapter that converts the existing W2V2-AASIST detector
    output into EchoShield's common detector format.
    """

    MODEL_NAME = "W2V2-AASIST"

    def __init__(self, model_path: str | Path = MODEL_PATH):
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(
                f"W2V2-AASIST model not found: {model_path}"
            )

        self.detector = W2V2AASISTDetector(str(model_path))

    @staticmethod
    def _sigmoid(x: float) -> float:
        x = max(min(float(x), 60.0), -60.0)
        return 1.0 / (1.0 + math.exp(-x))

    def predict_audio(
        self,
        audio,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:

        result = self.detector.predict_audio(
            audio,
            sample_rate=sample_rate,
        )

        bona_fide_logit = float(result["bona_fide_logit"])
        spoof_logit = float(result["spoof_logit"])

        # W2V2-AASIST:
        # higher bona-fide evidence = more genuine.
        #
        # Convert bona-fide evidence into a normalized
        # spoof-oriented score for EchoShield.
        bona_fide_probability = self._sigmoid(bona_fide_logit)
        spoof_score = 1.0 - bona_fide_probability

        standardized = DetectorResult(
            model=self.MODEL_NAME,
            raw_score=spoof_score,
            latency_ms=float(result["latency_ms"]),
            score_direction="higher_is_more_spoof",
            metadata={
                "bona_fide_logit": bona_fide_logit,
                "spoof_logit": spoof_logit,
                "bona_fide_probability": bona_fide_probability,
                "sample_rate": result["sample_rate"],
                "window_samples": result["window_samples"],
                "window_seconds": result["window_seconds"],
            },
        )

        return standardized.to_dict()


if __name__ == "__main__":
    print("W2V2-AASIST ADAPTER: IMPORT TEST")

    print("Model path:")
    print(MODEL_PATH)

    adapter = W2V2AASISTAdapter()

    print("Model:", adapter.MODEL_NAME)
    print("Adapter initialized successfully.")
