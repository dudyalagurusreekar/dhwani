"""
Dhwani - Tamper-Evident Hash Chain Ledger (Member 3)
Re-exports AuditHashChain and ledger primitives.
"""

from .audit_chain import AuditHashChain, GENESIS_PREV_HASH

__all__ = [
    "AuditHashChain",
    "GENESIS_PREV_HASH",
]
