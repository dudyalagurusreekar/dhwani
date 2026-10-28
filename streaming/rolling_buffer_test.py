import time
from collections import deque

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000

# W2V2-AASIST needs 64,600 samples
WINDOW_SAMPLES = 64600

# Analyze a new window every 1 second
HOP_SAMPLES = SAMPLE_RATE * 1

# Microphone callback block size
BLOCK_SIZE = 1600       # 100 ms at 16 kHz

CHANNELS = 1


buffer = deque(maxlen=WINDOW_SAMPLES)

window_count = 0
last_analysis = 0


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio status: {status}")

    samples = indata[:, 0]

    for sample in samples:
        buffer.append(float(sample))


print("==============================================")
print(" EchoShield - Rolling Microphone Buffer Test")
print("==============================================")
print()
print(f"Sample rate:       {SAMPLE_RATE} Hz")
print(f"Window:             {WINDOW_SAMPLES} samples")
print(f"Window duration:    {WINDOW_SAMPLES / SAMPLE_RATE:.3f} sec")
print(f"Analysis interval:  {HOP_SAMPLES / SAMPLE_RATE:.1f} sec")
print()
print("Speak normally.")
print("The system will build a rolling 4-second buffer.")
print("Press Ctrl+C to stop.")
print()


try:
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback,
    ):

        start_time = time.time()
        last_analysis_time = start_time

        while True:

            current_time = time.time()

            # Wait until enough audio exists
            if len(buffer) >= WINDOW_SAMPLES:

                # Analyze once every second
                if current_time - last_analysis_time >= 1.0:

                    audio_window = np.array(
                        buffer,
                        dtype=np.float32
                    )

                    window_count += 1

                    print(
                        f"[Window {window_count:02d}] "
                        f"samples={len(audio_window)} "
                        f"duration="
                        f"{len(audio_window) / SAMPLE_RATE:.3f}s"
                    )

                    last_analysis_time = current_time

            time.sleep(0.01)


except KeyboardInterrupt:

    print()
    print("Stopping microphone...")

    print(
        f"Total analysis windows observed: "
        f"{window_count}"
    )

    print("Rolling buffer test complete.")