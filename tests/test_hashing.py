"""
Unit tests for security/hashing.py.
"""

import unittest
from security.hashing import AudioHasher, hash_audio, hash_data, hash_session, verify_hash


class TestHashingModule(unittest.TestCase):

    def test_sha256_hashing(self):
        sample = b"VOICE_EVIDENCE_WAV_BYTES"
        h = hash_audio(sample)
        self.assertEqual(len(h), 64)
        self.assertTrue(verify_hash(sample, h))

    def test_session_hashing_determinism(self):
        s1 = {"session_id": "123", "caller": "+919999999999"}
        s2 = {"caller": "+919999999999", "session_id": "123"}
        self.assertEqual(hash_session(s1), hash_session(s2))


if __name__ == "__main__":
    unittest.main()
