"""
Dhwani / EchoShield - Tamper-Evident Audit Hash Chain
Maintains an immutable append-only cryptographic ledger of security events,
persists records to disk in JSONL format, and verifies chain integrity
to detect unauthorized modifications, deletions, and insertions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Union

from .schemas import (
    ChainVerificationReport,
    EventType,
    SecurityEvent,
    TamperType,
    get_current_utc_iso,
    to_canonical_json,
)

GENESIS_PREV_HASH: str = "0" * 64


class AuditHashChain:
    """
    Cryptographic hash chain ledger for security and provenance events.
    Thread-safe and supports append-only persistence to JSON Lines (.jsonl) files.
    """

    def __init__(self, persistence_file: Optional[Union[str, Path]] = None):
        self._chain: List[SecurityEvent] = []
        self._lock = threading.RLock()
        self.persistence_file: Optional[Path] = Path(persistence_file) if persistence_file else None

        if self.persistence_file and self.persistence_file.exists():
            self._load_from_disk()

    @property
    def length(self) -> int:
        with self._lock:
            return len(self._chain)

    @property
    def latest_hash(self) -> str:
        with self._lock:
            return self._chain[-1].chain_hash if self._chain else GENESIS_PREV_HASH

    def _compute_event_chain_hash(self, prev_hash: str, event: SecurityEvent) -> str:
        """
        Compute H_n = SHA-256(prev_hash + ":" + canonical_json(event_body))
        """
        canonical_payload = event.to_canonical_json()
        preimage = f"{prev_hash}:{canonical_payload}".encode("utf-8")
        return hashlib.sha256(preimage).hexdigest().lower()

    def append_event(
        self,
        session_id: str,
        event_type: EventType | str,
        audio_hash: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> SecurityEvent:
        """
        Create and append a new security event to the tamper-evident hash chain.
        """
        with self._lock:
            seq_num = len(self._chain)
            prev_hash = self._chain[-1].chain_hash if self._chain else GENESIS_PREV_HASH

            event = SecurityEvent.create(
                seq_num=seq_num,
                session_id=session_id,
                event_type=event_type,
                prev_hash=prev_hash,
                audio_hash=audio_hash,
                payload=payload or {},
                event_id=event_id,
                timestamp=timestamp,
            )

            # Cryptographically bind previous hash with the new canonical event body
            event.chain_hash = self._compute_event_chain_hash(prev_hash, event)
            self._chain.append(event)

            # Persist to disk if file configured
            if self.persistence_file:
                self._persist_event(event)

            return event

    def _persist_event(self, event: SecurityEvent) -> None:
        """Append event line to the persistence file atomically."""
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def _load_from_disk(self) -> None:
        """Load and reconstruct the chain from an existing JSONL file."""
        with self._lock:
            self._chain.clear()
            with open(self.persistence_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    self._chain.append(SecurityEvent.from_dict(data))

    def verify_integrity(self) -> ChainVerificationReport:
        """
        Audit the entire hash chain from the genesis block to the tip.
        Verifies:
        1. Genesis block references standard null hash.
        2. Recalculated hash matches recorded chain_hash (detects payload tampering).
        3. prev_hash pointer matches previous block's chain_hash (detects break, deletion, insertion).
        4. Sequence numbers are strictly monotonic: 0, 1, 2, ...
        """
        with self._lock:
            total_events = len(self._chain)
            if total_events == 0:
                return ChainVerificationReport(
                    is_valid=True,
                    total_events=0,
                    tamper_type=TamperType.NONE,
                    error_reason=None,
                )

            # 1. Verify Genesis Block
            genesis_event = self._chain[0]
            if genesis_event.prev_hash != GENESIS_PREV_HASH:
                return ChainVerificationReport(
                    is_valid=False,
                    total_events=total_events,
                    tampered_event_seq=0,
                    tampered_event_id=genesis_event.event_id,
                    tamper_type=TamperType.GENESIS_INVALID,
                    error_reason=(
                        f"Genesis block prev_hash invalid. Expected {GENESIS_PREV_HASH}, "
                        f"got {genesis_event.prev_hash}"
                    ),
                )

            # 2. Sequential Audit
            for i, event in enumerate(self._chain):
                # Verify monotonic sequence numbers
                if event.seq_num != i:
                    return ChainVerificationReport(
                        is_valid=False,
                        total_events=total_events,
                        tampered_event_seq=event.seq_num,
                        tampered_event_id=event.event_id,
                        tamper_type=TamperType.SEQUENCE_OUT_OF_ORDER,
                        error_reason=f"Event at index {i} has invalid sequence number {event.seq_num}",
                    )

                # Verify payload integrity by recomputing chain_hash
                recalculated_hash = self._compute_event_chain_hash(event.prev_hash, event)
                if not hmac.compare_digest(recalculated_hash, event.chain_hash):
                    return ChainVerificationReport(
                        is_valid=False,
                        total_events=total_events,
                        tampered_event_seq=event.seq_num,
                        tampered_event_id=event.event_id,
                        tamper_type=TamperType.PAYLOAD_ALTERED,
                        error_reason=(
                            f"Event #{event.seq_num} ({event.event_id}) payload or metadata was altered. "
                            f"Recorded hash: {event.chain_hash}, Recomputed: {recalculated_hash}"
                        ),
                    )

                # Verify chain linkage to previous event
                if i > 0:
                    prev_event = self._chain[i - 1]
                    if not hmac.compare_digest(event.prev_hash, prev_event.chain_hash):
                        return ChainVerificationReport(
                            is_valid=False,
                            total_events=total_events,
                            tampered_event_seq=event.seq_num,
                            tampered_event_id=event.event_id,
                            tamper_type=TamperType.CHAIN_BROKEN,
                            error_reason=(
                                f"Chain broken between Event #{prev_event.seq_num} and #{event.seq_num}. "
                                f"Event #{event.seq_num} points to prev_hash {event.prev_hash}, "
                                f"but Event #{prev_event.seq_num} has hash {prev_event.chain_hash}"
                            ),
                        )

            return ChainVerificationReport(
                is_valid=True,
                total_events=total_events,
                tamper_type=TamperType.NONE,
                error_reason=None,
            )

    def get_events(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SecurityEvent]:
        """Query security events with optional filtering."""
        with self._lock:
            results = self._chain
            if session_id:
                results = [e for e in results if e.session_id == session_id]
            if event_type:
                results = [e for e in results if e.event_type == event_type]
            if limit:
                results = results[-limit:]
            return list(results)

    def to_jsonl_string(self) -> str:
        """Export all events in the chain as a JSON Lines formatted string."""
        with self._lock:
            return "\n".join(json.dumps(e.to_dict()) for e in self._chain)

    def export_verification_certificate(self) -> Dict[str, Any]:
        """
        Generate a cryptographically sealed verification certificate of the audit ledger.
        Computes a cumulative root digest across all chained event hashes.
        Suitable for third-party compliance audits and non-repudiation attestations.
        """
        with self._lock:
            report = self.verify_integrity()
            # Compute cumulative root digest over all block hashes
            hasher = hashlib.sha256()
            for event in self._chain:
                hasher.update(event.chain_hash.encode("utf-8"))
            root_digest = hasher.hexdigest().lower()

            return {
                "certificate_version": "1.0.0",
                "is_valid": report.is_valid,
                "total_events": len(self._chain),
                "genesis_hash": self._chain[0].chain_hash if self._chain else GENESIS_PREV_HASH,
                "tip_hash": self.latest_hash,
                "ledger_root_digest": root_digest,
                "tamper_type": report.tamper_type.value,
                "certified_at": get_current_utc_iso(),
            }

    def get_session_audit_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Produce a forensic summary for a specific call/stream session.
        Aggregates chunks processed, risk trajectory, and provenance tokens.
        """
        with self._lock:
            session_events = [e for e in self._chain if e.session_id == session_id]
            if not session_events:
                return {
                    "session_id": session_id,
                    "total_events": 0,
                    "found": False,
                }

            fake_probs = []
            risk_scores = []
            statuses = []

            for e in session_events:
                p = e.payload or {}
                if "fake_probability" in p:
                    fake_probs.append(p["fake_probability"])
                elif "ai_score" in p:
                    fake_probs.append(p["ai_score"])
                if "risk_score" in p:
                    risk_scores.append(p["risk_score"])
                if "risk_status" in p:
                    statuses.append(p["risk_status"])

            return {
                "session_id": session_id,
                "found": True,
                "total_events": len(session_events),
                "first_event_at": session_events[0].timestamp,
                "last_event_at": session_events[-1].timestamp,
                "first_event_hash": session_events[0].chain_hash,
                "latest_event_hash": session_events[-1].chain_hash,
                "avg_fake_probability": round(sum(fake_probs) / len(fake_probs), 4) if fake_probs else None,
                "max_fake_probability": round(max(fake_probs), 4) if fake_probs else None,
                "max_risk_score": max(risk_scores) if risk_scores else None,
                "highest_risk_status": "HIGH" if "HIGH" in statuses else ("SUSPICIOUS" if "SUSPICIOUS" in statuses else "LOW"),
                "event_types": list(set(e.event_type for e in session_events)),
            }

    def tamper_for_testing(self, seq_num: int, field_name: str, new_value: Any) -> None:
        """
        Simulate malicious tampering on an in-memory event.
        Used exclusively in unit tests and demonstrations to verify tamper detection.
        """
        with self._lock:
            if 0 <= seq_num < len(self._chain):
                event = self._chain[seq_num]
                if field_name == "payload":
                    event.payload = new_value
                elif field_name == "audio_hash":
                    event.audio_hash = new_value
                elif field_name == "prev_hash":
                    event.prev_hash = new_value
                elif field_name == "chain_hash":
                    event.chain_hash = new_value
                elif field_name == "seq_num":
                    event.seq_num = new_value
                elif hasattr(event, field_name):
                    setattr(event, field_name, new_value)
