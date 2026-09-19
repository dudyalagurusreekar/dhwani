import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier
import torch.nn.functional as F

AUDIO_PATH = "member2/audio/real_speech.wav"

TARGET_SR = 16000
SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0


print("========================================")
print("MEMBER 2 - SPEAKER CONSISTENCY TEST")
print("========================================")


# ==================================================
# 1. LOAD AUDIO
# ==================================================

print("\n[1] Loading audio...")

waveform, sample_rate = torchaudio.load(AUDIO_PATH)

print("Original shape:", waveform.shape)
print("Original sample rate:", sample_rate)


# ==================================================
# 2. CONVERT TO MONO
# ==================================================

if waveform.shape[0] > 1:
    waveform = waveform.mean(dim=0, keepdim=True)


# ==================================================
# 3. RESAMPLE TO 16 kHz
# ==================================================

if sample_rate != TARGET_SR:

    waveform = torchaudio.functional.resample(
        waveform,
        sample_rate,
        TARGET_SR
    )

    sample_rate = TARGET_SR


duration = waveform.shape[-1] / TARGET_SR

print("Processed shape:", waveform.shape)
print("Sample rate:", TARGET_SR)
print(f"Duration: {duration:.2f} seconds")


# ==================================================
# 4. SPLIT AUDIO INTO OVERLAPPING SEGMENTS
# ==================================================

print("\n[2] Creating audio segments...")

segment_samples = int(SEGMENT_SECONDS * TARGET_SR)
hop_samples = int(HOP_SECONDS * TARGET_SR)

segments = []

start = 0

while start + segment_samples <= waveform.shape[-1]:

    segment = waveform[:, start:start + segment_samples]

    segments.append(segment)

    start += hop_samples


print("Segment duration:", SEGMENT_SECONDS, "seconds")
print("Hop duration:", HOP_SECONDS, "seconds")
print("Number of segments:", len(segments))


# ==================================================
# 5. LOAD ECAPA
# ==================================================

print("\n[3] Loading ECAPA-TDNN...")

model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb"
)

print("ECAPA loaded.")


# ==================================================
# 6. GENERATE EMBEDDINGS
# ==================================================

print("\n[4] Generating embeddings...")

embeddings = []

with torch.inference_mode():

    for i, segment in enumerate(segments):

        embedding = model.encode_batch(segment)

        embedding = embedding.flatten()

        embeddings.append(embedding)

        print(
            f"Segment {i + 1:02d} | "
            f"Embedding shape: {tuple(embedding.shape)}"
        )


# ==================================================
# 7. CALCULATE PAIRWISE COSINE SIMILARITY
# ==================================================

print("\n[5] Calculating cosine similarities...")

similarities = []

for i in range(len(embeddings)):

    for j in range(i + 1, len(embeddings)):

        similarity = F.cosine_similarity(
            embeddings[i].unsqueeze(0),
            embeddings[j].unsqueeze(0)
        ).item()

        similarities.append(similarity)

        print(
            f"Segment {i + 1:02d} vs "
            f"Segment {j + 1:02d}: "
            f"{similarity:.4f}"
        )


# ==================================================
# 8. SUMMARY
# ==================================================

print("\n========================================")
print("CONSISTENCY SUMMARY")
print("========================================")

if similarities:

    mean_similarity = sum(similarities) / len(similarities)

    sorted_scores = sorted(similarities)

    middle = len(sorted_scores) // 2

    if len(sorted_scores) % 2 == 0:

        median_similarity = (
            sorted_scores[middle - 1]
            + sorted_scores[middle]
        ) / 2

    else:

        median_similarity = sorted_scores[middle]


    print(f"Number of comparisons : {len(similarities)}")
    print(f"Mean similarity      : {mean_similarity:.4f}")
    print(f"Median similarity    : {median_similarity:.4f}")
    print(f"Minimum similarity   : {min(similarities):.4f}")
    print(f"Maximum similarity   : {max(similarities):.4f}")

else:

    print("Not enough segments for comparison.")


print("\n========================================")
print("CHECKPOINT 2 COMPLETE")
print("========================================")