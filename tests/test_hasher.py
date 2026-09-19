"""
Unit tests for Dhwani AudioHasher and cryptographic functions.
"""

import io
import tempfile
import unittest
from pathlib import Path

import numpy as np

from security.hasher import (
    AudioHasher,
    bind_provenance_token,
    compute_audio_hash,
    compute_file_hash,
    compute_metadata_hash,
    compute_numpy_hash,
    compute_stream_hash,
    verify_hash,
)


class TestAudioHasher(unittest.TestCase):

    def test_standard_sha256_vectors(self):
        # Standard known test vectors for SHA-256
        empty_hash = AudioHasher.hash_bytes(b"")
        self.assertEqual(
            empty_hash,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

        sample_bytes = b"hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        self.assertEqual(AudioHasher.hash_bytes(sample_bytes), expected)
        self.assertTrue(verify_hash(sample_bytes, expected))

    def test_stream_hashing_equivalence(self):
        data = b"STREAMING_AUDIO_CHUNK_" * 5000  # ~110 KB
        bytes_hash = AudioHasher.hash_bytes(data)

        stream = io.BytesIO(data)
        stream_hash = AudioHasher.hash_stream(stream, chunk_size=1024)
        self.assertEqual(bytes_hash, stream_hash)

    def test_file_hashing_equivalence(self):
        data = b"WAV_HEADER_AND_PCM_SAMPLES" * 1000
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            expected = AudioHasher.hash_bytes(data)
            actual = AudioHasher.hash_file(temp_path, chunk_size=512)
            self.assertEqual(expected, actual)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_numpy_audio_hashing(self):
        # 1-second audio array at 16kHz
        arr = np.linspace(-1.0, 1.0, 16000, dtype=np.float32)
        h1 = AudioHasher.hash_numpy_audio(arr)
        h2 = AudioHasher.hash_numpy_audio(arr.copy())
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

        # Different array must yield different hash
        arr_diff = arr.copy()
        arr_diff[0] += 0.001
        self.assertNotEqual(h1, AudioHasher.hash_numpy_audio(arr_diff))

    def test_session_metadata_canonicalization(self):
        # Dictionaries with identical contents but reversed insertion order
        meta_1 = {
            "session_id": "sess_123",
            "caller": "+1234567890",
            "timestamp": "2026-09-19T10:00:00Z",
            "nested": {"beta": 2, "alpha": 1},
        }
        meta_2 = {
            "nested": {"alpha": 1, "beta": 2},
            "timestamp": "2026-09-19T10:00:00Z",
            "caller": "+1234567890",
            "session_id": "sess_123",
        }

        h1 = AudioHasher.hash_session_metadata(meta_1)
        h2 = AudioHasher.hash_session_metadata(meta_2)
        self.assertEqual(h1, h2)

    def test_provenance_token_binding(self):
        session_hash = "1111111111111111111111111111111111111111111111111111111111111111"
        audio_hash = "2222222222222222222222222222222222222222222222222222222222222222"

        token = bind_provenance_token(session_hash, audio_hash)
        self.assertEqual(len(token), 64)

        # Changing either must change the token
        diff_token = bind_provenance_token(session_hash, audio_hash.replace("2", "3", 1))
        self.assertNotEqual(token, diff_token)


if __name__ == "__main__":
    unittest.main()
