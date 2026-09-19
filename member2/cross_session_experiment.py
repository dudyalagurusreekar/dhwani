from pathlib import Path
from itertools import combinations
from statistics import median

import torch
import torchaudio
import torch.nn.functional as F

from speechbrain.inference.speaker import EncoderClassifier


TARGET_SR = 16000
SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0

AUDIO_DIR = Path("member2/audio")

SESSION_1 = AUDIO_DIR / "real_speech.wav"
SESSION_2 = AUDIO_DIR / "real_speech_session2.wav"
DIFFERENT_SPEAKER = AUDIO_DIR / "friend.wav"


# ============================================================
# LOAD + PREPROCESS
# ============================================================

def load_audio(path):

    waveform, sample_rate = torchaudio.load(str(path))

    print(f"Original sample rate: {sample_rate}")
    print(f"Original channels: {waveform.shape[0]}")

    # Stereo -> mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample -> 16 kHz
    if sample_rate != TARGET_SR:
        waveform = torchaudio.functional.resample(
            waveform,
            orig_freq=sample_rate,
            new_freq=TARGET_SR
        )

    return waveform


# ============================================================
# SEGMENT AUDIO
# ============================================================

def split_audio(waveform):

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
# EMBEDDINGS
# ============================================================

def get_embeddings(model, waveform):

    segments = split_audio(waveform)

    embeddings = []

    for segment in segments:

        with torch.inference_mode():

            embedding = model.encode_batch(
                segment
            )

        embedding = embedding.squeeze().cpu()

        embeddings.append(embedding)

    return embeddings


# ============================================================
# PAIRWISE SIMILARITY
# ============================================================

def pairwise_similarity(
    embeddings_a,
    embeddings_b
):

    scores = []

    for a in embeddings_a:

        for b in embeddings_b:

            a = a.flatten().unsqueeze(0)
            b = b.flatten().unsqueeze(0)

            score = F.cosine_similarity(
                a,
                b
            ).item()

            scores.append(float(score))

    return scores


# ============================================================
# ANALYZE CROSS-SESSION
# ============================================================

def analyze_pair(
    model,
    name_a,
    path_a,
    name_b,
    path_b
):

    print("\n" + "=" * 75)
    print(f"{name_a}  VS  {name_b}")
    print("=" * 75)

    print(f"\nLoading: {path_a}")

    waveform_a = load_audio(path_a)

    duration_a = (
        waveform_a.shape[-1] / TARGET_SR
    )

    print(
        f"Processed duration: "
        f"{duration_a:.2f} sec"
    )

    embeddings_a = get_embeddings(
        model,
        waveform_a
    )

    print(
        f"Segments A: "
        f"{len(embeddings_a)}"
    )

    print(f"\nLoading: {path_b}")

    waveform_b = load_audio(path_b)

    duration_b = (
        waveform_b.shape[-1] / TARGET_SR
    )

    print(
        f"Processed duration: "
        f"{duration_b:.2f} sec"
    )

    embeddings_b = get_embeddings(
        model,
        waveform_b
    )

    print(
        f"Segments B: "
        f"{len(embeddings_b)}"
    )

    scores = pairwise_similarity(
        embeddings_a,
        embeddings_b
    )

    result = {
        "mean": sum(scores) / len(scores),
        "median": median(scores),
        "min": min(scores),
        "max": max(scores),
        "pairs": len(scores),
    }

    print(
        f"\nPairs: {result['pairs']}"
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

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print("CHECKPOINT 5C - CROSS-SESSION SPEAKER CONSISTENCY")
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

    # --------------------------------------------------------
    # SAME SPEAKER: SESSION 1 VS SESSION 2
    # --------------------------------------------------------

    same_speaker = analyze_pair(
        model,
        "Speaker A - Session 1",
        SESSION_1,
        "Speaker A - Session 2",
        SESSION_2
    )

    # --------------------------------------------------------
    # DIFFERENT SPEAKER
    # --------------------------------------------------------

    different_speaker = analyze_pair(
        model,
        "Speaker A - Session 1",
        SESSION_1,
        "Speaker B",
        DIFFERENT_SPEAKER
    )

    # --------------------------------------------------------
    # FINAL COMPARISON
    # --------------------------------------------------------

    print("\n")
    print("=" * 75)
    print("FINAL CROSS-SESSION RESULTS")
    print("=" * 75)

    print(
        f"{'Comparison':<35}"
        f"{'Pairs':<10}"
        f"{'Mean':<12}"
        f"{'Median':<12}"
        f"{'Min':<12}"
        f"{'Max':<12}"
    )

    print("-" * 91)

    print(
        f"{'Same speaker (Session 1 vs 2)':<35}"
        f"{same_speaker['pairs']:<10}"
        f"{same_speaker['mean']:<12.4f}"
        f"{same_speaker['median']:<12.4f}"
        f"{same_speaker['min']:<12.4f}"
        f"{same_speaker['max']:<12.4f}"
    )

    print(
        f"{'Different speaker (A vs B)':<35}"
        f"{different_speaker['pairs']:<10}"
        f"{different_speaker['mean']:<12.4f}"
        f"{different_speaker['median']:<12.4f}"
        f"{different_speaker['min']:<12.4f}"
        f"{different_speaker['max']:<12.4f}"
    )

    print("\nExperiment complete.")


if __name__ == "__main__":
    main()