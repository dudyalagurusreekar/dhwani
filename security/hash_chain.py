"""
Dhwani / EchoShield - Tamper-Evident Hash Chain Module (Member 3)
Connects security events sequentially so that any modification to past records
breaks the mathematical verification of the chain.

EVENT 1
   ↓
Hash 1
   ↓
EVENT 2 + Hash 1
   ↓
Hash 2
   ↓
EVENT 3 + Hash 2
   ↓
Hash 3
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .event_schema import create_security_event, validate_security_event

GENESIS_HASH: str = "0" * 64


class HashChain:
    """
    Manages an append-only, tamper-evident chain of security events.
    Each event contains the hash of the previous event.
    """

    def __init__(self, storage_file: Optional[Union[str, Path]] = None):
        self.chain: List[Dict[str, Any]] = []
        self.storage_file: Optional[Path] = Path(storage_file) if storage_file else None

        if self.storage_file and self.storage_file.exists():
            self.load_from_file(self.storage_file)

    @property
    def length(self) -> int:
        return len(self.chain)

    def get_last_hash(self) -> str:
        """Returns the event_hash of the most recent event, or GENESIS_HASH if empty."""
        if not self.chain:
            return GENESIS_HASH
        return self.chain[-1]["event_hash"]

    def add_event(
        self,
        session_id: str,
        event_type: str,
        risk_score: float | int,
        model_version: str,
        audio_hash: str,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create and append a new security event linked to the previous event's hash.

        Args:
            session_id: Call or stream session identifier.
            event_type: Type of event (e.g. "CALL_STARTED", "SUSPICIOUS_VOICE", "ALERT_GENERATED").
            risk_score: Risk score (e.g. 0 to 100).
            model_version: AI model identifier (e.g. "w2v2-aasist-v1").
            audio_hash: SHA-256 fingerprint of the audio evidence.
            timestamp: Optional ISO 8601 UTC timestamp.

        Returns:
            The newly created and linked security event dictionary.
        """
        prev_hash = self.get_last_hash()
        event = create_security_event(
            session_id=session_id,
            event_type=event_type,
            risk_score=risk_score,
            model_version=model_version,
            audio_hash=audio_hash,
            previous_event_hash=prev_hash,
            timestamp=timestamp,
        )
        self.chain.append(event)

        if self.storage_file:
            self._append_to_disk(event)

        return event

    def get_events(self) -> List[Dict[str, Any]]:
        """Return a copy of all events in the chain."""
        return list(self.chain)

    def _append_to_disk(self, event: Dict[str, Any]) -> None:
        """Append event as a line in a JSON Lines file."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save the entire chain to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.chain, f, indent=2)

    def load_from_file(self, file_path: Union[str, Path]) -> None:
        """Load the chain from a JSON or JSONL file."""
        path = Path(file_path)
        if not path.exists():
            return

        self.chain.clear()
        with open(path, "r", encoding="utf-8") as f:
            first_char = f.read(1).strip()
            f.seek(0)
            if first_char == "[":
                # Standard JSON array
                self.chain = json.load(f)
            else:
                # JSON Lines format
                for line in f:
                    line = line.strip()
                    if line:
                        self.chain.append(json.loads(line))

    def tamper_event(self, index: int, field: str, new_value: Any) -> None:
        """
        Simulate tampering with an event at a given index.
        Used for testing and demonstration of tamper detection.
        """
        if 0 <= index < len(self.chain):
            self.chain[index][field] = new_value


# Re-export AuditHashChain for unified compatibility
from .audit_chain import AuditHashChain
