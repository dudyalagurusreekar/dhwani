"""
Unit tests for cybersecurity/audit_verification (Module 2).
Validates Ed25519 digital signatures, checkpoints, and recalculation attack detection.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cybersecurity.audit_verification.checkpoint import (
    AuditCheckpoint,
    create_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from cybersecurity.audit_verification.signatures import (
    AuditSignatureVerifier,
    AuditSigner,
    export_private_key_pem,
    export_public_key_pem,
    generate_keypair,
    load_private_key_pem,
    load_public_key_pem,
    sign_data,
    verify_signature,
)
from cybersecurity.audit_verification.verify_signature import (
    detect_chain_recalculation_attack,
    verify_checkpoint_integrity,
)
from security.hash_chain import HashChain


class TestAuditVerification(unittest.TestCase):

    def setUp(self):
        self.private_key, self.public_key = generate_keypair()
        self.signer = AuditSigner(private_key=self.private_key, signer_id="test-signer-01")
        self.verifier = AuditSignatureVerifier(public_key=self.public_key)

    def test_keypair_pem_export_and_load(self):
        priv_pem = export_private_key_pem(self.private_key)
        pub_pem = export_public_key_pem(self.public_key)

        self.assertIn("BEGIN PRIVATE KEY", priv_pem)
        self.assertIn("BEGIN PUBLIC KEY", pub_pem)

        reloaded_priv = load_private_key_pem(priv_pem)
        reloaded_pub = load_public_key_pem(pub_pem)

        test_data = "test_audit_message_2026"
        sig = sign_data(reloaded_priv, test_data)
        self.assertTrue(verify_signature(reloaded_pub, sig, test_data))

    def test_signature_verification_failure_on_corrupted_data(self):
        data = "chain_head_hash_abcdef123456"
        signature = sign_data(self.private_key, data)

        # Valid verification
        self.assertTrue(verify_signature(self.public_key, signature, data))

        # Corrupted data verification fails
        self.assertFalse(verify_signature(self.public_key, signature, data + "_corrupted"))

        # Corrupted signature verification fails
        corrupted_sig = ("00" if signature[:2] != "00" else "ff") + signature[2:]
        self.assertFalse(verify_signature(self.public_key, corrupted_sig, data))

    def test_checkpoint_creation_and_serialization(self):
        chain = HashChain()
        chain.add_event(
            session_id="session_chk_1",
            event_type="CALL_STARTED",
            risk_score=0,
            model_version="v1",
            audio_hash="a" * 64,
        )

        checkpoint = create_checkpoint(chain, self.signer)
        self.assertEqual(checkpoint.chain_length, 1)
        self.assertEqual(checkpoint.latest_hash, chain.get_last_hash())
        self.assertEqual(checkpoint.signer_id, "test-signer-01")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "checkpoint.json"
            save_checkpoint(checkpoint, file_path)
            loaded = load_checkpoint(file_path)

            self.assertEqual(loaded.checkpoint_id, checkpoint.checkpoint_id)
            self.assertEqual(loaded.latest_hash, checkpoint.latest_hash)
            self.assertEqual(loaded.signature, checkpoint.signature)

    def test_checkpoint_integrity_verification_untampered(self):
        chain = HashChain()
        chain.add_event(
            session_id="session_chk_2",
            event_type="CALL_STARTED",
            risk_score=0,
            model_version="v1",
            audio_hash="1" * 64,
        )
        chain.add_event(
            session_id="session_chk_2",
            event_type="SUSPICIOUS_VOICE",
            risk_score=78,
            model_version="v1",
            audio_hash="2" * 64,
        )

        checkpoint = create_checkpoint(chain, self.signer)
        result = verify_checkpoint_integrity(checkpoint, chain)

        self.assertTrue(result.is_valid)
        self.assertTrue(result.signature_valid)
        self.assertTrue(result.chain_matches_checkpoint)
        self.assertIsNone(result.tamper_type)

    def test_detect_chain_recalculation_attack(self):
        """
        Adversary Scenario:
        An attacker hacks into the audit database, modifies Event 2's risk_score from 85 to 10,
        and recomputes the SHA-256 hash chain so that internal links appear mathematically valid.
        However, the signed checkpoint holds the genuine private-key signed tip hash.
        """
        chain = HashChain()
        chain.add_event("sess_attack", "CALL_STARTED", 0, "v1", "a" * 64)
        chain.add_event("sess_attack", "SUSPICIOUS_VOICE", 85, "v1", "b" * 64)
        chain.add_event("sess_attack", "HIGH_RISK_ALERT", 95, "v1", "c" * 64)

        # Honest checkpoint is generated and signed
        honest_checkpoint = create_checkpoint(chain, self.signer)

        # Attacker tampers with event 1 (index 1) and recalculates the subsequent hashes
        chain.tamper_event(1, "risk_score", 10)
        # Recalculate chain to fix the simple hash linkage
        from security.hashing import hash_data
        for i in range(1, len(chain.chain)):
            prev_h = chain.chain[i - 1]["event_hash"]
            chain.chain[i]["previous_event_hash"] = prev_h
            payload = chain.chain[i].copy()
            payload.pop("event_hash", None)
            chain.chain[i]["event_hash"] = hash_data(str(payload).encode("utf-8"))

        # Verification against checkpoint must catch the recalculation attack
        is_attack, explanation = detect_chain_recalculation_attack(chain, honest_checkpoint)
        self.assertTrue(is_attack)
        self.assertIn("recalculation attack", explanation.lower())

    def test_detect_forged_checkpoint_signature(self):
        chain = HashChain()
        chain.add_event("sess_chk_3", "CALL_STARTED", 0, "v1", "d" * 64)
        checkpoint = create_checkpoint(chain, self.signer)

        # Attacker tries to alter the checkpoint hash
        checkpoint.latest_hash = "f" * 64
        result = verify_checkpoint_integrity(checkpoint, chain)

        self.assertFalse(result.is_valid)
        self.assertFalse(result.signature_valid)
        self.assertEqual(result.tamper_type, "SIGNATURE_FORGERY")

    def test_detect_chain_truncation_attack(self):
        chain = HashChain()
        chain.add_event("sess_chk_4", "CALL_STARTED", 0, "v1", "e" * 64)
        chain.add_event("sess_chk_4", "SUSPICIOUS_VOICE", 80, "v1", "f" * 64)

        checkpoint = create_checkpoint(chain, self.signer)

        # Truncate chain by popping the last event
        chain.chain.pop()

        result = verify_checkpoint_integrity(checkpoint, chain)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.tamper_type, "CHAIN_TRUNCATION")


if __name__ == "__main__":
    unittest.main()
