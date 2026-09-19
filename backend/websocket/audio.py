from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect
)

from backend.streaming.capture import AudioChunk
from backend.streaming.stream_manager import StreamManager

from backend.services.detector import detect_voice
from backend.services.risk_engine import calculate_risk


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

    sequence = 0

    try:
        while True:
            # Receive raw audio bytes (PCM16 or container)
            audio_bytes = await websocket.receive_bytes()
            sequence += 1

            # Create chunk
            chunk = AudioChunk(
                session_id=session_id,
                sequence=sequence,
                audio_bytes=audio_bytes,
                sample_rate=16000,
                channels=1
            )

            # VAD + buffer
            stream_result = stream_manager.process_chunk(chunk)

            # No speech
            if not stream_result["speech"]:
                await websocket.send_json({
                    "session_id": session_id,
                    "sequence": sequence,
                    "speech": False,
                    "status": "NO_SPEECH",
                    "risk_score": 0,
                    "alert": "Silence / background noise detected",
                    "recommendation": "CONTINUE",
                })
                continue

            # Retrieve accumulated audio window from session buffer for deep model context
            buf = stream_manager.get_buffer(session_id)
            audio_to_eval = buf.get_audio() if buf.size() > 0 else audio_bytes

            # Real multi-model deep inference
            prediction = await detect_voice(audio_to_eval)

            # Multi-model risk calculation & active prevention policy
            risk = calculate_risk(
                fake_probability=prediction["fake_probability"],
                detector_results=prediction.get("detectors"),
                audio_quality=prediction.get("quality"),
            )

            # Standardized + enriched response contract
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
                "attack_vector": risk.get("attack_vector", "UNKNOWN"),
                "consensus_level": risk.get("consensus_level", "UNANIMOUS"),
                "consensus_explanation": risk.get("consensus_explanation", ""),
                "policy_action": risk.get("policy_action", "ALLOW"),
                "policy_severity": risk.get("policy_severity", "INFO"),
                "policy_reason": risk.get("policy_reason", ""),
                "detectors": [
                    {
                        "model": d.get("model"),
                        "raw_score": d.get("raw_score"),
                        "latency_ms": d.get("latency_ms"),
                    }
                    for d in prediction.get("detectors", [])
                ],
            }

            await websocket.send_json(result)

    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")

    except Exception as e:
        print(f"WebSocket error: {e}")