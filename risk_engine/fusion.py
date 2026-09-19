from typing import Any, Dict, Iterable, List

from ai.common.config import MODEL_WEIGHTS
from risk_engine.normalizer import normalize_detector_result


class FusionEngine:
    """
    Combines normalized detector scores into one spoof-evidence score.

    NOTE:
    MODEL_WEIGHTS are engineering placeholders. They must eventually
    be evaluated/calibrated using appropriate validation data.
    """

    def __init__(
        self,
        weights: Dict[str, float] | None = None,
    ):
        self.weights = dict(weights or MODEL_WEIGHTS)

        if not self.weights:
            raise ValueError("Fusion weights cannot be empty.")

        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("Fusion weights cannot be negative.")

        total_weight = sum(self.weights.values())

        if total_weight <= 0:
            raise ValueError("Fusion weights must have a positive sum.")

        # Normalize weights so they sum to 1.
        self.weights = {
            model: weight / total_weight
            for model, weight in self.weights.items()
        }

    def fuse(
        self,
        detector_results: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Fuse detector results.

        Each detector result must contain:
            model
            raw_score
            score_direction
            latency_ms
            metadata
        """

        results: List[Dict[str, Any]] = list(detector_results)

        if not results:
            raise ValueError("No detector results provided.")

        normalized_results = [
            normalize_detector_result(result)
            for result in results
        ]

        contributions = []
        weighted_sum = 0.0
        total_active_weight = 0.0

        for result in normalized_results:
            model = result["model"]

            if model not in self.weights:
                continue

            weight = self.weights[model]
            score = float(result["score"])

            contribution = score * weight

            weighted_sum += contribution
            total_active_weight += weight

            contributions.append(
                {
                    "model": model,
                    "score": score,
                    "weight": weight,
                    "contribution": contribution,
                    "latency_ms": result["latency_ms"],
                }
            )

        if total_active_weight <= 0:
            raise ValueError(
                "None of the supplied detector results have "
                "a configured fusion weight."
            )

        # Renormalize when only a subset of detectors is available.
        fused_score = weighted_sum / total_active_weight

        return {
            "fused_score": max(0.0, min(1.0, fused_score)),
            "active_models": [
                item["model"] for item in contributions
            ],
            "total_active_weight": total_active_weight,
            "contributions": contributions,
        }


if __name__ == "__main__":
    print("FUSION ENGINE: IMPORT TEST")

    engine = FusionEngine()

    print("Weights:")
    for model, weight in engine.weights.items():
        print(f"  {model}: {weight:.4f}")

    mock_results = [
        {
            "model": "W2V2-AASIST",
            "raw_score": 0.46608708163726253,
            "latency_ms": 39.34,
            "score_direction": "higher_is_more_spoof",
            "metadata": {},
        },
        {
            "model": "AASIST",
            "raw_score": 0.60,
            "latency_ms": 25.0,
            "score_direction": "higher_is_more_spoof",
            "metadata": {
                "mock": True,
            },
        },
    ]

    result = engine.fuse(mock_results)

    print()
    print("Mock fusion result:")
    print(result)
