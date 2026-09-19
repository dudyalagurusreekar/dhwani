"""
Audit Checkpoint Model & Serialization.

Encapsulates signed checkpoints binding chain length, tip hash, timestamp,
and Ed25519 digital signature into a durable, auditable artifact.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .signatures import AuditSigner


@dataclass
class AuditCheckpoint:
    """Represents a cryptographically signed state checkpoint of Dhwani's audit chain."""
    checkpoint_id: str
    chain_length: int
    latest_hash: str
    created_at: str
    signer_id: str
    public_key_pem: str
    signature: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditCheckpoint:
        return cls(
            checkpoint_id=data["checkpoint_id"],
            chain_length=int(data["chain_length"]),
            latest_hash=data["latest_hash"],
            created_at=data["created_at"],
            signer_id=data.get("signer_id", "dhwani-validator"),
            public_key_pem=data["public_key_pem"],
            signature=data["signature"],
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> AuditCheckpoint:
        data = json.loads(json_str)
        return cls.from_dict(data)


def create_checkpoint(
    chain: Any,
    signer: AuditSigner,
    checkpoint_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditCheckpoint:
    """
    Creates and digitally signs a new checkpoint from a HashChain or AuditHashChain.

    Args:
        chain: The active HashChain instance.
        signer: The AuditSigner holding the protected private key.
        checkpoint_id: Optional custom identifier (defaults to uuid).
        metadata: Optional contextual metadata.
    """
    chk_id = checkpoint_id or f"chk_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Accommodate both chain interfaces
    length = getattr(chain, "length", len(getattr(chain, "chain", [])))
    latest_hash = getattr(chain, "latest_hash", None)
    if latest_hash is None and hasattr(chain, "get_last_hash"):
        latest_hash = chain.get_last_hash()
    elif latest_hash is None and hasattr(chain, "get_latest_hash"):
        latest_hash = chain.get_latest_hash()
    elif latest_hash is None and hasattr(chain, "chain") and chain.chain:
        last_event = chain.chain[-1]
        latest_hash = (
            last_event.get("event_hash")
            if isinstance(last_event, dict)
            else getattr(last_event, "current_hash", None)
        )

    if not latest_hash:
        raise ValueError("Cannot checkpoint an uninitialized or empty chain without a tip hash.")

    signature = signer.sign_chain_head(length, latest_hash)

    return AuditCheckpoint(
        checkpoint_id=chk_id,
        chain_length=length,
        latest_hash=latest_hash,
        created_at=now_iso,
        signer_id=signer.signer_id,
        public_key_pem=signer.public_key_pem,
        signature=signature,
        metadata=metadata or {},
    )


def save_checkpoint(checkpoint: AuditCheckpoint, file_path: str | Path) -> None:
    """Serializes checkpoint to disk."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(checkpoint.to_json())


def load_checkpoint(file_path: str | Path) -> AuditCheckpoint:
    """Loads a serialized checkpoint from disk."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        return AuditCheckpoint.from_json(f.read())
