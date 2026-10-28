"""
Dhwani / EchoShield - Cryptographic Hasher
Provides SHA-256 hashing for audio data, stream buffers, tensor representations,
session metadata, and cryptographic session-audio binding tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, Union

from .schemas import to_canonical_json


class AudioHasher:
    """
    Cryptographic SHA-256 hashing utility for audio buffers, files, and session metadata.
    Enforces deterministic canonical hashing and constant-time integrity checks.
    """

    CHUNK_SIZE: int = 64 * 1024  # 64 KB default buffer for stream hashing

    @staticmethod
    def hash_bytes(data: Union[bytes, bytearray, memoryview]) -> str:
        """
        Compute SHA-256 hex digest of raw binary bytes.
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(f"Expected binary buffer, got {type(data).__name__}")
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest().lower()

    compute_audio_hash = hash_bytes

    @classmethod
    def hash_stream(cls, stream: BinaryIO, chunk_size: int = CHUNK_SIZE) -> str:
        """
        Compute SHA-256 hash of a readable binary stream chunk-by-chunk.
        Avoids loading large audio files into memory.
        """
        hasher = hashlib.sha256()
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
        return hasher.hexdigest().lower()

    @classmethod
    def hash_file(cls, filepath: Union[str, Path], chunk_size: int = CHUNK_SIZE) -> str:
        """
        Compute SHA-256 hash of a file on disk.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {filepath}")
        with open(path, "rb") as f:
            return cls.hash_stream(f, chunk_size=chunk_size)

    @classmethod
    def hash_numpy_audio(cls, audio_array: Any) -> str:
        """
        Compute deterministic SHA-256 hash of a NumPy array or PyTorch audio tensor.
        Normalizes into a contiguous C-order byte buffer for cross-platform reproducibility.
        """
        # Handle PyTorch Tensor if passed
        if hasattr(audio_array, "detach") and hasattr(audio_array, "cpu") and hasattr(audio_array, "numpy"):
            audio_array = audio_array.detach().cpu().numpy()

        # Handle NumPy ndarray
        if hasattr(audio_array, "tobytes"):
            # Ensure C-contiguous memory layout
            if hasattr(audio_array, "flags") and not audio_array.flags["C_CONTIGUOUS"]:
                import numpy as np
                audio_array = np.ascontiguousarray(audio_array)
            raw_bytes = audio_array.tobytes()
            # Include dtype and shape descriptor to prevent type collision
            header = f"{str(audio_array.dtype)}:{','.join(map(str, audio_array.shape))}:".encode("utf-8")
            hasher = hashlib.sha256()
            hasher.update(header)
            hasher.update(raw_bytes)
            return hasher.hexdigest().lower()

        raise TypeError(f"Unsupported audio array type: {type(audio_array).__name__}")

    @staticmethod
    def hash_session_metadata(metadata: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of session metadata using deterministic canonical JSON.
        Guarantees identical hash regardless of key order.
        """
        canonical_str = to_canonical_json(metadata)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def bind_session_and_audio(session_hash: str, audio_hash: str) -> str:
        """
        Produce a dual-anchor cryptographic provenance token:
        SHA-256(session_hash + ":" + audio_hash).
        Ties the session context irrevocably to the audio data evaluated.
        """
        combined = f"{session_hash.lower()}:{audio_hash.lower()}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest().lower()

    @staticmethod
    def verify_hash(data: Union[bytes, bytearray, memoryview], expected_hash: str) -> bool:
        """
        Verify binary buffer against expected SHA-256 hash using constant-time comparison
        to mitigate timing attack vulnerabilities.
        """
        actual_hash = AudioHasher.hash_bytes(data)
        return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())


# Convenience module-level functions
compute_audio_hash = AudioHasher.hash_bytes
compute_stream_hash = AudioHasher.hash_stream
compute_file_hash = AudioHasher.hash_file
compute_numpy_hash = AudioHasher.hash_numpy_audio
compute_metadata_hash = AudioHasher.hash_session_metadata
bind_provenance_token = AudioHasher.bind_session_and_audio
verify_hash = AudioHasher.verify_hash
