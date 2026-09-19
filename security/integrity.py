"""
Dhwani - Integrity Verification Module (Member 3)
Standalone auditing and tamper-detection functions.
"""

from __future__ import annotations

from typing import List, Optional

from .audit_chain import AuditHashChain
from .schemas import ChainVerificationReport, SecurityEvent


def verify_chain(chain: AuditHashChain) -> ChainVerificationReport:
    """Audit the complete hash chain from genesis to tip."""
    return chain.verify_integrity()


def verify_event(event: SecurityEvent) -> bool:
    """Verify an individual event's internal cryptographic hash."""
    recomputed = event.to_canonical_json()
    from .hasher import AudioHasher
    import hashlib
    preimage = f"{event.prev_hash}:{recomputed}".encode("utf-8")
    expected = hashlib.sha256(preimage).hexdigest().lower()
    import hmac
    return hmac.compare_digest(expected, event.chain_hash)


def detect_tampering(chain: AuditHashChain) -> Optional[str]:
    """
    Returns a human-readable failure diagnosis if the chain has been tampered with,
    or None if the chain is completely authentic.
    """
    report = chain.verify_integrity()
    return report.error_reason if not report.is_valid else None
