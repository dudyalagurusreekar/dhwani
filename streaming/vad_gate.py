"""
EchoShield Speech Activity Detector / VAD Gate
===============================================
A lightweight, deterministic energy and short-time feature gate
designed to filter out non-speech audio (silence, flat ambient noise,
hiss) BEFORE windows reach deep-learning speech anti-spoofing models.

Non-speech audio must NOT be interpreted as voice spoofing evidence.
This gate does NOT compute a spoof score; it only decides:
    SPEECH vs NON_SPEECH
"""

import time
from typing import Any, Dict, Optional
import numpy as np


class EnergyVADGate:
    """
    Deterministic audio activity gate based on RMS energy, decibel levels,
    short-time frame energy variance, and zero-crossing rate.
    """

    def __init__(
        self,
        energy_threshold_db: float = -38.0,
        active_frame_ratio_threshold: float = 0.20,
        zcr_min: float = 0.01,
        zcr_max: float = 0.50,
        sample_rate: int = 16000,
        frame_duration_ms: float = 20.0,
    ):
        """
        Parameters:
        -----------
        energy_threshold_db: Minimum dBFS required for speech consideration.
            Baseline: Silence is -180 dB, room background is ~ -75 dB,
            typical speech is ~ -20 to -30 dB. Default -50.0 dB provides
            a robust ~25 dB safety margin above typical ambient room noise.
        active_frame_ratio_threshold: Minimum fraction of 20ms frames that
            must exceed the energy threshold. Speech exhibits dynamic modulation,
            whereas flat noise or isolated clicks do not.
        zcr_min, zcr_max: Plausible Zero-Crossing Rate range for voiced/unvoiced speech.
        sample_rate: Audio sampling rate (default 16,000 Hz).
        frame_duration_ms: Frame length in milliseconds for short-time analysis.
        """
        self.energy_threshold_db = float(energy_threshold_db)
        self.active_frame_ratio_threshold = float(active_frame_ratio_threshold)
        self.zcr_min = float(zcr_min)
        self.zcr_max = float(zcr_max)
        self.sample_rate = int(sample_rate)
        self.frame_len = int(self.sample_rate * (frame_duration_ms / 1000.0))  # 320 samples @ 16 kHz

    def is_speech(
        self,
        audio: np.ndarray,
        sample_rate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an audio window and determine whether valid speech is present.

        Returns:
        --------
        dict containing:
            speech_detected: bool
            speech_activity_score: float (0.0 to 1.0)
            energy_db: float
            rms: float
            active_frame_ratio: float
            zcr: float
            status: "SPEECH" | "NON_SPEECH"
            reason: str
            latency_ms: float
        """
        t_start = time.perf_counter()

        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        total_samples = len(audio)
        if total_samples == 0:
            return {
                "speech_detected": False,
                "speech_present": False,
                "speech_ratio": 0.0,
                "speech_activity_score": 0.0,
                "energy_db": -180.0,
                "rms": 0.0,
                "active_frame_ratio": 0.0,
                "zcr": 0.0,
                "status": "NON_SPEECH",
                "reason": "empty_audio",
                "latency_ms": (time.perf_counter() - t_start) * 1000.0,
            }

        # 1. Overall RMS and Decibel Level
        mean_sq = float(np.mean(audio ** 2))
        rms = float(np.sqrt(mean_sq))
        energy_db = float(20.0 * np.log10(rms + 1e-9))

        # 2. Short-time Frame Energy Distribution
        frame_size = self.frame_len if self.frame_len > 0 else 320
        num_frames = total_samples // frame_size

        if num_frames > 0:
            frames = audio[: num_frames * frame_size].reshape(num_frames, frame_size)
            frame_energies_ms = np.mean(frames ** 2, axis=1)
            frame_dbs = 20.0 * np.log10(np.sqrt(frame_energies_ms) + 1e-9)
            # A frame is active if its dB exceeds the threshold
            active_frames = np.sum(frame_dbs >= self.energy_threshold_db)
            active_frame_ratio = float(active_frames / num_frames)
        else:
            active_frame_ratio = 1.0 if energy_db >= self.energy_threshold_db else 0.0

        # 3. Zero-Crossing Rate (ZCR)
        signs = np.sign(audio)
        zcr = float(np.mean(np.abs(np.diff(signs))) / 2.0)

        # 4. Speech vs. Non-Speech Classification
        if energy_db < self.energy_threshold_db:
            speech_detected = False
            reason = "low_energy_silence"
        elif active_frame_ratio < self.active_frame_ratio_threshold:
            speech_detected = False
            reason = "flat_background_noise"
        elif zcr < self.zcr_min:
            speech_detected = False
            reason = "low_frequency_noise"
        elif zcr > self.zcr_max:
            speech_detected = False
            reason = "high_frequency_hiss"
        else:
            speech_detected = True
            reason = "speech_activity_detected"

        # 5. Deterministic Speech Activity Score in [0.0, 1.0]
        # (Continuous representation reflecting loudness and active frame proportion)
        if not speech_detected:
            # Sub-threshold activity score (capped below 0.35)
            normalized_db = max(0.0, min(1.0, (energy_db - (-80.0)) / (self.energy_threshold_db - (-80.0))))
            activity_score = float(normalized_db * 0.30 * active_frame_ratio)
        else:
            # Active speech score scaled from 0.40 to 1.00 based on energy depth and active ratio
            db_factor = max(0.0, min(1.0, (energy_db - self.energy_threshold_db) / 25.0))
            frame_factor = max(0.0, min(1.0, active_frame_ratio / 0.50))
            activity_score = float(0.40 + 0.60 * (0.6 * db_factor + 0.4 * frame_factor))

        activity_score = max(0.0, min(1.0, activity_score))
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "speech_detected": speech_detected,
            "speech_present": speech_detected,
            "speech_ratio": round(active_frame_ratio, 4),
            "speech_activity_score": round(activity_score, 4),
            "energy_db": round(energy_db, 2),
            "rms": round(rms, 6),
            "active_frame_ratio": round(active_frame_ratio, 4),
            "zcr": round(zcr, 4),
            "status": "SPEECH" if speech_detected else "NON_SPEECH",
            "reason": reason,
            "latency_ms": round(latency_ms, 3),
        }


if __name__ == "__main__":
    print("ENERGY VAD GATE: SELF TEST")
    print("=" * 50)

    gate = EnergyVADGate()

    # Test pure silence
    silence = np.zeros(64600, dtype=np.float32)
    res_silence = gate.is_speech(silence)
    print("Silence:", res_silence)

    # Test random ambient noise (very low energy)
    noise = np.random.normal(0, 1e-4, 64600).astype(np.float32)
    res_noise = gate.is_speech(noise)
    print("Low Noise:", res_noise)

    # Test artificial tone/speech-like burst (sinusoid at -20 dB)
    t = np.linspace(0, 4.0375, 64600)
    burst = (0.1 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    res_burst = gate.is_speech(burst)
    print("Burst Tone:", res_burst)
