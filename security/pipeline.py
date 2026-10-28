"""
Dhwani / EchoShield - Complete 7-Stage Provenance Pipeline
Orchestrates the end-to-end security pipeline:
  AUDIO INPUT -> SHA-256 HASHING -> AI DETECTION -> RISK ENGINE
  -> SECURITY EVENT -> HASH CHAIN -> INTEGRITY VERIFICATION
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

from .audit_chain import AuditHashChain
from .hasher import AudioHasher
from .privacy import EphemeralAudioBuffer
from .risk_engine import RiskAssessment, RiskEngine
from .schemas import (
    ChainVerificationReport,
    EventType,
    RiskAction,
    RiskLevel,
    SecurityEvent,
)


@dataclass(frozen=True)
class PipelineResult:
    """Consolidated outcome of the 7-stage Dhwani security pipeline."""
    session_id: str
    audio_hash: str
    provenance_token: str
    ai_score: float
    confidence: float
    risk_assessment: RiskAssessment
    security_event: SecurityEvent
    chain_length: int
    chain_hash: str
    is_chain_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "audio_hash": self.audio_hash,
            "provenance_token": self.provenance_token,
            "ai_score": round(self.ai_score, 6),
            "confidence": round(self.confidence, 6),
            "risk_assessment": self.risk_assessment.to_dict(),
            "security_event": self.security_event.to_dict(),
            "chain_length": self.chain_length,
            "chain_hash": self.chain_hash,
            "is_chain_valid": self.is_chain_valid,
        }


class DhwaniProvenancePipeline:
    """
    Unified execution pipeline coordinating hashing, inference, risk classification,
    tamper-evident audit recording, and chain verification.
    """

    def __init__(
        self,
        audit_chain: Optional[AuditHashChain] = None,
        risk_engine: Optional[RiskEngine] = None,
        persistence_file: Optional[Union[str, Path]] = None,
    ):
        self.chain = audit_chain or AuditHashChain(persistence_file=persistence_file)
        self.risk_engine = risk_engine or RiskEngine()

    def process_audio(
        self,
        audio_data: Union[bytes, bytearray, memoryview],
        session_id: str,
        ai_detector: Optional[Callable[[bytes], Tuple[float, float]]] = None,
        audio_metadata: Optional[Dict[str, Any]] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Execute the complete 7-stage security and provenance pipeline:

        Stage 1: AUDIO INPUT -> Ingest into EphemeralAudioBuffer
        Stage 2: SHA-256 HASHING -> Compute cryptographic hash of audio & session
        Stage 3: AI DETECTION -> Pass in-memory buffer to model
        Stage 4: RISK ENGINE -> Evaluate risk level, confidence, and action
        Stage 5: SECURITY EVENT -> Generate standardized canonical event
        Stage 6: HASH CHAIN -> Append event to immutable ledger
        Stage 7: INTEGRITY VERIFICATION -> Audit chain integrity
        """
        audio_metadata = audio_metadata or {}
        session_metadata = session_metadata or {}

        # STAGE 1: AUDIO INPUT (Protected by Ephemeral Sandbox)
        with EphemeralAudioBuffer(audio_data, session_id=session_id) as audio_ctx:

            # STAGE 2: SHA-256 HASHING
            audio_hash = audio_ctx.audio_hash
            session_ctx_hash = AudioHasher.hash_session_metadata({
                "session_id": session_id,
                **session_metadata,
            })
            provenance_token = AudioHasher.bind_session_and_audio(session_ctx_hash, audio_hash)

            # STAGE 3: AI DETECTION (In-memory execution)
            if ai_detector:
                raw_buffer = audio_ctx.get_buffer()
                ai_score, confidence = ai_detector(raw_buffer)
            else:
                # Default baseline if no detector is provided
                ai_score, confidence = 0.05, 0.99

            # Audio buffer will be wiped from memory immediately upon leaving this 'with' block

        # STAGE 4: RISK ENGINE
        risk_assessment = self.risk_engine.evaluate(
            ai_score=ai_score,
            confidence=confidence,
            model_name=audio_metadata.get("model_name", "AASIST"),
            audio_metadata=audio_metadata,
            session_id=session_id,
        )

        # STAGE 5: SECURITY EVENT
        event_payload = {
            "provenance_token": provenance_token,
            "session_context_hash": session_ctx_hash,
            "ai_score": round(ai_score, 6),
            "confidence": round(confidence, 6),
            "risk_assessment": risk_assessment.to_dict(),
            "audio_metadata": audio_metadata,
        }

        # STAGE 6: HASH CHAIN
        security_event = self.chain.append_event(
            session_id=session_id,
            event_type=EventType.AI_INFERENCE_COMPLETED,
            audio_hash=audio_hash,
            payload=event_payload,
        )

        # STAGE 7: INTEGRITY VERIFICATION
        verification_report = self.chain.verify_integrity()

        return PipelineResult(
            session_id=session_id,
            audio_hash=audio_hash,
            provenance_token=provenance_token,
            ai_score=ai_score,
            confidence=confidence,
            risk_assessment=risk_assessment,
            security_event=security_event,
            chain_length=self.chain.length,
            chain_hash=security_event.chain_hash,
            is_chain_valid=verification_report.is_valid,
        )

    def verify_chain(self) -> ChainVerificationReport:
        """Audit the entire hash chain for integrity."""
        return self.chain.verify_integrity()
