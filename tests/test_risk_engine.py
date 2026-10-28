"""
Unit tests for Dhwani Risk Engine.
"""

import unittest

from security.risk_engine import RiskEngine, RiskThresholds
from security.schemas import RiskAction, RiskLevel


class TestRiskEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RiskEngine(
            thresholds=RiskThresholds(low_cutoff=0.30, medium_cutoff=0.60, high_cutoff=0.85),
            max_consecutive_high_before_block=2,
            min_reliable_duration_sec=0.5,
        )

    def test_threshold_classification(self):
        # Low risk -> ALLOW
        res_low = self.engine.evaluate(ai_score=0.15, confidence=0.98)
        self.assertEqual(res_low.level, RiskLevel.LOW)
        self.assertEqual(res_low.action, RiskAction.ALLOW)

        # Medium risk -> MONITOR
        res_med = self.engine.evaluate(ai_score=0.45, confidence=0.95)
        self.assertEqual(res_med.level, RiskLevel.MEDIUM)
        self.assertEqual(res_med.action, RiskAction.MONITOR)

        # High risk -> FLAG
        res_high = self.engine.evaluate(ai_score=0.72, confidence=0.92)
        self.assertEqual(res_high.level, RiskLevel.HIGH)
        self.assertEqual(res_high.action, RiskAction.FLAG)

        # Critical risk -> BLOCK
        res_crit = self.engine.evaluate(ai_score=0.95, confidence=0.99)
        self.assertEqual(res_crit.level, RiskLevel.CRITICAL)
        self.assertEqual(res_crit.action, RiskAction.BLOCK)

    def test_short_duration_confidence_penalty(self):
        res = self.engine.evaluate(
            ai_score=0.20,
            confidence=0.90,
            audio_metadata={"duration_sec": 0.2},  # Under 0.5s threshold
        )
        self.assertTrue(res.factors.get("short_duration_flag"))
        # Confidence should be scaled by 0.7
        self.assertAlmostEqual(res.confidence, 0.90 * 0.7, places=4)

    def test_stateful_session_escalation(self):
        session_id = "sess_attack_flow"

        # 1st high score -> FLAG
        r1 = self.engine.evaluate(ai_score=0.75, session_id=session_id)
        self.assertEqual(r1.level, RiskLevel.HIGH)
        self.assertEqual(r1.action, RiskAction.FLAG)

        # 2nd consecutive high score -> Escalation to BLOCK
        r2 = self.engine.evaluate(ai_score=0.78, session_id=session_id)
        self.assertEqual(r2.level, RiskLevel.CRITICAL)
        self.assertEqual(r2.action, RiskAction.BLOCK)
        self.assertTrue(any("Repeated high spoof scores" in r for r in r2.reasons))

    def test_session_reset(self):
        session_id = "sess_to_reset"
        self.engine.evaluate(ai_score=0.80, session_id=session_id)
        self.assertIsNotNone(self.engine.get_session_context(session_id))

        self.engine.reset_session(session_id)
        self.assertIsNone(self.engine.get_session_context(session_id))


if __name__ == "__main__":
    unittest.main()
