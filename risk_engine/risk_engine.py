from typing import Any, Dict, Iterable, Optional

from risk_engine.fusion import FusionEngine
from risk_engine.temporal import TemporalRiskEngine


class RiskEngine:
    """
    EchoShield end-to-end risk orchestration.

    Pipeline:

        detector results
            ↓
        score normalization
            ↓
        model fusion
            ↓
        temporal aggregation
            ↓
        risk assessment
    """

    def __init__(
        self,
        fusion_engine: Optional[FusionEngine] = None,
        temporal_engine: Optional[TemporalRiskEngine] = None,
    ):
        self.fusion_engine = fusion_engine or FusionEngine()
        self.temporal_engine = temporal_engine or TemporalRiskEngine()

    def update(
        self,
        detector_results: Iterable[Dict[str, Any]],
        model_agreement: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Process one analysis window.

        detector_results:
            Standardized detector dictionaries containing
            model, raw_score, score_direction, latency_ms,
            and optional metadata.
        """

        detector_results = list(detector_results)

        if not detector_results:
            raise ValueError(
                "At least one detector result is required."
            )

        fusion_result = self.fusion_engine.fuse(
            detector_results
        )

        temporal_result = self.temporal_engine.update(
            fused_score=fusion_result["fused_score"],
            model_agreement=model_agreement,
        )

        return {
            "risk_score": temporal_result["risk_score"],
            "risk_score_percent": temporal_result[
                "risk_score_percent"
            ],
            "risk_level": temporal_result["risk_level"],
            "current_fused_score": fusion_result["fused_score"],
            "active_models": fusion_result["active_models"],
            "fusion": fusion_result,
            "temporal": temporal_result,
            "reasons": temporal_result["reasons"],
        }


if __name__ == "__main__":
    print("ECHOSHIELD RISK ENGINE: TEST")
    print("=" * 60)

    engine = RiskEngine()

    windows = [
        {
            "W2V2-AASIST": 0.20,
            "AASIST": 0.25,
        },
        {
            "W2V2-AASIST": 0.42,
            "AASIST": 0.48,
        },
        {
            "W2V2-AASIST": 0.55,
            "AASIST": 0.60,
        },
        {
            "W2V2-AASIST": 0.70,
            "AASIST": 0.76,
        },
        {
            "W2V2-AASIST": 0.78,
            "AASIST": 0.82,
        },
    ]

    for index, scores in enumerate(windows, start=1):
        detector_results = [
            {
                "model": model,
                "raw_score": score,
                "latency_ms": 40.0,
                "score_direction": "higher_is_more_spoof",
                "metadata": {
                    "mock": True,
                },
            }
            for model, score in scores.items()
        ]

        # For this test, both detectors are deliberately
        # moving in the same direction.
        model_agreement = True

        result = engine.update(
            detector_results,
            model_agreement=model_agreement,
        )

        print()
        print(f"Window {index}")
        print(
            f"  W2V2-AASIST: {scores['W2V2-AASIST']:.3f}"
        )
        print(
            f"  AASIST:      {scores['AASIST']:.3f}"
        )
        print(
            f"  Fusion:      "
            f"{result['current_fused_score']:.3f}"
        )
        print(
            f"  Risk:        "
            f"{result['risk_score']:.3f}"
        )
        print(
            f"  Risk %:      "
            f"{result['risk_score_percent']:.1f}"
        )
        print(
            f"  Level:       "
            f"{result['risk_level']}"
        )
        print(
            f"  Reasons:     "
            f"{result['reasons']}"
        )
