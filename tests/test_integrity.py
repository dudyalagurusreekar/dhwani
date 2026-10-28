"""
Unit tests for security/integrity.py (Member 3).
Verifies that any unauthorized modification to security events or hash chain links is detected.
"""

import unittest

from security.event_schema import create_security_event, validate_security_event
from security.hash_chain import HashChain, GENESIS_HASH
from security.integrity import detect_tampering, verify_event, verify_hash_chain


class TestIntegrityVerification(unittest.TestCase):

    def setUp(self):
        self.chain = HashChain()
        # Event 1: Call started
        self.chain.add_event(
            session_id="session_001",
            event_type="CALL_STARTED",
            risk_score=0,
            model_version="w2v2-aasist-v1",
            audio_hash="1111" * 16,
        )
        # Event 2: Suspicious voice detected
        self.chain.add_event(
            session_id="session_001",
            event_type="SUSPICIOUS_VOICE",
            risk_score=82,
            model_version="w2v2-aasist-v1",
            audio_hash="2222" * 16,
        )
        # Event 3: High-risk alert generated
        self.chain.add_event(
            session_id="session_001",
            event_type="ALERT_GENERATED",
            risk_score=95,
            model_version="w2v2-aasist-v1",
            audio_hash="3333" * 16,
        )

    def test_untampered_chain_is_valid(self):
        """Verify that an untouched chain passes verification."""
        is_valid, msg = verify_hash_chain(self.chain)
        self.assertTrue(is_valid)
        self.assertIn("3 events verified successfully", msg)

        report = detect_tampering(self.chain)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["is_valid"])

    def test_detect_modified_risk_score(self):
        """
        Scenario: An attacker modifies Event 2 risk_score from 82 to 10
        to cover up a detected deepfake.
        """
        self.chain.tamper_event(1, "risk_score", 10)

        is_valid, msg = verify_hash_chain(self.chain)
        self.assertFalse(is_valid)
        self.assertIn("Tamper detected", msg)
        self.assertIn("index 1", msg)

        report = detect_tampering(self.chain)
        self.assertEqual(report["status"], "FAIL_TAMPER_DETECTED")

    def test_detect_modified_audio_hash(self):
        """
        Scenario: Someone alters the recorded audio hash in Event 1.
        """
        self.chain.tamper_event(0, "audio_hash", "9999" * 16)

        is_valid, msg = verify_hash_chain(self.chain)
        self.assertFalse(is_valid)
        self.assertIn("Tamper detected", msg)
        self.assertIn("index 0", msg)

    def test_detect_broken_chain_pointer(self):
        """
        Scenario: An attacker changes previous_event_hash in Event 3.
        """
        self.chain.tamper_event(2, "previous_event_hash", "0000" * 16)

        is_valid, msg = verify_hash_chain(self.chain)
        self.assertFalse(is_valid)
        self.assertIn("Tamper detected", msg)

    def test_detect_deleted_intermediate_event(self):
        """
        Scenario: An attacker deletes Event 2 (SUSPICIOUS_VOICE).
        The chain pointer between Event 1 and Event 3 will break.
        """
        # Delete Event 2
        del self.chain.chain[1]

        is_valid, msg = verify_hash_chain(self.chain)
        self.assertFalse(is_valid)
        self.assertIn("Broken chain", msg)

    def test_verify_single_event(self):
        event = create_security_event(
            session_id="test_sess",
            event_type="SUSPICIOUS_VOICE",
            risk_score=75,
            model_version="v1",
            audio_hash="abcd" * 16,
            previous_event_hash=GENESIS_HASH,
        )
        self.assertTrue(verify_event(event))

        # Tamper with event
        event["risk_score"] = 5
        self.assertFalse(verify_event(event))


if __name__ == "__main__":
    unittest.main()
