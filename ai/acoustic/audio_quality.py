"""
EchoShield Audio Quality Analyzer
=================================
Calculates lightweight acoustic quality and reliability signals:
- RMS & Peak amplitude
- Clipping ratio (distortion detection)
- Estimated noise floor & SNR indicator
- Zero-crossing rate
- Spectral flatness (tonal vs noise-like distribution)
- Speech ratio & usable speech duration
- Reliability quality score & categorical level

IMPORTANT:
These metrics are NEVER used as voice spoof scores.
They provide context on acoustic channel reliability (e.g., poor quality
signals reduce confidence in detector evidence, whereas clean audio
preserves standard detector confidence).
"""

import time
from typing import Any, Dict, Optional
import numpy as np


class AudioQualityAnalyzer:
    """
    Extracts acoustic transmission and signal-quality features
    to assess audio reliability for downstream anti-spoofing models.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: float = 20.0,
        clipping_threshold: float = 0.995,
        speech_energy_threshold_db: float = -38.0,
    ):
        self.sample_rate = int(sample_rate)
        self.frame_len = int(self.sample_rate * (frame_duration_ms / 1000.0))  # 320 samples
        self.clipping_threshold = float(clipping_threshold)
        self.speech_energy_threshold_db = float(speech_energy_threshold_db)

    def analyze(
        self,
        audio: np.ndarray,
        sample_rate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze audio waveform and return acoustic quality metrics.

        Parameters:
        -----------
        audio: 1D numpy array of float32 samples.
        sample_rate: Audio sampling rate (default: self.sample_rate).

        Returns:
        --------
        dict of quality metrics, reliability score, and quality level.
        """
        t_start = time.perf_counter()

        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        sr = sample_rate or self.sample_rate
        total_samples = len(audio)
        total_duration_s = total_samples / sr if sr > 0 else 0.0

        if total_samples == 0:
            return {
                "rms": 0.0,
                "peak_amplitude": 0.0,
                "clipping_ratio": 0.0,
                "estimated_noise_floor_db": -180.0,
                "estimated_snr_db": 0.0,
                "zero_crossing_rate": 0.0,
                "spectral_flatness": 0.0,
                "speech_ratio": 0.0,
                "usable_speech_duration_s": 0.0,
                "quality_score": 0.0,
                "quality_level": "POOR",
                "reliability_multiplier": 0.50,
                "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
            }

        # 1. Amplitude & RMS
        peak_amp = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(audio ** 2)))
        rms_db = 20.0 * np.log10(rms + 1e-9)

        # 2. Clipping Ratio
        clipped_samples = np.sum(np.abs(audio) >= self.clipping_threshold)
        clipping_ratio = float(clipped_samples / total_samples)

        # 3. Short-Time Frame Energy & Estimated SNR
        frame_size = self.frame_len if self.frame_len > 0 else 320
        num_frames = total_samples // frame_size

        if num_frames > 0:
            frames = audio[: num_frames * frame_size].reshape(num_frames, frame_size)
            frame_energies = np.mean(frames ** 2, axis=1)
            frame_dbs = 20.0 * np.log10(np.sqrt(frame_energies) + 1e-9)

            # Noise floor estimated from lowest 10th percentile of frame energy
            noise_floor_db = float(np.percentile(frame_dbs, 10))

            # Speech frames
            speech_frames_mask = frame_dbs >= self.speech_energy_threshold_db
            speech_frame_count = int(np.sum(speech_frames_mask))
            speech_ratio = float(speech_frame_count / num_frames)

            if speech_frame_count > 0:
                speech_energy_db = float(np.mean(frame_dbs[speech_frames_mask]))
                estimated_snr_db = max(0.0, speech_energy_db - noise_floor_db)
            else:
                speech_energy_db = float(np.mean(frame_dbs))
                estimated_snr_db = 0.0
        else:
            noise_floor_db = rms_db
            speech_ratio = 1.0 if rms_db >= self.speech_energy_threshold_db else 0.0
            estimated_snr_db = 0.0

        usable_speech_duration_s = float(speech_ratio * total_duration_s)

        # 4. Zero-Crossing Rate
        signs = np.sign(audio)
        zcr = float(np.mean(np.abs(np.diff(signs))) / 2.0)

        # 5. Spectral Flatness (Wiener entropy)
        # Power spectrum via rfft
        fft_data = np.abs(np.fft.rfft(audio)) ** 2 + 1e-12
        geom_mean = float(np.exp(np.mean(np.log(fft_data))))
        arith_mean = float(np.mean(fft_data))
        spectral_flatness = float(min(1.0, geom_mean / (arith_mean + 1e-12)))

        # 6. Holistic Reliability & Quality Scoring in [0.0, 1.0]
        # High SNR (>20 dB) -> 1.0, low SNR (<6 dB) -> 0.0
        snr_factor = max(0.0, min(1.0, estimated_snr_db / 20.0))

        # Adequate speech duration in window (>1.5s out of 4s) -> 1.0
        speech_factor = max(0.0, min(1.0, usable_speech_duration_s / 1.5))

        # Clipping penalty
        clip_penalty = min(1.0, clipping_ratio * 50.0)  # >2% clipping is heavy penalty

        # Tonal clarity: very high spectral flatness (>0.6) suggests white noise/hiss
        flatness_factor = max(0.0, min(1.0, (0.7 - spectral_flatness) / 0.5))

        quality_score = float(
            0.35 * snr_factor
            + 0.35 * speech_factor
            + 0.15 * flatness_factor
            + 0.15 * (1.0 - clip_penalty)
        )
        quality_score = max(0.0, min(1.0, quality_score))

        # Categorical Quality Level
        if quality_score >= 0.65:
            quality_level = "GOOD"
            reliability_multiplier = 1.00
        elif quality_score >= 0.40:
            quality_level = "FAIR"
            reliability_multiplier = 0.80
        else:
            quality_level = "POOR"
            reliability_multiplier = 0.50

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "rms": round(rms, 6),
            "peak_amplitude": round(peak_amp, 4),
            "clipping_ratio": round(clipping_ratio, 4),
            "estimated_noise_floor_db": round(noise_floor_db, 1),
            "estimated_snr_db": round(estimated_snr_db, 1),
            "zero_crossing_rate": round(zcr, 4),
            "spectral_flatness": round(spectral_flatness, 4),
            "speech_ratio": round(speech_ratio, 4),
            "usable_speech_duration_s": round(usable_speech_duration_s, 3),
            "quality_score": round(quality_score, 4),
            "quality_level": quality_level,
            "reliability_multiplier": reliability_multiplier,
            "latency_ms": round(latency_ms, 3),
        }


if __name__ == "__main__":
    print("AUDIO QUALITY ANALYZER: SELF TEST")
    print("=" * 50)

    analyzer = AudioQualityAnalyzer()

    # 1. Test clean speech-like signal
    t = np.linspace(0, 4.0375, 64600)
    clean_audio = (0.2 * np.sin(2 * np.pi * 300 * t) + 0.1 * np.sin(2 * np.pi * 600 * t)).astype(np.float32)
    res_clean = analyzer.analyze(clean_audio)
    print("Clean Signal Quality:")
    for k, v in res_clean.items():
        print(f"  {k}: {v}")

    # 2. Test clipped noise
    noisy_clipped = (1.5 * np.random.normal(0, 0.5, 64600)).clip(-1.0, 1.0).astype(np.float32)
    res_clipped = analyzer.analyze(noisy_clipped)
    print("\nClipped Noise Quality:")
    for k, v in res_clipped.items():
        print(f"  {k}: {v}")
