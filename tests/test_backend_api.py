"""
Integration tests for EchoShield AI FastAPI backend and Member 3 Security/Audit endpoints.
"""

import sys
import unittest
from pathlib import Path

# Ensure paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from security import get_global_pipeline


class TestBackendAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.pipeline = get_global_pipeline()

    def test_health_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_analyze_endpoint_with_provenance(self):
        audio_content = b"RIFF_MOCK_PCM_WAVEFORM_SAMPLE_BYTES"
        files = {"file": ("test_voice.wav", audio_content, "audio/wav")}
        headers = {"X-Session-ID": "test_session_api_01"}

        res = self.client.post("/api/analyze", files=files, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Check detection results
        self.assertIn("fake_probability", data)
        self.assertIn("risk_score", data)
        self.assertIn("status", data)

        # Check cryptographic provenance fields
        self.assertIn("provenance", data)
        prov = data["provenance"]
        self.assertEqual(len(prov["audio_hash"]), 64)
        self.assertEqual(len(prov["provenance_token"]), 64)
        self.assertEqual(len(prov["chain_hash"]), 64)
        self.assertIsInstance(prov["event_seq"], int)

    def test_analyze_empty_file_fails(self):
        files = {"file": ("empty.wav", b"", "audio/wav")}
        res = self.client.post("/api/analyze", files=files)
        self.assertEqual(res.status_code, 400)

    def test_audit_verify_endpoint(self):
        res = self.client.get("/api/audit/verify")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_valid"])
        self.assertGreaterEqual(data["total_events"], 1)
        self.assertEqual(data["tamper_type"], "NONE")

    def test_audit_trail_endpoint(self):
        res = self.client.get("/api/audit/trail")
        self.assertEqual(res.status_code, 200)
        events = res.json()
        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 1)

    def test_audit_latest_hash_endpoint(self):
        res = self.client.get("/api/audit/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("length", data)
        self.assertEqual(len(data["latest_hash"]), 64)

    def test_audit_certificate_endpoint(self):
        res = self.client.get("/api/audit/certificate")
        self.assertEqual(res.status_code, 200)
        cert = res.json()
        self.assertTrue(cert["is_valid"])
        self.assertIn("ledger_root_digest", cert)
        self.assertEqual(len(cert["ledger_root_digest"]), 64)
        self.assertIn("certified_at", cert)

    def test_session_audit_summary_endpoint(self):
        session_id = "test_session_api_01"
        res = self.client.get(f"/api/audit/session/{session_id}/summary")
        self.assertEqual(res.status_code, 200)
        summary = res.json()
        self.assertTrue(summary["found"])
        self.assertEqual(summary["session_id"], session_id)
        self.assertGreaterEqual(summary["total_events"], 1)

    def test_session_audit_summary_not_found(self):
        res = self.client.get("/api/audit/session/non_existent_session_999/summary")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
