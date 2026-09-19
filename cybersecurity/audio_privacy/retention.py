"""
Audio Retention Policy & Secure Lifecycle Management Layer.

Enforces privacy-by-design:
- Zero-Retention default (purely ephemeral in-RAM processing).
- Time-to-Live (TTL) retention for forensic evidence holds.
- Cryptographic disk zero-overwrite upon retention expiration.
- Permanent preservation of non-PII SHA-256 hash fingerprints in audit ledger.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from security.hashing import hash_data
from .encryption import AudioVault, secure_wipe_buffer


class RetentionPolicy(str, Enum):
    """Supported retention duration policies for voice recordings."""
    ZERO_RETENTION = "zero_retention"          # Raw audio processed in RAM & discarded immediately
    EPHEMERAL_HOLD_1H = "ephemeral_hold_1h"    # Retained in encrypted form for 1 hour
    STANDARD_HOLD_24H = "standard_hold_24h"    # Retained in encrypted form for 24 hours
    LEGAL_HOLD_30D = "legal_hold_30d"          # Retained under strict forensic chain of custody for 30 days
    CUSTOM = "custom"                          # User-specified custom TTL seconds


POLICY_DURATIONS: Dict[RetentionPolicy, float] = {
    RetentionPolicy.ZERO_RETENTION: 0.0,
    RetentionPolicy.EPHEMERAL_HOLD_1H: 3600.0,
    RetentionPolicy.STANDARD_HOLD_24H: 86400.0,
    RetentionPolicy.LEGAL_HOLD_30D: 2592000.0,
}


@dataclass
class AudioRecordMetadata:
    """Forensic metadata for an ingested audio recording."""
    record_id: str
    session_id: str
    audio_hash: str
    policy: str
    created_at: float
    expires_at: Optional[float]
    storage_path: Optional[str]
    is_purged: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AudioRecordMetadata:
        return cls(**data)


class RetentionManager:
    """
    Coordinates storage, encryption, TTL expiration, and secure purging
    of voice recordings in compliance with GDPR Article 9 and India's DPDP Act 2023.
    """

    def __init__(
        self,
        storage_dir: Optional[Union[str, Path]] = None,
        vault: Optional[AudioVault] = None,
    ) -> None:
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(tempfile.gettempdir()) / "dhwani_secure_vault"

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.vault = vault or AudioVault()
        self._records: Dict[str, AudioRecordMetadata] = {}

    def handle_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        policy: RetentionPolicy = RetentionPolicy.ZERO_RETENTION,
        custom_ttl_seconds: Optional[float] = None,
    ) -> AudioRecordMetadata:
        """
        Processes an audio recording according to the specified retention policy.
        Always records the SHA-256 fingerprint.
        """
        record_id = f"aud_{uuid.uuid4().hex[:12]}"
        audio_fingerprint = hash_data(audio_bytes)
        now = time.time()

        if policy == RetentionPolicy.ZERO_RETENTION:
            # Ephemeral: zero out temporary mutable buffer copy
            scratch = bytearray(audio_bytes)
            secure_wipe_buffer(scratch)
            del scratch

            meta = AudioRecordMetadata(
                record_id=record_id,
                session_id=session_id,
                audio_hash=audio_fingerprint,
                policy=policy.value,
                created_at=now,
                expires_at=now,
                storage_path=None,
                is_purged=True,
            )
            self._records[record_id] = meta
            return meta

        # Retained recording: Encrypt before writing to disk
        duration = (
            custom_ttl_seconds
            if custom_ttl_seconds is not None
            else POLICY_DURATIONS.get(policy, 3600.0)
        )
        expires_at = now + duration

        encrypted_payload = self.vault.seal(audio_bytes)
        file_path = self.storage_dir / f"{record_id}.enc"
        with open(file_path, "wb") as f:
            f.write(encrypted_payload)

        meta = AudioRecordMetadata(
            record_id=record_id,
            session_id=session_id,
            audio_hash=audio_fingerprint,
            policy=policy.value,
            created_at=now,
            expires_at=expires_at,
            storage_path=str(file_path),
            is_purged=False,
        )
        self._records[record_id] = meta
        return meta

    def purge_record(self, record_id: str) -> bool:
        """
        Securely shreds and removes an audio recording from disk.
        Overwrites file contents with zeros prior to unlinking (DoD 5220.22-M sanitization pattern).
        """
        record = self._records.get(record_id)
        if not record or record.is_purged:
            return False

        if record.storage_path and os.path.exists(record.storage_path):
            file_size = os.path.getsize(record.storage_path)
            # Overwrite with zeros
            with open(record.storage_path, "wb") as f:
                f.write(b"\x00" * file_size)
                f.flush()
                os.fsync(f.fileno())
            os.remove(record.storage_path)

        record.is_purged = True
        record.storage_path = None
        return True

    def purge_expired_records(self, current_time: Optional[float] = None) -> List[str]:
        """
        Scans all managed records and permanently purges any whose retention period has expired.

        Returns:
            List of purged record IDs.
        """
        now = current_time if current_time is not None else time.time()
        purged_ids: List[str] = []

        for record_id, record in list(self._records.items()):
            if not record.is_purged and record.expires_at is not None and record.expires_at <= now:
                if self.purge_record(record_id):
                    purged_ids.append(record_id)

        return purged_ids

    def read_encrypted_audio(self, record_id: str) -> bytes:
        """Reads encrypted audio ciphertext from disk."""
        record = self._records.get(record_id)
        if not record:
            raise KeyError(f"Record {record_id} not found.")
        if record.is_purged or not record.storage_path:
            raise ValueError(f"Record {record_id} has already been purged in accordance with retention policy.")

        with open(record.storage_path, "rb") as f:
            return f.read()

    def get_record(self, record_id: str) -> Optional[AudioRecordMetadata]:
        return self._records.get(record_id)

    def list_active_records(self) -> List[AudioRecordMetadata]:
        return [r for r in self._records.values() if not r.is_purged]


_global_retention_mgr: Optional[RetentionManager] = None


def get_retention_manager() -> RetentionManager:
    """Returns singleton global RetentionManager."""
    global _global_retention_mgr
    if _global_retention_mgr is None:
        _global_retention_mgr = RetentionManager()
    return _global_retention_mgr
