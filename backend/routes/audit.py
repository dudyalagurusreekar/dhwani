"""
EchoShield AI - Security & Audit Trail Router (Member 3 - Provenance Module)
Exposes endpoints to verify cryptographic audit chain integrity and query security event logs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on path for security package import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from security import get_global_pipeline

router = APIRouter(prefix="/audit", tags=["Security & Audit Provenance"])


@router.get("/verify", summary="Verify audit chain integrity and detect log tampering")
async def verify_audit_chain():
    """
    Traverses the cryptographic hash chain from the genesis block to tip.
    Mathematically verifies that no past audio detection verdicts, sequence numbers,
    or hashes have been modified, deleted, or inserted.
    """
    pipeline = get_global_pipeline()
    report = pipeline.verify_chain()
    status_code = 200 if report.is_valid else 409
    return JSONResponse(status_code=status_code, content=report.to_dict())


@router.get("/trail", summary="Retrieve sanitized security event audit log")
async def get_audit_trail(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: Optional[int] = Query(50, description="Max records to return"),
):
    """
    Returns the immutable audit ledger entries.
    Adheres strictly to privacy-by-design: contains cryptographic hashes
    and AI risk scores, but zero raw audio recordings.
    """
    pipeline = get_global_pipeline()
    events = pipeline.chain.get_events(session_id=session_id, event_type=event_type, limit=limit)
    return JSONResponse(content=[e.to_dict() for e in events])


@router.get("/latest", summary="Get the latest chain tip hash")
async def get_latest_hash():
    """Returns the current cryptographic tip hash of the audit chain."""
    pipeline = get_global_pipeline()
    return {
        "length": pipeline.chain.length,
        "latest_hash": pipeline.chain.latest_hash,
    }


@router.get("/certificate", summary="Export cryptographically sealed audit certificate")
async def get_verification_certificate():
    """
    Produces a cryptographically sealed compliance certificate with cumulative root digest.
    Used for non-repudiation attestations and third-party forensic validation.
    """
    pipeline = get_global_pipeline()
    cert = pipeline.chain.export_verification_certificate()
    return JSONResponse(content=cert)


@router.get("/session/{session_id}/summary", summary="Get forensic audit summary for a session")
async def get_session_summary(session_id: str):
    """
    Aggregates chunk history, risk trajectory, and provenance tokens for a specific session.
    """
    pipeline = get_global_pipeline()
    summary = pipeline.chain.get_session_audit_summary(session_id)
    if not summary.get("found"):
        raise HTTPException(status_code=404, detail=f"No audit records found for session {session_id}")
    return JSONResponse(content=summary)

