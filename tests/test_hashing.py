"""
Unit tests for security/hashing.py (Member 3).
"""

import tempfile
import unittest
from pathlib import Path

from security.hashing import hash_audio_file, hash_data, hash_session_data, verify_hash


class TestHashing(unittest.TestCase):

    def test_hash_data_sha256(self):
        # Known SHA-256 test vector
        sample = b"hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        actual = hash_data(sample)
        self.assertEqual(actual, expected)
        self.assertTrue(verify_hash(sample, expected))

    def test_hash_audio_file(self):
        content = b"RIFF_AUDIO_SAMPLE_PCM_BYTES" * 100
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(content)
            temp_path = f.name

        try:
            expected = hash_data(content)
            actual = hash_audio_file(temp_path)
            self.assertEqual(actual, expected)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_hash_session_data_deterministic(self):
        s1 = {"session_id": "sess_001", "risk_score": 82, "caller": "+919876543210"}
        s2 = {"caller": "+919876543210", "risk_score": 82, "session_id": "sess_001"}
        # Key order differences should still produce identical hash
        self.assertEqual(hash_session_data(s1), hash_session_data(s2))

    def test_verify_hash_mismatch(self):
        data = b"genuine_voice"
        wrong_hash = "0" * 64
        self.assertFalse(verify_hash(data, wrong_hash))


if __name__ == "__main__":
    unittest.main()
