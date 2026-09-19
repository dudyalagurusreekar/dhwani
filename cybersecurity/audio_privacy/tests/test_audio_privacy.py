"""
Unit tests for cybersecurity/audio_privacy (Module 3).
Validates Fernet audio encryption, zero-retention defaults, TTL expiration purging,
and audited access controls.
"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cybersecurity.api_security.authorization import Permission, Role
from cybersecurity.audio_privacy.access_control import (
    AccessDeniedError,
    AudioAccessGate,
)
from cybersecurity.audio_privacy.encryption import (
    AudioVault,
    decrypt_audio,
    encrypt_audio,
    generate_encryption_key,
    secure_wipe_buffer,
)
from cybersecurity.audio_privacy.retention import (
    RetentionManager,
    RetentionPolicy,
)
from security.hash_chain import HashChain


class TestAudioPrivacy(unittest.TestCase):

    def setUp(self):
        self.sample_audio = b"RIFF....WAVEfmt ....data" + b"\x12\x34\x56\x78" * 128

    def test_audio_encryption_and_decryption_roundtrip(self):
        key = generate_encryption_key()
        ciphertext, used_key = encrypt_audio(self.sample_audio, key)

        self.assertEqual(key, used_key)
        self.assertNotEqual(ciphertext, self.sample_audio)

        decrypted = decrypt_audio(ciphertext, key)
        self.assertEqual(decrypted, self.sample_audio)

    def test_decryption_fails_with_wrong_key(self):
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        ciphertext, _ = encrypt_audio(self.sample_audio, key1)
        with self.assertRaises(ValueError):
            decrypt_audio(ciphertext, key2)

    def test_decryption_fails_with_tampered_ciphertext(self):
        key = generate_encryption_key()
        ciphertext, _ = encrypt_audio(self.sample_audio, key)

        # Mutate ciphertext payload
        tampered = bytearray(ciphertext)
        tampered[-5] ^= 0xFF

        with self.assertRaises(ValueError):
            decrypt_audio(bytes(tampered), key)

    def test_secure_wipe_buffer(self):
        buffer = bytearray(b"secret_voice_stream_data_in_ram")
        self.assertNotEqual(set(buffer), {0})

        secure_wipe_buffer(buffer)
        self.assertEqual(set(buffer), {0})
        self.assertEqual(len(buffer), len(b"secret_voice_stream_data_in_ram"))

    def test_zero_retention_policy_creates_no_disk_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RetentionManager(storage_dir=tmpdir)
            meta = mgr.handle_audio(
                session_id="session_zero_01",
                audio_bytes=self.sample_audio,
                policy=RetentionPolicy.ZERO_RETENTION,
            )

            self.assertTrue(meta.is_purged)
            self.assertIsNone(meta.storage_path)
            self.assertEqual(len(meta.audio_hash), 64)
            # Verify no files were created in storage directory
            self.assertEqual(len(list(Path(tmpdir).glob("*"))), 0)

    def test_ephemeral_retention_and_expiration_purge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RetentionManager(storage_dir=tmpdir)
            # Retain with short custom TTL (1.0s)
            meta = mgr.handle_audio(
                session_id="session_ret_01",
                audio_bytes=self.sample_audio,
                policy=RetentionPolicy.CUSTOM,
                custom_ttl_seconds=1.0,
            )

            self.assertFalse(meta.is_purged)
            self.assertIsNotNone(meta.storage_path)
            self.assertTrue(Path(meta.storage_path).exists())

            # Immediate purge check (should not purge yet)
            purged_early = mgr.purge_expired_records(current_time=time.time())
            self.assertEqual(len(purged_early), 0)
            self.assertTrue(Path(meta.storage_path).exists())

            # Simulate passage of 2 seconds
            future_time = time.time() + 2.0
            purged_ids = mgr.purge_expired_records(current_time=future_time)

            self.assertIn(meta.record_id, purged_ids)
            self.assertTrue(meta.is_purged)
            self.assertIsNone(meta.storage_path)
            # Verify file was shredded and removed from disk
            self.assertEqual(len(list(Path(tmpdir).glob("*.enc"))), 0)
            # Verify non-PII audio hash is STILL preserved
            self.assertEqual(len(meta.audio_hash), 64)

    def test_access_control_denied_without_permission(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RetentionManager(storage_dir=tmpdir)
            meta = mgr.handle_audio(
                session_id="sess_gate_1",
                audio_bytes=self.sample_audio,
                policy=RetentionPolicy.STANDARD_HOLD_24H,
            )

            gate = AudioAccessGate(retention_manager=mgr)
            unauthorized_user = {"sub": "client_app", "role": Role.CLIENT.value, "scopes": []}

            with self.assertRaises(AccessDeniedError):
                gate.request_audio_decryption(
                    record_id=meta.record_id,
                    user=unauthorized_user,
                    justification="Legal audit check",
                )

            logs = gate.get_access_logs(meta.record_id)
            self.assertEqual(len(logs), 1)
            self.assertFalse(logs[0].success)
            self.assertEqual(logs[0].accessor_id, "client_app")

    def test_access_control_granted_and_logged_to_hash_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = RetentionManager(storage_dir=tmpdir)
            meta = mgr.handle_audio(
                session_id="sess_gate_2",
                audio_bytes=self.sample_audio,
                policy=RetentionPolicy.STANDARD_HOLD_24H,
            )

            chain = HashChain()
            gate = AudioAccessGate(retention_manager=mgr, audit_chain=chain)

            authorized_user = {
                "sub": "auditor_jones",
                "role": Role.AUDITOR.value,
                "scopes": [Permission.AUDIO_DECRYPT.value],
            }

            decrypted = gate.request_audio_decryption(
                record_id=meta.record_id,
                user=authorized_user,
                justification="Subpoena order 4482-B",
            )

            self.assertEqual(decrypted, self.sample_audio)

            logs = gate.get_access_logs(meta.record_id)
            self.assertEqual(len(logs), 1)
            self.assertTrue(logs[0].success)
            self.assertEqual(logs[0].action, "DECRYPT_SUCCESS")

            # Verify security event was automatically appended to Dhwani Hash Chain
            self.assertEqual(chain.length, 1)
            event = chain.chain[0]
            self.assertEqual(event["event_type"], "AUDIO_RECORDING_ACCESSED")
            self.assertEqual(event["session_id"], "sess_gate_2")
            self.assertEqual(event["audio_hash"], meta.audio_hash)


if __name__ == "__main__":
    unittest.main()
