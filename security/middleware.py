"""
Dhwani / EchoShield - FastAPI Middleware & Dependency Injection
Provides integration utilities for FastAPI backends to trace audio requests,
bind session IDs, enforce audit logging, and inject the provenance pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import uuid

from .pipeline import DhwaniProvenancePipeline
from .schemas import EventType


class DhwaniSecurityContext:
    """Carries request-scoped provenance and security tracking metadata."""

    def __init__(self, session_id: str, pipeline: DhwaniProvenancePipeline):
        self.session_id = session_id
        self.pipeline = pipeline

    def record_event(
        self,
        event_type: EventType | str,
        audio_hash: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        """Helper to append an event into the request's audit chain."""
        return self.pipeline.chain.append_event(
            session_id=self.session_id,
            event_type=event_type,
            audio_hash=audio_hash,
            payload=payload or {},
        )


# Global default pipeline instance for app-wide audit logging
_GLOBAL_PIPELINE: Optional[DhwaniProvenancePipeline] = None


def get_global_pipeline(persistence_file: Optional[str] = None) -> DhwaniProvenancePipeline:
    """Retrieve or initialize the singleton application pipeline."""
    global _GLOBAL_PIPELINE
    if _GLOBAL_PIPELINE is None:
        _GLOBAL_PIPELINE = DhwaniProvenancePipeline(persistence_file=persistence_file)
    return _GLOBAL_PIPELINE


def set_global_pipeline(pipeline: DhwaniProvenancePipeline) -> None:
    """Explicitly assign a pipeline instance (useful in tests)."""
    global _GLOBAL_PIPELINE
    _GLOBAL_PIPELINE = pipeline


def fastapi_security_dependency(session_id: Optional[str] = None) -> DhwaniSecurityContext:
    """
    FastAPI dependency callable.
    Usage:
        @app.post("/detect")
        async def detect_audio(
            file: UploadFile,
            sec_ctx: DhwaniSecurityContext = Depends(fastapi_security_dependency)
        ):
            audio_bytes = await file.read()
            result = sec_ctx.pipeline.process_audio(audio_bytes, session_id=sec_ctx.session_id)
            return result.to_dict()
    """
    active_session_id = session_id or str(uuid.uuid4())
    pipeline = get_global_pipeline()
    return DhwaniSecurityContext(session_id=active_session_id, pipeline=pipeline)
