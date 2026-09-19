import torchaudio
from pathlib import Path

AUDIO_DIR = Path("member2/audio")

files = [
    ("friend_session2.aac", "friend_session2.wav"),
    ("speaker_c_session1.aac", "speaker_c_session1.wav"),
    ("speaker_c_session2.aac", "speaker_c_session2.wav"),
]

for source_name, output_name in files:

    source = AUDIO_DIR / source_name
    output = AUDIO_DIR / output_name

    print("=" * 60)
    print(f"Converting: {source}")

    waveform, sample_rate = torchaudio.load(str(source))

    print(f"Input sample rate: {sample_rate}")
    print(f"Input channels: {waveform.shape[0]}")
    print(f"Input frames: {waveform.shape[1]}")

    # Convert stereo to mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Convert to 16 kHz
    if sample_rate != 16000:
        waveform = torchaudio.functional.resample(
            waveform,
            orig_freq=sample_rate,
            new_freq=16000,
        )

    torchaudio.save(
        str(output),
        waveform,
        16000,
        encoding="PCM_S",
        bits_per_sample=16,
    )

    print(f"Saved: {output}")

print()
print("ALL CONVERSIONS COMPLETE")