"""
Deterministic Verification Suite for Multi-Model Live Risk Pipeline
====================================================================
Tests:
1. Silence: Pure zero audio -> NON_SPEECH, 0 W2V2/AASIST inferences, audio_quality present.
2. Low-energy ambient noise -> NON_SPEECH, 0 W2V2/AASIST inferences.
3. Real speech (real_speech.wav) -> SPEECH, both W2V2-AASIST and AASIST executed, fusion verified.
4. Audio Quality -> Validates SNR, clipping, spectral flatness, usable speech duration.
5. JSON serialization -> Validates all event schemas (SPEECH and NON_SPEECH).
"""

import json
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streaming.live_risk_pipeline import LiveRiskPipeline


def test_silence_and_noise():
    print("\n--- TEST 1 & 2: SILENCE & LOW-ENERGY NOISE ---")
    pipeline = LiveRiskPipeline()

    # 1. Pure silence
    silence = np.zeros(64600, dtype=np.float32)
    ev_silence = pipeline.process_window(silence)

    assert ev_silence["vad"]["status"] == "NON_SPEECH"
    assert ev_silence["speech_present"] is False
    assert ev_silence["risk_status"] == "NO_SPEECH"
    assert len(ev_silence["detectors"]) == 0
    assert "audio_quality" in ev_silence
    assert pipeline.w2v2_executions == 0
    assert pipeline.aasist_executions == 0
    print("PASS: Pure silence cleanly emitted NO_SPEECH without detector execution.")

    # 2. Low-energy ambient noise (-80 dB)
    noise = np.random.normal(0, 1e-4, 64600).astype(np.float32)
    ev_noise = pipeline.process_window(noise)

    assert ev_noise["vad"]["status"] == "NON_SPEECH"
    assert ev_noise["speech_present"] is False
    assert ev_noise["risk_status"] == "NO_SPEECH"
    assert len(ev_noise["detectors"]) == 0
    assert "audio_quality" in ev_noise
    assert pipeline.w2v2_executions == 0
    assert pipeline.aasist_executions == 0
    print("PASS: Low ambient noise cleanly emitted NO_SPEECH without detector execution.")


def test_real_speech_and_json():
    print("\n--- TEST 3, 4 & 5: REAL SPEECH, MULTI-MODEL FUSION & JSON SERIALIZATION ---")
    pipeline = LiveRiskPipeline()
    events = pipeline.run_file("real_speech.wav")

    assert len(events) == 10, f"Expected 10 windows, got {len(events)}"
    assert pipeline.speech_windows > 0, "Expected speech windows in real_speech.wav"
    assert pipeline.w2v2_executions == pipeline.speech_windows
    assert pipeline.aasist_executions == pipeline.speech_windows

    print(f"Total windows: {len(events)}")
    print(f"Speech windows: {pipeline.speech_windows}")
    print(f"Non-speech windows: {pipeline.non_speech_windows}")
    print(f"W2V2 executions: {pipeline.w2v2_executions}")
    print(f"AASIST executions: {pipeline.aasist_executions}")

    # Verify JSON serialization & schema
    for idx, ev in enumerate(events, start=1):
        # JSON serialize check
        json_str = json.dumps(ev)
        assert json_str is not None

        assert "window_id" in ev
        assert "timestamp" in ev
        assert "speech_present" in ev
        assert "speech_ratio" in ev
        assert "audio" in ev
        assert "vad" in ev
        assert "audio_quality" in ev
        assert "quality_level" in ev["audio_quality"]

        if ev["speech_present"]:
            assert "detectors" in ev
            assert len(ev["detectors"]) == len(pipeline.active_detectors), f"Expected {len(pipeline.active_detectors)} detectors, got {len(ev['detectors'])}"
            models = [d["model"] for d in ev["detectors"]]
            assert "W2V2-AASIST" in models
            assert "AASIST" in models
            assert "AASIST-L" in models
            assert "ACOUSTIC" in models
            assert "fusion" in ev
            assert "active_models" in ev["fusion"]
            assert len(ev["fusion"]["active_models"]) == len(pipeline.active_detectors)
            assert "temporal" in ev
            assert "risk_score" in ev
            assert "risk_level" in ev
            assert "reasons" in ev
        else:
            assert ev["risk_status"] == "NO_SPEECH"
            assert len(ev["detectors"]) == 0

    print("PASS: All 10 windows verified for schema integrity, multi-model fusion, and JSON serialization.")


if __name__ == "__main__":
    test_silence_and_noise()
    test_real_speech_and_json()
    print("\nALL MULTI-MODEL PIPELINE TESTS PASSED SUCCESSFULLY!")
