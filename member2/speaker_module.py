import time
from statistics import mean, median

import torch
import torchaudio
import torch.nn.functional as F
from speechbrain.inference.speaker import EncoderClassifier


class SpeakerConsistencyAnalyzer:

    def __init__(
        self,
        model_name="speechbrain/spkrec-ecapa-voxceleb",
        segment_seconds=2.0,
        hop_seconds=1.0,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.segment_seconds = segment_seconds
        self.hop_seconds = hop_seconds

        self.model = EncoderClassifier.from_hparams(
            source=model_name,
            run_opts={"device": self.device},
        )

    def load_audio(self, path):
        waveform, sample_rate = torchaudio.load(path)

        # Convert stereo -> mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Convert to 16 kHz
        if sample_rate != 16000:
            waveform = torchaudio.functional.resample(
                waveform,
                sample_rate,
                16000,
            )

        return waveform

    def segment_audio(self, waveform):
        segment_samples = int(
            self.segment_seconds * 16000
        )

        hop_samples = int(
            self.hop_seconds * 16000
        )

        segments = []
        start = 0

        while start + segment_samples <= waveform.shape[-1]:
            segments.append(
                waveform[:, start:start + segment_samples]
            )
            start += hop_samples

        return segments

    def create_embeddings(self, segments):
        embeddings = []

        for segment in segments:
            with torch.inference_mode():
                embedding = self.model.encode_batch(
                    segment.to(self.device)
                )

            embedding = embedding.squeeze().flatten().cpu()
            embeddings.append(embedding)

        return embeddings

    def calculate_similarities(self, embeddings):
        scores = []

        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):

                score = F.cosine_similarity(
                    embeddings[i].unsqueeze(0),
                    embeddings[j].unsqueeze(0),
                ).item()

                scores.append(float(score))

        return scores

    def analyze(self, audio_path):
        start_time = time.perf_counter()

        waveform = self.load_audio(audio_path)

        duration = waveform.shape[-1] / 16000

        segments = self.segment_audio(waveform)

        if len(segments) < 2:
            raise ValueError(
                "Audio must contain at least two complete segments."
            )

        embeddings = self.create_embeddings(segments)

        similarities = self.calculate_similarities(
            embeddings
        )

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        result = {
            "model": "ECAPA-TDNN",
            "device": self.device,
            "speaker_consistency": float(
                median(similarities)
            ),
            "median_similarity": float(
                median(similarities)
            ),
            "mean_similarity": float(
                mean(similarities)
            ),
            "min_similarity": float(
                min(similarities)
            ),
            "max_similarity": float(
                max(similarities)
            ),
            "segments_used": len(segments),
            "num_pairs": len(similarities),
            "duration_seconds": round(
                duration, 3
            ),
            "latency_ms": round(
                latency_ms, 2
            ),
        }

        return result


if __name__ == "__main__":

    analyzer = SpeakerConsistencyAnalyzer()

    test_files = [
        "member2/audio/real_speech.wav",
        "member2/audio/real_speech_session2.wav",
        "member2/audio/friend.wav",
        "member2/audio/friend_session2.wav",
        "member2/audio/speaker_c_session1.wav",
        "member2/audio/speaker_c_session2.wav",
    ]

    print("\n" + "=" * 70)
    print("MEMBER 2 - SPEAKER CONSISTENCY MODULE")
    print("=" * 70)

    for path in test_files:

        print(f"\nFILE: {path}")

        result = analyzer.analyze(path)

        for key, value in result.items():
            print(f"{key:22}: {value}")

    print("\n" + "=" * 70)
    print("MODULE TEST COMPLETE")
    print("=" * 70)

