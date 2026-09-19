"""
Digital Signature & Audit Verification Module for Dhwani.
Provides Ed25519 public-key digital signatures, periodic audit checkpoints,
and signature verification against history rewriting attacks.
"""

from .signatures import (
    generate_keypair,
    sign_data,
    verify_signature,
    AuditSigner,
    AuditSignatureVerifier,
    export_private_key_pem,
    export_public_key_pem,
    load_private_key_pem,
    load_public_key_pem,
)
from .checkpoint import (
    AuditCheckpoint,
    create_checkpoint,
    save_checkpoint,
    load_checkpoint,
)
from .verify_signature import (
    verify_checkpoint_integrity,
    detect_chain_recalculation_attack,
    CheckpointVerificationResult,
)

__all__ = [
    "generate_keypair",
    "sign_data",
    "verify_signature",
    "AuditSigner",
    "AuditSignatureVerifier",
    "export_private_key_pem",
    "export_public_key_pem",
    "load_private_key_pem",
    "load_public_key_pem",
    "AuditCheckpoint",
    "create_checkpoint",
    "save_checkpoint",
    "load_checkpoint",
    "verify_checkpoint_integrity",
    "detect_chain_recalculation_attack",
    "CheckpointVerificationResult",
]
