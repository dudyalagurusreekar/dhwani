"""
Integration test suite for Dhwani Cybersecurity Architecture.
Tests the FastAPI backend endpoints for API Security, Digital Signatures, and Audio Privacy.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from cybersecurity.api_security.authorization import Role, Permission
from cybersecurity.audio_privacy.retention import get_retention_manager, RetentionPolicy


class TestCybersecurityIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_token_issuance_endpoint(self):
        resp = self.client.post(
            "/api/security/token",
            json={"subject": "test_analyst_01", "role": "analyst", "scopes": ["audit:read"]},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "analyst")
        self.assertEqual(data["subject"], "test_analyst_01")

    def test_validator_public_key_endpoint(self):
        resp = self.client.get("/api/security/validator/public-key")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["algorithm"], "Ed25519")
        self.assertIn("BEGIN PUBLIC KEY", data["public_key_pem"])
        self.assertEqual(len(data["public_key_hex"]), 64)

    def test_checkpoint_signing_and_verification_flow(self):
        # 1. Issue an AUDITOR token
        token_resp = self.client.post(
            "/api/security/token",
            json={"subject": "auditor_node", "role": "auditor"},
        )
        auditor_token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {auditor_token}"}

        # 2. Add an event to ensure the chain has records
        from security import get_global_pipeline
        pipeline = get_global_pipeline()
        pipeline.chain.add_event(
            session_id="test_chk_flow",
            event_type="CALL_STARTED",
            risk_score=0,
            model_version="test-v1",
            audio_hash="1" * 64,
        )

        # 3. Sign checkpoint
        sign_resp = self.client.post("/api/security/checkpoint/sign", headers=headers)
        self.assertEqual(sign_resp.status_code, 200)
        checkpoint = sign_resp.json()
        self.assertIn("signature", checkpoint)
        self.assertEqual(len(checkpoint["signature"]), 128)

        # 4. Verify checkpoint
        verify_resp = self.client.post(
            "/api/security/checkpoint/verify",
            json={"checkpoint": checkpoint},
        )
        self.assertEqual(verify_resp.status_code, 200)
        verify_data = verify_resp.json()
        self.assertTrue(verify_data["is_valid"])
        self.assertTrue(verify_data["signature_valid"])
        self.assertTrue(verify_data["chain_matches_checkpoint"])

    def test_checkpoint_signing_rejected_for_client_role(self):
        # Client lacks AUDITOR or ADMIN role
        token_resp = self.client.post(
            "/api/security/token",
            json={"subject": "mobile_app", "role": "client"},
        )
        client_token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {client_token}"}

        sign_resp = self.client.post("/api/security/checkpoint/sign", headers=headers)
        self.assertEqual(sign_resp.status_code, 403)
        self.assertIn("Forbidden", sign_resp.json()["detail"])

    def test_recalculation_attack_detected_via_api(self):
        token_resp = self.client.post(
            "/api/security/token",
            json={"subject": "auditor_node", "role": "auditor"},
        )
        headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

        # Sign legitimate checkpoint
        sign_resp = self.client.post("/api/security/checkpoint/sign", headers=headers)
        checkpoint = sign_resp.json()

        # Attacker tampers with the latest_hash
        checkpoint["latest_hash"] = "9" * 64

        verify_resp = self.client.post(
            "/api/security/checkpoint/verify",
            json={"checkpoint": checkpoint},
        )
        self.assertEqual(verify_resp.status_code, 409)
        verify_data = verify_resp.json()
        self.assertFalse(verify_data["is_valid"])
        self.assertEqual(verify_data["tamper_type"], "SIGNATURE_FORGERY")

    def test_audio_retention_and_controlled_decryption_api(self):
        # Store audio under standard retention
        sample_pcm = b"SECURE_WAVE_AUDIO_BYTES_FOR_FORENSICS_12345"
        mgr = get_retention_manager()
        meta = mgr.handle_audio(
            session_id="session_api_ret",
            audio_bytes=sample_pcm,
            policy=RetentionPolicy.STANDARD_HOLD_24H,
        )

        # 1. Unauthorized attempt (client role) fails with 403
        client_token = self.client.post(
            "/api/security/token",
            json={"subject": "unauth_actor", "role": "client"},
        ).json()["access_token"]

        fail_resp = self.client.post(
            "/api/security/audio/decrypt",
            headers={"Authorization": f"Bearer {client_token}"},
            json={"record_id": meta.record_id, "justification": "Curiosity"},
        )
        self.assertEqual(fail_resp.status_code, 403)

        # 2. Authorized attempt (admin role) succeeds with 200
        admin_token = self.client.post(
            "/api/security/token",
            json={"subject": "sec_admin", "role": "admin"},
        ).json()["access_token"]

        ok_resp = self.client.post(
            "/api/security/audio/decrypt",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"record_id": meta.record_id, "justification": "Forensic warrant #782"},
        )
        self.assertEqual(ok_resp.status_code, 200)
        res = ok_resp.json()
        self.assertEqual(bytes.fromhex(res["audio_hex"]), sample_pcm)


if __name__ == "__main__":
    unittest.main()
