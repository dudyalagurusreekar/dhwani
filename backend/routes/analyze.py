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

    audio_bytes = (
        await file.read()
    )

    prediction = (
        await detect_voice(
            audio_bytes
        )
    )

    risk = calculate_risk(
        prediction[
            "fake_probability"
        ]
    )

    return {

        "fake_probability":
            prediction[
                "fake_probability"
            ],

        "real_probability":
            prediction[
                "real_probability"
            ],

        **risk
    }