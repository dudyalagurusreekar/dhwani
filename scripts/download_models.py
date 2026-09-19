"""
Download script for Dhwani / EchoShield large models.
Downloads pre-trained models from Hugging Face:
- SpeechAntiSpoofingBenchmarks/W2V2-AASIST -> models/w2v2_aasist/w2v2-aasist.onnx (~1.26 GB)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models" / "w2v2_aasist"
MODEL_FILE = MODELS_DIR / "w2v2-aasist.onnx"

REPO_ID = "SpeechAntiSpoofingBenchmarks/W2V2-AASIST"
FILENAME = "w2v2-aasist.onnx"


def check_or_download_w2v2():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_FILE.exists():
        size_mb = MODEL_FILE.stat().st_size / (1024 * 1024)
        print(f"[OK] Model already exists: {MODEL_FILE} ({size_mb:.2f} MB)")
        return

    print("============================================================")
    print(" Dhwani / EchoShield - Model Downloader")
    print("============================================================")
    print(f"Downloading {FILENAME} from {REPO_ID}...")
    print(f"Target location: {MODEL_FILE}")
    print("This is ~1.26 GB and may take a few minutes depending on connection.")
    print("============================================================")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[ERROR] huggingface_hub is not installed.")
        print("Please run: pip install huggingface-hub")
        sys.exit(1)

    try:
        downloaded_path = hf_hub_download(
            repo_id=REPO_ID,
            filename=FILENAME,
            local_dir=str(MODELS_DIR),
        )
        print(f"\n[SUCCESS] Download completed: {downloaded_path}")
        size_mb = MODEL_FILE.stat().st_size / (1024 * 1024)
        print(f"File size: {size_mb:.2f} MB")
    except Exception as e:
        print(f"\n[FAILED] Download failed: {e}")
        print("\nAlternative manual download options:")
        print(f"1) CLI: hf download {REPO_ID} {FILENAME} --local-dir models/w2v2_aasist")
        print(f"2) Browser: https://huggingface.co/{REPO_ID}/resolve/main/{FILENAME}")
        sys.exit(1)


if __name__ == "__main__":
    check_or_download_w2v2()
