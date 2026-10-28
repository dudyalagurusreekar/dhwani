"""
Unit tests for Dhwani AuditHashChain and tamper detection engine.
"""

import tempfile
import unittest
from pathlib import Path

from security.audit_chain import AuditHashChain, GENESIS_PREV_HASH
from security.schemas import EventType, TamperType


class TestAuditHashChain(unittest.TestCase):

    def test_empty_chain_is_valid(self):
        chain = AuditHashChain()
        report = chain.verify_integrity()
        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_events, 0)
        self.assertEqual(report.tamper_type, TamperType.NONE)

    def test_append_events_and_verify_validity(self):
        chain = AuditHashChain()
        e0 = chain.append_event(
            session_id="sess_1",
            event_type=EventType.SESSION_START,
            payload={"client": "web"},
        )
        self.assertEqual(e0.seq_num, 0)
        self.assertEqual(e0.prev_hash, GENESIS_PREV_HASH)
        self.assertEqual(len(e0.chain_hash), 64)

        e1 = chain.append_event(
            session_id="sess_1",
            event_type=EventType.AUDIO_INGESTED,
            audio_hash="a" * 64,
            payload={"duration_sec": 2.5},
        )
        self.assertEqual(e1.seq_num, 1)
        self.assertEqual(e1.prev_hash, e0.chain_hash)

        e2 = chain.append_event(
            session_id="sess_1",
            event_type=EventType.AI_INFERENCE_COMPLETED,
            audio_hash="a" * 64,
            payload={"score": 0.05},
        )
        self.assertEqual(e2.seq_num, 2)
        self.assertEqual(e2.prev_hash, e1.chain_hash)

        report = chain.verify_integrity()
        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_events, 3)
        self.assertEqual(report.tamper_type, TamperType.NONE)

    def test_persistence_and_reload(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            temp_path = f.name

        try:
            # Create chain with persistence
            chain1 = AuditHashChain(persistence_file=temp_path)
            chain1.append_event(session_id="sess_p", event_type=EventType.SESSION_START)
            chain1.append_event(session_id="sess_p", event_type=EventType.AUDIO_INGESTED, audio_hash="b" * 64)
            self.assertEqual(chain1.length, 2)

            # Reload into a new chain instance
            chain2 = AuditHashChain(persistence_file=temp_path)
            self.assertEqual(chain2.length, 2)
            report = chain2.verify_integrity()
            self.assertTrue(report.is_valid)
            self.assertEqual(chain1.latest_hash, chain2.latest_hash)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_tamper_detection_payload_altered(self):
        chain = AuditHashChain()
        for i in range(5):
            chain.append_event(
                session_id="sess_t",
                event_type=EventType.AI_INFERENCE_COMPLETED,
                payload={"ai_score": 0.95 if i == 2 else 0.05},
            )

        # Confirm valid before tampering
        self.assertTrue(chain.verify_integrity().is_valid)

        # Malicious actor changes Event #2 deepfake score from 0.95 to 0.01
        chain.tamper_for_testing(seq_num=2, field_name="payload", new_value={"ai_score": 0.01})

        report = chain.verify_integrity()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.tampered_event_seq, 2)
        self.assertEqual(report.tamper_type, TamperType.PAYLOAD_ALTERED)
        self.assertIn("payload or metadata was altered", report.error_reason)

    def test_tamper_detection_chain_broken(self):
        chain = AuditHashChain()
        for i in range(4):
            chain.append_event(
                session_id="sess_b",
                event_type=EventType.AUDIO_INGESTED,
                audio_hash=f"{i:064d}",
            )

        # Alter prev_hash pointer of Event #3
        chain.tamper_for_testing(seq_num=3, field_name="prev_hash", new_value="f" * 64)

        report = chain.verify_integrity()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.tampered_event_seq, 3)
        # Because prev_hash changed, the recomputed chain_hash won't match, flagging alteration
        self.assertIn(report.tamper_type, [TamperType.PAYLOAD_ALTERED, TamperType.CHAIN_BROKEN])

    def test_tamper_detection_genesis_invalid(self):
        chain = AuditHashChain()
        chain.append_event(session_id="sess_g", event_type=EventType.SESSION_START)

        # Invalidate genesis prev_hash
        chain.tamper_for_testing(seq_num=0, field_name="prev_hash", new_value="1" * 64)

        report = chain.verify_integrity()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.tampered_event_seq, 0)
        self.assertEqual(report.tamper_type, TamperType.GENESIS_INVALID)


if __name__ == "__main__":
    unittest.main()
