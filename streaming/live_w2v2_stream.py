import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai.ssl_detector.w2v2_aasist_detector import (
    W2V2AASISTDetector
)


# ============================================================
# CONFIGURATION
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

WINDOW_SAMPLES = 64600
WINDOW_SECONDS = WINDOW_SAMPLES / SAMPLE_RATE

BLOCK_SIZE = 1600          # 100 ms
ANALYSIS_INTERVAL = 1.0    # analyze every 1 second


MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "w2v2_aasist"
    / "w2v2-aasist.onnx"
)


# ============================================================
# SHARED BUFFER
# ============================================================

audio_buffer = deque(
    maxlen=WINDOW_SAMPLES
)

window_count = 0
last_analysis_time = 0.0


# ============================================================
# LOAD MODEL ONCE
# ============================================================

print("==============================================")
print(" EchoShield - REAL-TIME W2V2-AASIST")
print("==============================================")
print()

print("Loading W2V2-AASIST...")

detector = W2V2AASISTDetector(
    str(MODEL_PATH)
)

print("Model loaded.")
print()

print("Execution providers:")
print(detector.session.get_providers())
print()

print(f"Sample rate:       {SAMPLE_RATE} Hz")
print(f"Window:             {WINDOW_SAMPLES} samples")
print(f"Window duration:    {WINDOW_SECONDS:.3f} sec")
print(f"Analysis interval:  {ANALYSIS_INTERVAL:.1f} sec")
print()

print("Speak normally.")
print("Real-time analysis will begin after")
print(f"{WINDOW_SECONDS:.1f} seconds of audio.")
print()
print("Press Ctrl+C to stop.")
print()


# ============================================================
# MICROPHONE CALLBACK
# ============================================================

def audio_callback(indata, frames, time_info, status):

    if status:
        print(f"\nAudio status: {status}")

    samples = indata[:, 0]

    for sample in samples:
        audio_buffer.append(float(sample))


# ============================================================
# REAL-TIME LOOP
# ============================================================

try:

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback,
    ):

        stream_start = time.perf_counter()
        last_analysis_time = stream_start

        while True:

            current_time = time.perf_counter()

            # Wait until the first complete window exists.
            if len(audio_buffer) >= WINDOW_SAMPLES:

                if (
                    current_time - last_analysis_time
                    >= ANALYSIS_INTERVAL
                ):

                    # Copy the rolling buffer.
                    audio_window = np.array(
                        audio_buffer,
                        dtype=np.float32,
                    )

                    window_count += 1

                    # Run W2V2-AASIST.
                    result = detector.predict_audio(
                        audio_window,
                        SAMPLE_RATE,
                    )

                    print()
                    print(
                        f"========== WINDOW "
                        f"{window_count:03d} =========="
                    )

                    print(
                        f"Bona-fide logit: "
                        f"{result['bona_fide_logit']:.4f}"
                    )

                    print(
                        f"Spoof logit:     "
                        f"{result['spoof_logit']:.4f}"
                    )

                    print(
                        f"Inference:       "
                        f"{result['latency_ms']:.2f} ms"
                    )

                    print(
                        f"Window:          "
                        f"{result['window_seconds']:.3f} sec"
                    )

                    last_analysis_time = current_time

            time.sleep(0.01)


except KeyboardInterrupt:

    print()
    print("==============================================")
    print(" Stopping EchoShield")
    print("==============================================")
    print()
    print(
        f"Windows analyzed: {window_count}"
    )