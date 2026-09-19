"""
Telephony Call Session & Privacy Management for Dhwani / EchoShield AI
Tracks live phone call state, rolling audio buffer, and privacy-masked metadata.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional
import numpy as np


def mask_phone_number(phone: Optional[str]) -> str:
    """
    Mask a phone number for privacy compliance according to Dhwani security guidelines.
    Example: '+14155552671' -> '+1 ***-***-2671'
             '+919876543210' -> '+91 ***-***-3210'
    """
    if not phone:
        return "UNKNOWN_CALLER"

    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "***"

    last_four = digits[-4:]
    if phone.startswith("+1"):
        prefix = "+1"
    elif phone.startswith("+91"):
        prefix = "+91"
    elif phone.startswith("+"):
        prefix = phone[:3]
    else:
        prefix = ""

    if prefix:
        return f"{prefix} ***-***-{last_four}"
    return f"***-***-{last_four}"



class CallSession:
    """
    State and audio management for an active telephony media stream.
    """

    def __init__(
        self,
        call_sid: str,
        stream_sid: str,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
        sample_rate: int = 16000,
        window_size: int = 64600,
        hop_size: int = 16000,
    ):
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.from_number_raw = from_number
        self.from_number_masked = mask_phone_number(from_number)
        self.to_number_masked = mask_phone_number(to_number)
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.status = "CONNECTED"

        self.sample_rate = sample_rate
        self.window_size = window_size
        self.hop_size = hop_size

        # Internal float32 audio accumulation buffer
        self._audio_buffer = np.empty(0, dtype=np.float32)
        self.total_samples_received = 0

        # Real-time state metrics
        self.windows_processed = 0
        self.current_risk_score = 0
        self.current_risk_level = "LOW"
        self.latest_consensus = "NONE"
        self.latest_attribution = "UNKNOWN"
        self.latest_reasons: List[str] = []
        self.active_countermeasure: Optional[str] = None
        self.history: List[Dict] = []

    def append_audio(self, audio_chunk_16k: np.ndarray) -> List[np.ndarray]:
        """
        Append 16 kHz float32 samples to the session buffer.
        Extracts complete 64600-sample windows ready for AI inference.

        Returns:
            List of 64600-sample windows (if any reached capacity).
        """
        if len(audio_chunk_16k) == 0:
            return []

        self._audio_buffer = np.concatenate([self._audio_buffer, audio_chunk_16k])
        self.total_samples_received += len(audio_chunk_16k)

        windows = []
        while len(self._audio_buffer) >= self.window_size:
            window = self._audio_buffer[: self.window_size].copy()
            windows.append(window)
            # Advance buffer by hop_size (1 second / 16000 samples)
            self._audio_buffer = self._audio_buffer[self.hop_size :]

        return windows

    def update_risk_telemetry(
        self,
        risk_score: int,
        risk_level: str,
        consensus: str,
        attribution: str,
        reasons: List[str],
        countermeasure: Optional[str] = None,
        detectors: Optional[List[Dict]] = None,
    ):
        """Update session risk state after an AI window evaluation."""
        self.windows_processed += 1
        self.current_risk_score = risk_score
        self.current_risk_level = risk_level
        self.latest_consensus = consensus
        self.latest_attribution = attribution
        self.latest_reasons = reasons
        self.active_countermeasure = countermeasure

        snapshot = {
            "window": self.windows_processed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "consensus": consensus,
            "attribution": attribution,
            "reasons": reasons,
            "countermeasure": countermeasure,
            "detectors": detectors or [],
        }
        self.history.append(snapshot)
        if len(self.history) > 100:
            self.history.pop(0)

    def to_dict(self) -> Dict:
        """Serialize current session status for dashboard streaming."""
        return {
            "call_sid": self.call_sid,
            "stream_sid": self.stream_sid,
            "caller": self.from_number_masked,
            "callee": self.to_number_masked,
            "start_time": self.start_time,
            "status": self.status,
            "windows_processed": self.windows_processed,
            "total_duration_sec": round(self.total_samples_received / self.sample_rate, 2),
            "current_risk_score": self.current_risk_score,
            "current_risk_level": self.current_risk_level,
            "consensus": self.latest_consensus,
            "attribution": self.latest_attribution,
            "reasons": self.latest_reasons,
            "active_countermeasure": self.active_countermeasure,
        }
