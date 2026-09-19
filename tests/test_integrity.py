"""
Unit tests for security/hashing.py and security/integrity.py.
"""

import unittest

from security.hashing import hash_audio, hash_data, hash_session, verify_hash
from security.hash_chain import AuditHashChain
from security.integrity import detect_tampering, verify_chain, verify_event
from security.schemas import EventType


class TestIntegrityModule(unittest.TestCase):

    def test_hashing_aliases(self):
        sample = b"TEST_DATA_BYTES"
        h = hash_data(sample)
        self.assertEqual(len(h), 64)
        self.assertTrue(verify_hash(sample, h))
        self.assertEqual(hash_audio(sample), h)

    def test_verify_chain_and_event(self):
        chain = AuditHashChain()
        e1 = chain.append_event(session_id="s1", event_type=EventType.SESSION_START)
        e2 = chain.append_event(session_id="s1", event_type=EventType.AUDIO_INGESTED, audio_hash="a" * 64)

        # Standalone verify_event
        self.assertTrue(verify_event(e1))
        self.assertTrue(verify_event(e2))

        # Standalone verify_chain
        report = verify_chain(chain)
        self.assertTrue(report.is_valid)
        self.assertIsNone(detect_tampering(chain))

        # Malicious modification
        chain.tamper_for_testing(0, "payload", {"altered": True})
        tamper_msg = detect_tampering(chain)
        self.assertIsNotNone(tamper_msg)
        self.assertIn("payload or metadata was altered", tamper_msg)


if __name__ == "__main__":
    unittest.main()
