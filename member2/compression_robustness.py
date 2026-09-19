from pathlib import Path
from itertools import combinations
from statistics import median

import torch
import torchaudio
import torch.nn.functional as F

from speechbrain.inference.speaker import EncoderClassifier


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_SR = 16000
SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0

BASE_DIR = Path("member2/audio")
COMPRESSION_DIR = BASE_DIR / "compression"

FILES = {
    "Clean": BASE_DIR / "real_speech.wav",
    "MP3 128 kbps": COMPRESSION_DIR / "mp3_128_decoded.wav",
    "MP3 64 kbps": COMPRESSION_DIR / "mp3_64_decoded.wav",
    "MP3 32 kbps": COMPRESSION_DIR / "mp3_32_decoded.wav",
}


# ============================================================
# AUDIO PREPROCESSING
# ============================================================

def load_audio(path):

    waveform, sample_rate = torchaudio.load(str(path))

    # Convert stereo -> mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if necessary
    if sample_rate != TARGET_SR:
        waveform = torchaudio.functional.resample(
            waveform,
            orig_freq=sample_rate,
            new_freq=TARGET_SR
        )

    return waveform


# ============================================================
# SEGMENTATION
# ============================================================

def split_audio(
    waveform,
    segment_seconds=SEGMENT_SECONDS,
    hop_seconds=HOP_SECONDS
):

    segment_samples = int(segment_seconds * TARGET_SR)
    hop_samples = int(hop_seconds * TARGET_SR)

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
# COSINE SIMILARITY
# ============================================================

def pairwise_similarities(embeddings):

    scores = []

    for a, b in combinations(embeddings, 2):

        a = a.flatten().unsqueeze(0)
        b = b.flatten().unsqueeze(0)

        score = F.cosine_similarity(a, b).item()

        scores.append(float(score))

    return scores


# ============================================================
# ANALYZE ONE AUDIO FILE
# ============================================================

def analyze_file(model, path):

    waveform = load_audio(path)

    duration = waveform.shape[-1] / TARGET_SR

    segments = split_audio(waveform)

    embeddings = []

    for segment in segments:

        with torch.inference_mode():

            embedding = model.encode_batch(
                segment
            )

        embedding = embedding.squeeze().cpu()

        embeddings.append(embedding)

    similarities = pairwise_similarities(
        embeddings
    )

    return {
        "duration": duration,
        "segments": len(segments),
        "pairs": len(similarities),
        "mean": sum(similarities) / len(similarities),
        "median": median(similarities),
        "min": min(similarities),
        "max": max(similarities),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print("CHECKPOINT 5B - COMPRESSION ROBUSTNESS")
    print("=" * 75)

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(f"\nDevice: {device}")

    print("\nLoading ECAPA-TDNN...")

    model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={
            "device": device
        }
    )

    print("ECAPA model loaded successfully.")

    results = {}

    for name, path in FILES.items():

        print("\n" + "-" * 75)
        print(f"Processing: {name}")
        print(f"File: {path}")

        if not path.exists():

            print("ERROR: File not found.")

            continue

        result = analyze_file(
            model,
            path
        )

        results[name] = result

        print(
            f"Duration: {result['duration']:.2f} sec"
        )

        print(
            f"Segments: {result['segments']}"
        )

        print(
            f"Pairs: {result['pairs']}"
        )

        print(
            f"Mean similarity: "
            f"{result['mean']:.4f}"
        )

        print(
            f"Median similarity: "
            f"{result['median']:.4f}"
        )

        print(
            f"Minimum similarity: "
            f"{result['min']:.4f}"
        )

        print(
            f"Maximum similarity: "
            f"{result['max']:.4f}"
        )

    # ========================================================
    # FINAL TABLE
    # ========================================================

    print("\n")
    print("=" * 75)
    print("COMPRESSION ROBUSTNESS RESULTS")
    print("=" * 75)

    print(
        f"{'Condition':<18}"
        f"{'Duration':<12}"
        f"{'Segments':<10}"
        f"{'Mean':<12}"
        f"{'Median':<12}"
        f"{'Min':<12}"
        f"{'Max':<12}"
    )

    print("-" * 86)

    for name, result in results.items():

        print(
            f"{name:<18}"
            f"{result['duration']:<12.2f}"
            f"{result['segments']:<10}"
            f"{result['mean']:<12.4f}"
            f"{result['median']:<12.4f}"
            f"{result['min']:<12.4f}"
            f"{result['max']:<12.4f}"
        )

    print("\n")
    print("Experiment complete.")


if __name__ == "__main__":
    main()