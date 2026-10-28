import sys
from pathlib import Path

import sounddevice as sd
import numpy as np

# Allow importing our AI detector
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai.ssl_detector.w2v2_aasist_detector import (
    W2V2AASISTDetector
)


SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "w2v2_aasist"
    / "w2v2-aasist.onnx"
)


print("======================================")
print(" EchoShield - Live W2V2-AASIST Test")
print("======================================")
print()

detector = W2V2AASISTDetector(
    str(MODEL_PATH)
)

print("Execution providers:")
print(detector.session.get_providers())
print()

print(f"Speak normally for {RECORD_SECONDS} seconds...")
print("Recording...")

audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
)

sd.wait()

audio = audio.reshape(-1)

print("Recording complete.")
print(f"Captured samples: {len(audio)}")
print()

print("Running W2V2-AASIST...")

result = detector.predict_audio(
    audio,
    SAMPLE_RATE
)

print()
print("========== DETECTION RESULT ==========")

for key, value in result.items():
    print(f"{key}: {value}")

print("======================================")