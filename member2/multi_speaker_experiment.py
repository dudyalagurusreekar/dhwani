import os
import torch
import torchaudio
import torch.nn.functional as F
from itertools import combinations
from statistics import mean, median
from speechbrain.inference.speaker import EncoderClassifier

A1 = "member2/audio/real_speech.wav"
A2 = "member2/audio/real_speech_session2.wav"

B1 = "member2/audio/friend.wav"
B2 = "member2/audio/friend_session2.wav"

C1 = "member2/audio/speaker_c_session1.wav"
C2 = "member2/audio/speaker_c_session2.wav"

FILES = {
    "A1": A1, "A2": A2,
    "B1": B1, "B2": B2,
    "C1": C1, "C2": C2
}

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading ECAPA-TDNN...")
model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    run_opts={"device": device}
)

def load_audio(path):
    wav, sr = torchaudio.load(path)

    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)

    if sr != 16000:
        wav = torchaudio.functional.resample(
            wav, sr, 16000
        )

    return wav

def segment(wav, seconds=2.0, hop=1.0):
    size = int(seconds * 16000)
    step = int(hop * 16000)

    segments = []
    start = 0

    while start + size <= wav.shape[-1]:
        segments.append(wav[:, start:start + size])
        start += step

    return segments

def embeddings(path):
    wav = load_audio(path)
    segments = segment(wav)

    result = []

    for s in segments:
        with torch.inference_mode():
            e = model.encode_batch(
                s.to(device)
            ).squeeze().flatten()

        result.append(e.cpu())

    return result

print("\nCreating embeddings...")
all_embeddings = {}

for name, path in FILES.items():
    print(f"{name}: {os.path.basename(path)}")
    all_embeddings[name] = embeddings(path)
    print(f"  segments = {len(all_embeddings[name])}")

def compare(file1, file2):
    scores = []

    for a in all_embeddings[file1]:
        for b in all_embeddings[file2]:
            score = F.cosine_similarity(
                a.unsqueeze(0),
                b.unsqueeze(0)
            ).item()

            scores.append(score)

    return {
        "pairs": len(scores),
        "mean": mean(scores),
        "median": median(scores),
        "min": min(scores),
        "max": max(scores)
    }

pairs = [
    ("SAME", "A1", "A2"),
    ("SAME", "B1", "B2"),
    ("SAME", "C1", "C2"),

    ("DIFFERENT", "A1", "B1"),
    ("DIFFERENT", "A1", "C1"),
    ("DIFFERENT", "B1", "C1"),
]

print("\n" + "=" * 70)
print("MULTI-SPEAKER CROSS-SESSION EXPERIMENT")
print("=" * 70)

results = []

for label, f1, f2 in pairs:
    r = compare(f1, f2)

    results.append((label, f1, f2, r))

    print(
        f"\n{label:9} {f1} vs {f2}"
    )
    print(
        f"pairs   : {r['pairs']}"
    )
    print(
        f"mean    : {r['mean']:.4f}"
    )
    print(
        f"median  : {r['median']:.4f}"
    )
    print(
        f"min     : {r['min']:.4f}"
    )
    print(
        f"max     : {r['max']:.4f}"
    )

same = [r["mean"] for label, _, _, r in results if label == "SAME"]
different = [r["mean"] for label, _, _, r in results if label == "DIFFERENT"]

print("\n" + "=" * 70)
print("RECORDING-PAIR SUMMARY")
print("=" * 70)

print(f"Same-speaker recording-pair means:")
for x in same:
    print(f"  {x:.4f}")

print(f"\nDifferent-speaker recording-pair means:")
for x in different:
    print(f"  {x:.4f}")

print(f"\nSame-speaker average : {mean(same):.4f}")
print(f"Different-speaker average : {mean(different):.4f}")
print(f"Difference : {mean(same) - mean(different):.4f}")

print("\nEXPERIMENT COMPLETE")
