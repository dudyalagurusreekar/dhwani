"""
Dhwani / EchoShield - Security & Provenance Schemas
Provides standardized data models, enums, canonical JSON serialization,
and verification report structures for tamper-evident audit logging.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EventType(str, Enum):
    """Categorical classification of security and audit events."""
    SESSION_START = "SESSION_START"
    AUDIO_INGESTED = "AUDIO_INGESTED"
    AI_INFERENCE_COMPLETED = "AI_INFERENCE_COMPLETED"
    RISK_EVALUATED = "RISK_EVALUATED"
    POLICY_DECISION = "POLICY_DECISION"
    SECURITY_ALERT = "SECURITY_ALERT"
    TAMPER_DETECTED = "TAMPER_DETECTED"
    SESSION_END = "SESSION_END"


class RiskLevel(str, Enum):
    """Graded risk classifications for audio spoofing and integrity threats."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAction(str, Enum):
    """Recommended enforcement action determined by the risk engine."""
    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    CHALLENGE = "CHALLENGE"
    FLAG = "FLAG"
    BLOCK = "BLOCK"


class TamperType(str, Enum):
    """Classification of audit log tampering or corruption."""
    NONE = "NONE"
    GENESIS_INVALID = "GENESIS_INVALID"
    PAYLOAD_ALTERED = "PAYLOAD_ALTERED"
    CHAIN_BROKEN = "CHAIN_BROKEN"
    EVENT_DELETED = "EVENT_DELETED"
    EVENT_INSERTED = "EVENT_INSERTED"
    SEQUENCE_OUT_OF_ORDER = "SEQUENCE_OUT_OF_ORDER"
    TIMESTAMP_REGRESSION = "TIMESTAMP_REGRESSION"


def get_current_utc_iso() -> str:
    """Generate RFC 3339 / ISO 8601 UTC timestamp with microsecond resolution."""
    return datetime.now(timezone.utc).isoformat()


def to_canonical_json(data: Any) -> str:
    """
    Deterministic canonical JSON serializer adhering to RFC 8785 principles.
    Ensures identical byte sequences across different platforms, python versions,
    and dictionary key ordering.
    """
    def _default_encoder(obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default_encoder,
    )


@dataclass(frozen=True)
class RiskAssessment:
    """
    Structured output from the Dhwani Risk Engine.
    Represents the synthesized risk profile of an ingested audio segment.
    """
    score: float  # 0.0 (fully genuine) to 1.0 (definite spoof/deepfake)
    level: RiskLevel
    action: RiskAction
    confidence: float
    reasons: List[str] = field(default_factory=list)
    factors: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "level": self.level.value if isinstance(self.level, Enum) else self.level,
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "confidence": round(self.confidence, 6),
            "reasons": list(self.reasons),
            "factors": self.factors,
        }


@dataclass
class SecurityEvent:
    """
    A single immutable block in the Dhwani tamper-evident audit hash chain.
    Captures security metadata, audio fingerprints, and linkage to previous blocks.
    Strictly forbids storing raw audio bytes.
    """
    event_id: str
    seq_num: int
    timestamp: str
    session_id: str
    event_type: str
    audio_hash: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    chain_hash: str = ""

    @classmethod
    def create(
        cls,
        seq_num: int,
        session_id: str,
        event_type: EventType | str,
        prev_hash: str,
        audio_hash: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> SecurityEvent:
        """Factory method to initialize an event prior to hash computation."""
        return cls(
            event_id=event_id or str(uuid.uuid4()),
            seq_num=seq_num,
            timestamp=timestamp or get_current_utc_iso(),
            session_id=session_id,
            event_type=event_type.value if isinstance(event_type, Enum) else str(event_type),
            audio_hash=audio_hash,
            payload=payload or {},
            prev_hash=prev_hash,
            chain_hash="",
        )

    def canonical_body(self) -> Dict[str, Any]:
        """
        Extract the canonical fields of the event that are cryptographically signed.
        Excludes chain_hash itself to prevent circular hashing.
        """
        return {
            "event_id": self.event_id,
            "seq_num": self.seq_num,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "audio_hash": self.audio_hash,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }

    def to_canonical_json(self) -> str:
        """Produces canonical JSON for the event payload."""
        return to_canonical_json(self.canonical_body())

    def to_dict(self) -> Dict[str, Any]:
        """Full dictionary representation including the finalized chain_hash."""
        return {
            "event_id": self.event_id,
            "seq_num": self.seq_num,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "audio_hash": self.audio_hash,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "chain_hash": self.chain_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityEvent:
        """Reconstruct a SecurityEvent instance from serialized dictionary."""
        return cls(
            event_id=data["event_id"],
            seq_num=data["seq_num"],
            timestamp=data["timestamp"],
            session_id=data["session_id"],
            event_type=data["event_type"],
            audio_hash=data.get("audio_hash"),
            payload=data.get("payload", {}),
            prev_hash=data.get("prev_hash", ""),
            chain_hash=data.get("chain_hash", ""),
        )


@dataclass(frozen=True)
class ChainVerificationReport:
    """
    Detailed audit report generated when verifying hash chain integrity.
    """
    is_valid: bool
    total_events: int
    tampered_event_seq: Optional[int] = None
    tampered_event_id: Optional[str] = None
    tamper_type: TamperType = TamperType.NONE
    error_reason: Optional[str] = None
    verified_at: str = field(default_factory=get_current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_events": self.total_events,
            "tampered_event_seq": self.tampered_event_seq,
            "tampered_event_id": self.tampered_event_id,
            "tamper_type": self.tamper_type.value if isinstance(self.tamper_type, Enum) else self.tamper_type,
            "error_reason": self.error_reason,
            "verified_at": self.verified_at,
        }
