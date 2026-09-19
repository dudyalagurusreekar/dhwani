from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path for security package import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from security import (
    AudioHasher,
    EphemeralAudioBuffer,
    EventType,
    get_global_pipeline,
)
from services.detector import detect_voice
from services.risk_engine import calculate_risk
from streaming.capture import AudioChunk
from streaming.stream_manager import StreamManager

router = APIRouter()
stream_manager = StreamManager()


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()

    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.send_json({"error": "session_id required"})
        await websocket.close()
        return

    pipeline = get_global_pipeline()

    # Log session start into the cryptographic audit chain
    pipeline.chain.append_event(
        session_id=session_id,
        event_type=EventType.SESSION_START,
        payload={"transport": "websocket", "client": "streaming_caller"},
    )

    sequence = 0

    try:
        while True:
            # Receive raw audio chunk
            audio_bytes = await websocket.receive_bytes()
            sequence += 1

            # STAGE 1 & 2: Ingest into Ephemeral Sandbox & Compute SHA-256 Fingerprint
            with EphemeralAudioBuffer(audio_bytes, session_id=session_id) as audio_ctx:
                chunk_hash = audio_ctx.audio_hash

                # Compute dual-anchor stream provenance token
                session_meta_hash = AudioHasher.hash_session_metadata({
                    "session_id": session_id,
                    "sequence": sequence,
                })
                provenance_token = AudioHasher.bind_session_and_audio(session_meta_hash, chunk_hash)

                # Create chunk for VAD
                chunk = AudioChunk(
                    session_id=session_id,
                    sequence=sequence,
                    audio_bytes=audio_ctx.get_buffer(),
                    sample_rate=16000,
                    channels=1,
                )

                # Process VAD + buffer
                stream_result = stream_manager.process_chunk(chunk)

                if not stream_result["speech"]:
                    await websocket.send_json({
                        "session_id": session_id,
                        "sequence": sequence,
                        "speech": False,
                        "status": "NO_SPEECH",
                        "audio_hash": chunk_hash,
                    })
                    continue

                # STAGE 3: AI Inference (in-memory buffer)
                prediction = await detect_voice(audio_ctx.get_buffer())

            # Audio buffer is guaranteed memory-wiped upon exiting the with block

            # STAGE 4: Risk Engine
            risk = calculate_risk(prediction["fake_probability"])

            # STAGE 5 & 6: Security Event & Hash Chain Append
            event = pipeline.chain.append_event(
                session_id=session_id,
                event_type=EventType.AI_INFERENCE_COMPLETED,
                audio_hash=chunk_hash,
                payload={
                    "sequence": sequence,
                    "fake_probability": prediction["fake_probability"],
                    "real_probability": prediction["real_probability"],
                    "risk_score": risk["risk_score"],
                    "risk_status": risk["status"],
                    "provenance_token": provenance_token,
                },
            )

            # Response with provenance verification token
            result = {
                "session_id": session_id,
                "sequence": sequence,
                "speech": True,
                "fake_probability": prediction["fake_probability"],
                "real_probability": prediction["real_probability"],
                "risk_score": risk["risk_score"],
                "status": risk["status"],
                "alert": risk["alert"],
                "recommendation": risk["recommendation"],
                "provenance": {
                    "audio_hash": chunk_hash,
                    "provenance_token": provenance_token,
                    "chain_hash": event.chain_hash,
                    "event_seq": event.seq_num,
                },
            }

            await websocket.send_json(result)

    except WebSocketDisconnect:
        # Record session termination in tamper-evident audit ledger
        pipeline.chain.append_event(
            session_id=session_id,
            event_type=EventType.SESSION_END,
            payload={"total_sequences": sequence, "reason": "client_disconnected"},
        )
        print(f"Session {session_id} disconnected cleanly (total chunks: {sequence})")

    except Exception as e:
        print(f"WebSocket error in session {session_id}: {e}")