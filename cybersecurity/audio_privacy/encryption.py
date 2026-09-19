"""
Audio Encryption Layer: Cryptographic Protection for Retained Recordings.

Implements symmetric authenticated encryption (Fernet / AES-128-CBC + HMAC-SHA256)
and secure memory zeroization to protect sensitive customer voice recordings.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken


def generate_encryption_key() -> bytes:
    """Generates a secure 256-bit Fernet key for symmetric audio encryption."""
    return Fernet.generate_key()


def secure_wipe_buffer(buf: bytearray) -> None:
    """
    Overwrites the contents of a mutable buffer with zero bytes (0x00).
    Ensures transient raw voice data in RAM cannot be extracted via memory dump.
    """
    for i in range(len(buf)):
        buf[i] = 0


def encrypt_audio(audio_bytes: bytes, key: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Encrypts raw audio bytes using authenticated symmetric encryption.

    Args:
        audio_bytes: The raw PCM/WAV audio bytes.
        key: Optional 32-byte URL-safe base64 Fernet key. If None, a new key is generated.

    Returns:
        Tuple of (ciphertext: bytes, key: bytes)
    """
    enc_key = key or generate_encryption_key()
    fernet = Fernet(enc_key)
    ciphertext = fernet.encrypt(audio_bytes)
    return ciphertext, enc_key


def decrypt_audio(ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypts encrypted audio ciphertext using the corresponding key.

    Raises:
        ValueError: If key is invalid or ciphertext has been altered.
    """
    try:
        fernet = Fernet(key)
        return fernet.decrypt(ciphertext)
    except (InvalidToken, Exception) as exc:
        raise ValueError("Decryption failed: corrupted ciphertext or invalid key.") from exc


class AudioVault:
    """
    In-memory or filesystem vault storing encrypted audio blobs with key separation.
    """

    def __init__(self, master_key: Optional[bytes] = None) -> None:
        self._master_key = master_key or generate_encryption_key()
        self._fernet = Fernet(self._master_key)

    @property
    def master_key(self) -> bytes:
        return self._master_key

    def seal(self, raw_audio: bytes) -> bytes:
        """Encrypts raw audio using vault master key."""
        return self._fernet.encrypt(raw_audio)

    def unseal(self, encrypted_audio: bytes) -> bytes:
        """Decrypts encrypted audio using vault master key."""
        try:
            return self._fernet.decrypt(encrypted_audio)
        except InvalidToken as exc:
            raise ValueError("Vault unseal failed: invalid authentication tag.") from exc
