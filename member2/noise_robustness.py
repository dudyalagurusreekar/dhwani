import torch
import torchaudio
import torch.nn.functional as F

from speechbrain.inference.speaker import EncoderClassifier
from statistics import mean, median


# ============================================================
# CONFIG
# ============================================================

AUDIO_PATH = "member2/audio/real_speech.wav"

TARGET_SR = 16000

SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0

SNR_LEVELS = [
    None,   # clean
    20,
    10,
    5
]


# ============================================================
# LOAD AUDIO
# ============================================================

def load_audio(path):

    waveform, sample_rate = torchaudio.load(path)

    # Stereo -> mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(
            dim=0,
            keepdim=True
        )

    # Resample
    if sample_rate != TARGET_SR:

        waveform = torchaudio.functional.resample(
            waveform,
            sample_rate,
            TARGET_SR
        )

    return waveform


# ============================================================
# ADD CONTROLLED WHITE NOISE
# ============================================================

def add_noise(waveform, snr_db):

    if snr_db is None:
        return waveform.clone()

    signal_power = waveform.pow(2).mean()

    noise_power = (
        signal_power /
        (10 ** (snr_db / 10))
    )

    noise = torch.randn_like(waveform)

    noise = noise * torch.sqrt(
        noise_power /
        noise.pow(2).mean()
    )

    noisy = waveform + noise

    return noisy


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

def generate_embeddings(model, segments):

    embeddings = []

    with torch.inference_mode():

        for segment in segments:

            embedding = model.encode_batch(
                segment
            )

            embedding = embedding.flatten()

            embeddings.append(embedding)

    return embeddings


# ============================================================
# CONSISTENCY
# ============================================================

def calculate_consistency(embeddings):

    scores = []

    for i in range(len(embeddings)):

        for j in range(i + 1, len(embeddings)):

            score = F.cosine_similarity(
                embeddings[i].unsqueeze(0),
                embeddings[j].unsqueeze(0)
            ).item()

            scores.append(score)

    return {
        "mean": mean(scores),
        "median": median(scores),
        "minimum": min(scores),
        "maximum": max(scores),
        "pairs": len(scores)
    }


# ============================================================
# MAIN
# ============================================================

print("============================================")
print("MEMBER 2 - NOISE ROBUSTNESS EXPERIMENT")
print("============================================")


# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

print("\n[1] Loading audio...")

audio = load_audio(AUDIO_PATH)

duration = audio.shape[-1] / TARGET_SR

print(f"Duration: {duration:.2f} seconds")


# ------------------------------------------------------------
# LOAD MODEL
# ------------------------------------------------------------

print("\n[2] Loading ECAPA-TDNN...")

model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb"
)

print("ECAPA loaded.")


# ------------------------------------------------------------
# EXPERIMENT
# ------------------------------------------------------------

results = []


for snr in SNR_LEVELS:

    if snr is None:

        label = "CLEAN"

        test_audio = audio.clone()

    else:

        label = f"{snr} dB SNR"

        test_audio = add_noise(
            audio,
            snr
        )


    print("\n--------------------------------------------")
    print(f"Testing: {label}")
    print("--------------------------------------------")


    # Segment

    segments = create_segments(
        test_audio
    )

    print(
        "Segments:",
        len(segments)
    )


    # Embeddings

    embeddings = generate_embeddings(
        model,
        segments
    )


    # Consistency

    stats = calculate_consistency(
        embeddings
    )


    print(
        f"Mean similarity   : "
        f"{stats['mean']:.4f}"
    )

    print(
        f"Median similarity : "
        f"{stats['median']:.4f}"
    )

    print(
        f"Minimum           : "
        f"{stats['minimum']:.4f}"
    )

    print(
        f"Maximum           : "
        f"{stats['maximum']:.4f}"
    )


    results.append(
        (label, stats)
    )


# ============================================================
# FINAL TABLE
# ============================================================

print("\n")
print("============================================")
print("NOISE ROBUSTNESS RESULTS")
print("============================================")

print(
    f"{'Condition':<15}"
    f"{'Mean':>10}"
    f"{'Median':>10}"
    f"{'Min':>10}"
    f"{'Max':>10}"
)

print("--------------------------------------------")


for label, stats in results:

    print(
        f"{label:<15}"
        f"{stats['mean']:>10.4f}"
        f"{stats['median']:>10.4f}"
        f"{stats['minimum']:>10.4f}"
        f"{stats['maximum']:>10.4f}"
    )


print("\n============================================")
print("CHECKPOINT 4 COMPLETE")
print("============================================")