"""
EchoShield Tiered Inference Engine
==================================
Implements intelligent two-tier cascaded execution to optimize real-time latency
and GPU computational efficiency:

TIER 1 (Ultra-Fast Edge Models, ~25 ms total):
- AASIST (CUDA, ~21 ms)
- AASIST-L (CUDA, ~22 ms)
- ACOUSTIC (CPU, ~10 ms)

TIER 2 (Deep SSL Escalation Model, ~37 ms):
- W2V2-AASIST (CUDA, ~37 ms, 1.18 GB)

ESCALATION LOGIC:
- If Tier 1 average spoof probability < escalation_threshold (default: 0.25):
    Audio is definitively bona fide.
    Tier 2 execution is BYPASSED (saves ~37 ms and ~2.2 GB active GPU bandwidth).
- If Tier 1 average spoof probability >= escalation_threshold (default: 0.25):
    Preliminary suspicion or ambiguity detected.
    Tier 2 is invoked for full deep SSL contextual confirmation.
"""

from typing import Any, Callable, Dict, List, Optional
import numpy as np


class TieredInferenceManager:
    """
    Manages cascaded two-tier inference between fast edge models and deep SSL models.
    """

    def __init__(
        self,
        tier1_detectors: List[Any],
        tier2_detectors: List[Any],
        escalation_threshold: float = 0.25,
        enabled: bool = True,
    ):
        self.tier1_detectors = tier1_detectors
        self.tier2_detectors = tier2_detectors
        self.escalation_threshold = escalation_threshold
        self.enabled = enabled

    def run_inference(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:
        """
        Execute tiered inference pipeline.

        Returns:
            {
                "results": List[Dict[str, Any]],
                "tier2_triggered": bool,
                "escalation_reason": str,
                "tier1_avg_score": float,
            }
        """
        all_results = []

        # 1. Execute Tier 1
        tier1_scores = []
        for detector in self.tier1_detectors:
            res = detector.predict_audio(audio, sample_rate)
            all_results.append(res)
            tier1_scores.append(float(res.get("raw_score", 0.0)))

        tier1_avg = float(np.mean(tier1_scores)) if tier1_scores else 0.0

        # If tiered mode is disabled, always run Tier 2 (full ensemble mode)
        if not self.enabled:
            for detector in self.tier2_detectors:
                res = detector.predict_audio(audio, sample_rate)
                all_results.append(res)
            return {
                "results": all_results,
                "tier2_triggered": True,
                "escalation_reason": "Tiered mode disabled; full ensemble executed.",
                "tier1_avg_score": round(tier1_avg, 4),
            }

        # Check escalation condition
        tier2_needed = tier1_avg >= self.escalation_threshold

        if tier2_needed:
            for detector in self.tier2_detectors:
                res = detector.predict_audio(audio, sample_rate)
                all_results.append(res)
            reason = f"Tier 1 avg score ({tier1_avg:.3f}) >= threshold ({self.escalation_threshold:.2f}); Tier 2 deep SSL engaged."
        else:
            reason = f"Tier 1 avg score ({tier1_avg:.3f}) < threshold ({self.escalation_threshold:.2f}); Tier 2 bypassed (clean bona fide)."

        return {
            "results": all_results,
            "tier2_triggered": tier2_needed,
            "escalation_reason": reason,
            "tier1_avg_score": round(tier1_avg, 4),
        }
