"""
Unit tests for security/hash_chain.py (Member 3).
"""

import tempfile
import unittest
from pathlib import Path

from security.hash_chain import GENESIS_HASH, HashChain


class TestHashChain(unittest.TestCase):

    def test_hash_chain_sequential_linking(self):
        """
        Verify the exact scenario from specification:
        EVENT 1: Call started -> Hash 1
        EVENT 2: Suspicious voice detected + Hash 1 -> Hash 2
        EVENT 3: High-risk alert generated + Hash 2 -> Hash 3
        """
        chain = HashChain()

        # Event 1: Call started
        e1 = chain.add_event(
            session_id="session_001",
            event_type="CALL_STARTED",
            risk_score=0,
            model_version="w2v2-aasist-v1",
            audio_hash="a" * 64,
        )
        self.assertEqual(e1["previous_event_hash"], GENESIS_HASH)
        self.assertEqual(len(e1["event_hash"]), 64)

        # Event 2: Suspicious voice detected
        e2 = chain.add_event(
            session_id="session_001",
            event_type="SUSPICIOUS_VOICE",
            risk_score=82,
            model_version="w2v2-aasist-v1",
            audio_hash="b" * 64,
        )
        self.assertEqual(e2["previous_event_hash"], e1["event_hash"])
        self.assertEqual(len(e2["event_hash"]), 64)

        # Event 3: High-risk alert generated
        e3 = chain.add_event(
            session_id="session_001",
            event_type="ALERT_GENERATED",
            risk_score=95,
            model_version="w2v2-aasist-v1",
            audio_hash="c" * 64,
        )
        self.assertEqual(e3["previous_event_hash"], e2["event_hash"])
        self.assertEqual(len(e3["event_hash"]), 64)

        self.assertEqual(chain.length, 3)

    def test_hash_chain_save_and_load(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            chain = HashChain(storage_file=temp_path)
            chain.add_event("sess_1", "CALL_STARTED", 10, "v1", "hash1")
            chain.add_event("sess_1", "SUSPICIOUS_VOICE", 85, "v1", "hash2")

            # Load into new instance
            loaded_chain = HashChain(storage_file=temp_path)
            self.assertEqual(loaded_chain.length, 2)
            self.assertEqual(loaded_chain.get_last_hash(), chain.get_last_hash())
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
