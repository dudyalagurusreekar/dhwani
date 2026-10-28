"""
Phase 1: Automated Regression Tests for Trustworthy AI Inference Foundation
===========================================================================
Covers:
- Adapter-level PyTorch checkpoint loading and inference (AASIST, AASIST-L)
- Graceful unavailable state handling (W2V2-AASIST, ECAPA-TDNN)
- Audio preprocessing resilience (silence, extreme noise, non-finite values, empty buffers)
- Output contract validation (DetectorResult schema, score scale and direction)
- Partial-ensemble adaptive evidence fusion and consensus without crashes
- Dynamic system health and detector lifecycle telemetry
"""

import math
from pathlib import Path
import numpy as np
import pytest
import torch

from ai.common.detector_interface import BaseDetector, DetectorResult, DetectorStatus
from ai.aasist.aasist_adapter import AASISTAdapter
from ai.aasist.aasist_l_adapter import AASISTLAdapter
from ai.ssl_detector.w2v2_aasist_adapter import W2V2AASISTAdapter
from ai.speaker.speaker_consistency import SpeakerConsistencyEngine
from ai.acoustic.acoustic_detector import AcousticDetector
from backend.services import detector
from risk_engine.adaptive_fusion import AdaptiveFusionEngine
from risk_engine.model_agreement import ModelAgreementEngine
from backend.services.risk_engine import calculate_risk


class TestPhase1Adapters:
    """Test neural and acoustic detector adapters."""

    def test_aasist_pytorch_loading_and_inference(self):
        adapter = AASISTAdapter(strict=False)
        assert adapter.is_available is True
        assert adapter.status == DetectorStatus.READY
        assert adapter.backend == "pytorch"
        assert adapter.device == "cpu"

        # Test inference with random audio
        audio = np.random.randn(64600).astype(np.float32)
        res = adapter.predict_audio(audio)

        assert res["model"] == "AASIST"
        assert res["status"] == "SUCCESS"
        assert res["raw_score"] is not None
        assert 0.0 <= res["raw_score"] <= 1.0
        assert res["score_direction"] == "higher_is_more_spoof"
        assert res["device"] == "cpu"
        assert res["backend"] == "pytorch"
        assert res["latency_ms"] > 0.0

    def test_aasist_l_pytorch_loading_and_inference(self):
        adapter = AASISTLAdapter(strict=False)
        assert adapter.is_available is True
        assert adapter.status == DetectorStatus.READY
        assert adapter.backend == "pytorch"
        assert adapter.device == "cpu"

        # Test inference with synthetic sine wave
        t = np.linspace(0, 4.0, 64600, endpoint=False, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        res = adapter.predict_audio(audio)

        assert res["model"] == "AASIST-L"
        assert res["status"] == "SUCCESS"
        assert res["raw_score"] is not None
        assert 0.0 <= res["raw_score"] <= 1.0
        assert res["score_direction"] == "higher_is_more_spoof"

    def test_acoustic_detector_execution(self):
        det = AcousticDetector()
        assert det.is_available is True
        assert det.status == DetectorStatus.READY
        assert det.device == "cpu"
        assert det.backend == "numpy"

        # Pure silence test
        silence = np.zeros(64600, dtype=np.float32)
        res_silence = det.predict_audio(silence)
        assert res_silence["status"] == "SUCCESS"
        assert 0.0 <= res_silence["raw_score"] <= 1.0

        # Random speech test
        audio = np.random.randn(64600).astype(np.float32)
        res = det.predict_audio(audio)
        assert res["status"] == "SUCCESS"
        assert 0.0 <= res["raw_score"] <= 1.0

    def test_missing_checkpoints_graceful_handling(self):
        # W2V2-AASIST with strict=False
        w2v2 = W2V2AASISTAdapter(strict=False)
        assert w2v2.is_available is False
        assert w2v2.status == DetectorStatus.UNAVAILABLE
        res = w2v2.predict_audio(np.zeros(64600, dtype=np.float32))
        assert res["status"] == "SKIPPED"
        assert res["raw_score"] is None
        assert res["error"] is not None

        # W2V2-AASIST with strict=True
        with pytest.raises(FileNotFoundError):
            W2V2AASISTAdapter(strict=True)

        # ECAPA-TDNN with strict=False
        spk = SpeakerConsistencyEngine(strict=False)
        assert spk.is_available is False
        assert spk.status == DetectorStatus.UNAVAILABLE
        eval_res = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32))
        assert eval_res["status"] == "UNAVAILABLE"
        assert eval_res["cosine_similarity"] is None

        # ECAPA-TDNN with strict=True
        with pytest.raises(FileNotFoundError):
            SpeakerConsistencyEngine(strict=True)

    def test_audio_preprocessing_resilience(self):
        adapter = AASISTAdapter(strict=False)

        # Short audio (should be padded without crash)
        short_audio = np.ones(100, dtype=np.float32)
        res = adapter.predict_audio(short_audio)
        assert res["status"] == "SUCCESS"
        assert res["raw_score"] is not None

        # Stereo audio (should be downmixed to mono)
        stereo_audio = np.random.randn(64600, 2).astype(np.float32)
        res = adapter.predict_audio(stereo_audio)
        assert res["status"] == "SUCCESS"

        # Non-finite values (NaN / Inf)
        bad_audio = np.array([np.nan, np.inf, -np.inf] + [0.0] * 64597, dtype=np.float32)
        res = adapter.predict_audio(bad_audio)
        assert res["status"] == "SUCCESS"
        assert not math.isnan(res["raw_score"])

    def test_numerical_reproducibility(self):
        adapter = AASISTAdapter(strict=False)
        # Deterministic input
        np.random.seed(42)
        audio = np.random.randn(64600).astype(np.float32)

        res1 = adapter.predict_audio(audio)
        res2 = adapter.predict_audio(audio)

        assert abs(res1["raw_score"] - res2["raw_score"]) < 1e-5


