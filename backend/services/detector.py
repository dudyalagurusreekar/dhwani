import os
import uuid
import subprocess
import tempfile

import torch
import librosa
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification


MODEL_NAME = "garystafford/wav2vec2-deepfake-voice-detector"

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"Loading W2V2 detector on {device}...")

feature_extractor = AutoFeatureExtractor.from_pretrained(
    MODEL_NAME
)

model = AutoModelForAudioClassification.from_pretrained(
    MODEL_NAME
)

model.to(device)
model.eval()

print("W2V2 detector loaded.")


async def detect_voice(audio_bytes: bytes):

    input_id = str(uuid.uuid4())

    input_file = os.path.join(
        tempfile.gettempdir(),
        f"dhwani_input_{input_id}.m4a"
    )

    output_file = os.path.join(
        tempfile.gettempdir(),
        f"dhwani_input_{input_id}.wav"
    )

    try:

        with open(input_file, "wb") as f:
            f.write(audio_bytes)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_file,
                "-ar",
                "16000",
                "-ac",
                "1",
                output_file
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        audio, sr = librosa.load(
            output_file,
            sr=16000,
            mono=True
        )

        inputs = feature_extractor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
            padding=True
        )

        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }

        with torch.no_grad():
            outputs = model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )[0]

        labels = model.config.id2label

        fake_probability = 0.0
        real_probability = 0.0

        for index, probability in enumerate(probabilities):

            label = labels[index].lower()
            value = float(probability)

            if "fake" in label:
                fake_probability = value

            elif "real" in label:
                real_probability = value

        return {
            "fake_probability": fake_probability,
            "real_probability": real_probability
        }

    finally:

        if os.path.exists(input_file):
            os.remove(input_file)

        if os.path.exists(output_file):
            os.remove(output_file)