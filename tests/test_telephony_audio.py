"""
Unit & Integration Tests for Telephony Audio Decoding & Resampling
Validates:
1. G.711 mu-law decoding table and bit-accuracy.
2. 8 kHz to 16 kHz polyphase resampling ratio.
3. Audio clipping safety and amplitude bounds [-1.0, 1.0].
4. CallSession rolling buffer window generation (64600 samples @ 16kHz).
5. Caller phone number privacy masking.
"""

import math
import unittest
import numpy as np

from streaming.telephony.audio_decoder import TelephonyAudioDecoder
from streaming.telephony.call_session import CallSession, mask_phone_number
from streaming.telephony.twiml import generate_twiml_media_stream


class TestTelephonyAudio(unittest.TestCase):
    def setUp(self):
        self.decoder = TelephonyAudioDecoder(target_sample_rate=16000, source_sample_rate=8000)

    def test_ulaw_decoding_silence(self):
        # In G.711 mu-law, 0xFF corresponds to zero/near-zero amplitude
        ulaw_bytes = bytes([0xFF] * 160)
        pcm = self.decoder.decode_ulaw_bytes(ulaw_bytes)
        self.assertEqual(len(pcm), 160)
        self.assertEqual(pcm.dtype, np.int16)
        # Mu-law 0xFF decodes to 0
        self.assertEqual(pcm[0], 0)

    def test_resampling_8k_to_16k(self):
        # 160 samples @ 8 kHz (20ms) should resample to exactly 320 samples @ 16 kHz
        t = np.linspace(0, 0.02, 160, endpoint=False)
        tone_8k = (np.sin(2 * np.pi * 440 * t) * 32000).astype(np.int16)
        f32_16k = self.decoder.resample_8k_to_16k(tone_8k)

        self.assertEqual(len(f32_16k), 320)
        self.assertEqual(f32_16k.dtype, np.float32)
        # Verify amplitude bounds [-1.0, 1.0]
        self.assertTrue(np.all(f32_16k >= -1.0))
        self.assertTrue(np.all(f32_16k <= 1.0))

    def test_call_session_rolling_buffer(self):
        session = CallSession(
            call_sid="CA12345678",
            stream_sid="MZ12345678",
            from_number="+14155552671",
            to_number="+18005550199",
            window_size=64600,
            hop_size=16000,
        )

        # Masked number validation
        self.assertEqual(session.from_number_masked, "+1 ***-***-2671")
        self.assertEqual(session.to_number_masked, "+1 ***-***-0199")

        # Feed 4 seconds of audio (64,000 samples) -> should not produce window yet (< 64600)
        chunk_64k = np.zeros(64000, dtype=np.float32)
        windows = session.append_audio(chunk_64k)
        self.assertEqual(len(windows), 0)

        # Feed another 1,000 samples (total 65,000 samples) -> should produce exactly 1 window
        chunk_1k = np.zeros(1000, dtype=np.float32)
        windows = session.append_audio(chunk_1k)
        self.assertEqual(len(windows), 1)
        self.assertEqual(len(windows[0]), 64600)

        # Buffer should now hold (65000 - 16000) = 49000 samples
        self.assertEqual(len(session._audio_buffer), 49000)

    def test_phone_number_masking(self):
        self.assertEqual(mask_phone_number("+12125551234"), "+1 ***-***-1234")
        self.assertEqual(mask_phone_number("+919876543210"), "+91 ***-***-3210")
        self.assertEqual(mask_phone_number("1234"), "***-***-1234")
        self.assertEqual(mask_phone_number(""), "UNKNOWN_CALLER")
        self.assertEqual(mask_phone_number(None), "UNKNOWN_CALLER")

    def test_twiml_generation(self):
        xml_str = generate_twiml_media_stream(
            stream_url="wss://example.ngrok-free.app/twilio/media",
            greeting_text="Dhwani voice protection active.",
        )
        self.assertIn("<Stream", xml_str)
        self.assertIn("wss://example.ngrok-free.app/twilio/media", xml_str)
        self.assertIn("Dhwani voice protection active.", xml_str)
        self.assertIn("inbound_track", xml_str)


if __name__ == "__main__":
    unittest.main()
