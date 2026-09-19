import sys
import torch
import librosa
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

MODEL_NAME = "garystafford/wav2vec2-deepfake-voice-detector"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Loading W2V2 deepfake detector...")

feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_NAME)
model = AutoModelForAudioClassification.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()

print(f"Model loaded on {device}")


def detect(audio_path):
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)

    inputs = feature_extractor(
        audio,
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(outputs.logits, dim=-1)[0]

    result = {
        model.config.id2label[i]: float(probabilities[i])
        for i in range(len(probabilities))
    }

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python w2v2_detector.py <audio_file>")
        sys.exit(1)

    print(detect(sys.argv[1]))