class TestPhase1DetectorService:
    """Test backend detector service lifecycle, partial ensemble, and status."""

    def test_registry_and_active_detectors(self):
        reg = detector.get_detector_registry()
        assert "AASIST" in reg
        assert "AASIST-L" in reg
        assert "ACOUSTIC" in reg

        active = detector.get_active_detectors()
        assert len(active) >= 4

        # Verify real operational status
        status_map = {d["model"]: d for d in active}
        assert status_map["AASIST"]["is_available"] is True
        assert status_map["AASIST-L"]["is_available"] is True
        assert status_map["ACOUSTIC"]["is_available"] is True
        assert status_map["W2V2-AASIST"]["is_available"] is False

    def test_detector_health_summary(self):
        health = detector.get_detector_health()
        assert health["lifecycle"] == "READY"
        assert health["ready_count"] >= 3
        assert health["unavailable_count"] >= 1
        assert health["failed_count"] == 0

    def test_detect_voice_sync_partial_ensemble(self):
        audio = np.random.randn(64600).astype(np.float32)
        resp = detector.detect_voice_sync(audio)

        assert resp["fake_probability"] is not None
        assert 0.0 <= resp["fake_probability"] <= 1.0
        assert resp["real_probability"] is not None
        assert round(resp["fake_probability"] + resp["real_probability"], 3) == 1.0

        # Verify active contributing models
        contributing = resp["active_models"]
        assert "AASIST" in contributing
        assert "AASIST-L" in contributing
        assert "ACOUSTIC" in contributing
        assert "W2V2-AASIST" not in contributing

        # Verify skipped detector appears with SKIPPED status
        det_map = {d["model"]: d for d in resp["detectors"]}
        assert det_map["W2V2-AASIST"]["status"] == "SKIPPED"
        assert det_map["W2V2-AASIST"]["raw_score"] is None

    def test_detect_voice_sync_with_empty_bytes(self):
        resp = detector.detect_voice_sync(b"")
        assert resp["fake_probability"] is not None
        assert len(resp["detectors"]) >= 4


class TestPhase1RiskFusion:
    """Test risk fusion resilience against missing, failed, and disagreeing detectors."""

    def test_adaptive_fusion_filters_unsuccessful_detectors(self):
        engine = AdaptiveFusionEngine()
        mixed_results = [
            {"model": "AASIST", "raw_score": 0.90, "status": "SUCCESS"},
            {"model": "ACOUSTIC", "raw_score": 0.80, "status": "SUCCESS"},
            {"model": "W2V2-AASIST", "raw_score": None, "status": "SKIPPED", "error": "file not found"},
            {"model": "BROKEN_MODEL", "raw_score": None, "status": "FAILED", "error": "cuda oom"},
        ]
        fused = engine.fuse(mixed_results)
        assert fused["fused_score"] is not None
        assert 0.80 <= fused["fused_score"] <= 0.90
        assert "AASIST" in fused["active_models"]
        assert "ACOUSTIC" in fused["active_models"]
        assert "W2V2-AASIST" not in fused["active_models"]
        assert "BROKEN_MODEL" not in fused["active_models"]

    def test_adaptive_fusion_empty_or_all_failed(self):
        engine = AdaptiveFusionEngine()
        all_failed = [
            {"model": "M1", "raw_score": None, "status": "FAILED"},
            {"model": "M2", "raw_score": None, "status": "SKIPPED"},
        ]
        fused = engine.fuse(all_failed)
        assert fused["fused_score"] is None
        assert fused["active_models"] == []

    def test_model_agreement_with_partial_models(self):
        engine = ModelAgreementEngine(decision_threshold=0.50)
        results = [
            {"model": "AASIST", "raw_score": 0.85, "status": "SUCCESS"},
            {"model": "AASIST-L", "raw_score": 0.90, "status": "SUCCESS"},
            {"model": "W2V2", "raw_score": None, "status": "SKIPPED"},
        ]
        agree = engine.evaluate_agreement(results)
        assert agree["consensus_level"] == "UNANIMOUS"
        assert agree["spoof_votes"] == 2
        assert agree["bonafide_votes"] == 0

    def test_calculate_risk_when_detectors_unavailable(self):
        # fake_probability is None
        risk = calculate_risk(fake_probability=None)
        assert risk["status"] == "INDETERMINATE"
        assert risk["risk_score"] == 0
        assert risk["recommendation"] == "VERIFY_CALLER"

    def test_adaptive_fusion_backward_compatibility_missing_status(self):
        engine = AdaptiveFusionEngine()
        # Legacy detector results without explicit "status" key
        legacy_results = [
            {"model": "AASIST", "raw_score": 0.85},
            {"model": "ACOUSTIC", "raw_score": 0.75},
        ]
        fused = engine.fuse(legacy_results)
        assert fused["fused_score"] is not None
        assert 0.75 <= fused["fused_score"] <= 0.85
        assert len(fused["active_models"]) == 2

    def test_model_agreement_backward_compatibility_missing_status(self):
        engine = ModelAgreementEngine(decision_threshold=0.50)
        legacy_results = [
            {"model": "AASIST", "raw_score": 0.85},
            {"model": "ACOUSTIC", "raw_score": 0.75},
        ]
        agreement = engine.evaluate_agreement(legacy_results)
        assert agreement["consensus_level"] == "UNANIMOUS"
        assert agreement["spoof_votes"] == 2


