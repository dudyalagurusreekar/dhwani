from typing import Optional
import math


def sigmoid(x: float) -> float:
    x = max(min(float(x), 60.0), -60.0)
    return 1.0 / (1.0 + math.exp(-x))


def normalize_binary_logits(logit: float, spoof_class: bool = True) -> float:
    probability = sigmoid(logit)
    return probability if spoof_class else 1.0 - probability


def normalize_probability(
    probability: float,
    spoof_class: bool = True,
) -> float:
    probability = max(0.0, min(1.0, float(probability)))
    return probability if spoof_class else 1.0 - probability


def clamp_score(score: float) -> float:
    return max(0.0, min(1.0, float(score)))
