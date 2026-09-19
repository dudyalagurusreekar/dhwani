import torch
import torchaudio
import torch.nn.functional as F
from speechbrain.inference.speaker import EncoderClassifier
from statistics import mean, median


# ============================================================
# CONFIGURATION
# ============================================================

AUDIO_A = "member2/audio/real_speech.wav"
AUDIO_B = "member2/audio/friend.wav"

TARGET_SR = 16000

SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0


# ============================================================
# LOAD + PREPROCESS AUDIO
# ============================================================

def load_audio(path):

    waveform, sample_rate = torchaudio.load(path)

    print(f"\nLoading: {path}")
    print("Original sample rate:", sample_rate)
    print("Original channels:", waveform.shape[0])

    # Stereo -> mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample -> 16 kHz
    if sample_rate != TARGET_SR:

        waveform = torchaudio.functional.resample(
            waveform,
            sample_rate,
            TARGET_SR
        )

    duration = waveform.shape[-1] / TARGET_SR

    print("Processed sample rate:", TARGET_SR)
    print("Processed channels:", waveform.shape[0])
    print(f"Duration: {duration:.2f} seconds")

    return waveform


# ============================================================
# SEGMENT AUDIO
# ============================================================

def create_segments(waveform):

    segment_samples = int(
        SEGMENT_SECONDS * TARGET_SR
    )

    hop_samples = int(
        HOP_SECONDS * TARGET_SR
    )

    segments = []

    start = 0

    while start + segment_samples <= waveform.shape[-1]:

        segment = waveform[
            :,
            start:start + segment_samples
        ]

        segments.append(segment)

        start += hop_samples

    return segments


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

def generate_embeddings(model, segments, label):

    embeddings = []

    print(
        f"\nGenerating embeddings for Speaker {label}..."
    )

    with torch.inference_mode():

        for i, segment in enumerate(segments):

            embedding = model.encode_batch(segment)

            embedding = embedding.flatten()

            embeddings.append(embedding)

            print(
                f"Speaker {label} | "
                f"Segment {i + 1:02d} | "
                f"Shape: {tuple(embedding.shape)}"
            )

    return embeddings


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    return F.cosine_similarity(
        a.unsqueeze(0),
        b.unsqueeze(0)
    ).item()


# ============================================================
# WITHIN-SPEAKER COMPARISON
# ============================================================

def within_speaker_scores(embeddings):

    scores = []

    for i in range(len(embeddings)):

        for j in range(i + 1, len(embeddings)):

            score = cosine_similarity(
                embeddings[i],
                embeddings[j]
            )

            scores.append(score)

    return scores


# ============================================================
# CROSS-SPEAKER COMPARISON
# ============================================================

def cross_speaker_scores(embeddings_a, embeddings_b):

    scores = []

    for a in embeddings_a:

        for b in embeddings_b:

            score = cosine_similarity(a, b)

            scores.append(score)

    return scores


# ============================================================
# PRINT STATISTICS
# ============================================================

def print_statistics(name, scores):

    print("\n----------------------------------------")
    print(name)
    print("----------------------------------------")

    print("Number of comparisons:", len(scores))

    print(
        f"Mean   : {mean(scores):.4f}"
    )

    print(
        f"Median : {median(scores):.4f}"
    )

    print(
        f"Minimum: {min(scores):.4f}"
    )

    print(
        f"Maximum: {max(scores):.4f}"
    )


# ============================================================
# MAIN
# ============================================================

print("============================================")
print("MEMBER 2 - SPEAKER VERIFICATION EXPERIMENT")
print("============================================")


# ------------------------------------------------------------
# 1. LOAD AUDIO
# ------------------------------------------------------------

print("\n[1] Loading Speaker A")

audio_a = load_audio(AUDIO_A)

print("\n[2] Loading Speaker B")

audio_b = load_audio(AUDIO_B)


# ------------------------------------------------------------
# 2. SEGMENT
# ------------------------------------------------------------

print("\n[3] Creating segments")

segments_a = create_segments(audio_a)
segments_b = create_segments(audio_b)

print(
    f"Speaker A segments: {len(segments_a)}"
)

print(
    f"Speaker B segments: {len(segments_b)}"
)


# ------------------------------------------------------------
# 3. LOAD ECAPA
# ------------------------------------------------------------

print("\n[4] Loading ECAPA-TDNN")

model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb"
)

print("ECAPA loaded successfully.")


# ------------------------------------------------------------
# 4. GENERATE EMBEDDINGS
# ------------------------------------------------------------

print("\n[5] Speaker A embeddings")

embeddings_a = generate_embeddings(
    model,
    segments_a,
    "A"
)

print("\n[6] Speaker B embeddings")

embeddings_b = generate_embeddings(
    model,
    segments_b,
    "B"
)


# ------------------------------------------------------------
# 5. SAME SPEAKER A
# ------------------------------------------------------------

print("\n[7] Same-speaker A-A comparison")

scores_aa = within_speaker_scores(
    embeddings_a
)


# ------------------------------------------------------------
# 6. SAME SPEAKER B
# ------------------------------------------------------------

print("\n[8] Same-speaker B-B comparison")

scores_bb = within_speaker_scores(
    embeddings_b
)


# ------------------------------------------------------------
# 7. DIFFERENT SPEAKER
# ------------------------------------------------------------

print("\n[9] Different-speaker A-B comparison")

scores_ab = cross_speaker_scores(
    embeddings_a,
    embeddings_b
)


# ------------------------------------------------------------
# 8. RESULTS
# ------------------------------------------------------------

print("\n")
print("============================================")
print("FINAL RESULTS")
print("============================================")

print_statistics(
    "SAME SPEAKER A-A",
    scores_aa
)

print_statistics(
    "SAME SPEAKER B-B",
    scores_bb
)

print_statistics(
    "DIFFERENT SPEAKER A-B",
    scores_ab
)


# ------------------------------------------------------------
# 9. SIMPLE SUMMARY
# ------------------------------------------------------------

same_speaker_mean = (
    mean(scores_aa) +
    mean(scores_bb)
) / 2

different_speaker_mean = mean(scores_ab)

print("\n============================================")
print("SUMMARY")
print("============================================")

print(
    f"Average same-speaker similarity      : "
    f"{same_speaker_mean:.4f}"
)

print(
    f"Average different-speaker similarity : "
    f"{different_speaker_mean:.4f}"
)

print(
    f"Difference                           : "
    f"{same_speaker_mean - different_speaker_mean:.4f}"
)

print("\n============================================")
print("CHECKPOINT 3 COMPLETE")
print("============================================")