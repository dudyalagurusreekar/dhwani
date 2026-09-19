"""
EchoShield Adaptive Reliability Fusion Engine
=============================================
Performs dynamically weighted evidence fusion across arbitrary active detectors:
- Baseline architecture weights:
    W2V2-AASIST: 0.35
    AASIST:      0.30
    AASIST-L:    0.20
    ACOUSTIC:    0.15
- Dynamic Reliability Scaling:
    Modulates each detector's weight based on:
    1. Signal-to-Noise Ratio (SNR) and Audio Quality level.
    2. Model Confidence Distance: |score - 0.5| * 2.0 (decisive predictions get higher weight).
    3. Clipping Penalty: If audio is clipped, acoustic/spectral weights are downweighted.
- Active Renormalization:
    Ensures weights of present detectors strictly sum to 1.0.
"""

from typing import Any, Dict, List, Optional
import numpy as np


DEFAULT_BASELINE_WEIGHTS: Dict[str, float] = {
    "W2V2-AASIST": 0.35,
    "AASIST": 0.30,
    "AASIST-L": 0.20,
    "ACOUSTIC": 0.15,
}


class AdaptiveFusionEngine:
    """
    Combines spoof probabilities from diverse models with quality-aware reliability weighting.
    """

    def __init__(self, baseline_weights: Optional[Dict[str, float]] = None):
        self.baseline_weights = dict(baseline_weights or DEFAULT_BASELINE_WEIGHTS)

    def fuse(
        self,
        detector_results: List[Dict[str, Any]],
        audio_quality: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fuse detector scores with dynamic reliability weighting.

        Returns:
            {
                "fused_score": float,
                "active_models": List[str],
                "effective_weights": Dict[str, float],
                "confidence": float,
            }
        """
        if not detector_results:
            return {
                "fused_score": 0.0,
                "active_models": [],
                "effective_weights": {},
                "confidence": 0.0,
            }

        quality_level = "GOOD"
        snr_db = 20.0
        clipping_ratio = 0.0

        if audio_quality:
            quality_level = audio_quality.get("quality_level", "GOOD")
            snr_db = float(audio_quality.get("estimated_snr", 20.0))
            clipping_ratio = float(audio_quality.get("clipping_ratio", 0.0))

        # Calculate dynamic reliability per model
        raw_weights: Dict[str, float] = {}
        scores: Dict[str, float] = {}

        for det in detector_results:
            model_name = det.get("model", "UNKNOWN")
            score = float(det.get("raw_score", 0.0))
            scores[model_name] = score

            base_w = self.baseline_weights.get(model_name, 0.25)

            # Reliability factor based on prediction decisiveness:
            # Predictions near 0.5 are uncertain; predictions near 0.0 or 1.0 are confident
            confidence_factor = 0.7 + 0.6 * abs(score - 0.5)  # in [0.7, 1.0]

            # Quality factor
            quality_factor = 1.0
            if model_name == "ACOUSTIC":
                # Acoustic spectral features are sensitive to noise and clipping
                if quality_level == "POOR" or snr_db < 5.0:
                    quality_factor = 0.5
                elif clipping_ratio > 0.02:
                    quality_factor = 0.4
            elif model_name.startswith("W2V2"):
                # SSL models are more robust to noise
                if quality_level == "POOR":
                    quality_factor = 0.9

            raw_weights[model_name] = base_w * confidence_factor * quality_factor

        total_weight = sum(raw_weights.values())
        if total_weight <= 0:
            # Fallback uniform
            effective_weights = {m: 1.0 / len(detector_results) for m in scores}
        else:
            effective_weights = {m: raw_weights[m] / total_weight for m in raw_weights}

        fused_score = sum(scores[m] * effective_weights[m] for m in scores)
        fused_score = max(0.0, min(1.0, float(fused_score)))

        # Overall fusion confidence
        avg_confidence = float(np.mean([abs(scores[m] - 0.5) * 2.0 for m in scores]))

        return {
            "fused_score": round(fused_score, 4),
            "active_models": list(scores.keys()),
            "effective_weights": {m: round(w, 4) for m, w in effective_weights.items()},
            "confidence": round(avg_confidence, 4),
        }
