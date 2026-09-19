"""
EchoShield Multi-Model Agreement & Consensus Engine
===================================================
Evaluates inter-model consensus across all active detectors.
Features:
- Pairwise correlation & directional agreement matrix.
- Agreement Level categorization:
    UNANIMOUS (100% concordant)
    MAJORITY  (>= 66% concordant)
    DIVIDED   (>= 50% concordant)
    CONFLICTED (< 50% concordant)
- Explainable consensus rationale for security teams.
"""

from itertools import combinations
from typing import Any, Dict, List, Tuple


class ModelAgreementEngine:
    """
    Computes agreement matrices and explainable consensus metadata.
    """

    def __init__(self, decision_threshold: float = 0.40):
        self.decision_threshold = decision_threshold

    def evaluate_agreement(
        self,
        detector_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compute consensus and pairwise agreement.

        Returns:
            {
                "consensus_level": "UNANIMOUS" | "MAJORITY" | "DIVIDED" | "CONFLICTED",
                "consensus_ratio": float,
                "spoof_votes": int,
                "bonafide_votes": int,
                "pairwise_agreement": Dict[str, bool],
                "explanation": str,
                "is_concordant": bool,
            }
        """
        if not detector_results or len(detector_results) < 2:
            return {
                "consensus_level": "UNANIMOUS" if detector_results else "NONE",
                "consensus_ratio": 1.0 if detector_results else 0.0,
                "spoof_votes": 1 if detector_results and detector_results[0].get("raw_score", 0) >= self.decision_threshold else 0,
                "bonafide_votes": 1 if detector_results and detector_results[0].get("raw_score", 0) < self.decision_threshold else 0,
                "pairwise_agreement": {},
                "explanation": "Single detector active; consensus trivial.",
                "is_concordant": True,
            }

        votes = {}
        for det in detector_results:
            name = det.get("model", "UNKNOWN")
            score = float(det.get("raw_score", 0.0))
            is_spoof = score >= self.decision_threshold
            votes[name] = is_spoof

        total_models = len(votes)
        spoof_votes = sum(1 for v in votes.values() if v)
        bonafide_votes = total_models - spoof_votes

        majority_votes = max(spoof_votes, bonafide_votes)
        consensus_ratio = float(majority_votes / total_models)

        # Pairwise agreement
        pairwise = {}
        names = list(votes.keys())
        agreed_pairs = 0
        total_pairs = 0
        for m1, m2 in combinations(names, 2):
            agreed = votes[m1] == votes[m2]
            pairwise[f"{m1}_vs_{m2}"] = agreed
            if agreed:
                agreed_pairs += 1
            total_pairs += 1

        # Consensus level
        if consensus_ratio == 1.0:
            consensus_level = "UNANIMOUS"
            direction = "spoof" if spoof_votes == total_models else "genuine"
            explanation = f"All {total_models} models unanimously agree audio is {direction}."
            is_concordant = True
        elif consensus_ratio >= 0.66:
            consensus_level = "MAJORITY"
            direction = "spoof" if spoof_votes > bonafide_votes else "genuine"
            explanation = f"{majority_votes}/{total_models} majority agreement ({direction})."
            is_concordant = True
        elif consensus_ratio >= 0.50:
            consensus_level = "DIVIDED"
            explanation = f"Models divided ({spoof_votes} spoof vs {bonafide_votes} genuine)."
            is_concordant = False
        else:
            consensus_level = "CONFLICTED"
            explanation = "High disagreement across models."
            is_concordant = False

        return {
            "consensus_level": consensus_level,
            "consensus_ratio": round(consensus_ratio, 3),
            "spoof_votes": spoof_votes,
            "bonafide_votes": bonafide_votes,
            "pairwise_agreement": pairwise,
            "explanation": explanation,
            "is_concordant": is_concordant,
        }
