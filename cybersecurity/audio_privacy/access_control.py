"""
Audio Access Control Layer: Controlled Access to Retained Recordings.

Enforces strict authorization, justification logging, and tamper-evident
audit trails whenever encrypted voice evidence is decrypted or accessed.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from cybersecurity.api_security.authorization import Permission, Role, user_has_permission
from .retention import RetentionManager


class AccessDeniedError(Exception):
    """Raised when an actor lacks authority to decrypt or access voice recordings."""
    pass


@dataclass
class AudioAccessLogEntry:
    """Forensic record of an audio retrieval or decryption event."""
    timestamp: float
    record_id: str
    accessor_id: str
    action: str
    justification: str
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AudioAccessGate:
    """
    Guards access to encrypted audio files held in storage.
    Enforces chain-of-custody logging for legal and forensic compliance.
    """

    def __init__(
        self,
        retention_manager: RetentionManager,
        audit_chain: Optional[Any] = None,
    ) -> None:
        self.retention_manager = retention_manager
        self.audit_chain = audit_chain
        self.access_logs: List[AudioAccessLogEntry] = []

    def request_audio_decryption(
        self,
        record_id: str,
        user: Dict[str, Any],
        justification: str,
    ) -> bytes:
        """
        Validates authorization, logs the access request, and returns decrypted audio.

        Args:
            record_id: Identifier of the retained audio record.
            user: Decoded user dictionary containing 'sub', 'role', and 'scopes'.
            justification: Forensic or administrative justification for accessing voice data.

        Raises:
            AccessDeniedError: If caller lacks audio:decrypt permission.
            ValueError: If record is expired, purged, or invalid.
        """
        now = time.time()
        accessor_id = user.get("sub", "unknown_user")

        # Authorization check: Requires AUDIO_DECRYPT permission or ADMIN role
        has_access = user_has_permission(user, Permission.AUDIO_DECRYPT.value)

        if not has_access:
            log_entry = AudioAccessLogEntry(
                timestamp=now,
                record_id=record_id,
                accessor_id=accessor_id,
                action="DECRYPT_ATTEMPT",
                justification=justification,
                success=False,
            )
            self.access_logs.append(log_entry)
            raise AccessDeniedError(
                f"Access denied: User '{accessor_id}' lacks permission '{Permission.AUDIO_DECRYPT.value}'."
            )

        # Retrieve encrypted ciphertext from retention manager
        ciphertext = self.retention_manager.read_encrypted_audio(record_id)

        # Decrypt via vault
        raw_audio = self.retention_manager.vault.unseal(ciphertext)

        # Log successful chain-of-custody event
        log_entry = AudioAccessLogEntry(
            timestamp=now,
            record_id=record_id,
            accessor_id=accessor_id,
            action="DECRYPT_SUCCESS",
            justification=justification,
            success=True,
        )
        self.access_logs.append(log_entry)

        # If connected to Dhwani Hash Chain, record forensic access block
        if self.audit_chain is not None and hasattr(self.audit_chain, "add_event"):
            rec = self.retention_manager.get_record(record_id)
            session_id = rec.session_id if rec else "unknown_session"
            audio_hash = rec.audio_hash if rec else "0" * 64
            self.audit_chain.add_event(
                session_id=session_id,
                event_type="AUDIO_RECORDING_ACCESSED",
                risk_score=0,
                model_version="forensic-vault-v1",
                audio_hash=audio_hash,
            )

        return raw_audio

    def get_access_logs(self, record_id: Optional[str] = None) -> List[AudioAccessLogEntry]:
        """Returns forensic access log entries, optionally filtered by record ID."""
        if record_id is None:
            return list(self.access_logs)
        return [entry for entry in self.access_logs if entry.record_id == record_id]
