from typing import Any, Dict


def clamp_score(score: float) -> float:
    """Keep a normalized score inside [0, 1]."""
    return max(0.0, min(1.0, float(score)))


def normalize_score(
    score: float,
    score_direction: str = "higher_is_more_spoof",
) -> float:
    """
    Convert a detector score into EchoShield's common convention:

        0.0 = least spoof evidence
        1.0 = most spoof evidence

    Supported directions:
        - higher_is_more_spoof
        - lower_is_more_spoof
    """
    score = clamp_score(score)

    if score_direction == "higher_is_more_spoof":
        return score

    if score_direction == "lower_is_more_spoof":
        return 1.0 - score

    raise ValueError(
        f"Unsupported score_direction: {score_direction}"
    )


def normalize_detector_result(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize a standardized detector result while preserving
    the original detector metadata.
    """
    if "raw_score" not in result:
        raise KeyError("Detector result missing 'raw_score'")

    direction = result.get(
        "score_direction",
        "higher_is_more_spoof",
    )

    normalized_score = normalize_score(
        result["raw_score"],
        direction,
    )

    return {
        "model": result.get("model", "unknown"),
        "score": normalized_score,
        "latency_ms": float(result.get("latency_ms", 0.0)),
        "score_direction": "higher_is_more_spoof",
        "metadata": result.get("metadata", {}),
    }
