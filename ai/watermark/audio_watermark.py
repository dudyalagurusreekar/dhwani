"""
EchoShield Dynamic Audio Watermarking Engine
============================================
Provides inaudible acoustic watermarking using high-frequency Spread-Spectrum
modulation for continuous origin authentication.

Theory:
1. Embedding: Modulates a pseudo-random pseudo-noise (PN) sequence into the
   inaudible high-frequency band (6,800 - 7,800 Hz) at low amplitude (-42 dBFS).
   Human ear is insensitive to this low-energy band, while microphone sampling captures it.
2. Verification: Neural vocoders (HiFi-GAN, WaveGlow, Diffusion) regenerate speech
   from mel-spectrograms or latent tokens, which inevitably destroys or alters
   high-frequency phase-coherent PN watermarks.
3. Detection: Matched-filter cross-correlation against the secret PN sequence.
   Correlation peak > threshold confirms authentic transmission.
"""

import hashlib
import numpy as np
import scipy.signal
from typing import Any, Dict, Tuple


class AudioWatermarkEngine:
    """
    Inaudible psychoacoustic spread-spectrum watermarking engine.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        carrier_freq_low: float = 6800.0,
        carrier_freq_high: float = 7800.0,
        embedding_depth_db: float = -38.0,
        correlation_threshold: float = 0.25,
    ):
        self.sample_rate = sample_rate
        self.f_low = carrier_freq_low
        self.f_high = carrier_freq_high
        self.depth_linear = 10.0 ** (embedding_depth_db / 20.0)
        self.correlation_threshold = correlation_threshold

        # Design bandpass filter for watermark channel
        nyquist = 0.5 * sample_rate
        self.b, self.a = scipy.signal.butter(
            4,
            [self.f_low / nyquist, min(0.98, self.f_high / nyquist)],
            btype="bandpass",
        )

    def generate_token_pn_sequence(self, session_token: str, length: int) -> np.ndarray:
        """Generate deterministic pseudo-noise sequence from session token."""
        # Use SHA-256 hash as seed for reproducible PN sequence
        seed = int(hashlib.sha256(session_token.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        # Bipolar Barker-like sequence (+1, -1)
        raw_pn = rng.choice([-1.0, 1.0], size=length).astype(np.float32)
        # Bandpass shape PN to carrier frequencies
        shaped_pn = scipy.signal.lfilter(self.b, self.a, raw_pn).astype(np.float32)
        # Normalize energy
        norm = np.std(shaped_pn) + 1e-12
        return shaped_pn / norm

    def embed_watermark(
        self,
        audio: np.ndarray,
        session_token: str,
    ) -> np.ndarray:
        """
        Embed inaudible watermark into audio signal.
        """
        orig_shape = audio.shape
        sig = audio.flatten().astype(np.float32)

        pn_seq = self.generate_token_pn_sequence(session_token, len(sig))
        watermark = pn_seq * self.depth_linear

        watermarked_audio = sig + watermark
        # Prevent clipping
        watermarked_audio = np.clip(watermarked_audio, -1.0, 1.0)
        return watermarked_audio.reshape(orig_shape)

    def verify_watermark(
        self,
        audio: np.ndarray,
        session_token: str,
    ) -> Dict[str, Any]:
        """
        Detect presence of authentic session watermark in audio.

        Returns:
            {
                "watermark_detected": bool,
                "correlation_peak": float,
                "confidence": float,
                "status": "AUTHENTIC" | "CORRUPTED_OR_ABSENT"
            }
        """
        sig = audio.flatten().astype(np.float32)
        if len(sig) < 1600:
            return {
                "watermark_detected": False,
                "correlation_peak": 0.0,
                "confidence": 0.0,
                "status": "AUDIO_TOO_SHORT",
            }

        # Filter audio to watermark band
        filtered_sig = scipy.signal.lfilter(self.b, self.a, sig).astype(np.float32)
        filtered_norm = np.std(filtered_sig) + 1e-12
        filtered_sig = filtered_sig / filtered_norm

        # Reference PN
        ref_pn = self.generate_token_pn_sequence(session_token, len(sig))

        # Normalized cross-correlation
        corr = scipy.signal.correlate(filtered_sig, ref_pn, mode="same") / len(sig)
        peak = float(np.max(np.abs(corr)))

        detected = peak >= self.correlation_threshold
        status = "AUTHENTIC" if detected else "CORRUPTED_OR_ABSENT"

        return {
            "watermark_detected": detected,
            "correlation_peak": round(peak, 4),
            "confidence": round(min(1.0, peak / self.correlation_threshold), 3),
            "status": status,
        }
