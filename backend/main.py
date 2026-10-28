import os
from pathlib import Path
import sys
import time
from typing import Optional

# Setup environment pathing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) in sys.path:
    sys.path.remove(str(BACKEND_DIR))
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.gpu_utils import setup_nvidia_dll_paths
setup_nvidia_dll_paths()

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from security.auth import require_api_key, verify_websocket_auth
from backend.routes.health import router as health_router
from backend.routes.analyze import router as analyze_router
from backend.routes.sessions import router as session_router
from backend.routes.system import router as system_router
from backend.routes.media_analysis import router as media_router
from backend.routes.incidents import router as incidents_router
from backend.routes.audit import router as audit_router
from backend.routes.twilio_routes import router as twilio_router
from backend.websocket.audio import router as websocket_router
from backend.websocket.dashboard import dashboard_manager
from streaming.telephony.twilio_websocket import handle_twilio_media_stream

from ai.prevention.honeypot import VoiceHoneypotEngine
from ai.watermark.audio_watermark import AudioWatermarkEngine

app = FastAPI(
    title="Dhwani / EchoShield AI - Enterprise Voice Anti-Spoofing Platform",
    version="2.1.0"
)

# Environment-configurable CORS allowlist without wildcard credentials violation
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001")
)
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
# Per W3C CORS spec: wildcard '*' cannot be combined with credentials
allow_credentials = False if (len(allowed_origins) == 1 and allowed_origins[0] == "*") else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Session-ID"],
)

# Core Routers: Public Health/Readiness & Telephony Webhooks
app.include_router(health_router)
app.include_router(twilio_router)  # Twilio signature validation handled in route
app.include_router(websocket_router)  # Audio WebSocket handles its own auth handshake

# Protected REST API Routes (enforces API key / Bearer auth when configured)
api_dependencies = [Depends(require_api_key)]
app.include_router(analyze_router, prefix="/api", dependencies=api_dependencies)
app.include_router(session_router, prefix="/api", dependencies=api_dependencies)
app.include_router(system_router, prefix="/api", dependencies=api_dependencies)
app.include_router(media_router, prefix="/api", dependencies=api_dependencies)
app.include_router(incidents_router, prefix="/api", dependencies=api_dependencies)
app.include_router(audit_router, prefix="/api", dependencies=api_dependencies)


# Real-time WebSocket Endpoints
@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """Real-time telemetry and risk stream to connected web dashboards."""
    if not verify_websocket_auth(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await dashboard_manager.connect(websocket)
    try:
        while True:
            # Keep alive and listen for client commands/pings
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        await dashboard_manager.disconnect(websocket)
    except Exception:
        await dashboard_manager.disconnect(websocket)


@app.websocket("/twilio/media")
async def twilio_media_stream_endpoint(websocket: WebSocket):
    """Real-time G.711 u-law audio stream receiver for Twilio Programmable Voice."""
    await handle_twilio_media_stream(websocket)


# Prevention & Telemetry Engines
honeypot_engine = VoiceHoneypotEngine()
watermark_engine = AudioWatermarkEngine()


class ChallengeRequest(BaseModel):
    session_id: str = "caller_session_01"


@app.post("/api/honeypot/challenge", dependencies=api_dependencies)
async def create_honeypot_challenge(req: ChallengeRequest):
    return honeypot_engine.issue_challenge(req.session_id)


class VerifyChallengeRequest(BaseModel):
    session_id: str
    elapsed_seconds: float


@app.post("/api/honeypot/verify", dependencies=api_dependencies)
async def verify_honeypot_challenge(req: VerifyChallengeRequest):
    simulated_ts = honeypot_engine.active_challenges.get(req.session_id, {}).get("issued_at", time.time()) + req.elapsed_seconds
    return honeypot_engine.evaluate_response(
        session_id=req.session_id,
        response_timestamp=simulated_ts,
    )


@app.get("/")
async def root():
    return {
        "name": "Dhwani / EchoShield AI",
        "status": "running",
        "models": ["W2V2-AASIST", "AASIST", "AASIST-L", "ACOUSTIC", "ECAPA-TDNN"],
        "endpoints": [
            "/health",
            "/api/system/status",
            "/api/analyze/upload",
            "/api/analyze/youtube",
            "/api/incidents",
            "/twilio/voice",
            "/twilio/media",
            "/ws/dashboard",
            "/ws/audio",
        ],
    }