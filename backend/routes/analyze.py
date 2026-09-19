from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from security import (
    AudioHasher,
    EphemeralAudioBuffer,
    EventType,
    get_global_pipeline,
)
from services.detector import detect_voice
from services.risk_engine import calculate_risk

router = APIRouter(prefix="/analyze", tags=["Voice Analysis"])


@router.post("", summary="Analyze voice sample for deepfake spoofing with cryptographic provenance")
async def analyze(
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    session_id = x_session_id or f"sess_{os.urandom(8).hex()}"
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file provided")

    pipeline = get_global_pipeline()

    # STAGE 1 & 2: Ephemeral In-Memory Sandbox & SHA-256 Hashing (Zero Raw Audio Retention)
    with EphemeralAudioBuffer(audio_bytes, session_id=session_id) as audio_ctx:
        audio_hash = audio_ctx.audio_hash

        # Generate dual-anchor provenance token
        session_ctx_hash = AudioHasher.hash_session_metadata({
            "session_id": session_id,
            "filename": file.filename,
            "content_type": file.content_type,
        })
        provenance_token = AudioHasher.bind_session_and_audio(session_ctx_hash, audio_hash)

        # STAGE 3: AI Inference (in-memory buffer pass)
        prediction = await detect_voice(audio_ctx.get_buffer())

    # Raw audio bytes are guaranteed memory-wiped and purged upon exiting the 'with' block

    # STAGE 4: Risk Engine Evaluation
    risk = calculate_risk(prediction["fake_probability"])

    # STAGE 5 & 6: Security Event & Cryptographic Hash Chain Append
    event = pipeline.chain.append_event(
        session_id=session_id,
        event_type=EventType.AI_INFERENCE_COMPLETED,
        audio_hash=audio_hash,
        payload={
            "provenance_token": provenance_token,
            "fake_probability": prediction["fake_probability"],
            "real_probability": prediction["real_probability"],
            "risk_score": risk.get("risk_score"),
            "risk_status": risk.get("status"),
            "recommendation": risk.get("recommendation"),
            "filename": file.filename,
        },
    )

    return {
        "session_id": session_id,
        "fake_probability": prediction["fake_probability"],
        "real_probability": prediction["real_probability"],
        "provenance": {
            "audio_hash": audio_hash,
            "provenance_token": provenance_token,
            "chain_hash": event.chain_hash,
            "event_seq": event.seq_num,
        },
        **risk,
    }