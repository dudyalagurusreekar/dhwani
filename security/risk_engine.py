"""
Dhwani / EchoShield - Risk Engine
Evaluates AI deepfake detection scores, confidence metrics, audio anomalies,
and historical session context to assign risk classifications and policy enforcement actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import threading

from .schemas import RiskAction, RiskAssessment, RiskLevel


@dataclass
class RiskThresholds:
    """Configurable probability cutoffs for risk categorization."""
    low_cutoff: float = 0.30       # < 0.30: LOW (Allow)
    medium_cutoff: float = 0.60    # 0.30 <= x < 0.60: MEDIUM (Monitor)
    high_cutoff: float = 0.85      # 0.60 <= x < 0.85: HIGH (Challenge/Flag)
                                   # >= 0.85: CRITICAL (Block)

    def validate(self) -> None:
        if not (0.0 <= self.low_cutoff < self.medium_cutoff < self.high_cutoff <= 1.0):
            raise ValueError(
                f"Invalid threshold ordering: {self.low_cutoff} < {self.medium_cutoff} < {self.high_cutoff}"
            )


@dataclass
class SessionRiskContext:
    """Tracks stateful risk trajectory across chunks in an ongoing call or stream."""
    total_evaluations: int = 0
    consecutive_high_scores: int = 0
    max_score_seen: float = 0.0
    history: List[float] = field(default_factory=list)


class RiskEngine:
    """
    Synthesizes AI detection results into actionable security risk decisions.
    Applies multi-factor scoring, confidence weighting, anomaly penalties,
    and stateful escalation rules.
    """

    def __init__(
        self,
        thresholds: Optional[RiskThresholds] = None,
        max_consecutive_high_before_block: int = 2,
        min_reliable_duration_sec: float = 0.5,
    ):
        self.thresholds = thresholds or RiskThresholds()
        self.thresholds.validate()
        self.max_consecutive_high = max_consecutive_high_before_block
        self.min_reliable_duration_sec = min_reliable_duration_sec
        self._session_contexts: Dict[str, SessionRiskContext] = {}
        self._lock = threading.Lock()

    def evaluate(
        self,
        ai_score: float,
        confidence: float = 1.0,
        model_name: str = "AASIST",
        audio_metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> RiskAssessment:
        """
        Evaluate an AI deepfake detection output and produce a standardized RiskAssessment.

        Args:
            ai_score: Probability that the audio is synthetic/spoofed (0.0 to 1.0).
            confidence: Model confidence metric (0.0 to 1.0).
            model_name: Identifier of the AI inference model.
            audio_metadata: Optional dict with duration_sec, sample_rate, channels, etc.
            session_id: Optional session identifier for cross-chunk stateful tracking.
        """
        clamped_score = max(0.0, min(1.0, float(ai_score)))
        clamped_confidence = max(0.0, min(1.0, float(confidence)))
        audio_metadata = audio_metadata or {}
        duration_sec = audio_metadata.get("duration_sec", 1.0)

        reasons: List[str] = []
        factors: Dict[str, Any] = {
            "raw_ai_score": clamped_score,
            "model_confidence": clamped_confidence,
            "model_name": model_name,
            "duration_sec": duration_sec,
        }

        # 1. Base classification via threshold bands
        if clamped_score < self.thresholds.low_cutoff:
            level = RiskLevel.LOW
            action = RiskAction.ALLOW
            reasons.append(f"AI score {clamped_score:.3f} below low cutoff ({self.thresholds.low_cutoff})")
        elif clamped_score < self.thresholds.medium_cutoff:
            level = RiskLevel.MEDIUM
            action = RiskAction.MONITOR
            reasons.append(
                f"AI score {clamped_score:.3f} within medium risk band "
                f"[{self.thresholds.low_cutoff}, {self.thresholds.medium_cutoff})"
            )
        elif clamped_score < self.thresholds.high_cutoff:
            level = RiskLevel.HIGH
            action = RiskAction.FLAG
            reasons.append(
                f"AI score {clamped_score:.3f} within high risk band "
                f"[{self.thresholds.medium_cutoff}, {self.thresholds.high_cutoff})"
            )
        else:
            level = RiskLevel.CRITICAL
            action = RiskAction.BLOCK
            reasons.append(f"AI score {clamped_score:.3f} exceeds critical cutoff ({self.thresholds.high_cutoff})")

        # 2. Duration penalty / anomaly check
        if duration_sec < self.min_reliable_duration_sec:
            reasons.append(
                f"Audio segment duration ({duration_sec:.2f}s) is shorter than minimum reliable "
                f"threshold ({self.min_reliable_duration_sec:.2f}s); confidence dampened"
            )
            clamped_confidence *= 0.7
            factors["short_duration_flag"] = True

        # 3. Confidence adjustment: if model is uncertain on a borderline score
        if clamped_confidence < 0.5 and level == RiskLevel.LOW and clamped_score > (self.thresholds.low_cutoff * 0.8):
            level = RiskLevel.MEDIUM
            action = RiskAction.MONITOR
            reasons.append("Low model confidence escalated LOW risk to MEDIUM for monitoring")

        # 4. Stateful session tracking & escalation
        if session_id:
            with self._lock:
                ctx = self._session_contexts.setdefault(session_id, SessionRiskContext())
                ctx.total_evaluations += 1
                ctx.history.append(clamped_score)
                ctx.max_score_seen = max(ctx.max_score_seen, clamped_score)

                if level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                    ctx.consecutive_high_scores += 1
                else:
                    ctx.consecutive_high_scores = 0

                factors["session_eval_count"] = ctx.total_evaluations
                factors["session_consecutive_high"] = ctx.consecutive_high_scores
                factors["session_max_score"] = ctx.max_score_seen

                if ctx.consecutive_high_scores >= self.max_consecutive_high and action != RiskAction.BLOCK:
                    level = RiskLevel.CRITICAL
                    action = RiskAction.BLOCK
                    reasons.append(
                        f"Repeated high spoof scores ({ctx.consecutive_high_scores} consecutive) "
                        f"triggered policy escalation to BLOCK"
                    )

        return RiskAssessment(
            score=clamped_score,
            level=level,
            action=action,
            confidence=clamped_confidence,
            reasons=reasons,
            factors=factors,
        )

    def reset_session(self, session_id: str) -> None:
        """Clear stateful history for a closed session."""
        with self._lock:
            self._session_contexts.pop(session_id, None)

    def get_session_context(self, session_id: str) -> Optional[SessionRiskContext]:
        """Retrieve tracking context for an active session."""
        with self._lock:
            return self._session_contexts.get(session_id)
