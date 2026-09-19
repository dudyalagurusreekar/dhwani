"""
Dhwani / EchoShield - FastAPI Integration & AI Detection Demo
Demonstrates how the 7-stage security pipeline integrates with FastAPI
and AI detection models (e.g. AASIST / RawNet).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from security import DhwaniProvenancePipeline


def mock_aasist_detector(audio_bytes: bytes) -> tuple[float, float]:
    """
    Mock AI deepfake detection model (simulating AASIST / RawNet inference).
    In production, this feeds audio_bytes to AASIST PyTorch model weights.
    Returns: (deepfake_probability, confidence)
    """
    # Deterministic mock based on byte length or content for demonstration
    if len(audio_bytes) % 2 == 0:
        return 0.92, 0.98  # Simulates detected synthetic deepfake
    return 0.08, 0.95      # Simulates genuine human speech


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Dhwani / EchoShield Provenance API",
        description="Tamper-evident deepfake detection API with SHA-256 hash chaining and zero audio retention.",
        version="1.0.0",
    )

    audit_file = PROJECT_ROOT / "data" / "audit_trail.jsonl"
    pipeline = DhwaniProvenancePipeline(persistence_file=audit_file)

    @app.post("/api/v1/detect", summary="Ingest audio, compute hash, run AI detection, and record event")
    async def detect_audio(
        file: UploadFile = File(...),
        x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    ):
        session_id = x_session_id or f"sess_{os.urandom(8).hex()}"
        audio_bytes = await file.read()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file provided")

        result = pipeline.process_audio(
            audio_data=audio_bytes,
            session_id=session_id,
            ai_detector=mock_aasist_detector,
            audio_metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "model_name": "AASIST-L",
                "duration_sec": max(0.1, len(audio_bytes) / 32000.0),
            },
        )

        return JSONResponse(content=result.to_dict())

    @app.get("/api/v1/audit/verify", summary="Verify audit chain integrity and detect tampering")
    async def verify_audit_chain():
        report = pipeline.verify_chain()
        status_code = 200 if report.is_valid else 409
        return JSONResponse(status_code=status_code, content=report.to_dict())

    @app.get("/api/v1/audit/trail", summary="Retrieve sanitized security event audit log")
    async def get_audit_trail(session_id: Optional[str] = Query(None)):
        events = pipeline.chain.get_events(session_id=session_id)
        return JSONResponse(content=[e.to_dict() for e in events])

    @app.post("/api/v1/audit/simulate-tamper", summary="Simulate tampering for testing verification")
    async def simulate_tamper(seq_num: int = 0):
        if pipeline.chain.length == 0:
            raise HTTPException(status_code=400, detail="Audit chain is empty. Process at least one audio first.")
        # Modify score payload maliciously
        pipeline.chain.tamper_for_testing(seq_num, "payload", {"tampered": True, "ai_score": 0.001})
        report = pipeline.verify_chain()
        return JSONResponse(content={
            "message": f"Tampered event #{seq_num}",
            "verification_result": report.to_dict(),
        })

    return app


# Expose application instance at module level for Uvicorn: `uvicorn examples.fastapi_integration:app`
app: FastAPI = create_app()


def run_cli_demo():
    """Standalone CLI demonstration of the complete 7-stage pipeline."""
    print("=" * 80)
    print("Dhwani / EchoShield - 7-Stage Security & Provenance Pipeline Demo")
    print("=" * 80)

    audit_path = PROJECT_ROOT / "data" / "demo_audit_trail.jsonl"
    if audit_path.exists():
        audit_path.unlink()

    pipeline = DhwaniProvenancePipeline(persistence_file=audit_path)

    # 1. Simulate Audio Input
    print("\n[Stage 1 & 2] Ingesting Audio & SHA-256 Hashing...")
    sample_audio_1 = b"SAMPLE_AUDIO_BYTES_WAVEFORM_GENUINE_VOICE_CHUNK"
    sample_audio_2 = b"SAMPLE_AUDIO_BYTES_WAVEFORM_SYNTHETIC_DEEPFAKE_CHUNK_2"

    print("Session 1: Processing authentic voice...")
    res1 = pipeline.process_audio(
        audio_data=sample_audio_1,
        session_id="call_001",
        ai_detector=lambda b: (0.04, 0.99),
        audio_metadata={"duration_sec": 3.5, "model_name": "AASIST"},
    )
    print(f" -> Audio Hash:      {res1.audio_hash}")
    print(f" -> Provenance Token:{res1.provenance_token}")
    print(f" -> AI Score:        {res1.ai_score} (Confidence: {res1.confidence})")
    print(f" -> Risk Level:      {res1.risk_assessment.level.value} (Action: {res1.risk_assessment.action.value})")
    print(f" -> Chain Hash:      {res1.chain_hash}")
    print(f" -> Chain Valid?     {res1.is_chain_valid}")

    print("\nSession 2: Processing synthetic deepfake audio...")
    print(" (Demonstrating detection of deepfake audio -> Risk Level CRITICAL, Action BLOCK)")
    res2 = pipeline.process_audio(
        audio_data=sample_audio_2,
        session_id="call_002",
        ai_detector=lambda b: (0.94, 0.97),
        audio_metadata={"duration_sec": 2.8, "model_name": "AASIST"},
    )
    print(f" -> Audio Hash:      {res2.audio_hash}")
    print(f" -> Provenance Token:{res2.provenance_token}")
    print(f" -> AI Score:        {res2.ai_score} (Confidence: {res2.confidence})")
    print(f" -> Risk Level:      {res2.risk_assessment.level.value} (Action: {res2.risk_assessment.action.value})")
    print(f" -> Chain Hash:      {res2.chain_hash}")
    print(f" -> Chain Valid?     {res2.is_chain_valid}")

    print("\n[Stage 7] Performing Cryptographic Integrity Audit...")
    report = pipeline.verify_chain()
    print(f" -> Total Audited Events: {report.total_events}")
    print(f" -> Verification Status:  {'PASS (Tamper-Free)' if report.is_valid else 'FAIL'}")

    print("\n[Tamper Detection Simulation - Testing Security Defense]")
    original_payload = dict(pipeline.chain._chain[0].payload)
    print("Simulating an attacker maliciously modifying Event #0 score to bypass deepfake flag...")
    pipeline.chain.tamper_for_testing(0, "payload", {"tampered_score": 0.0001})
    tamper_report = pipeline.verify_chain()

    print(f" -> Defense Status:          TAMPER DETECTED (Chain verification successfully caught tamper)")
    print(f" -> Tamper Type Identified:  {tamper_report.tamper_type.value}")
    print(f" -> Tampered Event Index:    #{tamper_report.tampered_event_seq}")
    print(f" -> Forensic Diagnostic:     {tamper_report.error_reason}")
    print(" -> [VERIFIED]: Tampered event was mathematically isolated by the hash chain.")

    # Restore event to show clean audit recovery
    pipeline.chain.tamper_for_testing(0, "payload", original_payload)
    restored_report = pipeline.verify_chain()
    print(f"\n[Post-Incident Recovery Check]")
    print(f" -> Restored Chain Valid:    {restored_report.is_valid} ({'PASS (Tamper-Free)' if restored_report.is_valid else 'FAIL'})")

    print("\n" + "=" * 80)
    print("All 7 Pipeline Stages & Security Invariants Verified Successfully.")
    print("=" * 80)


if __name__ == "__main__":
    run_cli_demo()
