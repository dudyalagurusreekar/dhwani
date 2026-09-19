import os
from pathlib import Path
import sys
import time
from typing import Optional

# Setup environment pathing
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
for p in [str(BACKEND_DIR), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ai.common.gpu_utils import setup_nvidia_dll_paths
setup_nvidia_dll_paths()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.routes.health import router as health_router
from backend.routes.analyze import router as analyze_router
from backend.routes.sessions import router as session_router
from backend.websocket.audio import router as websocket_router

from ai.prevention.honeypot import VoiceHoneypotEngine
from ai.watermark.audio_watermark import AudioWatermarkEngine

app = FastAPI(
    title="EchoShield AI - Enterprise Voice Anti-Spoofing Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Routers from backend branch
app.include_router(health_router)
app.include_router(analyze_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(websocket_router)

# Prevention & Telemetry Engines
honeypot_engine = VoiceHoneypotEngine()
watermark_engine = AudioWatermarkEngine()


class ChallengeRequest(BaseModel):
    session_id: str = "caller_session_01"


@app.post("/api/honeypot/challenge")
async def create_honeypot_challenge(req: ChallengeRequest):
    return honeypot_engine.issue_challenge(req.session_id)


class VerifyChallengeRequest(BaseModel):
    session_id: str
    elapsed_seconds: float


@app.post("/api/honeypot/verify")
async def verify_honeypot_challenge(req: VerifyChallengeRequest):
    simulated_ts = honeypot_engine.active_challenges.get(req.session_id, {}).get("issued_at", time.time()) + req.elapsed_seconds
    return honeypot_engine.evaluate_response(
        session_id=req.session_id,
        response_timestamp=simulated_ts,
    )


@app.get("/")
async def root():
    return {
        "name": "EchoShield AI",
        "status": "running",
        "models": ["W2V2-AASIST", "AASIST", "AASIST-L", "ACOUSTIC", "ECAPA-TDNN"],
        "endpoints": ["/health", "/api/analyze", "/api/session", "/ws/audio"],
    }