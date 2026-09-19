"""
Unit tests for the end-to-end 7-stage DhwaniProvenancePipeline.
"""

import unittest

from security.pipeline import DhwaniProvenancePipeline
from security.schemas import RiskAction, RiskLevel


class TestDhwaniPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = DhwaniProvenancePipeline()

    def test_full_7_stage_pipeline_execution(self):
        audio_chunk = b"WAVEFORM_SAMPLES_FRAME_001"
        session_id = "test_call_100"

        # AI detector stub returning genuine voice score
        def ai_detector(buf: bytes):
            return 0.12, 0.96

        result = self.pipeline.process_audio(
            audio_data=audio_chunk,
            session_id=session_id,
            ai_detector=ai_detector,
            audio_metadata={"duration_sec": 1.5, "model_name": "AASIST"},
            session_metadata={"caller": "+919876543210"},
        )

        # Stage 2 check: SHA-256 hashing
        self.assertEqual(len(result.audio_hash), 64)
        self.assertEqual(len(result.provenance_token), 64)

        # Stage 3 check: AI detection
        self.assertAlmostEqual(result.ai_score, 0.12)
        self.assertAlmostEqual(result.confidence, 0.96)

        # Stage 4 check: Risk Engine
        self.assertEqual(result.risk_assessment.level, RiskLevel.LOW)
        self.assertEqual(result.risk_assessment.action, RiskAction.ALLOW)

        # Stage 5 & 6 check: Security Event & Hash Chain
        self.assertEqual(result.chain_length, 1)
        self.assertEqual(result.security_event.seq_num, 0)
        self.assertEqual(len(result.chain_hash), 64)

        # Stage 7 check: Integrity verification
        self.assertTrue(result.is_chain_valid)

    def test_sequential_chunks_in_session(self):
        session_id = "test_call_200"

        # Chunk 1: Low risk
        r1 = self.pipeline.process_audio(
            audio_data=b"CHUNK_1",
            session_id=session_id,
            ai_detector=lambda b: (0.10, 0.95),
        )
        self.assertEqual(r1.risk_assessment.level, RiskLevel.LOW)
        self.assertEqual(r1.security_event.seq_num, 0)

        # Chunk 2: High risk spoof injected
        r2 = self.pipeline.process_audio(
            audio_data=b"CHUNK_2_SPOOFED",
            session_id=session_id,
            ai_detector=lambda b: (0.88, 0.99),
        )
        self.assertEqual(r2.risk_assessment.level, RiskLevel.CRITICAL)
        self.assertEqual(r2.risk_assessment.action, RiskAction.BLOCK)
        self.assertEqual(r2.security_event.seq_num, 1)
        self.assertEqual(r2.security_event.prev_hash, r1.chain_hash)

        # Entire chain must remain valid
        report = self.pipeline.verify_chain()
        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_events, 2)


if __name__ == "__main__":
    unittest.main()
