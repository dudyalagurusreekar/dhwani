"""
Telephony Audio Decoder & Resampler for Dhwani / EchoShield AI
Converts Twilio 8 kHz G.711 u-law audio streams into normalized 16 kHz mono float32/int16 PCM
suitable for direct injection into the Dhwani rolling buffer and AI detection pipeline.
"""

import base64
from typing import Tuple
import numpy as np
from scipy import signal


def _build_ulaw_table() -> np.ndarray:
    """Precompute the 256-element G.711 mu-law to 16-bit linear PCM conversion table."""
    table = np.zeros(256, dtype=np.int16)
    for i in range(256):
        byte = ~i & 0xFF
        sign = byte & 0x80
        exponent = (byte >> 4) & 0x07
        mantissa = byte & 0x0F
        sample = ((mantissa << 3) + 132) << exponent
        sample -= 132
        table[i] = -sample if sign else sample
    return table


_ULAW_LOOKUP = _build_ulaw_table()


class TelephonyAudioDecoder:
    """
    Decodes Twilio G.711 u-law payloads and resamples to 16 kHz mono PCM.
    """

    def __init__(self, target_sample_rate: int = 16000, source_sample_rate: int = 8000):
        self.source_sample_rate = source_sample_rate
        self.target_sample_rate = target_sample_rate
        self.up_factor = target_sample_rate // source_sample_rate  # 2 for 8k -> 16k

    def decode_ulaw_bytes(self, ulaw_raw: bytes) -> np.ndarray:
        """
        Decode raw 8-bit G.711 u-law bytes to int16 linear PCM array [-32768, 32767].
        """
        if not ulaw_raw:
            return np.empty(0, dtype=np.int16)
        u8_arr = np.frombuffer(ulaw_raw, dtype=np.uint8)
        return _ULAW_LOOKUP[u8_arr]

    def decode_base64_payload(self, base64_payload: str) -> np.ndarray:
        """
        Decode Twilio media payload (base64 string of u-law audio) into int16 PCM.
        """
        raw_bytes = base64.b64decode(base64_payload)
        return self.decode_ulaw_bytes(raw_bytes)

    def resample_8k_to_16k(self, pcm_8k: np.ndarray) -> np.ndarray:
        """
        Resample 8 kHz PCM to 16 kHz using polyphase filtering.
        Input can be int16 or float32. Returns float32 normalized to [-1.0, 1.0].
        """
        if len(pcm_8k) == 0:
            return np.empty(0, dtype=np.float32)

        if pcm_8k.dtype == np.int16:
            f32 = pcm_8k.astype(np.float32) / 32768.0
        else:
            f32 = pcm_8k.astype(np.float32)

        # 2x polyphase resampling (8000 Hz -> 16000 Hz)
        resampled = signal.resample_poly(f32, self.up_factor, 1)
        return np.clip(resampled, -1.0, 1.0).astype(np.float32)

    def process_twilio_media_chunk(self, base64_payload: str) -> Tuple[np.ndarray, bytes]:
        """
        Complete processing of a Twilio media payload:
        Base64 -> u-law -> int16 (8kHz) -> resample (16kHz float32) -> 16-bit PCM bytes.

        Returns:
            (float32_array, raw_pcm16_bytes)
        """
        pcm_8k = self.decode_base64_payload(base64_payload)
        f32_16k = self.resample_8k_to_16k(pcm_8k)
        int16_16k = (f32_16k * 32767.0).astype(np.int16)
        return f32_16k, int16_16k.tobytes()
