"""
Unit tests for Dhwani EphemeralAudioBuffer and zero raw audio retention.
"""

import unittest

from security.hasher import AudioHasher
from security.privacy import (
    BufferPurgedError,
    EphemeralAudioBuffer,
    ephemeral_audio_context,
)
from security.schemas import EventType, SecurityEvent


class TestPrivacySandbox(unittest.TestCase):

    def test_ephemeral_buffer_lifecycle_and_purge(self):
        raw_audio = b"BIOMETRIC_SENSITIVE_VOICE_DATA_12345"
        expected_hash = AudioHasher.hash_bytes(raw_audio)

        buf = EphemeralAudioBuffer(raw_audio, session_id="call_test")
        self.assertEqual(buf.audio_hash, expected_hash)
        self.assertFalse(buf.is_purged)

        # Buffer accessible before purge
        self.assertEqual(buf.get_buffer(), raw_audio)

        # Explicit purge
        buf.purge()
        self.assertTrue(buf.is_purged)

        # Access after purge must raise BufferPurgedError
        with self.assertRaises(BufferPurgedError):
            buf.get_buffer()

    def test_context_manager_automatic_purge(self):
        raw_audio = b"CALLER_AUDIO_BYTES_SAMPLE"
        captured_hash = None

        with EphemeralAudioBuffer(raw_audio) as ctx:
            captured_hash = ctx.audio_hash
            self.assertEqual(ctx.get_buffer(), raw_audio)
            self.assertFalse(ctx.is_purged)

        # Context exited -> buffer MUST be purged
        self.assertTrue(ctx.is_purged)
        with self.assertRaises(BufferPurgedError):
            ctx.get_buffer()

    def test_helper_context_manager(self):
        raw_audio = b"ANOTHER_VOICE_SAMPLE"
        with ephemeral_audio_context(raw_audio) as ctx:
            self.assertEqual(ctx.get_buffer(), raw_audio)
        self.assertTrue(ctx.is_purged)

    def test_audit_event_contains_zero_raw_audio_bytes(self):
        # Verify that SecurityEvent schema does not allow or leak raw audio
        event = SecurityEvent.create(
            seq_num=0,
            session_id="call_anon",
            event_type=EventType.AUDIO_INGESTED,
            prev_hash="0" * 64,
            audio_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            payload={"duration_sec": 4.2, "sample_rate": 16000},
        )
        serialized = event.to_dict()

        # The dictionary and canonical string should strictly contain the 64-char hash
        self.assertIn("audio_hash", serialized)
        self.assertEqual(len(serialized["audio_hash"]), 64)
        # Ensure no raw audio or base64 audio stream fields exist
        self.assertNotIn("raw_audio", serialized)
        self.assertNotIn("audio_bytes", serialized)
        self.assertNotIn("audio_content", serialized)


if __name__ == "__main__":
    unittest.main()
