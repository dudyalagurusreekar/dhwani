import sounddevice as sd
import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION = 5

print("================================")
print(" EchoShield Microphone Test")
print("================================")
print()
print("Speak normally for 5 seconds...")
print("Recording...")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
)

sd.wait()

audio = audio.reshape(-1)

print("Recording complete.")
print(f"Samples: {len(audio)}")
print(f"Sample rate: {SAMPLE_RATE}")
print(f"Channels: {CHANNELS}")

sf.write(
    "microphone_test.wav",
    audio,
    SAMPLE_RATE,
)

print("Saved: microphone_test.wav")