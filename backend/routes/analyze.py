from fastapi import (
    APIRouter,
    UploadFile,
    File
)

from services.detector import detect_voice
from services.risk_engine import calculate_risk


router = APIRouter(
    prefix="/analyze"
)


@router.post("")
async def analyze(
    file: UploadFile = File(...)
):
    audio_bytes = await file.read()

    # Real multi-model deep inference
    prediction = await detect_voice(audio_bytes)

    # Risk calculation with model consensus and quality diagnostics
    risk = calculate_risk(
        fake_probability=prediction["fake_probability"],
        detector_results=prediction.get("detectors"),
        audio_quality=prediction.get("quality"),
    )

    return {
        "fake_probability": prediction["fake_probability"],
        "real_probability": prediction["real_probability"],
        **risk,
        "speaker_consistency": prediction.get("speaker_consistency", {}),
        "detectors": [
            {
                "model": d.get("model"),
                "raw_score": d.get("raw_score"),
                "latency_ms": d.get("latency_ms"),
            }
            for d in prediction.get("detectors", [])
        ],
        "quality": prediction.get("quality", {}),
    }