"""
Automated Tests for Dhwani REST API & Webhooks
Validates:
1. GET /health
2. GET /api/system/status (GPU, CPU, active models)
3. GET /api/incidents & chain verification
4. POST /twilio/voice (Inbound TwiML webhook XML response)
5. POST /api/analyze/upload (File upload with real_speech.wav)
"""

from pathlib import Path
import unittest
from fastapi.testclient import TestClient

from backend.main import app


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.wav_path = Path("real_speech.wav").resolve()

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")

    def test_system_status(self):
        resp = self.client.get("/api/system/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "OPERATIONAL")
        self.assertIn("gpu", data)
        self.assertIn("system", data)
        self.assertIn("active_models", data)

    def test_incidents_listing(self):
        resp = self.client.get("/api/incidents")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("count", data)
        self.assertIn("chain_intact", data)
        self.assertTrue(data["chain_intact"])

    def test_twilio_voice_webhook(self):
        resp = self.client.post(
            "/twilio/voice",
            data={
                "CallSid": "CA9988776655",
                "From": "+14155552671",
                "To": "+18005550199",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/xml")
        xml_content = resp.text
        self.assertIn("<Response>", xml_content)
        self.assertIn("<Stream", xml_content)
        self.assertIn("/twilio/media", xml_content)

    def test_analyze_upload(self):
        self.assertTrue(self.wav_path.exists())
        with open(self.wav_path, "rb") as f:
            resp = self.client.post(
                "/api/analyze/upload",
                files={"file": ("real_speech.wav", f, "audio/wav")},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("analysis_id", data)
        self.assertEqual(data["source_type"], "file")
        self.assertGreater(data["windows_analyzed"], 0)
        self.assertIn("risk_score", data)
        self.assertIn("evidence_hash", data)


if __name__ == "__main__":
    unittest.main()
