import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf
import librosa


class W2V2AASISTDetector:
    SAMPLE_RATE = 16000
    WINDOW_SAMPLES = 64600

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}"
            )

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=[
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def prepare_audio(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> np.ndarray:

        audio = np.asarray(audio, dtype=np.float32)

        # Stereo/multichannel → mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # Resample → 16 kHz
        if sample_rate != self.SAMPLE_RATE:
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=self.SAMPLE_RATE,
            )

        # Remove DC offset
        audio = audio - np.mean(audio)

        # Prevent NaN/Inf
        audio = np.nan_to_num(audio)

        # Exactly one model window
        if len(audio) < self.WINDOW_SAMPLES:
            audio = np.pad(
                audio,
                (0, self.WINDOW_SAMPLES - len(audio)),
                mode="constant",
            )
        else:
            audio = audio[:self.WINDOW_SAMPLES]

        return audio.astype(np.float32)

    def predict_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> dict:

        audio = self.prepare_audio(audio, sample_rate)

        model_input = audio[np.newaxis, :]

        start = time.perf_counter()

        outputs = self.session.run(
            [self.output_name],
            {self.input_name: model_input},
        )

        latency_ms = (
            time.perf_counter() - start
        ) * 1000

        logits = np.asarray(outputs[0])[0]

        # W2V2-AASIST:
        # class 1 = bona fide
        bona_fide_logit = float(logits[1])
        spoof_logit = float(logits[0])

        return {
            "model": "W2V2-AASIST",
            "bona_fide_logit": bona_fide_logit,
            "spoof_logit": spoof_logit,
            "latency_ms": round(latency_ms, 2),
            "sample_rate": self.SAMPLE_RATE,
            "window_samples": self.WINDOW_SAMPLES,
            "window_seconds": round(
                self.WINDOW_SAMPLES / self.SAMPLE_RATE,
                3,
            ),
        }

    def predict_file(self, audio_path: str) -> dict:

        audio, sample_rate = sf.read(
            audio_path,
            dtype="float32",
        )

        return self.predict_audio(
            audio,
            sample_rate,
        )


if __name__ == "__main__":

    MODEL_PATH = (
        "models/w2v2_aasist/"
        "w2v2-aasist.onnx"
    )

    AUDIO_PATH = "real_speech.wav"

    detector = W2V2AASISTDetector(
        MODEL_PATH
    )

    print("\n=== W2V2-AASIST DETECTOR ===")
    print("Providers:")
    print(detector.session.get_providers())

    print("\nAnalyzing:")
    print(AUDIO_PATH)

    result = detector.predict_file(
        AUDIO_PATH
    )

    print("\nResult:")

    for key, value in result.items():
        print(f"{key}: {value}")