class TestPhase1SessionIsolation:
    """Test session isolation and lifecycle state boundaries in speaker consistency."""

    def test_session_isolated_anchor_and_history(self):
        spk = SpeakerConsistencyEngine(strict=False)
        # Mock ready status and embedder for isolated state testing
        spk.status = DetectorStatus.READY
        spk.session = object()  # Non-None sentinel for is_available

        emb_a = np.zeros(192, dtype=np.float32)
        emb_a[0] = 1.0  # Unit vector along axis 0

        emb_b = np.zeros(192, dtype=np.float32)
        emb_b[1] = 1.0  # Orthogonal unit vector along axis 1

        # Enroll Session A
        spk.extract_embedding = lambda audio, sr=16000: emb_a
        res_a1 = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="session_A")
        assert res_a1["status"] == "ENROLLED"

        # Enroll Session B with orthogonal embedding
        spk.extract_embedding = lambda audio, sr=16000: emb_b
        res_b1 = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="session_B")
        assert res_b1["status"] == "ENROLLED"

        # Verify Session A evaluates against emb_a (should be consistent with emb_a)
        spk.extract_embedding = lambda audio, sr=16000: emb_a
        res_a2 = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="session_A")
        assert res_a2["status"] == "CONSISTENT"
        assert abs(res_a2["cosine_similarity"] - 1.0) < 1e-4

        # Verify Session B evaluates against emb_b (emb_a should trigger SPEAKER_SWITCH for B)
        res_b2 = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="session_B")
        assert res_b2["status"] == "SPEAKER_SWITCH"
        assert abs(res_b2["cosine_similarity"] - 0.0) < 1e-4

    def test_session_reset_lifecycle(self):
        spk = SpeakerConsistencyEngine(strict=False)
        spk.status = DetectorStatus.READY
        spk.session = object()

        emb = np.ones(192, dtype=np.float32) / np.sqrt(192)
        spk.extract_embedding = lambda audio, sr=16000: emb

        spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="sess_1")
        spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="sess_2")

        assert "sess_1" in spk.session_profiles
        assert "sess_2" in spk.session_profiles

        # Reset sess_1 selectively
        spk.reset_session("sess_1")
        assert "sess_1" not in spk.session_profiles
        assert "sess_2" in spk.session_profiles

        # Reset all sessions
        spk.reset_session()
        assert len(spk.session_profiles) == 0

    def test_non_finite_embedding_does_not_poison_state(self):
        spk = SpeakerConsistencyEngine(strict=False)
        spk.status = DetectorStatus.READY
        spk.session = object()

        # Inject non-finite embedding
        spk.extract_embedding = lambda audio, sr=16000: np.full(192, np.nan, dtype=np.float32)
        res = spk.evaluate_consistency(np.zeros(16000, dtype=np.float32), session_id="sess_poison")

        assert res["status"] == "FAILED"
        assert res["cosine_similarity"] is None
        # Must not enroll NaN embedding as anchor
        assert "sess_poison" not in spk.session_profiles

    def test_backend_detector_service_session_api_integration(self):
        audio = np.random.randn(64600).astype(np.float32)
        resp = detector.detect_voice_sync(audio, session_id="call_sess_phase1")
        assert resp["fake_probability"] is not None

        # Reset session via backend service hook
        detector.reset_session("call_sess_phase1")
        detector.reset_session()

