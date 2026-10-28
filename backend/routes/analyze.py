import io
import os
from typing import Optional
import uuid
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Header,
    HTTPException,
    Request,
)
import soundfile as sf

from backend.services.detector import detect_voice
from backend.services.risk_engine import calculate_risk
from security import (
    get_global_pipeline,
    AudioHasher,
    EventType,
)

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)))
CHUNK_SIZE = 1024 * 1024  # 1 MB

router = APIRouter(
    prefix="/analyze"
)


@router.post("")
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    # Pre-check Content-Length header if present
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds maximum permitted size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
                )
        except ValueError:
            pass

    # Read in bounded chunks to prevent streaming memory exhaustion
    total_size = 0
    chunks = []
    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds maximum permitted size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
            )
        chunks.append(chunk)

    audio_bytes = b"".join(chunks)

    # Reject empty files immediately
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file provided.")

    MAX_AUDIO_DURATION_SEC = 300.0  # 5 minutes
    MAX_CHANNELS = 8
    MAX_SAMPLE_RATE = 192000

    # Validate audio readability or known container before deep inference
    is_valid_audio = False
    try:
        with io.BytesIO(audio_bytes) as bio:
            with sf.SoundFile(bio) as sf_file:
                if sf_file.frames > 0:
                    if sf_file.channels > MAX_CHANNELS:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Audio channel count ({sf_file.channels}) exceeds maximum allowed ({MAX_CHANNELS}).",
                        )
                    if sf_file.samplerate > MAX_SAMPLE_RATE:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Audio sample rate ({sf_file.samplerate} Hz) exceeds maximum allowed ({MAX_SAMPLE_RATE} Hz).",
                        )
                    duration_sec = sf_file.frames / sf_file.samplerate if sf_file.samplerate > 0 else 0
                    if duration_sec > MAX_AUDIO_DURATION_SEC:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Audio duration ({duration_sec:.1f}s) exceeds maximum allowed ({MAX_AUDIO_DURATION_SEC}s).",
                        )
                    is_valid_audio = True
    except HTTPException:
        raise
    except Exception:
        # Allow mock or raw audio starting with known magic headers
        if audio_bytes.startswith(b"RIFF") or audio_bytes.startswith(b"OggS") or audio_bytes.startswith(b"fLaC") or audio_bytes.startswith(b"ID3"):
            is_valid_audio = True

    if not is_valid_audio:
        raise HTTPException(
            status_code=400,
            detail="Malformed or unsupported audio payload. File could not be parsed as valid audio.",
        )

    session_id = x_session_id or f"sess_{uuid.uuid4().hex[:12]}"

    # Real multi-model deep inference
    prediction = await detect_voice(audio_bytes, session_id=session_id)

    # Risk calculation with model consensus and quality diagnostics
    risk = calculate_risk(
        fake_probability=prediction["fake_probability"],
        detector_results=prediction.get("detectors"),
        audio_quality=prediction.get("quality"),
    )

    # Record tamper-evident cryptographic security audit event
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