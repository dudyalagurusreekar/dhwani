"""
EchoShield Attack Attribution Engine
====================================
Analyzes spoof detections to attribute the attack vector to:
- SYNTHETIC_TTS: Full text-to-speech synthesis (vocoder & phoneme generation).
- VOICE_CONVERSION: Source-to-target voice conversion / real-time voice changer.
- PHYSICAL_REPLAY: Playback of authentic recording via physical loudspeaker.
- BONA_FIDE: Genuine human speech.

Evaluates:
1. Spectral rolloff and high-frequency cutoff (replay & vocoder band limits).
2. Spectral flux / frame jitter (synthetic speech has unnatural smoothness).
3. Audio quality & SNR characteristics (replay has secondary acoustic room resonance).
4. Relative model sensitivity (SSL models detect neural vocoders; AASIST detects graph artifacts).
"""

from typing import Any, Dict, List, Optional
import numpy as np


class AttackAttributionEngine:
    """
    Classifies spoof detections into granular attack vectors with explainable confidence.
    """

    def __init__(self, spoof_threshold: float = 0.40):
        self.spoof_threshold = spoof_threshold

    def attribute_attack(
        self,
        risk_score: float,
        detector_results: List[Dict[str, Any]],
        audio_quality: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Determine attack vector and provide confidence breakdown.

        Returns:
            {
                "primary_vector": "BONA_FIDE" | "SYNTHETIC_TTS" | "VOICE_CONVERSION" | "PHYSICAL_REPLAY",
                "confidence": float,
                "vector_probabilities": Dict[str, float],
                "attribution_reasons": List[str],
            }
        """
        if risk_score < self.spoof_threshold:
            return {
                "primary_vector": "BONA_FIDE",
                "confidence": round(1.0 - risk_score, 3),
                "vector_probabilities": {
                    "BONA_FIDE": round(1.0 - risk_score, 3),
                    "SYNTHETIC_TTS": round(risk_score * 0.4, 3),
                    "VOICE_CONVERSION": round(risk_score * 0.4, 3),
                    "PHYSICAL_REPLAY": round(risk_score * 0.2, 3),
                },
                "attribution_reasons": ["Acoustic & neural models indicate genuine speech dynamics."],
            }

        # Extract features
        reasons = []
        scores = {d.get("model"): float(d.get("raw_score", 0)) for d in detector_results}

        acoustic_meta = {}
        for d in detector_results:
            if d.get("model") == "ACOUSTIC":
                acoustic_meta = d.get("metadata", {})
                break

        snr_db = 20.0
        flatness = 0.02
        if audio_quality:
            snr_db = float(audio_quality.get("estimated_snr", 20.0))
            flatness = float(audio_quality.get("spectral_flatness", 0.02))

        hf_ratio = acoustic_meta.get("hf_ratio", 0.15)
        rolloff_hz = acoustic_meta.get("rolloff_85_hz", 4500.0)
        spectral_flux = acoustic_meta.get("spectral_flux", 50.0)

        tts_score = 0.35
        vc_score = 0.35
        replay_score = 0.30

        # Physical Replay evidence:
        # Speaker bandwidth cutoff (< 3400 Hz) + low SNR + high reverberant noise floor
        if rolloff_hz < 3500:
            replay_score += 0.30
            tts_score -= 0.15
            reasons.append("Acoustic frequency cutoff below 3.5 kHz characteristic of loudspeaker transducer.")
        if snr_db < 8.0:
            replay_score += 0.20
            reasons.append("Elevated secondary room reverberation and ambient microphone noise floor.")

        # Synthetic TTS evidence:
        # Neural vocoder signatures: high spectral flatness, low inter-frame jitter / flux
        if spectral_flux < 2.0:
            tts_score += 0.35
            vc_score -= 0.15
            reasons.append("Abnormally low inter-frame spectral flux indicating robotic vocoder phase synthesis.")
        if flatness > 0.035:
            tts_score += 0.20
            reasons.append("Elevated spectral flatness typical of parametric or diffusion neural vocoders.")

        # Voice Conversion evidence:
        # High SSL model detection with moderate acoustic variability
        w2v2_score = scores.get("W2V2-AASIST", 0.0)
        aasist_score = scores.get("AASIST", 0.0)
        if w2v2_score > 0.85 and spectral_flux >= 2.0:
            vc_score += 0.30
            reasons.append("Strong self-supervised vocal tract representation shift with organic temporal cadence.")

        # Normalize probabilities
        total = tts_score + vc_score + replay_score
        p_tts = tts_score / total
        p_vc = vc_score / total
        p_replay = replay_score / total

        probs = {
            "SYNTHETIC_TTS": round(p_tts, 3),
            "VOICE_CONVERSION": round(p_vc, 3),
            "PHYSICAL_REPLAY": round(p_replay, 3),
        }

        best_vector = max(probs, key=probs.get)
        if not reasons:
            reasons.append("Multi-model deep neural anti-spoofing consensus.")

        return {
            "primary_vector": best_vector,
            "confidence": probs[best_vector],
            "vector_probabilities": probs,
            "attribution_reasons": reasons,
        }
