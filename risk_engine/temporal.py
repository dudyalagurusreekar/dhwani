from collections import deque
from typing import Any, Dict, List, Optional


class TemporalRiskEngine:
    """
    Maintains recent fusion scores and converts them into
    an explainable temporal risk assessment.

    The thresholds are engineering placeholders and are
    not benchmark-validated.
    """

    def __init__(
        self,
        history_size: int = 10,
        suspicious_threshold: float = 0.40,
        high_threshold: float = 0.70,
    ):
        if history_size <= 0:
            raise ValueError("history_size must be positive.")

        if not 0.0 <= suspicious_threshold <= 1.0:
            raise ValueError("suspicious_threshold must be in [0, 1].")

        if not 0.0 <= high_threshold <= 1.0:
            raise ValueError("high_threshold must be in [0, 1].")

        if suspicious_threshold >= high_threshold:
            raise ValueError(
                "suspicious_threshold must be lower than high_threshold."
            )

        self.history = deque(maxlen=history_size)
        self.suspicious_threshold = suspicious_threshold
        self.high_threshold = high_threshold

    def _moving_average(self) -> float:
        if not self.history:
            return 0.0

        return sum(self.history) / len(self.history)

    def _ema(self, alpha: float = 0.4) -> float:
        if not self.history:
            return 0.0

        ema = self.history[0]

        for score in list(self.history)[1:]:
            ema = alpha * score + (1.0 - alpha) * ema

        return ema

    def _consecutive_suspicious(self) -> int:
        count = 0

        for score in reversed(self.history):
            if score >= self.suspicious_threshold:
                count += 1
            else:
                break

        return count

    def _suspicious_count(self) -> int:
        return sum(
            score >= self.suspicious_threshold
            for score in self.history
        )

    def _trend(self) -> float:
        if len(self.history) < 2:
            return 0.0

        return self.history[-1] - self.history[0]

    def _classify(self, risk_score: float) -> str:
        if risk_score >= self.high_threshold:
            return "HIGH"

        if risk_score >= self.suspicious_threshold:
            return "SUSPICIOUS"

        return "LOW"

    def _build_reasons(
        self,
        risk_score: float,
        consecutive_suspicious: int,
        suspicious_count: int,
        trend: float,
        model_agreement: Optional[bool],
    ) -> List[str]:
        reasons = []

        if consecutive_suspicious >= 3:
            reasons.append(
                "Multiple consecutive suspicious windows"
            )

        if suspicious_count >= 3:
            reasons.append(
                "Risk remained elevated across multiple windows"
            )

        if trend >= 0.15:
            reasons.append(
                "Risk trend is increasing"
            )

        if model_agreement is True:
            reasons.append(
                "Cross-model agreement"
            )

        if risk_score >= self.high_threshold and not reasons:
            reasons.append(
                "Current risk score is above the high-risk threshold"
            )

        if (
            risk_score >= self.suspicious_threshold
            and not reasons
        ):
            reasons.append(
                "Current risk score is above the suspicious threshold"
            )

        return reasons

    def update(
        self,
        fused_score: float,
        model_agreement: Optional[bool] = None,
    ) -> Dict[str, Any]:
        fused_score = max(0.0, min(1.0, float(fused_score)))

        self.history.append(fused_score)

        moving_average = self._moving_average()
        ema = self._ema()

        consecutive_suspicious = self._consecutive_suspicious()
        suspicious_count = self._suspicious_count()
        trend = self._trend()

        # Conservative initial temporal aggregation.
        # The current EMA receives the most weight, while
        # historical evidence provides persistence.
        risk_score = (
            0.50 * ema
            + 0.30 * moving_average
            + 0.20 * fused_score
        )

        risk_score = max(0.0, min(1.0, risk_score))

        risk_level = self._classify(risk_score)

        reasons = self._build_reasons(
            risk_score=risk_score,
            consecutive_suspicious=consecutive_suspicious,
            suspicious_count=suspicious_count,
            trend=trend,
            model_agreement=model_agreement,
        )

        return {
            "risk_score": risk_score,
            "risk_score_percent": risk_score * 100.0,
            "risk_level": risk_level,
            "current_fused_score": fused_score,
            "moving_average": moving_average,
            "ema": ema,
            "suspicious_window_count": suspicious_count,
            "consecutive_suspicious_windows": consecutive_suspicious,
            "trend": trend,
            "model_agreement": model_agreement,
            "history_length": len(self.history),
            "reasons": reasons,
        }


if __name__ == "__main__":
    print("TEMPORAL RISK ENGINE: TEST")
    print("=" * 50)

    engine = TemporalRiskEngine()

    test_scores = [
        0.20,
        0.35,
        0.45,
        0.52,
        0.61,
        0.72,
        0.78,
    ]

    for index, score in enumerate(test_scores, start=1):
        result = engine.update(
            score,
            model_agreement=True,
        )

        print()
        print(f"Window {index}")
        print(f"  Fusion score:       {score:.3f}")
        print(f"  Risk score:         {result['risk_score']:.3f}")
        print(f"  Risk %:             {result['risk_score_percent']:.1f}")
        print(f"  Level:              {result['risk_level']}")
        print(
            f"  Suspicious windows: "
            f"{result['suspicious_window_count']}"
        )
        print(
            f"  Consecutive:        "
            f"{result['consecutive_suspicious_windows']}"
        )
        print(f"  Trend:              {result['trend']:.3f}")
        print(f"  Reasons:            {result['reasons']}")
