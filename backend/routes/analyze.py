from typing import Optional
import uuid
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Header,
    HTTPException,
)

from backend.services.detector import detect_voice
from backend.services.risk_engine import calculate_risk
from security import (
    get_global_pipeline,
    AudioHasher,
    EventType,
)


router = APIRouter(
    prefix="/analyze"
)


@router.post("")
async def analyze(
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    audio_bytes = await file.read()

    # Reject empty files immediately
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file provided.")

    # Real multi-model deep inference
    prediction = await detect_voice(audio_bytes)

    # Risk calculation with model consensus and quality diagnostics
    risk = calculate_risk(
        fake_probability=prediction["fake_probability"],
        detector_results=prediction.get("detectors"),
        audio_quality=prediction.get("quality"),
    )

    # Record tamper-evident cryptographic security audit event
    session_id = x_session_id or f"sess_{uuid.uuid4().hex[:12]}"
    pipeline = get_global_pipeline()
    audio_hash = AudioHasher.compute_audio_hash(audio_bytes)
    session_ctx_hash = AudioHasher.hash_session_metadata({"session_id": session_id})
    provenance_token = AudioHasher.bind_session_and_audio(session_ctx_hash, audio_hash)

    event = pipeline.chain.append_event(
        session_id=session_id,
        event_type=EventType.AI_INFERENCE_COMPLETED,
        audio_hash=audio_hash,
        payload={
            "provenance_token": provenance_token,
            "fake_probability": prediction["fake_probability"],
            "risk_score": risk.get("risk_score", 0.0),
            "risk_status": risk.get("status", "LOW"),
        },
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
        "provenance": {
            "audio_hash": audio_hash,
            "provenance_token": provenance_token,
            "chain_hash": event.chain_hash,
            "event_seq": event.seq_num,
        },
    }