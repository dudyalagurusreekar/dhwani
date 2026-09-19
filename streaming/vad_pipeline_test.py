"""
Deterministic Verification Suite for VAD-Gated Live Risk Pipeline
==================================================================
Tests:
1. Silence: Pure zero audio -> NON_SPEECH, 0 W2V2 inferences.
2. Low-energy background noise -> NON_SPEECH, 0 W2V2 inferences.
3. Real speech (real_speech.wav) -> SPEECH, W2V2 executed only on speech.
4. JSON serialization -> all event schemas validate against JSON specification.
5. Existing pipeline compatibility -> RiskEngine output integrity on speech.
"""

import json
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streaming.live_risk_pipeline import LiveRiskPipeline
from streaming.vad_gate import EnergyVADGate


def test_silence_and_noise():
    print("\n--- TEST 1 & 2: SILENCE & LOW-ENERGY NOISE ---")
    pipeline = LiveRiskPipeline()

    # 1. Pure silence
    silence = np.zeros(64600, dtype=np.float32)
    ev_silence = pipeline.process_window(silence)

    assert ev_silence["vad"]["status"] == "NON_SPEECH", "Silence must be NON_SPEECH"
    assert ev_silence["vad"]["speech_detected"] is False
    assert ev_silence["risk_status"] == "NO_SPEECH"
    assert len(ev_silence["detectors"]) == 0, "No detectors should run on silence"
    assert pipeline.w2v2_executions == 0, "W2V2 must not execute on silence"
    print("PASS: Pure silence cleanly emitted NO_SPEECH without W2V2 execution.")

    # 2. Low-energy ambient noise (-80 dB)
    noise = np.random.normal(0, 1e-4, 64600).astype(np.float32)
    ev_noise = pipeline.process_window(noise)

    assert ev_noise["vad"]["status"] == "NON_SPEECH", "Low noise must be NON_SPEECH"
    assert ev_noise["vad"]["speech_detected"] is False
    assert ev_noise["risk_status"] == "NO_SPEECH"
    assert len(ev_noise["detectors"]) == 0
    assert pipeline.w2v2_executions == 0, "W2V2 must not execute on low noise"
    print("PASS: Low ambient noise cleanly emitted NO_SPEECH without W2V2 execution.")


def test_real_speech_and_json():
    print("\n--- TEST 3, 4 & 5: REAL SPEECH, JSON SERIALIZATION & PIPELINE COMPATIBILITY ---")
    pipeline = LiveRiskPipeline()
    events = pipeline.run_file("real_speech.wav")

    assert len(events) == 10, f"Expected 10 windows, got {len(events)}"
    assert pipeline.speech_windows > 0, "Expected speech windows in real_speech.wav"
    assert pipeline.w2v2_executions == pipeline.speech_windows, (
        f"W2V2 executions ({pipeline.w2v2_executions}) must equal speech windows ({pipeline.speech_windows})"
    )

    print(f"Total windows: {len(events)}")
    print(f"Speech windows: {pipeline.speech_windows}")
    print(f"Non-speech windows: {pipeline.non_speech_windows}")
    print(f"W2V2 executions: {pipeline.w2v2_executions}")

    # Verify JSON serialization & schema
    for idx, ev in enumerate(events, start=1):
        # JSON serialize check
        json_str = json.dumps(ev)
        assert json_str is not None

        assert "window_id" in ev
        assert "timestamp" in ev
        assert "audio" in ev
        assert "vad" in ev
        assert "status" in ev["vad"]

        if ev["vad"]["status"] == "SPEECH":
            assert "detectors" in ev
            assert len(ev["detectors"]) == 1
            assert ev["detectors"][0]["model"] == "W2V2-AASIST"
            assert ev["detectors"][0]["status"] == "REAL"
            assert "fusion" in ev
            assert "temporal" in ev
            assert "risk_score" in ev
            assert "risk_level" in ev
            assert "reasons" in ev
        else:
            assert ev["risk_status"] == "NO_SPEECH"
            assert len(ev["detectors"]) == 0

    print("PASS: All 10 windows verified for schema integrity, JSON serialization, and pipeline compatibility.")


if __name__ == "__main__":
    test_silence_and_noise()
    test_real_speech_and_json()
    print("\nALL DETERMINISTIC TESTS PASSED SUCCESSFULLY!")
