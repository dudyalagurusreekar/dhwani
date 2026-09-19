import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

AUDIO_PATH = "member2/audio/real_speech.wav"

print("========================================")
print("ECAPA-TDNN SPEAKER EMBEDDING TEST")
print("========================================")

# --------------------------------------------------
# 1. Load audio
# --------------------------------------------------

print("\n[1] Loading audio...")

waveform, sample_rate = torchaudio.load(AUDIO_PATH)

print("Original shape:", waveform.shape)
print("Original sample rate:", sample_rate)

# --------------------------------------------------
# 2. Convert stereo -> mono
# --------------------------------------------------

if waveform.shape[0] > 1:
    print("Converting stereo audio to mono...")
    waveform = waveform.mean(dim=0, keepdim=True)

# --------------------------------------------------
# 3. Resample -> 16 kHz
# --------------------------------------------------

if sample_rate != 16000:
    print(f"Resampling {sample_rate} Hz -> 16000 Hz...")
    waveform = torchaudio.functional.resample(
        waveform,
        sample_rate,
        16000
    )

sample_rate = 16000

print("Processed shape:", waveform.shape)
print("Processed sample rate:", sample_rate)

# --------------------------------------------------
# 4. Calculate duration
# --------------------------------------------------

duration = waveform.shape[-1] / sample_rate

print(f"Audio duration: {duration:.2f} seconds")

# --------------------------------------------------
# 5. Load ECAPA-TDNN
# --------------------------------------------------

print("\n[2] Loading ECAPA-TDNN...")

model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb"
)

print("ECAPA-TDNN loaded successfully.")

# --------------------------------------------------
# 6. Generate speaker embedding
# --------------------------------------------------

print("\n[3] Generating speaker embedding...")

with torch.inference_mode():
    embedding = model.encode_batch(waveform)

print("Embedding generated successfully!")

# --------------------------------------------------
# 7. Inspect embedding
# --------------------------------------------------

print("\n[4] Embedding information")

print("Embedding shape:", embedding.shape)
print("Embedding dtype:", embedding.dtype)

flat_embedding = embedding.flatten()

print("Flattened dimension:", flat_embedding.shape[0])

print("\nFirst 10 values:")
print(flat_embedding[:10])

print("\n========================================")
print("SUCCESS: ECAPA SPEAKER EMBEDDING CREATED")
print("========================================")