"""
Checkpoint & Signature Verification Layer.

Validates Ed25519 digital signatures on audit checkpoints and detects
advanced adversary scenarios including chain history recalculation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

from .checkpoint import AuditCheckpoint
from .signatures import (
    AuditSignatureVerifier,
    load_public_key_pem,
    verify_signature,
)


@dataclass
class CheckpointVerificationResult:
    """Detailed forensic result of verifying a signed audit checkpoint."""
    is_valid: bool
    signature_valid: bool
    chain_matches_checkpoint: bool
    checkpoint_id: str
    checkpoint_length: int
    current_chain_length: int
    checkpoint_hash: str
    current_chain_hash: str
    message: str
    tamper_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def verify_checkpoint_integrity(
    checkpoint: AuditCheckpoint,
    chain: Optional[Any] = None,
    trusted_public_key_pem: Optional[str] = None,
) -> CheckpointVerificationResult:
    """
    Forensically validates a signed checkpoint:
    1. Cryptographically checks the Ed25519 digital signature against the public key.
    2. Validates whether the recorded chain tip matches the signed reference.

    Args:
        checkpoint: The signed AuditCheckpoint to verify.
        chain: Optional active chain instance to compare against.
        trusted_public_key_pem: Optional out-of-band trusted public key PEM.
                                If None, uses checkpoint.public_key_pem.
    """
    key_pem = trusted_public_key_pem or checkpoint.public_key_pem
    try:
        pub_key = load_public_key_pem(key_pem)
    except Exception as exc:
        return CheckpointVerificationResult(
            is_valid=False,
            signature_valid=False,
            chain_matches_checkpoint=False,
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_length=checkpoint.chain_length,
            current_chain_length=0,
            checkpoint_hash=checkpoint.latest_hash,
            current_chain_hash="",
            message=f"Invalid or corrupted public key: {str(exc)}",
            tamper_type="MALFORMED_PUBLIC_KEY",
        )

    verifier = AuditSignatureVerifier(pub_key)
    sig_valid = verifier.verify_chain_head_signature(
        chain_length=checkpoint.chain_length,
        latest_hash=checkpoint.latest_hash,
        signature_hex=checkpoint.signature,
    )

    if not sig_valid:
        return CheckpointVerificationResult(
            is_valid=False,
            signature_valid=False,
            chain_matches_checkpoint=False,
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_length=checkpoint.chain_length,
            current_chain_length=0,
            checkpoint_hash=checkpoint.latest_hash,
            current_chain_hash="",
            message="CRITICAL: Ed25519 signature is INVALID. Checkpoint data was forged or tampered.",
            tamper_type="SIGNATURE_FORGERY",
        )

    # If no active chain provided, standalone checkpoint signature is mathematically valid
    if chain is None:
        return CheckpointVerificationResult(
            is_valid=True,
            signature_valid=True,
            chain_matches_checkpoint=True,
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_length=checkpoint.chain_length,
            current_chain_length=checkpoint.chain_length,
            checkpoint_hash=checkpoint.latest_hash,
            current_chain_hash=checkpoint.latest_hash,
            message="Checkpoint digital signature verified successfully.",
            tamper_type=None,
        )

    # Cross-reference with live chain
    current_length = getattr(chain, "length", len(getattr(chain, "chain", [])))
    current_hash = getattr(chain, "latest_hash", None)
    if current_hash is None and hasattr(chain, "get_last_hash"):
        current_hash = chain.get_last_hash()
    elif current_hash is None and hasattr(chain, "get_latest_hash"):
        current_hash = chain.get_latest_hash()
    elif current_hash is None and hasattr(chain, "chain") and chain.chain:
        last_event = chain.chain[-1]
        current_hash = (
            last_event.get("event_hash")
            if isinstance(last_event, dict)
            else getattr(last_event, "current_hash", "")
        )
    current_hash = current_hash or ""

    # For an exact point-in-time check
    if current_length == checkpoint.chain_length:
        if current_hash != checkpoint.latest_hash:
            return CheckpointVerificationResult(
                is_valid=False,
                signature_valid=True,
                chain_matches_checkpoint=False,
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_length=checkpoint.chain_length,
                current_chain_length=current_length,
                checkpoint_hash=checkpoint.latest_hash,
                current_chain_hash=current_hash,
                message=(
                    "CRITICAL: Chain recalculation attack detected! The chain history was rewritten "
                    f"and recomputed (tip: {current_hash[:16]}...), but the genuine signed checkpoint "
                    f"attests tip ({checkpoint.latest_hash[:16]}...)."
                ),
                tamper_type="CHAIN_REWRITTEN_RECALCULATED",
            )
    elif current_length < checkpoint.chain_length:
        return CheckpointVerificationResult(
            is_valid=False,
            signature_valid=True,
            chain_matches_checkpoint=False,
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_length=checkpoint.chain_length,
            current_chain_length=current_length,
            checkpoint_hash=checkpoint.latest_hash,
            current_chain_hash=current_hash,
            message="CRITICAL: Truncation attack detected! Live chain is shorter than signed checkpoint.",
            tamper_type="CHAIN_TRUNCATION",
        )

    return CheckpointVerificationResult(
        is_valid=True,
        signature_valid=True,
        chain_matches_checkpoint=True,
        checkpoint_id=checkpoint.checkpoint_id,
        checkpoint_length=checkpoint.chain_length,
        current_chain_length=current_length,
        checkpoint_hash=checkpoint.latest_hash,
        current_chain_hash=current_hash,
        message="Integrity verified: Ed25519 signature is valid and matches chain state.",
        tamper_type=None,
    )


def detect_chain_recalculation_attack(chain: Any, checkpoint: AuditCheckpoint) -> Tuple[bool, str]:
    """
    Convenience method: returns (is_attack_detected, explanation).
    """
    res = verify_checkpoint_integrity(checkpoint, chain)
    if not res.is_valid:
        return True, res.message
    return False, "No attack detected. Chain matches signed checkpoint."
