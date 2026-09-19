"""
Dhwani / EchoShield - Security Event Schema (Member 3)
Defines the structured format for storing detection events, including session ID,
timestamp, risk score, model version, audio evidence hash, and chain hashes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .hashing import hash_data

REQUIRED_FIELDS = [
    "session_id",
    "timestamp",
    "event_type",
    "risk_score",
    "model_version",
    "audio_hash",
    "previous_event_hash",
    "event_hash",
]


def get_current_timestamp() -> str:
    """Generate RFC 3339 / ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def compute_event_hash(event_data: Dict[str, Any]) -> str:
    """
    Generate SHA-256 hash for a security event dictionary.
    Excludes the 'event_hash' field itself to prevent circular hashing.
    Keys are sorted to ensure deterministic hashing.
    """
    fields_to_hash = {
        "session_id": str(event_data.get("session_id", "")),
        "timestamp": str(event_data.get("timestamp", "")),
        "event_type": str(event_data.get("event_type", "")),
        "risk_score": float(event_data.get("risk_score", 0)),
        "model_version": str(event_data.get("model_version", "")),
        "audio_hash": str(event_data.get("audio_hash", "")),
        "previous_event_hash": str(event_data.get("previous_event_hash", "")),
    }
    canonical_json = json.dumps(fields_to_hash, sort_keys=True, separators=(",", ":"))
    return hash_data(canonical_json.encode("utf-8"))


def create_security_event(
    session_id: str,
    event_type: str,
    risk_score: float | int,
    model_version: str,
    audio_hash: str,
    previous_event_hash: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a structured security event matching the Dhwani specification:
    {
      "session_id": "session_001",
      "timestamp": "2026-09-19T11:00:00",
      "event_type": "SUSPICIOUS_VOICE",
      "risk_score": 82,
      "model_version": "w2v2-aasist-v1",
      "audio_hash": "sha256_hash_here",
      "previous_event_hash": "previous_hash_here",
      "event_hash": "current_hash_here"
    }
    """
    event = {
        "session_id": session_id,
        "timestamp": timestamp or get_current_timestamp(),
        "event_type": event_type,
        "risk_score": round(float(risk_score), 2),
        "model_version": model_version,
        "audio_hash": audio_hash,
        "previous_event_hash": previous_event_hash,
        "event_hash": "",
    }
    # Calculate and assign the cryptographic hash of this event
    event["event_hash"] = compute_event_hash(event)
    return event


def validate_security_event(event: Dict[str, Any]) -> bool:
    """
    Validate that an event contains all mandatory fields and that its event_hash
    correctly matches its contents.
    """
    if not isinstance(event, dict):
        return False

    for required in REQUIRED_FIELDS:
        if required not in event:
            return False

    # Check hash integrity
    expected_hash = compute_event_hash(event)
    import hmac
    return hmac.compare_digest(str(event["event_hash"]).lower(), expected_hash.lower())


@dataclass
class SecurityEvent:
    """Dataclass representation of a Dhwani Security Event."""
    session_id: str
    timestamp: str
    event_type: str
    risk_score: float
    model_version: str
    audio_hash: str
    previous_event_hash: str
    event_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityEvent:
        return cls(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            risk_score=data["risk_score"],
            model_version=data["model_version"],
            audio_hash=data["audio_hash"],
            previous_event_hash=data["previous_event_hash"],
            event_hash=data["event_hash"],
        )
