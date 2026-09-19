"""
EchoShield Production Risk Engine Service
=========================================
Connects risk calculation with:
- Temporal Risk Engine (EMA / moving average smoothing)
- Model Agreement & Consensus Engine (Unanimous / Majority / Conflicted)
- Attack Attribution Engine (Synthetic TTS / Voice Conversion / Physical Replay)
- Active Call Interceptor & Mitigation Policies (Allow / Honeypot / Disruption / Terminate)
"""

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from risk_engine.risk_engine import RiskEngine
from risk_engine.model_agreement import ModelAgreementEngine
from ai.common.attack_attribution import AttackAttributionEngine
from ai.prevention.call_interceptor import CallInterceptor

_agreement_engine = ModelAgreementEngine(decision_threshold=0.40)
_attribution_engine = AttackAttributionEngine(spoof_threshold=0.40)
_interceptor = CallInterceptor()
_temporal_engine = RiskEngine()


def calculate_risk(
    fake_probability: float,
    detector_results: Optional[List[Dict[str, Any]]] = None,
    audio_quality: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate risk metrics and mitigation actions.
    Preserves exact contract keys required by routes and tests:
    - risk_score: int (0 - 100)
    - status: "LOW" | "SUSPICIOUS" | "HIGH"
    - alert: str
    - recommendation: "CONTINUE" | "VERIFY_CALLER" | "TRIGGER_VOICE_HONEYPOT" | "TERMINATE_SESSION"
    Plus enriched telemetry.
    """
    fake_probability = max(0.0, min(1.0, float(fake_probability)))
    score = int(round(fake_probability * 100))

    if score >= 70:
        status = "HIGH"
    elif score >= 40:
        status = "SUSPICIOUS"
    else:
        status = "LOW"

    # Multi-model agreement
    agreement = _agreement_engine.evaluate_agreement(detector_results or [])

    # Attack attribution
    attribution = _attribution_engine.attribute_attack(
        risk_score=fake_probability,
        detector_results=detector_results or [],
        audio_quality=audio_quality,
    )

    # Active Call Interceptor action
    action = _interceptor.evaluate_action(
        risk_score=fake_probability,
        risk_level=status,
        attribution=attribution,
        agreement=agreement,
    )

    # Recommendation mapping
    rec = "CONTINUE"
    if action["action"] == "TERMINATE_SESSION":
        rec = "TERMINATE_SESSION"
        alert = f"CRITICAL: Definitive spoof attack ({attribution['primary_vector']}). Terminating call."
    elif action["action"] == "INJECT_DISRUPTION_TONE":
        rec = "DISRUPT_STREAM"
        alert = f"HIGH RISK: Persistent synthetic speech ({attribution['primary_vector']}). Acoustic disruption engaged."
    elif action["action"] == "TRIGGER_VOICE_HONEYPOT":
        rec = "TRIGGER_VOICE_HONEYPOT"
        alert = f"HIGH RISK: Possible synthetic speech ({attribution['primary_vector']}). Voice honeypot challenge issued."
    elif status == "SUSPICIOUS":
        rec = "VERIFY_CALLER"
        alert = f"SUSPICIOUS: Acoustic anomalies detected ({attribution['primary_vector']}). Step-up verification recommended."
    else:
        rec = "CONTINUE"
        alert = "No high-risk signal detected. Authentic human speech verified."

    return {
        "risk_score": score,
        "status": status,
        "risk_level": status,
        "alert": alert,
        "recommendation": rec,
        "attack_vector": attribution.get("primary_vector", "UNKNOWN"),
        "consensus_level": agreement.get("consensus_level", "UNANIMOUS"),
        "consensus_explanation": agreement.get("explanation", ""),
        "policy_action": action.get("action", "ALLOW"),
        "policy_severity": action.get("severity", "INFO"),
        "policy_reason": action.get("policy_reason", ""),
        "reasons": attribution.get("attribution_reasons", []),
    }


def assess_risk(
    detector_results: List[Dict[str, Any]],
    session_id: Optional[str] = None,
    audio_quality: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    High-level risk evaluation helper.
    Computes ensemble fusion, temporal smoothing, consensus, attribution, and mitigation policies.
    """
    from risk_engine.adaptive_fusion import AdaptiveFusionEngine

    fusion_engine = AdaptiveFusionEngine()
    fusion_result = fusion_engine.fuse(detector_results, audio_quality)
    fused_score = fusion_result.get("fused_score", 0.0)

    res = calculate_risk(
        fake_probability=fused_score,
        detector_results=detector_results,
        audio_quality=audio_quality,
    )
    res["fused_score"] = round(float(fused_score), 4)
    res["detectors"] = detector_results
    return res