"""
Dhwani / EchoShield - SHA-256 Hashing Module (Member 3)
Generates fixed-length digital fingerprints (SHA-256) for audio files,
raw binary evidence, and session data.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Union


def hash_data(data: Union[bytes, bytearray, memoryview]) -> str:
    """
    Generate a SHA-256 hexadecimal digest for raw binary data.

    Args:
        data: Raw bytes, bytearray, or memoryview of the evidence.

    Returns:
        64-character lowercase hexadecimal SHA-256 hash.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"Expected binary data, got {type(data).__name__}")
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest().lower()


def hash_audio_file(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """
    Generate a SHA-256 hash for an audio file on disk (e.g. .wav, .flac).
    Reads the file in chunks to minimize memory consumption.

    Args:
        file_path: Path to the audio file.
        chunk_size: Byte size per chunk (default 64 KB).

    Returns:
        64-character lowercase hexadecimal SHA-256 hash.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def hash_session_data(session_data: Dict[str, Any]) -> str:
    """
    Generate a deterministic SHA-256 hash for session data or metadata dictionary.
    Keys are sorted and formatted without whitespace to guarantee deterministic hashing.

    Args:
        session_data: Dictionary containing session parameters.

    Returns:
        64-character lowercase hexadecimal SHA-256 hash.
    """
    canonical_json = json.dumps(
        session_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().lower()


def verify_hash(data: Union[bytes, bytearray, memoryview], expected_hash: str) -> bool:
    """
    Check whether the given binary data matches an expected SHA-256 hash.
    Uses constant-time comparison to prevent timing attacks.

    Args:
        data: The binary data to verify.
        expected_hash: The 64-character expected SHA-256 hash.

    Returns:
        True if the data produces the expected hash, False otherwise.
    """
    computed = hash_data(data)
    import hmac
    return hmac.compare_digest(computed.lower(), expected_hash.lower())


# Canonical aliases
hash_audio = hash_data
