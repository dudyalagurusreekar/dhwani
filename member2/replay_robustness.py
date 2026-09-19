from __future__ import annotations

from pathlib import Path
from statistics import mean, median
from itertools import combinations

import torch
import torchaudio
import torch.nn.functional as F

from speechbrain.inference.speaker import EncoderClassifier


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = Path("member2/audio/real_speech.wav")

TARGET_SR = 16000
SEGMENT_SECONDS = 2.0
HOP_SECONDS = 1.0

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================
# AUDIO LOADING
# ============================================================

def load_audio(path: Path) -> torch.Tensor:

    waveform, sr = torchaudio.load(str(path))

    print(f"Loading: {path}")
    print(f"Original sample rate: {sr}")
    print(f"Original channels: {waveform.shape[0]}")

    # Stereo -> mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample -> 16 kHz
    if sr != TARGET_SR:
        waveform = torchaudio.functional.resample(
            waveform,
            orig_freq=sr,
            new_freq=TARGET_SR,
        )

    # Normalize amplitude
    peak = waveform.abs().max()

    if peak > 0:
        waveform = waveform / peak

    duration = waveform.shape[-1] / TARGET_SR

    print(f"Processed duration: {duration:.2f} sec")

    return waveform


# ============================================================
# SIMULATED REPLAY / RECORDING CONDITION
# ============================================================

def simulate_replay(waveform: torch.Tensor) -> torch.Tensor:

    # 1. Slight bandwidth limitation
    # Downsample to 8 kHz and return to 16 kHz.
    replay = torchaudio.functional.resample(
        waveform,
        orig_freq=16000,
        new_freq=8000,
    )

    replay = torchaudio.functional.resample(
        replay,
        orig_freq=8000,
        new_freq=16000,
    )

    # 2. Add mild background noise
    signal_power = replay.pow(2).mean()

    snr_db = 15.0
    noise_power = signal_power / (10 ** (snr_db / 10))

    noise = torch.randn_like(replay) * torch.sqrt(noise_power)

    replay = replay + noise

    # 3. Normalize
    peak = replay.abs().max()

    if peak > 0:
        replay = replay / peak

    return replay


# ============================================================
# SEGMENTATION
# ============================================================

def split_audio(
    waveform: torch.Tensor,
    segment_seconds: float = SEGMENT_SECONDS,
    hop_seconds: float = HOP_SECONDS,
) -> list[torch.Tensor]:

    segment_samples = int(segment_seconds * TARGET_SR)
    hop_samples = int(hop_seconds * TARGET_SR)

    segments = []

    start = 0

    while start + segment_samples <= waveform.shape[-1]:

        segment = waveform[:, start:start + segment_samples]

        segments.append(segment)

        start += hop_samples

    return segments


# ============================================================
# EMBEDDINGS
# ============================================================

def get_embeddings(
    model,
    segments: list[torch.Tensor],
) -> list[torch.Tensor]:

    embeddings = []

    for segment in segments:

        with torch.inference_mode():

            embedding = model.encode_batch(
                segment.to(DEVICE)
            )

        embedding = embedding.squeeze().detach().cpu()

        embeddings.append(embedding)

    return embeddings


# ============================================================
# SIMILARITY
# ============================================================

def pairwise_similarity(
    embeddings: list[torch.Tensor],
) -> list[float]:

    scores = []

    for a, b in combinations(embeddings, 2):

        a = a.flatten().unsqueeze(0)
        b = b.flatten().unsqueeze(0)

        score = F.cosine_similarity(a, b).item()

        scores.append(float(score))

    return scores


def summarize(
    name: str,
    embeddings: list[torch.Tensor],
):

    scores = pairwise_similarity(embeddings)

    print()
    print("=" * 70)
    print(name)
    print("=" * 70)

    print(f"Segments: {len(embeddings)}")
    print(f"Pairs: {len(scores)}")

    print(f"Mean similarity:   {mean(scores):.4f}")
    print(f"Median similarity: {median(scores):.4f}")
    print(f"Minimum:           {min(scores):.4f}")
    print(f"Maximum:           {max(scores):.4f}")

    return scores


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("CHECKPOINT 6 - REPLAY-LIKE ROBUSTNESS")
print("=" * 70)

print()
print(f"Device: {DEVICE}")

print()
print("Loading ECAPA-TDNN...")

model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    run_opts={"device": DEVICE},
)

print("ECAPA model loaded successfully.")


# ------------------------------------------------------------
# CLEAN AUDIO
# ------------------------------------------------------------

clean = load_audio(INPUT_FILE)

clean_segments = split_audio(clean)

print(f"Clean segments: {len(clean_segments)}")

clean_embeddings = get_embeddings(
    model,
    clean_segments,
)

clean_scores = summarize(
    "CLEAN AUDIO",
    clean_embeddings,
)


# ------------------------------------------------------------
# SIMULATED REPLAY
# ------------------------------------------------------------

replay = simulate_replay(clean)

replay_segments = split_audio(replay)

print()
print(f"Replay-like segments: {len(replay_segments)}")

replay_embeddings = get_embeddings(
    model,
    replay_segments,
)

replay_scores = summarize(
    "SIMULATED REPLAY-LIKE AUDIO",
    replay_embeddings,
)


# ------------------------------------------------------------
# FINAL COMPARISON
# ------------------------------------------------------------

clean_mean = mean(clean_scores)
clean_median = median(clean_scores)

replay_mean = mean(replay_scores)
replay_median = median(replay_scores)

print()
print("=" * 70)
print("FINAL REPLAY ROBUSTNESS RESULTS")
print("=" * 70)

print(
    f"{'Condition':<30}"
    f"{'Mean':>10}"
    f"{'Median':>10}"
    f"{'Min':>10}"
    f"{'Max':>10}"
)

print("-" * 70)

print(
    f"{'Clean':<30}"
    f"{clean_mean:>10.4f}"
    f"{clean_median:>10.4f}"
    f"{min(clean_scores):>10.4f}"
    f"{max(clean_scores):>10.4f}"
)

print(
    f"{'Replay-like':<30}"
    f"{replay_mean:>10.4f}"
    f"{replay_median:>10.4f}"
    f"{min(replay_scores):>10.4f}"
    f"{max(replay_scores):>10.4f}"
)

print()
print(f"Mean change:   {replay_mean - clean_mean:+.4f}")
print(f"Median change: {replay_median - clean_median:+.4f}")

print()
print("Experiment complete.")