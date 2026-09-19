"""
Dhwani / EchoShield - Security & Provenance Module
Unified public package interface.
"""

from .audit_chain import AuditHashChain, GENESIS_PREV_HASH
from .hasher import (
    AudioHasher,
    bind_provenance_token,
    compute_audio_hash,
    compute_file_hash,
    compute_metadata_hash,
    compute_numpy_hash,
    compute_stream_hash,
    verify_hash,
)
from .middleware import (
    DhwaniSecurityContext,
    fastapi_security_dependency,
    get_global_pipeline,
    set_global_pipeline,
)
from .pipeline import DhwaniProvenancePipeline, PipelineResult
from .privacy import BufferPurgedError, EphemeralAudioBuffer, ephemeral_audio_context
from .risk_engine import RiskEngine, RiskThresholds, SessionRiskContext
from .schemas import (
    ChainVerificationReport,
    EventType,
    RiskAction,
    RiskAssessment,
    RiskLevel,
    SecurityEvent,
    TamperType,
    get_current_utc_iso,
    to_canonical_json,
)

__all__ = [
    # Hasher
    "AudioHasher",
    "compute_audio_hash",
    "compute_stream_hash",
    "compute_file_hash",
    "compute_numpy_hash",
    "compute_metadata_hash",
    "bind_provenance_token",
    "verify_hash",
    # Audit Chain
    "AuditHashChain",
    "GENESIS_PREV_HASH",
    # Privacy
    "EphemeralAudioBuffer",
    "ephemeral_audio_context",
    "BufferPurgedError",
    # Risk Engine
    "RiskEngine",
    "RiskThresholds",
    "SessionRiskContext",
    # Pipeline
    "DhwaniProvenancePipeline",
    "PipelineResult",
    # Schemas
    "SecurityEvent",
    "EventType",
    "RiskLevel",
    "RiskAction",
    "RiskAssessment",
    "TamperType",
    "ChainVerificationReport",
    "get_current_utc_iso",
    "to_canonical_json",
    # Middleware
    "DhwaniSecurityContext",
    "get_global_pipeline",
    "set_global_pipeline",
    "fastapi_security_dependency",
]
