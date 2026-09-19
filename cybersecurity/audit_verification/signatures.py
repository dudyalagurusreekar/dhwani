"""
Digital Signature Layer: Ed25519 Cryptographic Signatures for Dhwani Audit Trail.

Implements high-speed, constant-time asymmetric Ed25519 signatures to seal
the hash-chain head, ensuring non-repudiation and detecting retroactive log rewriting.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def generate_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generates an Ed25519 private/public keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def export_private_key_pem(
    private_key: ed25519.Ed25519PrivateKey,
    password: Optional[str] = None,
) -> str:
    """Exports private key to PKCS8 PEM string format."""
    encryption_algo: serialization.KeySerializationEncryption
    if password:
        encryption_algo = serialization.BestAvailableEncryption(password.encode("utf-8"))
    else:
        encryption_algo = serialization.NoEncryption()

    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algo,
    )
    return pem_bytes.decode("utf-8")


def export_public_key_pem(public_key: ed25519.Ed25519PublicKey) -> str:
    """Exports public key to SubjectPublicKeyInfo PEM string format."""
    pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_bytes.decode("utf-8")


def load_private_key_pem(
    pem_str: str,
    password: Optional[str] = None,
) -> ed25519.Ed25519PrivateKey:
    """Loads an Ed25519 private key from PEM string."""
    pw_bytes = password.encode("utf-8") if password else None
    key = serialization.load_pem_private_key(
        pem_str.encode("utf-8"),
        password=pw_bytes,
    )
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise TypeError("Expected Ed25519PrivateKey")
    return key


def load_public_key_pem(pem_str: str) -> ed25519.Ed25519PublicKey:
    """Loads an Ed25519 public key from PEM string."""
    key = serialization.load_pem_public_key(pem_str.encode("utf-8"))
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise TypeError("Expected Ed25519PublicKey")
    return key


def sign_data(private_key: ed25519.Ed25519PrivateKey, data: str | bytes) -> str:
    """
    Signs raw data or a hex digest using an Ed25519 private key.

    Returns:
        Hex-encoded 64-byte signature string (128 hex chars).
    """
    data_bytes = data.encode("utf-8") if isinstance(data, str) else data
    sig_bytes = private_key.sign(data_bytes)
    return sig_bytes.hex()


def verify_signature(
    public_key: ed25519.Ed25519PublicKey,
    signature_hex: str,
    data: str | bytes,
) -> bool:
    """
    Verifies an Ed25519 signature against data.

    Returns:
        True if valid; False if tampered or invalid.
    """
    data_bytes = data.encode("utf-8") if isinstance(data, str) else data
    try:
        sig_bytes = bytes.fromhex(signature_hex)
        public_key.verify(sig_bytes, data_bytes)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


class AuditSigner:
    """
    Manages cryptographic signing of Dhwani audit chain heads.
    Kept strictly isolated from the audit log repository.
    """

    def __init__(
        self,
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
        signer_id: str = "dhwani-validator-01",
    ) -> None:
        self.signer_id = signer_id
        if private_key is not None:
            self._private_key = private_key
        else:
            # Check environment variable for persisted key, else generate ephemeral instance
            env_key = os.getenv("DHWANI_SIGNING_KEY_PEM")
            if env_key:
                self._private_key = load_private_key_pem(env_key)
            else:
                self._private_key, _ = generate_keypair()

    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Returns corresponding public key."""
        return self._private_key.public_key()

    @property
    def public_key_pem(self) -> str:
        """Returns public key in PEM format."""
        return export_public_key_pem(self.public_key)

    @property
    def public_key_hex(self) -> str:
        """Returns raw 32-byte public key in hex format."""
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw.hex()

    def sign_chain_head(self, chain_length: int, latest_hash: str) -> str:
        """
        Deterministically canonicalizes and signs the chain tip:
        Message = "DHWANI_CHAIN_HEAD:{chain_length}:{latest_hash}"
        """
        canonical_message = f"DHWANI_CHAIN_HEAD:{chain_length}:{latest_hash}"
        return sign_data(self._private_key, canonical_message)


class AuditSignatureVerifier:
    """
    Verifies signed chain-head checkpoints using only the public key.
    Requires ZERO access to private signing keys.
    """

    def __init__(self, public_key: ed25519.Ed25519PublicKey) -> None:
        self.public_key = public_key

    def verify_chain_head_signature(
        self,
        chain_length: int,
        latest_hash: str,
        signature_hex: str,
    ) -> bool:
        """Verifies whether the signature matches the chain-head hash."""
        canonical_message = f"DHWANI_CHAIN_HEAD:{chain_length}:{latest_hash}"
        return verify_signature(self.public_key, signature_hex, canonical_message)
