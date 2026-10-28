import asyncio
import re
import threading
import time
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from backend.streaming.capture import AudioChunk
from backend.streaming.stream_manager import StreamManager
from backend.services.detector import detect_voice, reset_session
from backend.services.risk_engine import calculate_risk
from security.auth import verify_websocket_auth, get_accepted_subprotocol

router = APIRouter()
stream_manager = StreamManager()

# Security and DoS boundaries
MAX_WS_FRAME_SIZE = 1024 * 1024       # 1 MB max frame payload
MAX_WS_FRAMES_PER_SESSION = 3600      # 1 hour at 1 chunk/sec
WS_IDLE_TIMEOUT_SECONDS = 60.0        # 60s inactivity timeout
MIN_CHUNK_INTERVAL_SEC = 0.02         # Max 50 chunks/sec rate ceiling
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,128}$")

# Active concurrent session tracking to prevent session hijacking and collision
ACTIVE_WS_SESSIONS = set()
ACTIVE_SESSIONS_LOCK = threading.Lock()


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    # 1. Verify authentication before full connection processing
    if not verify_websocket_auth(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_id = websocket.query_params.get("session_id")
    if not session_id or not SESSION_ID_PATTERN.match(session_id):
        await websocket.accept()
        await websocket.send_json({
            "error": "Valid session_id required (alphanumeric, dash, underscore, max 128 chars)"
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Prevent concurrent session hijacking: reject if session_id is currently active
    with ACTIVE_SESSIONS_LOCK:
        if session_id in ACTIVE_WS_SESSIONS:
            await websocket.accept()
            await websocket.send_json({
                "error": f"Session ID '{session_id}' is already active in a concurrent connection."
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        ACTIVE_WS_SESSIONS.add(session_id)

    subprotocol = get_accepted_subprotocol(websocket)
    await websocket.accept(subprotocol=subprotocol)
    sequence = 0
    last_chunk_time = 0.0

    try:
        while True:
            # Receive raw audio bytes with bounded idle timeout
            try:
                audio_bytes = await asyncio.wait_for(
                    websocket.receive_bytes(),
                    timeout=WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"error": "Session closed due to inactivity timeout."})
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return

            # Enforce max frame size to prevent memory exhaustion
            if len(audio_bytes) > MAX_WS_FRAME_SIZE:
                await websocket.send_json({
                    "error": f"Audio chunk exceeds maximum allowed size ({MAX_WS_FRAME_SIZE} bytes)"
                })
                await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                return

            # Enforce rate ceiling against flooding DoS
            now = time.monotonic()
            if last_chunk_time > 0 and (now - last_chunk_time) < MIN_CHUNK_INTERVAL_SEC:
                await websocket.send_json({"error": "Audio chunks submitted too rapidly (rate limit exceeded)."})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            last_chunk_time = now

            sequence += 1
            if sequence > MAX_WS_FRAMES_PER_SESSION:
                await websocket.send_json({
                    "error": f"Session frame limit ({MAX_WS_FRAMES_PER_SESSION}) exceeded"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

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
            prediction = await detect_voice(audio_to_eval, session_id=session_id)

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
        pass
    except Exception as e:
        print(f"WebSocket session {session_id} error: {e}")
    finally:
        with ACTIVE_SESSIONS_LOCK:
            ACTIVE_WS_SESSIONS.discard(session_id)
        # Guarantee session isolation: reset speaker profile and evict audio buffer
        reset_session(session_id)
        stream_manager.remove_session(session_id)