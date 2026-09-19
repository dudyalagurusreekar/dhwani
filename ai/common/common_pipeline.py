"""
Unified Media Analysis Pipeline for Dhwani / EchoShield AI
Executes end-to-end detection across all media sources (File, Video, YouTube, Microphone, Telephony).
Enforces:
AudioSource -> Resample/Normalize -> VAD -> Quality -> Rolling Windows ->
Multi-Model Ensemble -> Adaptive Fusion -> Temporal Risk -> Policy -> Canonical Result
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid
import numpy as np

from ai.common.media_sources import AudioSource
from streaming.vad_gate import VADGate
from ai.acoustic.audio_quality import AudioQualityAnalyzer
from backend.services.detector import detect_voice_sync
from backend.services.risk_engine import assess_risk
from security.hasher import compute_numpy_hash


class UnifiedMediaPipeline:
    """
    Standardized analysis engine ensuring every audio source passes through
    the identical anti-spoofing verification and tamper-evident logging flow.
    """

    def __init__(
        self,
        window_size: int = 64600,
        hop_size: int = 16000,
        vad_energy_threshold_db: float = -38.0,
    ):
        self.window_size = window_size
        self.hop_size = hop_size
        self.vad = VADGate(energy_threshold_db=vad_energy_threshold_db)
        self.quality_analyzer = AudioQualityAnalyzer()

    def analyze_source(
        self,
        source: AudioSource,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an AudioSource end-to-end and return the canonical AnalysisResult schema.
        """
        start_wall_time = time.perf_counter()
        if not analysis_id:
            analysis_id = str(uuid.uuid4())

        # Step 1: Ingestion & Normalization
        audio, sr = source.load_audio()
        total_samples = len(audio)
        duration_sec = round(total_samples / sr, 2)

        if total_samples == 0:
            raise ValueError("Audio source produced zero samples.")

        # Compute tamper-evident evidence hash
        audio_evidence_hash = compute_numpy_hash(audio)

        # Step 2: Global Quality Analysis
        quality_info = self.quality_analyzer.analyze(audio[: min(total_samples, 64600)])

        # Step 3: Rolling Window Slicing
        windows: List[np.ndarray] = []
        if total_samples <= self.window_size:
            # Pad short audio to exactly 64600 samples
            padded = np.zeros(self.window_size, dtype=np.float32)
            padded[:total_samples] = audio
            windows.append(padded)
        else:
            for start_idx in range(0, total_samples - self.window_size + 1, self.hop_size):
                windows.append(audio[start_idx : start_idx + self.window_size])

        # Step 4: Window-by-Window VAD and Multi-Model Evaluation
        windows_analyzed = 0
        speech_windows = 0
        latest_risk_result: Optional[Dict[str, Any]] = None
        window_telemetry: List[Dict[str, Any]] = []

        for w_idx, win in enumerate(windows):
            is_speech, speech_ratio, energy_db = self.vad.process_window(win)
            if not is_speech:
                continue

            speech_windows += 1
            windows_analyzed += 1

            # Run all 4 active models on GPU/CPU
            detector_resp = detect_voice_sync(win)
            detector_results = detector_resp.get("detectors", [])

            # Evaluate temporal risk, fusion, consensus, attribution, and policy
            risk_eval = assess_risk(
                detector_results,
                session_id=analysis_id,
                audio_quality=detector_resp.get("quality"),
            )
            latest_risk_result = risk_eval

            window_telemetry.append({
                "window_index": w_idx + 1,
                "speech_ratio": round(speech_ratio, 2),
                "energy_db": round(energy_db, 1),
                "risk_score": risk_eval["risk_score"],
                "risk_level": risk_eval["risk_level"],
                "consensus": risk_eval.get("consensus_level"),
                "attribution": risk_eval.get("attack_vector"),
                "detectors": detector_results,
            })

        # Calculate total speech duration
        speech_duration_sec = round((speech_windows * self.hop_size) / sr, 2)
        elapsed_ms = round((time.perf_counter() - start_wall_time) * 1000, 2)

        # If no speech was detected across all windows
        if windows_analyzed == 0 or latest_risk_result is None:
            return {
                "analysis_id": analysis_id,
                "source_type": source.get_source_type(),
                "source_metadata": source.get_metadata(),
                "duration_seconds": duration_sec,
                "speech_duration_seconds": 0.0,
                "windows_analyzed": 0,
                "detectors": [],
                "fusion": {"fused_score": 0.0, "weights": {}},
                "temporal": {"trend": "STABLE"},
                "risk_score": 0.0,
                "risk_level": "LOW",
                "reasons": ["No valid voiced human speech detected in the provided media."],
                "quality": quality_info,
                "evidence_hash": audio_evidence_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "processing_time_ms": elapsed_ms,
            }

        # Step 5: Format Canonical Analysis Result
        return {
            "analysis_id": analysis_id,
            "source_type": source.get_source_type(),
            "source_metadata": source.get_metadata(),
            "duration_seconds": duration_sec,
            "speech_duration_seconds": min(duration_sec, speech_duration_sec),
            "windows_analyzed": windows_analyzed,
            "detectors": latest_risk_result.get("detectors", []),
            "fusion": {
                "fused_score": latest_risk_result.get("fused_score", 0.0),
                "consensus_level": latest_risk_result.get("consensus_level", "NONE"),
                "consensus_explanation": latest_risk_result.get("consensus_explanation", ""),
            },
            "temporal": {
                "trend": latest_risk_result.get("temporal_trend", "STABLE"),
                "windows_in_history": len(window_telemetry),
            },
            "risk_score": float(latest_risk_result["risk_score"]),
            "risk_level": latest_risk_result["risk_level"],
            "reasons": latest_risk_result.get("reasons", []),
            "attack_vector": latest_risk_result.get("attack_vector", "UNKNOWN"),
            "policy_action": latest_risk_result.get("policy_action"),
            "policy_severity": latest_risk_result.get("policy_severity"),
            "policy_reason": latest_risk_result.get("policy_reason"),
            "recommendation": latest_risk_result.get("recommendation", "VERIFY_CALLER"),
            "alert": latest_risk_result.get("alert"),
            "quality": quality_info,
            "evidence_hash": audio_evidence_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": elapsed_ms,
            "window_telemetry": window_telemetry,
        }
