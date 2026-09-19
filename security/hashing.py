"""
Dhwani - SHA-256 Hashing Module (Member 3)
Re-exports core cryptographic hashing utilities.
"""

from .hasher import (
    AudioHasher,
    bind_provenance_token,
    compute_audio_hash,
    compute_file_hash,
    compute_metadata_hash,
    compute_numpy_hash,
    compute_stream_hash,
    verify_hash,
)

# Canonical aliases matching project specification
hash_audio = compute_audio_hash
hash_data = AudioHasher.hash_bytes
hash_session = compute_metadata_hash

__all__ = [
    "AudioHasher",
    "compute_audio_hash",
    "compute_stream_hash",
    "compute_file_hash",
    "compute_numpy_hash",
    "compute_metadata_hash",
    "bind_provenance_token",
    "verify_hash",
    "hash_audio",
    "hash_data",
    "hash_session",
]
